"""Combat regression tests use real Game actors and the ordinary damage pipeline."""
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import Game, make_item
from server import combat_rules as rules, martial_rules as martial, world_content as content
from server.martial_combat import MartialCombat


class MartialCombatTests(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def setUp(self):
        self.clock = base.Clock()
        cls = Game if issubclass(Game, MartialCombat) else type('MartialHarness', (MartialCombat, Game), {})
        self.g = cls(':memory:', clock=self.clock)
        self.g.combat_rng = base.Dice(15, 4)
        for e in self.g.enemies.values(): e.alive = False; e.respawn_at = 0
        self.g.legacy_enemies = []
        self.addCleanup(self.g.db.close)

    def hero(self, path='battle_master', choice='', pid='1', level=3):
        p = self.player('ranger' if path == 'hunter' else 'knight', level, pid)
        p.promoted = True; p.martial_archetype = path
        p.martial_state = dict(maneuvers=['precision', 'trip', 'menacing'], superiority_spent=0,
                              offense='', reaction='', hunter_choice=choice)
        return p

    def reaction(self, key='riposte'):
        p = self.hero(); p.martial_state['maneuvers'] = ['precision', 'riposte', 'parry']
        p.martial_state['reaction'] = key
        return p

    def advance(self, seconds=3.1):
        self.clock.advance(seconds)
        for p in self.g.players.values(): p.current_wall_time = self.clock()

    def equip(self, p, key):
        item = make_item(key); p.inventory.append(item); p.equipment['weapon'] = item['uid']

    def attack(self, p, e, **kwargs):
        return self.g.hit_enemy(p, e, melee=rules.gear.melee(p), **kwargs)

    def test_champion_critical_weapon_only_and_promotion_gate(self):
        p=self.hero('champion');e=self.enemy();self.g.combat_rng=base.Dice(19,4)
        weapon=self.attack(p,e)
        self.assertTrue(weapon['critical']);self.assertEqual(len(weapon['damage_rolls']),rules.weapon_dice(p)[0]*2)
        spell=self.attack(p,e,spell=True,dice=(1,8,0))
        self.assertFalse(spell['critical'])
        p.promoted=False
        self.assertFalse(self.attack(p,e)['critical'])
        p.promoted=True;self.equip(p,'mage_weapon_1')
        self.assertFalse(self.attack(p,e)['critical'])

    def test_champion_nineteen_hits_even_impossible_ac_and_scales(self):
        p=self.hero('champion');e=self.enemy();self.g.combat_rng=base.Dice(19,4)
        with patch.dict(content.ENEMIES[e.kind],armor_class=99):self.assertTrue(self.attack(p,e)['hit'])
        p.level=15;self.g.combat_rng=base.Dice(18,4)
        self.assertTrue(self.attack(p,e)['critical'])
        p.level=14;self.assertFalse(self.attack(p,e)['critical'])

    def test_precision_converts_miss_rolls_damage_once_and_spends_one(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='precision';self.g.combat_rng=base.Dice(8,4)
        with patch.dict(content.ENEMIES[e.kind],armor_class=rules.attack_bonus(p)+10):result=self.attack(p,e)
        self.assertTrue(result['hit']);self.assertEqual(result['superiority_rolls'],[4]);self.assertGreater(result['damage'],0)
        self.assertEqual(p.martial_state['superiority_spent'],1);self.assertEqual(p.martial_state['offense'],'')
        self.assertEqual(result['total'],8+rules.attack_bonus(p)+4)
        self.assertEqual(result['damage'],sum(result['damage_rolls'])+result['damage_modifier'])

    def test_precision_keeps_preparation_on_hit_or_natural_one_and_excludes_spells(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='precision'
        self.attack(p,e)
        self.g.combat_rng=base.Dice(1,4);self.attack(p,e)
        self.g.combat_rng=base.Dice(2,4);self.attack(p,e,spell=True,dice=(1,8,0))
        self.assertEqual(martial.remaining(p),4);self.assertEqual(p.martial_state['offense'],'precision')

    def test_precision_cannot_add_twice_or_supply_extra_damage(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='precision';self.g.combat_rng=base.Dice(3,1)
        result=self.attack(p,e)
        self.assertFalse(result['hit']);self.assertEqual(result['damage'],0)
        p.martial_state['offense']='precision'
        self.g.martial_precision(p,e,result,rules.weapon_dice(p))
        self.assertEqual(martial.remaining(p),3)

    def test_precision_resolves_after_shield_with_correct_new_damage(self):
        p=self.hero();q=self.player('mage',5,'2');q.x=p.x+70;p.pvp_safety=False;q.shield_armed=True
        p.martial_state['offense']='precision'
        initial=q.armor_class-rules.attack_bonus(p)+1
        self.assertGreater(initial,1);self.assertLess(initial,19)
        self.g.combat_rng=base.Dice(initial,4);before=q.hp
        result=self.g.hit_player(p,q,pvp=True)
        self.assertTrue(result['shielded']);self.assertTrue(result['shield_overcome']);self.assertTrue(result['hit'])
        self.assertGreater(before-q.hp,0);self.assertEqual(result['defense'],q.armor_class)
        self.assertEqual(martial.remaining(p),3)

    def test_precision_before_shield_cannot_spend_again(self):
        p=self.hero();q=self.player('mage',5,'2');q.x=p.x+70;p.pvp_safety=False;q.shield_armed=True
        p.martial_state['offense']='precision';self.g.combat_rng=base.Dice(q.armor_class-rules.attack_bonus(p)-1,4)
        result=self.g.hit_player(p,q,pvp=True)
        self.assertTrue(result['shielded']);self.assertFalse(result['hit']);self.assertEqual(martial.remaining(p),3)

    def test_trip_adds_die_and_save_uses_strength_or_dexterity(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='trip'
        with patch.object(self.g,'target_save',return_value=dict(saved=False,hit=False,damage=0)) as save:
            result=self.attack(p,e)
        self.assertEqual(result['superiority_rolls'],[4]);self.assertEqual(martial.remaining(p),3)
        self.assertIn('prone',e.conditions)
        self.assertEqual(save.call_args.args[1],'strength')
        self.assertEqual(save.call_args.args[2],8+rules.proficiency(p)+max(rules.ability_modifier(p,'strength'),rules.ability_modifier(p,'dexterity')))

    def test_trip_huge_target_gets_damage_without_prone_or_save(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='trip'
        with patch.dict(content.ENEMIES[e.kind],size='huge'),patch.object(self.g,'target_save') as save:
            result=self.attack(p,e)
        self.assertEqual(result['superiority_rolls'],[4]);save.assert_not_called();self.assertNotIn('prone',e.conditions)

    def test_trip_critical_doubles_superiority_die(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='trip';self.g.combat_rng=base.Dice(20,4)
        result=self.attack(p,e)
        self.assertEqual(result['superiority_rolls'],[4,4]);self.assertEqual(martial.remaining(p),3)

    def test_menacing_status_immune_save_and_exact_duration(self):
        p=self.hero();e=self.enemy();p.martial_state['offense']='menacing';self.g.begin_action(p)
        with patch.object(self.g,'target_save',return_value=dict(saved=False,hit=False,damage=0)):
            result=self.attack(p,e)
        self.assertEqual(result['martial_maneuver'],'menacing');self.assertEqual(e.conditions['frightened']['until'],self.clock()+6)
        self.assertTrue(self.g.environment_attack_flags(e,p)[0])
        self.assertTrue(self.g.blocked_for(e,e.x-5,e.y))
        with patch.object(self.g,'environment_can_see',return_value=False):self.assertFalse(self.g.martial_frightened(e))
        self.advance(6.1);self.assertFalse(self.g.martial_frightened(e))
        p.martial_state['offense']='menacing'
        with patch.dict(content.ENEMIES[e.kind],condition_immunities=['frightened']),patch.object(self.g,'target_save',return_value=dict(saved=False,hit=False,damage=0)):
            e.conditions={};self.attack(p,e)
        self.assertNotIn('frightened',e.conditions)

    def test_fear_disadvantages_ability_checks_and_forced_movement_allowed(self):
        p=self.hero();q=self.player('knight',3,'2');q.x=p.x+70;p.pvp_safety=False
        q.buffs['frightened']=dict(until=self.clock()+6,owner=p.id)
        result=self.g.environment_ability_check(q,'strength',10)
        self.assertEqual(len(result['rolls']),2)
        self.assertTrue(self.g.blocked_for(q,q.x-5,q.y))
        q._environment_forced=True
        with patch.object(self.g,'blocked',return_value=False):self.assertFalse(self.g.blocked_for(q,q.x-5,q.y))

    def test_parry_reduces_melee_before_resistance_uses_reaction_and_die(self):
        p=self.reaction('parry');e=self.enemy();p.hp=100;p.buffs['stoneskin']=dict(until=self.clock()+30)
        self.g.combat_rng=base.Dice(19,4)
        result=self.g.hit_player(e,p,dice=(2,8,2),melee=True)
        reduction=4+rules.ability_modifier(p,'dexterity')
        self.assertEqual(result['parry_reduction'],reduction)
        self.assertEqual(p.hp,100-int((10-reduction)*.5));self.assertEqual(martial.remaining(p),3)
        self.assertEqual(p.reaction_ready,self.clock()+3)
        result=self.g.hit_player(e,p,dice=(2,8,2),melee=True)
        self.assertNotIn('parry_reduction',result);self.assertEqual(martial.remaining(p),3)

    def test_parry_excludes_miss_ranged_saves_and_no_reaction(self):
        for mode in ('miss','ranged','area','no_reactions','incapacitated','dead'):
            with self.subTest(mode=mode):
                p=self.reaction('parry');e=self.enemy();p.hp=999
                self.g.combat_rng=base.Dice(1 if mode=='miss' else 19,4)
                if mode in ('no_reactions','incapacitated'):p.buffs[mode]=dict(until=self.clock()+3)
                if mode=='dead':p.hp=0
                result=self.g.hit_player(e,p,dice=(1,8,0),melee=mode!='ranged',area=mode=='area')
                self.assertEqual(martial.remaining(p),4)
                if result:self.assertNotIn('parry_reduction',result)

    def test_parry_covers_melee_spell_attack_and_mixed_damage_only_once(self):
        p=self.reaction('parry');e=self.enemy();p.hp=999
        result=dict(check='attack',hit=True,is_melee=True,is_spell=True,damage=10,damage_type='slashing',damage_components=[dict(type='slashing',damage=3),dict(type='fire',damage=7)])
        self.g.martial_parry(e,p,result)
        self.assertEqual(result['damage'],sum(c['damage'] for c in result['damage_components']))
        self.assertEqual(result['damage_components'][0]['damage'],0);self.assertEqual(martial.remaining(p),3)

    def test_riposte_melee_miss_rolls_independent_attack_without_main_action(self):
        p=self.reaction();e=self.enemy();self.g.combat_rng=base.Dice(1,4)
        cooldown=p.attack_cooldown_until
        result=self.g.hit_player(e,p,melee=True)
        self.assertFalse(result['hit']);self.assertEqual(martial.remaining(p),3)
        self.assertEqual(p.last_roll['action'],'Riposta');self.assertFalse(p.last_roll['hit'])
        self.assertEqual(p.attack_cooldown_until,cooldown);self.assertEqual(p.reaction_ready,self.clock()+3)

    def test_riposte_hit_adds_die_and_does_not_use_armed_offense(self):
        p=self.reaction();e=self.enemy();p.martial_state['offense']='precision'
        self.g.combat_rng=base.Dice(15,4)
        self.g.martial_after_incoming_attack(e,p,dict(check='attack',hit=False,is_melee=True))
        self.assertTrue(p.last_roll['hit']);self.assertEqual(p.last_roll['superiority_rolls'],[4])
        self.assertEqual(martial.remaining(p),3);self.assertEqual(p.martial_state['offense'],'precision')

    def test_riposte_validates_weapon_range_visibility_floor_safety_and_state(self):
        for lock in ('bow','far','blind','floor','safe','dead','reaction','empty'):
            with self.subTest(lock=lock):
                p=self.reaction();e=self.enemy()
                if lock=='bow':self.equip(p,'ranger_weapon_1')
                if lock=='far':e.x=p.x+200
                if lock=='blind':p.buffs['blind']=dict(until=self.clock()+30)
                if lock=='floor':e.floor=-99
                if lock=='safe':p.x=content.CITIES[0]['x'];p.y=content.CITIES[0]['y'];e.x=p.x+20;e.y=p.y
                if lock=='dead':p.hp=0
                if lock=='reaction':p.reaction_ready=self.clock()+3
                if lock=='empty':p.martial_state['superiority_spent']=4
                remaining=martial.remaining(p);before=e.hp
                self.g.martial_after_incoming_attack(e,p,dict(check='attack',hit=False,is_melee=True))
                self.assertEqual(e.hp,before);self.assertEqual(martial.remaining(p),remaining)

    def test_colossus_requires_prehit_wound_and_once_per_turn_critical(self):
        p=self.hero('hunter','colossus_slayer');e=self.enemy();e.hp=e.max_hp
        result=self.attack(p,e);self.assertNotIn('colossus_rolls',result)
        result=self.attack(p,e);self.assertEqual(result['colossus_rolls'],[4])
        result=self.attack(p,e);self.assertNotIn('colossus_rolls',result)
        self.advance();self.g.combat_rng=base.Dice(20,4)
        e.hp=e.max_hp-1;result=self.attack(p,e);self.assertEqual(result['colossus_rolls'],[4,4])

    def test_colossus_excludes_spells_and_focus(self):
        p=self.hero('hunter','colossus_slayer');e=self.enemy();e.hp=e.max_hp-1
        result=self.attack(p,e,spell=True,dice=(1,4,0));self.assertNotIn('colossus_rolls',result)
        self.equip(p,'mage_weapon_1');result=self.attack(p,e);self.assertNotIn('colossus_rolls',result)

    async def test_horde_after_miss_separate_roll_once_and_same_weapon(self):
        p=self.hero('hunter','horde_breaker');e=self.enemy(x=p.x+150);other=self.enemy('second',x=e.x+20)
        self.g.combat_rng=base.Dice(1,4)
        await self.g.dnd_attack(p,enemy_id=e.id)
        self.assertEqual(self.g.combat_rng.checks,2)
        self.assertEqual(p.last_roll['action'],'Rozbijacz hord');self.assertEqual(p.attack_cooldown_until,self.clock()+3)
        self.assertFalse(p.last_roll['hit']);self.assertEqual(p.martial_state['horde_until'],self.clock()+3)
        self.g.martial_horde_breaker(p,e);self.assertEqual(self.g.combat_rng.checks,2)

    async def test_horde_one_tile_limit_and_no_third_attack(self):
        p=self.hero('hunter','horde_breaker');e=self.enemy(x=p.x+150);second=self.enemy('second',x=e.x+64);third=self.enemy('third',x=e.x+63)
        before=[q.hp for q in (e,second,third)]
        await self.g.dnd_attack(p,enemy_id=e.id)
        self.assertEqual(sum(q.hp<b for q,b in zip((e,second,third),before)),2)
        self.assertEqual(self.g.combat_rng.checks,2)
        self.advance();second.x=e.x+65;third.floor=-99
        self.assertIsNone(self.g.martial_horde_breaker(p,e))

    def test_horde_does_not_attack_uninvolved_party_safe_or_different_floor_players(self):
        p=self.hero('hunter','horde_breaker');e=self.enemy();q=self.player('knight',3,'2');q.x=e.x+10;p.pvp_safety=False
        self.assertIsNone(self.g.martial_horde_breaker(p,e))
        p.aggressors[q.id]=self.clock()+20;q.floor=-99
        self.assertIsNone(self.g.martial_horde_breaker(p,e))
        q.floor=p.floor;p.party_id=q.party_id='party'
        self.assertIsNone(self.g.martial_horde_breaker(p,e))
        p.party_id=q.party_id='';q.pvp_safety=False
        before=q.hp;self.assertIs(self.g.martial_horde_breaker(p,e),q);self.assertLess(q.hp,before)

    def test_horde_checks_secondary_weapon_range_and_wall(self):
        p=self.hero('hunter','horde_breaker');e=self.enemy(x=p.x+300);other=self.enemy('other',x=p.x+320)
        self.assertIsNone(self.g.martial_horde_breaker(p,e))
        other.x=e.x+5
        with patch.object(self.g,'line_clear',return_value=False):self.assertIsNone(self.g.martial_horde_breaker(p,e))
        self.assertEqual(p.martial_state.get('horde_until',0),0)

    def test_giant_killer_after_hit_or_miss_once_reaction_within_five_feet(self):
        for hit in (True,False):
            with self.subTest(hit=hit):
                p=self.hero('hunter','giant_killer');e=self.enemy(x=p.x+30);p.hp=999
                with patch.dict(content.ENEMIES[e.kind],size='large'):
                    before=e.hp;cooldown=p.attack_cooldown_until
                    self.g.martial_after_incoming_attack(e,p,dict(check='attack',hit=hit,is_melee=True))
                    self.assertLess(e.hp,before);self.assertEqual(p.last_roll['action'],'Zabójca olbrzymów')
                    after=e.hp;self.g.martial_after_incoming_attack(e,p,dict(check='attack',hit=hit,is_melee=True))
                    self.assertEqual(e.hp,after);self.assertEqual(p.attack_cooldown_until,cooldown)

    def test_giant_killer_rejects_small_distant_hidden_dead_and_save_sources(self):
        for lock in ('small','distant','blind','dead','save','floor','pvp_safety'):
            with self.subTest(lock=lock):
                p=self.hero('hunter','giant_killer');e=self.enemy(x=p.x+30)
                source=e
                if lock=='distant':e.x=p.x+33
                if lock=='blind':p.buffs['blind']=dict(until=self.clock()+3)
                if lock=='dead':p.hp=0
                if lock=='floor':e.floor=-99
                if lock=='pvp_safety':source=self.player('druid',3,'2');source.x=p.x+25;source.form='bear'
                before=source.hp
                with patch.dict(content.ENEMIES[e.kind],size='medium' if lock=='small' else 'large'):
                    self.g.martial_after_incoming_attack(source,p,dict(check='save' if lock=='save' else 'attack',hit=True,is_melee=True))
                self.assertEqual(source.hp,before);self.assertEqual(p.reaction_ready,0)

    def test_reactive_attacks_enforce_depth_failsafe_and_exclude_companions(self):
        p=self.reaction();e=self.enemy();self.g._martial_extra_depth=32
        self.g.martial_after_incoming_attack(e,p,dict(check='attack',hit=False,is_melee=True))
        self.assertEqual(martial.remaining(p),4)
        self.g._martial_extra_depth=0
        p.martial_archetype='hunter';p.martial_state['hunter_choice']='giant_killer'
        from types import SimpleNamespace
        pet=SimpleNamespace(id='pet',x=p.x+20,y=p.y,floor=p.floor,alive=True,hp=100)
        self.g.martial_after_incoming_attack(pet,p,dict(check='attack',hit=False,is_melee=True))
        self.assertEqual(pet.hp,100)


if __name__ == '__main__': unittest.main()
