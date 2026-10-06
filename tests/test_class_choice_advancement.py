"""Class choices in real owner snapshots and historical advancement receipts."""
import copy
import unittest
import test_dnd as base
from server.server import Player, make_item
from server import level_up, character_sheet, progression_guide, spell_scaling


class ClassChoiceAdvancement(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    enemy=base.GameRules.enemy

    def setUp(self):
        self.clock=base.Clock()
        from server.server import Game
        self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice()
        for enemy in self.g.enemies.values():enemy.alive=False;enemy.respawn_at=0
        self.g.legacy_enemies=[]
        self.addCleanup(self.g.db.close)

    def test_ranger_two_and_druid_seven_have_separate_choice_actions(self):
        for cls,level,kind in (('ranger',2,'ranger_style'),('druid',7,'elemental_fury')):
            p=self.player(cls,level)
            level_up.record(p,level,level)
            receipt=level_up.pending(p)['pending_level_ups'][0]
            self.assertTrue(any(a['kind']==kind for a in receipt['actions']))
            self.assertFalse(any(a['kind']=='training_feat' for a in receipt['actions']))
            data=character_sheet.build(p)
            pending=data['fighter']['pending'] if cls=='ranger' else data['caster']['elemental_fury']['pending']
            self.assertTrue(pending)

    def test_old_receipt_does_not_inherit_later_class_choice(self):
        p=self.player('druid',11)
        level_up.record(p,11,11)
        batch=copy.deepcopy(p.level_up_batches[0])
        baseline=level_up.receipt(p,batch,11)
        p.elemental_fury='potent_spellcasting'
        self.assertEqual(level_up.receipt(p,batch,11),baseline)
        # Old save contexts without the new keys have the same stable replay.
        batch['context'].pop('elemental_fury',None)
        batch['context'].pop('elemental_damage_type',None)
        self.assertEqual(level_up.receipt(p,batch,11),baseline)

    def test_fifteen_receipt_and_guide_describe_actual_upgrade(self):
        p=self.player('druid',15)
        p.elemental_fury='primal_strike'
        level_up.record(p,15,15)
        rows=level_up.pending(p)['pending_level_ups'][0]['rows']
        self.assertTrue(any(r['id']=='improved_elemental_fury' and '2k8' in r['gain'] for r in rows))
        guide=progression_guide.catalog()
        for cls,level,text in (('ranger',2,'Styl walki'),('druid',7,'Elemental Fury'),('druid',15,'Improved Elemental Fury')):
            self.assertTrue(any(row['level']==level and text in row['name'] for row in guide[cls]))

    def test_improved_cantrip_target_is_visible_in_real_snapshot(self):
        p=self.player('druid',15)
        p.elemental_fury='potent_spellcasting'
        p.x,p.y,p.floor=1000,1000,-10
        e=self.enemy('far_wisp',p.x+2000,p.y,kind='wolf')
        e.floor=p.floor
        self.g.reindex_enemy(e)
        reach=spell_scaling.resolve(p,'starry_wisp')['range']
        self.assertGreater(reach,2000)
        snapshot=self.g.snapshot(p)
        self.assertIn(e.id,[entry['id'] for entry in snapshot['enemies']])
        p.elemental_fury='primal_strike'
        self.assertNotIn(e.id,[entry['id'] for entry in self.g.snapshot(p)['enemies']])

    def test_thrown_items_are_private_and_survive_load_with_exact_uid(self):
        p=self.player('ranger',3)
        item=make_item('training_dagger')
        p.thrown_weapons=[dict(item=item,x=p.x,y=p.y,floor=p.floor)]
        other_weapon=make_item('training_handaxe')
        p.inventory.append(other_weapon)
        p.equipment['weapon']=''
        p.equipment['offhand']=other_weapon['uid']
        other=self.player('knight',3,'2')
        public=p.public(self.clock.value,self.g.time,False,[])
        self.assertNotIn('thrown_weapons',public)
        own=p.public(self.clock.value,self.g.time,True,[])
        self.assertEqual(own['thrown_weapons'][0]['item']['uid'],item['uid'])
        loaded=self.g.load_player(p.id,p.name,p.ws,p.save_data())
        self.assertEqual(loaded.thrown_weapons[0]['item']['uid'],item['uid'])
        self.assertEqual(loaded.equipment['offhand'],other_weapon['uid'])
        self.assertNotIn(item['uid'],[i['uid'] for i in loaded.inventory])
        self.assertNotIn('thrown_weapons',other.public(self.clock.value,self.g.time,False,[]))


if __name__=='__main__':unittest.main()
