"""Gameplay regressions for SRD magic equipment and instance-bound attunement."""
import copy
import unittest
import test_dnd as base
from server.server import Game, ITEMS, make_item
from server import magic_items as magic, combat_rules as rules, environment_rules as env


class MagicItems(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    enemy=base.GameRules.enemy

    def setUp(self):
        magic.configure(ITEMS)
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice(10,4)
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[]

    def tearDown(self):self.g.db.close()

    def give(self,p,key,attuned=False,equipped=True):
        item=make_item(key);p.inventory.append(item)
        if equipped:p.equipment[item['slot']]=item['uid']
        if attuned:
            records=list(getattr(p,'magic_attunements',[]))
            records.append(dict(uid=item['uid'],template=key,away_since=None))
            p.magic_attunements=records
        return item

    def test_protection_requires_attunement_and_applies_to_all_saves(self):
        p=self.player();ac=p.armor_class;saves={a:rules.save_bonus(p,a) for a in p.spec['attributes']}
        item=self.give(p,'ring_protection')
        self.assertEqual(p.armor_class,ac)
        p.magic_attunements=[dict(uid=item['uid'],template=item['template'])]
        self.assertEqual(p.armor_class,ac+1)
        for a,before in saves.items():self.assertEqual(rules.save_bonus(p,a),before+1)
        p.form='wolf';self.assertEqual(magic.effect(p,'protection'),0)

    def test_resistance_is_immediate_and_does_not_stack(self):
        p=self.player();self.give(p,'ring_resistance_fire')
        self.assertEqual(rules.resistance_multiplier(p,'fire'),.5)
        p.buffs['resist_fire']=dict(until=self.clock()+30)
        self.assertEqual(rules.resistance_multiplier(p,'fire'),.5)
        self.assertEqual(rules.resistance_multiplier(p,'cold'),1)

    def test_free_action_blocks_spells_but_not_physical_grapples_or_poison(self):
        p=self.player();self.give(p,'ring_free_action',attuned=True)
        before=p.speed
        p.buffs['restrained']=dict(until=self.clock()+30,spell_id='ensnaring_strike')
        p.buffs['paralyzed']=dict(until=self.clock()+30,spell_id='hold_person')
        p.buffs['difficult_terrain']=dict(until=self.clock()+30)
        self.assertEqual(p.speed,before);self.assertFalse(env.incapacitated(p))
        self.assertFalse(self.g.apply_status(p,p,'web_restrained',30,{'id':'web'},hostile=False))
        p.buffs['paralyzed']=dict(until=self.clock()+30,source='ghoul_claws')
        self.assertTrue(env.incapacitated(p))
        p.buffs.clear();p.buffs['grappled']=dict(until=self.clock()+30,source='grick')
        self.assertEqual(p.speed,0)

    def test_warmth_uses_two_d8_before_resistance_and_no_unrelated_damage(self):
        p=self.player();self.give(p,'ring_warmth',attuned=True)
        rng=base.Dice(10,4)
        self.assertEqual(magic.reduce_damage(p,20,'cold',rng),12)
        self.assertEqual(magic.reduce_damage(p,7,'cold',rng),0)
        self.assertEqual(magic.reduce_damage(p,20,'fire',rng),20)
        p.magic_attunements=[];self.assertEqual(magic.reduce_damage(p,20,'cold',rng),20)

    def test_swim_speed_forty_does_not_grant_water_breathing(self):
        p=self.player();p.x,p.y=5880,8150
        self.assertEqual(env.movement_speed(p,90),45)
        self.give(p,'ring_swimming')
        self.assertTrue(env.swimming(p));self.assertEqual(env.movement_speed(p,90),120)
        self.assertFalse(env.active(p,'water_breathing'))
        p.form='wolf';self.assertEqual(env.movement_speed(p,90),45)

    def test_adamantine_changes_natural_twenty_to_normal_hit_not_miss(self):
        p=self.player('knight',80);self.give(p,'adamantine_chain_mail')
        enemy=self.enemy();self.g.combat_rng=base.Dice(20,4)
        result=self.g.hit_player(enemy,p,dice=(2,6,3))
        self.assertTrue(result['hit']);self.assertFalse(result['critical'])
        self.assertTrue(result['critical_prevented']);self.assertEqual(result['damage_rolls'],[4,4])
        self.assertEqual(result['damage'],11)
        p.buffs['unconscious']=dict(until=self.clock()+10);enemy.x=p.x+20
        self.g.combat_rng=base.Dice(19,4)
        result=self.g.hit_player(enemy,p,dice=(2,6,3))
        self.assertFalse(result['critical']);self.assertEqual(result['damage_rolls'],[4,4])

    def test_magic_weapon_shield_and_armor_have_separate_legal_bonuses(self):
        p=self.player();p.equipment={};p.inventory=[]
        self.give(p,'magic_longsword_1')
        self.assertEqual(rules.attack_bonus(p),rules.proficiency(p)+rules.ability_modifier(p,'strength')+1)
        self.assertEqual(rules.weapon_dice(p),(1,8,rules.ability_modifier(p,'strength')+1))
        self.give(p,'magic_chain_mail_1');self.give(p,'magic_shield_1')
        self.assertEqual(p.armor_class,20)
        self.give(p,'ring_protection',attuned=True);self.assertEqual(p.armor_class,21)

    def test_mithral_removes_strength_and_stealth_penalties(self):
        p=self.player('mage');self.give(p,'adamantine_chain_mail')
        self.assertGreater(rules.gear.armor_speed_penalty(p),0)
        result=self.g.environment_ability_check(p,'dexterity',10,'stealth')
        self.assertEqual(len(result['rolls']),2)
        self.give(p,'mithral_chain_mail');self.assertEqual(rules.gear.armor_speed_penalty(p),0)
        result=self.g.environment_ability_check(p,'dexterity',10,'stealth')
        self.assertEqual(len(result['rolls']),1)

    async def test_attunement_requires_completed_uninterrupted_short_rest(self):
        p=self.player();item=self.give(p,'ring_protection')
        await magic.command(self.g,p,dict(action='attune',uid=item['uid']))
        self.assertTrue(p.rest_state);self.assertFalse(magic.effect(p,'protection'))
        interrupted=dict(p.rest_state);self.g.cancel_rest(p,'')
        self.clock.advance(11);self.g.tick_rest(p)
        self.assertFalse(magic.effect(p,'protection'))
        p.rest_resources.clear()
        await magic.command(self.g,p,dict(action='attune',uid=item['uid']))
        rest=dict(p.rest_state);self.clock.advance(11);p.current_wall_time=self.clock()
        self.assertIn('ukończone',magic.finish_rest(p,rest))
        self.assertEqual(magic.effect(p,'protection'),1)
        self.assertTrue(magic.attunement_error(p,item['uid'],'attune'))
        self.assertTrue(interrupted['magic_item'])

    def test_limit_duplicate_copies_death_and_twenty_four_hour_separation(self):
        p=self.player();a=self.give(p,'ring_protection',attuned=True)
        duplicate=self.give(p,'ring_protection',equipped=False)
        self.assertIn('egzemplarzy',magic.attunement_error(p,duplicate['uid'],'attune'))
        self.give(p,'ring_warmth',attuned=True,equipped=False)
        self.give(p,'ring_free_action',attuned=True,equipped=False)
        self.assertEqual(magic.sheet(p)['used'],3)
        magic.maintain(p,self.clock());p.inventory.remove(a);p.equipment['ring']=''
        p.x+=1000;magic.maintain(p,self.clock())
        self.clock.advance(magic.DAY_SECONDS-1);magic.maintain(p,self.clock())
        self.assertEqual(len(p.magic_attunements),3)
        self.clock.advance(1);magic.maintain(p,self.clock());self.assertEqual(len(p.magic_attunements),2)
        magic.on_death(p);self.assertEqual(p.magic_attunements,[])

    def test_legacy_ring_migration_preserves_uid_but_removes_invented_attack_bonus(self):
        p=self.player();item=self.give(p,'hunter_ring');uid=item['uid']
        item.update(attack=99,ac_bonus=99)
        magic.migrate(p,ITEMS)
        self.assertEqual(item['uid'],uid);self.assertEqual(item['attack'],0);self.assertEqual(item['ac_bonus'],0)
        self.assertEqual(item['magic_id'],'ring_protection');self.assertFalse(magic.effect(p,'protection'))
        magic.configure(ITEMS);self.assertEqual(ITEMS['winter_ring']['magic_id'],'ring_resistance_cold')

    def test_native_monster_flight_and_polymorph_replace_movement(self):
        from server import world_content as content
        key='magic_test_flyer';content.ENEMIES[key]=dict(walking_speed_ft=10,fly=60,speed=32,armor_class=12)
        try:
            enemy=self.enemy(kind=key);enemy.current_wall_time=self.clock()
            self.assertTrue(env.flying(enemy));self.assertEqual(env.movement_speed(enemy,32),192)
            enemy.conditions['polymorph']=dict(until=self.clock()+10,form='wolf')
            self.assertFalse(env.flying(enemy))
        finally:content.ENEMIES.pop(key,None)

    def test_whole_coin_trade_and_returned_item_do_not_bypass_rest_contact(self):
        staff=ITEMS['magic_quarterstaff_1']
        self.assertEqual(staff['srd_value_gp'],400.2)
        self.assertEqual((staff['price'],staff['value']),(401,400))
        self.assertTrue(all(type(i['price']) is int and type(i['value']) is int for i in magic.CATALOG.values()))
        p=self.player();item=self.give(p,'ring_protection')
        p.rest_state=dict(kind='short',magic_item=dict(action='attune',uid=item['uid']))
        p.inventory.remove(item);magic.maintain(p,self.clock());p.inventory.append(item)
        self.assertIn('Przerwano',magic.finish_rest(p,p.rest_state))
        self.assertFalse(magic.effect(p,'protection'))


if __name__=='__main__':unittest.main()
