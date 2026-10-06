"""Live Light/Thrown/Unarmed actions, grapples and save/reload ownership."""
import json
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import Player, make_item
from server import combat_rules as rules, weapon_actions as weapons


class StyleWeaponsGame(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    def equip(self,p,template,slot='weapon'):
        item=make_item(template);p.inventory.append(item);p.equipment[slot]=item['uid']
        return item

    def advance(self,seconds=3.1):
        self.clock.advance(seconds);self.g.time+=seconds

    def ranger(self,style='',level=3):
        p=self.player('ranger',level);p.fighting_style=style
        p.equipment['weapon']=p.equipment['shield']=p.equipment['offhand']=''
        return p

    async def test_main_attack_miss_unlocks_exactly_one_independently_rolled_light_attack(self):
        p=self.ranger('two_weapon');self.equip(p,'training_dagger');self.equip(p,'training_scimitar','offhand')
        e=self.enemy(x=p.x+60);self.g.combat_rng=base.Dice(1,3)
        await self.g.dnd_attack(p,enemy_id=e.id)
        self.assertEqual(e.hp,999);main_ready=p.attack_cooldown_until;token=p._feat_turn_until
        self.g.combat_rng=base.Dice(15,3)
        result=await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertTrue(result['hit']);self.assertEqual(result['damage_modifier'],3)
        self.assertEqual(e.hp,993);self.assertEqual(p._feat_turn_until,token)
        self.assertEqual(p.attack_cooldown_until,main_ready)
        before=e.hp;await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertEqual(e.hp,before)

    async def test_other_style_gets_light_attack_without_positive_modifier_and_bonus_spell_blocks_it(self):
        p=self.ranger('archery');self.equip(p,'training_dagger');self.equip(p,'training_scimitar','offhand')
        e=self.enemy(x=p.x+60)
        await self.g.dnd_attack(p,enemy_id=e.id)
        result=await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertEqual(result['damage_modifier'],0)
        self.advance();await self.g.dnd_attack(p,enemy_id=e.id)
        p.bonus_cooldown_until=self.clock()+3
        before=e.hp;await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertEqual(e.hp,before)

    async def test_invalid_light_target_never_spends_bonus_or_deals_damage(self):
        p=self.ranger('two_weapon');self.equip(p,'training_dagger');self.equip(p,'training_handaxe','offhand')
        e=self.enemy(x=p.x+60);await self.g.dnd_attack(p,enemy_id=e.id)
        e.x=p.x+500;ready=p.bonus_cooldown_until
        await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertEqual(p.bonus_cooldown_until,ready)
        e.x=p.x+60
        with patch.object(self.g,'line_clear',return_value=False):await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertEqual(p.bonus_cooldown_until,ready)

    async def test_thrown_offhand_uses_ranged_disadvantage_and_distance_training(self):
        p=self.ranger('thrown_weapon');self.equip(p,'training_dagger');other=self.equip(p,'training_handaxe','offhand')
        p.weapon_attack_mode='throw';e=self.enemy(x=p.x+30)
        await self.g.dnd_attack(p,enemy_id=e.id)
        before=p.skill_tries.get('distance',0);melee_before=p.skill_tries.get('melee',0)
        self.g.combat_rng=base.Dice(15,3)
        result=await self.g.offhand_attack(p,enemy_id=e.id)
        self.assertTrue(result['disadvantage']);self.assertEqual(len(result['rolls']),2)
        self.assertEqual(p.skill_tries.get('distance',0),before+1)
        self.assertEqual(p.skill_tries.get('melee',0),melee_before)
        self.assertIn(other['uid'],{row['item']['uid'] for row in p.thrown_weapons})

    def test_thrown_close_threat_uses_five_feet_without_regular_weapon_radius(self):
        p=self.ranger('thrown_weapon');self.equip(p,'training_dagger');p.weapon_attack_mode='throw'
        e=self.enemy(x=p.x+32);self.g.combat_rng=base.Dice(15,3)
        result=self.g.hit_enemy(p,e,melee=False)
        self.assertTrue(result['disadvantage']);self.assertEqual(len(result['rolls']),2)
        e.x=p.x+40;self.g.combat_rng=base.Dice(15,3)
        result=self.g.hit_enemy(p,e,melee=False)
        self.assertFalse(result['disadvantage']);self.assertEqual(len(result['rolls']),1)

    async def test_thrown_horde_breaker_cannot_reuse_the_released_weapon(self):
        p=self.ranger('thrown_weapon');p.promoted=True;p.martial_archetype='hunter'
        p.martial_state={'hunter_choice':'horde_breaker'}
        item=self.equip(p,'training_dagger');p.weapon_attack_mode='throw'
        e=self.enemy(x=p.x+100);other=self.enemy('secondary',x=p.x+120)
        self.g.combat_rng=base.Dice(15,3)
        await self.g.dnd_attack(p,enemy_id=e.id)
        self.assertLess(e.hp,999);self.assertEqual(other.hp,999)
        self.assertEqual(self.g.combat_rng.checks,1)
        self.assertEqual(p.thrown_weapons[0]['item']['uid'],item['uid'])

    async def test_thrown_extra_attacks_release_each_uid_then_save_reload_and_recover(self):
        p=self.ranger('thrown_weapon',5);first=self.equip(p,'training_dagger')
        spare=make_item('training_dagger');p.inventory.append(spare)
        e=self.enemy(x=p.x+150);p.weapon_attack_mode='throw';self.g.combat_rng=base.Dice(15,3)
        self.account(p)
        await self.g.dnd_attack(p,enemy_id=e.id)
        self.assertEqual({row['item']['uid'] for row in p.thrown_weapons},{first['uid'],spare['uid']})
        self.assertEqual(p.equipment['weapon'],'')
        restored=self.g.load_player(p.id,p.name,p.ws,json.loads(json.dumps(p.save_data())))
        self.assertEqual({row['item']['uid'] for row in restored.thrown_weapons},{first['uid'],spare['uid']})
        restored.x=e.x;restored.y=e.y
        await self.g.recover_weapon(restored,first['uid'])
        self.assertEqual(sum(i['uid']==first['uid'] for i in restored.inventory),1)
        self.assertEqual(len(restored.thrown_weapons),1)
        await self.g.recover_weapon(restored,first['uid'])
        self.assertEqual(sum(i['uid']==first['uid'] for i in restored.inventory),1)

    async def test_unarmed_style_uses_strength_correct_die_and_five_foot_reach(self):
        p=self.ranger('unarmed')
        self.assertEqual(rules.attack_range(p),32)
        p.weapon_attack_mode='unarmed'
        self.assertEqual(rules.weapon_dice(p)[:2],(1,8));self.assertEqual(rules.attack_ability(p),'strength')
        self.equip(p,'training_dagger');self.assertEqual(rules.weapon_dice(p)[:2],(1,6))
        e=self.enemy(x=p.x+33);before=e.hp
        await self.g.dnd_attack(p,enemy_id=e.id);self.assertEqual(e.hp,before)
        e.x=p.x+32;await self.g.dnd_attack(p,enemy_id=e.id);self.assertLess(e.hp,before)

    async def test_grapple_is_target_save_and_unarmed_damage_ticks_once_per_own_turn(self):
        p=self.ranger('unarmed');e=self.enemy(x=p.x+30);self.g.combat_rng=base.Dice(1,4)
        result=await self.g.grapple_attack(p,enemy_id=e.id)
        self.assertEqual(result['check'],'save');self.assertFalse(result['saved'])
        self.assertEqual(e.conditions['grappled']['owner'],p.id)
        self.assertNotIn('restrained',e.conditions);self.assertEqual(e.hp,999)
        self.advance();self.g.style_weapon_update();self.assertEqual(e.hp,995)
        self.g.style_weapon_update();self.g.style_weapon_begin_turn(p);self.assertEqual(e.hp,995)
        self.advance();self.g.style_weapon_update();self.assertEqual(e.hp,991)

    async def test_unarmed_grapple_damage_never_applies_without_the_selected_style(self):
        p=self.ranger('defense');e=self.enemy(x=p.x+30);self.g.combat_rng=base.Dice(1,4)
        await self.g.grapple_attack(p,enemy_id=e.id)
        self.advance();self.g.style_weapon_update();self.assertEqual(e.hp,999)

    async def test_grapple_replaces_one_attack_and_preserves_extra_attack(self):
        p=self.ranger('unarmed',5);e=self.enemy(x=p.x+30);self.g.combat_rng=base.Dice(1,4)
        await self.g.grapple_attack(p,enemy_id=e.id)
        self.assertEqual(self.g.combat_rng.checks,2)  # save, then independent Unarmed Strike
        self.assertEqual(p.last_roll['check'],'attack')
        self.assertEqual(p.attack_cooldown_until,self.clock()+3)

    async def test_grapple_free_hand_size_range_and_pvp_safety_are_authoritative(self):
        p=self.ranger('unarmed');e=self.enemy(x=p.x+30)
        self.equip(p,'training_dagger');self.equip(p,'wooden_shield','shield')
        await self.g.grapple_attack(p,enemy_id=e.id);self.assertNotIn('grappled',e.conditions)
        p.equipment['shield']=''
        with patch.dict(base.ENEMY_TYPES[e.kind],size='huge'):
            await self.g.grapple_attack(p,enemy_id=e.id);self.assertNotIn('grappled',e.conditions)
        e.x=p.x+33;await self.g.grapple_attack(p,enemy_id=e.id);self.assertNotIn('grappled',e.conditions)
        target=self.player('ranger',3,'2');target.x=p.x+30
        await self.g.grapple_attack(p,target_id=target.id);self.assertNotIn('grappled',target.buffs)

    async def test_grapple_does_not_steal_main_action_from_a_queued_spell(self):
        p=self.ranger('unarmed');e=self.enemy(x=p.x+30)
        p.pending_spell=dict(until=self.clock()+3)
        await self.g.grapple_attack(p,enemy_id=e.id)
        self.assertEqual(p.attack_cooldown_until,0)
        self.assertNotIn('grappled',e.conditions)

    async def test_grapple_cleanup_escape_action_and_dragging_cost(self):
        p=self.ranger('unarmed');e=self.enemy(x=p.x+30);self.g.combat_rng=base.Dice(1,4)
        normal=p.speed;await self.g.grapple_attack(p,enemy_id=e.id)
        self.assertAlmostEqual(p.speed,normal*.5)
        old=(e.x,e.y);self.g.move(p,5,0);self.assertEqual((e.x,e.y),(old[0]+5,old[1]))
        self.advance();self.g.combat_rng=base.Dice(20,4);self.g.style_weapon_update()
        self.assertNotIn('grappled',e.conditions);self.assertGreater(e.ready,self.g.time)
        self.assertAlmostEqual(p.speed,normal)
        self.advance();e.x=p.x+30;self.g.combat_rng=base.Dice(1,4)
        await self.g.grapple_attack(p,enemy_id=e.id);e.x=p.x+33
        self.g.style_weapon_update();self.assertNotIn('grappled',e.conditions)

    async def test_human_can_escape_non_beast_grapple_via_existing_spell_action(self):
        p=self.ranger('unarmed');p.pvp_safety=False
        target=self.player('ranger',3,'2');target.x=p.x+30;target.pvp_safety=False
        self.g.combat_rng=base.Dice(1,3)
        await self.g.grapple_attack(p,target_id=target.id)
        self.assertEqual(target.buffs['grappled']['owner'],p.id)
        self.advance();self.g.combat_rng=base.Dice(20,3)
        await self.g.cast_spell(target,'escape_grapple')
        self.assertNotIn('grappled',target.buffs)
        self.assertEqual(target.attack_cooldown_until,self.clock()+3)


if __name__=='__main__':unittest.main()
