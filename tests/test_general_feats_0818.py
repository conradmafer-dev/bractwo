"""Selection, persistence, HP, armor and per-turn weapon feat regressions."""
import json
import unittest
import test_dnd as base
from server.server import Player, ITEMS, make_item
from server import combat_rules as rules, equipment_rules as gear


def wear(player,template):
    item=make_item(template)
    player.inventory.append(item)
    player.equipment[ITEMS[template]['slot']]=item['uid']


class Rolls:
    def __init__(self,*values):self.values=iter(values)
    def randint(self,lo,hi):
        value=next(self.values)
        assert lo<=value<=hi
        return value


class GeneralFeats(unittest.TestCase):
    def test_repeatable_asi_is_serializable_and_caps_each_allocation(self):
        p=Player('1','A',level=35)
        self.assertEqual(gear.select_feat(p,'ability_score_improvement',abilities=['constitution','constitution']),'')
        self.assertEqual(gear.select_feat(p,'ability_score_improvement',abilities=['constitution','dexterity']),'')
        self.assertEqual(rules.attributes(p)['constitution'],17)
        self.assertEqual(rules.attributes(p)['dexterity'],13)
        self.assertEqual(len(p.training_feats),2)
        saved=json.loads(json.dumps(p.training_feats))
        p.training_feats=saved
        gear.sanitize_feats(p)
        self.assertEqual(p.training_feats,saved)
        self.assertIsInstance(hash(gear._preview_signature(p)),int)
        p.level=55
        self.assertTrue(gear.select_feat(p,'ability_score_improvement',abilities=['strength','strength']))
        self.assertEqual(len(p.training_feats),2)

    def test_passives_require_a_point_and_cannot_be_repeated(self):
        p=Player('1','A',level=1)
        self.assertTrue(gear.select_feat(p,'tough'))
        p.level=15
        self.assertEqual(gear.select_feat(p,'tough'),'')
        self.assertEqual(p.training_feats,{'tough':''})
        p.level=35
        self.assertTrue(gear.select_feat(p,'tough'))
        self.assertEqual(gear.select_feat(p,'savage_attacker'),'')
        self.assertEqual(gear.feat_points(p),0)
        self.assertEqual({r['feat_id'] for r in gear.training_sheet(p)['chosen']},{'tough','savage_attacker'})

    def test_sanitizer_preserves_old_choices_and_rejects_invalid_allocations(self):
        p=Player('1','A',class_id='mage',level=75)
        p.training_feats={'lightly_armored':'dexterity','tough':'','ability_score_improvement':'wisdom+constitution',
                          'savage_attacker':['bad'],'ability_score_improvement_²':'strength+strength','unknown':''}
        gear.sanitize_feats(p)
        self.assertEqual(set(p.training_feats),{'lightly_armored','tough','ability_score_improvement'})
        self.assertTrue(gear.has(p,'light_armor'))
        self.assertEqual(rules.attributes(p)['dexterity'],15)

    def test_tough_uses_effective_level_and_druid_own_hp_in_form(self):
        p=Player('1','A',class_id='druid')
        for level,bonus in ((15,8),(20,10),(95,40),(999,40)):
            p.level=level;p.training_feats={};normal=p.max_hp
            p.training_feats={'tough':''}
            self.assertEqual(p.max_hp,normal+bonus)
            p.form='wolf'
            self.assertEqual(p.max_hp,normal+bonus)
            p.form=''

    def test_constitution_asi_increases_hp_without_using_wildshape_con(self):
        p=Player('1','A',class_id='druid',level=15)
        before=p.max_hp
        self.assertEqual(gear.select_feat(p,'ability_score_improvement','constitution'),'')
        self.assertGreater(p.max_hp,before)
        hp=p.max_hp;p.form='cat'
        self.assertEqual(p.max_hp,hp)

    def test_medium_master_needs_training_and_dexterity_sixteen(self):
        p=Player('1','A',class_id='mage',level=55)
        self.assertTrue(gear.select_feat(p,'medium_armor_master','dexterity'))
        p=Player('1','A',level=55)
        wear(p,'hide_armor')
        p.training_feats={'ability_score_improvement':'dexterity+dexterity','medium_armor_master':'dexterity'}
        self.assertEqual(rules.attributes(p)['dexterity'],15)
        self.assertEqual(p.armor_class,14)
        p.training_feats['ability_score_improvement_2']='dexterity+constitution'
        self.assertEqual(rules.attributes(p)['dexterity'],16)
        self.assertEqual(p.armor_class,15)

    def test_heavy_master_requires_heavy_armor_and_attack_physical_damage(self):
        p=Player('1','A',level=35)
        p.training_feats={'heavy_armor_master':'constitution'}
        heavy=next(k for k,v in ITEMS.items() if v.get('armor_kind')=='heavy')
        wear(p,heavy)
        for kind in ('bludgeoning','piercing','slashing'):
            self.assertEqual(gear.heavy_armor_reduction(p,kind,True),rules.proficiency(p))
            self.assertEqual(gear.heavy_armor_reduction(p,kind,False),0)
        self.assertEqual(gear.heavy_armor_reduction(p,'force',True),0)
        p.form='bear'
        self.assertEqual(gear.heavy_armor_reduction(p,'slashing',True),0)
        p.form='';wear(p,'hide_armor')
        self.assertEqual(gear.heavy_armor_reduction(p,'slashing',True),0)

    def test_savage_chooses_a_whole_set_once_per_turn_and_includes_critical_dice(self):
        p=Player('1','A',level=35)
        wear(p,'training_greatsword');p.training_feats={'savage_attacker':''}
        result=rules.roll_attack(Rolls(20,1,2,3,4),0,99,rules.weapon_dice(p))
        rules.begin_feat_turn(p,1000)
        rules.savage_attacker_damage(p,result,Rolls(6,5,4,3),1000)
        self.assertEqual(result['damage_rolls'],[6,5,4,3])
        self.assertEqual(result['damage'],18+rules.weapon_dice(p)[2])
        second=rules.roll_attack(Rolls(15,1,1),20,10,rules.weapon_dice(p))
        rules.begin_feat_turn(p,1001)  # a bonus action / extra action is the same turn
        rules.savage_attacker_damage(p,second,Rolls(),1001)
        self.assertNotIn('savage_attacker',second)
        rules.begin_feat_turn(p,1003)
        rules.savage_attacker_damage(p,second,Rolls(6,6),1003)
        self.assertEqual(second['damage_rolls'],[6,6])

    def test_savage_style_comparison_happens_before_riders_and_excludes_focus_and_form(self):
        p=Player('1','A',level=35);wear(p,'training_greatsword')
        p.training_feats={'savage_attacker':''};p.fighting_style='great_weapon'
        result=rules.roll_attack(Rolls(15,1,6),20,10,rules.weapon_dice(p))
        # Raw 4+4 > 1+6, but the style makes 3+6 the better complete set.
        rules.savage_attacker_damage(p,result,Rolls(4,4),1000)
        self.assertEqual(result['damage_rolls'],[1,6])
        self.assertEqual(result['savage_chosen'],0)
        for mode in ('unarmed','focus','form'):
            q=Player('2','B',class_id='mage',level=35);q.training_feats={'savage_attacker':''}
            if mode=='focus':wear(q,'mage_weapon_1')
            if mode=='form':q.form='wolf'
            hit={'hit':True,'damage_rolls':[1],'damage_modifier':0,'damage':1}
            rules.savage_attacker_damage(q,hit,Rolls(),1000)
            self.assertNotIn('savage_attacker',hit)


if __name__=='__main__':unittest.main()
