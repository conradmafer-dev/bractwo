"""Owned Light/Thrown/Unarmed actions: hand limits, turn gates and exact UIDs."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from server.server import Player, ITEMS, make_item
from server import equipment_rules as gear, weapon_actions as weapons


class WeaponActions(unittest.TestCase):
    def player(self):
        return Player('owner','Łowca',class_id='ranger',level=7,x=1000,y=1000,floor=0)

    def equip(self,p,template,slot='weapon'):
        item=make_item(template);p.inventory.append(item);p.equipment[slot]=item['uid']
        return item

    def test_light_offhand_needs_distinct_owned_weapons_and_two_free_hands(self):
        p=self.player();main=self.equip(p,'training_dagger')
        self.assertTrue(gear.equip_offhand(p,main['uid']))
        other=make_item('training_handaxe');p.inventory.append(other)
        self.assertEqual(gear.equip_offhand(p,other['uid']),'')
        self.assertEqual(p.equipment['offhand'],other['uid'])
        p.equipment['offhand']='';self.equip(p,'wooden_shield','shield')
        self.assertTrue(gear.equip_offhand(p,other['uid']))
        self.assertEqual(p.equipment['offhand'],'')
        p.equipment['shield']='';self.equip(p,'training_greatsword')
        self.assertTrue(gear.equip_offhand(p,other['uid']))
        self.assertTrue(gear.equip_offhand(p,'foreign_uid'))

    def test_extra_light_attack_qualifies_on_attempt_uses_existing_turn_bonus_once(self):
        p=self.player();main=self.equip(p,'training_dagger');self.equip(p,'training_handaxe','offhand')
        p._feat_turn_until=103
        self.assertTrue(weapons.offhand_error(p,100))
        self.assertFalse(weapons.record_light_attack(p,main,100,main_action=False))
        self.assertTrue(weapons.record_light_attack(p,main,100))  # no hit flag required
        self.assertEqual(weapons.offhand_error(p,100),'')
        self.assertEqual(weapons.spend_offhand(p,100),'')
        self.assertEqual(p.bonus_cooldown_until,103)
        self.assertEqual(p._feat_turn_until,103)
        self.assertTrue(weapons.spend_offhand(p,100))
        p.bonus_cooldown_until=0
        self.assertTrue(weapons.spend_offhand(p,100))  # does not become a second Light attack
        p._feat_turn_until=106
        self.assertTrue(weapons.offhand_error(p,103))
        self.assertTrue(weapons.record_light_attack(p,main,103))
        self.assertEqual(weapons.offhand_error(p,103),'')

    def test_bonus_action_spell_blocks_light_attack_and_reactions_do_not_reset_turn(self):
        p=self.player();main=self.equip(p,'training_dagger');other=self.equip(p,'training_handaxe','offhand')
        p._feat_turn_until=103;p.bonus_cooldown_until=103
        weapons.record_light_attack(p,main,100)
        self.assertTrue(weapons.offhand_error(p,100))
        with weapons.attack_context(p,other,offhand=True):
            self.assertFalse(weapons.record_light_attack(p,other,100))
            self.assertEqual(weapons.current_weapon(p)['uid'],other['uid'])
            with patch.object(weapons.fighter_rules,'style_active',return_value=False):
                self.assertEqual(weapons.damage_ability_modifier(p,3),0)
                self.assertEqual(weapons.damage_ability_modifier(p,-2),-2)
            with patch.object(weapons.fighter_rules,'style_active',return_value=True):
                p.fighting_style='two_weapon'
                self.assertEqual(weapons.damage_ability_modifier(p,3),3)
        self.assertEqual(weapons.current_weapon(p)['uid'],main['uid'])
        self.assertEqual(p._feat_turn_until,103)

    def test_throw_removes_exact_instance_auto_draws_spare_and_never_draws_offhand(self):
        p=self.player();main=self.equip(p,'training_dagger');other=self.equip(p,'training_dagger','offhand')
        spare=make_item('training_dagger');p.inventory.append(spare)
        p.weapon_attack_mode='throw';target=SimpleNamespace(x=p.x+120,y=p.y,floor=0)
        entry=weapons.throw_weapon(p,target)
        self.assertEqual(entry['item']['uid'],main['uid'])
        self.assertNotIn(main['uid'],[i['uid'] for i in p.inventory])
        self.assertEqual(p.equipment['weapon'],spare['uid'])
        self.assertEqual(p.equipment['offhand'],other['uid'])
        self.assertIsNone(weapons.throw_weapon(p,target,main))
        self.assertEqual(len(p.thrown_weapons),1)
        self.assertEqual(weapons.current_weapon(p)['uid'],spare['uid'])

    def test_persistent_recovery_requires_floor_range_visibility_capacity_and_preserves_uid(self):
        p=self.player();main=self.equip(p,'training_handaxe');p.weapon_attack_mode='throw'
        target=SimpleNamespace(x=p.x+128,y=p.y,floor=0)
        weapons.throw_weapon(p,target)
        p.thrown_weapons=json.loads(json.dumps(p.thrown_weapons))
        self.assertTrue(weapons.recover_thrown(p,main['uid'],40))
        p.x=target.x;p.floor=-1
        self.assertTrue(weapons.recover_thrown(p,main['uid'],40))
        p.floor=0
        self.assertTrue(weapons.recover_thrown(p,main['uid'],40,line_clear=lambda *_:False))
        self.assertTrue(weapons.recover_thrown(p,main['uid'],0))
        self.assertEqual(len(p.thrown_weapons),1)
        self.assertEqual(weapons.recover_thrown(p,main['uid'],40,line_clear=lambda *_:True),'')
        self.assertEqual(p.inventory[0]['uid'],main['uid'])
        self.assertEqual(p.thrown_weapons,[])
        self.assertTrue(weapons.recover_thrown(p,main['uid'],40))
        self.assertEqual(len(p.inventory),1)

    def test_throw_ranges_disadvantage_and_modes_are_authoritative(self):
        p=self.player();self.equip(p,'training_dagger')
        self.assertEqual(weapons.set_mode(p,'throw'),'')
        self.assertEqual(weapons.ranges(p),(128,384))
        target=SimpleNamespace(x=p.x+128,y=p.y)
        self.assertFalse(weapons.long_range_disadvantage(p,target))
        target.x+=.01
        self.assertTrue(weapons.long_range_disadvantage(p,target))
        self.assertTrue(weapons.set_mode(p,'invalid'))
        self.equip(p,'training_scimitar');self.assertTrue(weapons.set_mode(p,'throw'))
        p.form='wolf';self.assertTrue(weapons.set_mode(p,'unarmed'))
        p.form='';self.assertEqual(weapons.set_mode(p,'unarmed'),'')
        self.assertEqual(weapons.current_weapon(p),{})

    def test_unarmed_style_damage_depends_on_actually_held_items_not_attack_context(self):
        p=self.player();p.fighting_style='unarmed'
        with patch.object(weapons.fighter_rules,'style_active',return_value=True):
            self.assertEqual(weapons.unarmed_dice(p)[:2],(1,8))
            weapon=self.equip(p,'training_dagger')
            self.assertEqual(weapons.set_mode(p,'unarmed'),'')
            self.assertEqual(weapons.unarmed_dice(p)[:2],(1,6))
            with weapons.attack_context(p,{},attack_mode='unarmed'):
                self.assertEqual(weapons.unarmed_dice(p)[:2],(1,6))
            self.assertTrue(weapons.free_hand(p))
            self.equip(p,'wooden_shield','shield');self.assertFalse(weapons.free_hand(p))
            p.equipment['weapon']='';p.equipment['shield']=''
            self.assertEqual(weapons.unarmed_dice(p)[:2],(1,8))

    def test_style_preview_eligibility_never_grants_unselected_benefits(self):
        p=self.player();item=self.equip(p,'training_dagger')
        with patch.object(weapons.fighter_rules,'style_active',return_value=True):
            self.assertEqual(weapons.unarmed_dice(p)[:2],(0,1))
            with weapons.attack_context(p,item,offhand=True):
                self.assertEqual(weapons.damage_ability_modifier(p,3),0)

    def test_load_sanitizes_unique_thrown_instances_without_duplication(self):
        p=self.player();held=self.equip(p,'training_dagger');dropped=make_item('training_handaxe')
        p.weapon_attack_mode='invalid';p.equipment['offhand']=held['uid']
        row=dict(item=dropped,x=1000,y=1000,floor=0)
        p.thrown_weapons=[row,row,dict(item=held,x=1000,y=1000,floor=0),dict(item={'template':{}},x=0,y=0,floor=0),
            dict(item=make_item('training_scimitar'),x=0,y=0,floor=0),dict(item=make_item('training_dagger'),x=float('nan'),y=0,floor=0)]
        weapons.sanitize(p)
        self.assertEqual(p.weapon_attack_mode,'weapon')
        self.assertEqual(p.equipment['offhand'],'')
        self.assertEqual(len(p.thrown_weapons),1)
        self.assertEqual(p.thrown_weapons[0]['item']['uid'],dropped['uid'])

    def test_grapple_damage_only_applies_to_owners_live_grapple(self):
        p=self.player();target=SimpleNamespace(conditions={'grappled':dict(owner='other',until=103)})
        self.assertFalse(weapons.owned_grapple(p,target,100))
        target.conditions['grappled']['owner']=p.id
        self.assertTrue(weapons.owned_grapple(p,target,100))
        self.assertFalse(weapons.owned_grapple(p,target,103))


if __name__=='__main__':unittest.main()
