"""0.8.7: real paid scaling, persistence, owner payloads, old receipts and PvP.
Run: python -m unittest discover -s tests -p 'test_spell_scaling_087.py' -v
"""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.server import Player, xp_next, make_item
from server import spell_scaling as scale, dnd_content as dnd, combat_rules as rules, level_up
import test_dnd as fixtures
Dice=fixtures.Dice


def player(cls='mage', level=1):
    return Player('1','Test',class_id=cls,level=level)


class ScalingProfiles(unittest.TestCase):
    def test_one_caster_level_every_five_game_levels(self):
        for level, steps in [(1,0),(4,0),(5,1),(9,1),(10,2),(15,3),(95,19),(1000000,19)]:
            with self.subTest(level=level):self.assertEqual(scale.caster_steps(level),steps)

    def test_two_caster_levels_every_ten_game_levels(self):
        for level, steps in [(1,0),(9,0),(10,1),(19,1),(20,2),(30,3)]:
            self.assertEqual(scale.caster_steps(level,every=2),steps)

    def test_three_caster_levels_every_fifteen_game_levels(self):
        for level, steps in [(1,0),(14,0),(15,1),(29,1),(30,2),(44,2),(45,3)]:
            self.assertEqual(scale.caster_steps(level,every=3),steps)

    def test_invalid_growth_interval_is_rejected(self):
        for value in (0,-1,True,1.5,'3'):
            with self.assertRaises(ValueError):scale.caster_steps(30,every=value)

    def test_magic_missile_automatic_progression(self):
        for level, count, cost in [(1,3,20),(9,3,20),(10,4,30),(19,4,30),(20,5,50),(80,11,130),(999999,11,130)]:
            with self.subTest(level=level):
                s=scale.resolve(player(level=level),'magic_missile')
                self.assertEqual((s['shots'],s['mana'],s['dice']),(count,cost,[1,4,1]))
                self.assertEqual(s['visual']['shots'],count)

    def test_scorching_ray_increases_count_not_each_ray_damage(self):
        s=scale.resolve(player(level=40),'scorching_ray')
        self.assertEqual((s['shots'],s['dice'],s['mana']),(6,[2,6,0],70))

    def test_all_damage_upcasts_increase_correct_die_count(self):
        keys={'burning_hands':(11,6),'moonbeam':(9,10),'fireball':(14,6),'lightning_bolt':(14,6),
              'call_lightning':(9,10),'blight':(13,8),'ice_storm':(7,10),'cone_of_cold':(12,8)}
        for key,(n,sides) in keys.items():
            p=player(dnd.SPELLS[key]['class_ids'][0],80)
            with self.subTest(key=key):self.assertEqual(scale.resolve(p,key)['dice'],[n,sides,0])

    def test_ice_storm_does_not_scale_cold_component(self):
        s=scale.resolve(player(level=80),'ice_storm')
        self.assertEqual(s['extra_dice'],[4,6,0])

    def test_srd_2024_healing_uses_two_added_dice(self):
        p=player('druid',10)
        self.assertEqual(scale.resolve(p,'cure_wounds')['dice'],[4,8,3])
        self.assertEqual(scale.resolve(p,'healing_word')['dice'],[4,4,3])

    def test_mass_healing_adds_one_die_per_circle(self):
        self.assertEqual(scale.resolve(player('druid',80),'mass_cure_wounds')['dice'],[9,8,5])

    def test_heal_adds_ten_fixed_hp_per_circle(self):
        for level,n in [(50,70),(60,80),(70,90),(80,100),(999,100)]:
            self.assertEqual(scale.resolve(player('druid',level),'heal')['flat_heal'],n)

    def test_chain_adds_targets_not_damage(self):
        s=scale.resolve(player(level=80),'chain_lightning')
        self.assertEqual((s['max_targets'],s['dice']),(7,[10,8,0]))

    def test_longstrider_adds_targets_not_speed_or_duration(self):
        p=player('druid',80);s=scale.resolve(p,'longstrider')
        self.assertEqual((s['ally_targets'],s['duration_rounds'],s['speed_bonus_feet']),(9,600,10))
        self.assertFalse(s.get('concentration'))

    def test_freedom_adds_allies_at_full_and_delayed_caster_gates(self):
        for cls,level,targets,cost in [('druid',30,1,60),('druid',40,2,70),('druid',80,6,130),('ranger',60,1,60),('ranger',80,2,70)]:
            with self.subTest(cls=cls,level=level):
                s=scale.resolve(player(cls,level),'freedom_of_movement')
                self.assertEqual((s['ally_targets'],s['mana'],s['duration']),(targets,cost,60))

    def test_mark_uses_delayed_ranger_gates_and_useful_ranks(self):
        for level,rank,rounds,cost in [(1,1,600,0),(20,1,600,0),(40,3,4800,0),(60,3,4800,0),(80,5,14400,0),(100,5,14400,0)]:
            with self.subTest(level=level):
                s=scale.resolve(player('ranger',level),'hunters_mark')
                self.assertEqual((s['cast_circle'],s['duration_rounds'],s['mana']),(rank,rounds,cost))
                self.assertEqual(s['dice'],[1,6,0])

    def test_ranger_other_magic_does_not_inherit_full_caster_gates(self):
        for level,n in [(1,2),(19,2),(20,4),(39,4),(40,6),(60,8),(80,10),(100,10)]:
            self.assertEqual(scale.resolve(player('ranger',level),'cure_wounds')['dice'][0],n)

    def test_non_scaling_spells_stay_base_cost_and_effect(self):
        keys=('shield','mage_armor','entangle','misty_step','barkskin','spike_growth','sunbeam',
              'finger_of_death','fire_storm','sunburst','incendiary_cloud','meteor_swarm','foresight')
        for key in keys:
            cls=dnd.SPELLS[key]['class_ids'][0];p=player(cls,999999);s=scale.resolve(p,key)
            with self.subTest(key=key):
                for field in ('mana','dice','extra_dice','duration','blind','slow'):
                    self.assertEqual(s.get(field),dnd.SPELLS[key].get(field))
                self.assertEqual(s['power_options'],[])

    def test_no_caster_modifier_added_to_magic_missile(self):
        self.assertEqual(scale.resolve(player(level=95),'magic_missile')['dice'],[1,4,1])

    def test_cantrip_milestones_and_zero_cost(self):
        for key,s in dnd.SPELLS.items():
            if not s.get('scales'):continue
            for level,n in [(19,1),(20,2),(49,2),(50,3),(79,3),(80,4),(10000,4)]:
                p=player(s['class_ids'][0],level);resolved=scale.resolve(p,key)
                self.assertEqual((resolved['dice'][0],resolved['mana']),(n,0),(key,level))

    def test_second_wind_grows_at_five_not_each_level(self):
        for level,n in [(1,1),(4,1),(5,2),(9,2),(10,3),(15,4),(95,20)]:
            self.assertEqual(scale.resolve(player('knight',level),'second_wind')['dice'],[1,10,n])

    def test_shillelagh_current_weapon_dice_match_real_weapon(self):
        for level in (1,20,50,80):
            p=player('druid',level);i=make_item('druid_weapon_1');p.inventory.append(i);p.equipment['weapon']=i['uid'];s=scale.resolve(p,'shillelagh')
            p.buffs={'shillelagh':{'until':1}}
            self.assertEqual(s['weapon_dice'],list(rules.weapon_dice(p)))

    def test_static_catalogue_not_mutated(self):
        original=copy.deepcopy(dnd.SPELLS)
        for cls in dnd.CLASS_SPECS:
            scale.client_profiles(player(cls,100))
        self.assertEqual(dnd.SPELLS,original)

    def test_profiles_cached_and_invalidated_after_level_change(self):
        p=player(level=9);first=scale.client_profiles(p)
        self.assertIs(first,scale.client_profiles(p))
        p.level=10;second=scale.client_profiles(p)
        self.assertIsNot(second,first);self.assertEqual(second['magic_missile']['shots'],4)

    def test_base_power_can_be_selected_and_auto_restored(self):
        p=player(level=80)
        self.assertTrue(scale.choose_circle(p,'magic_missile',1))
        self.assertEqual(scale.resolve(p,'magic_missile')['shots'],3)
        self.assertTrue(scale.choose_circle(p,'magic_missile',0))
        self.assertEqual(scale.resolve(p,'magic_missile')['shots'],11)

    def test_invalid_rank_wrong_class_locked_spell_are_rejected(self):
        p=player(level=10)
        for key,rank in [('magic_missile',3),('magic_missile',True),('magic_missile',-1),('magic_missile','2'),
            ('magic_missile',1.5),('shield',1),('fire_bolt',0),('fireball',3),('cure_wounds',1),([],1),(None,0)]:
            self.assertFalse(scale.choose_circle(p,key,rank),(key,rank))
        self.assertEqual(p.spell_circle_choices,{})

    def test_useless_hunters_mark_ranks_cannot_be_selected(self):
        p=player('ranger',100)
        self.assertFalse(scale.choose_circle(p,'hunters_mark',2));self.assertFalse(scale.choose_circle(p,'hunters_mark',4))

    def test_corrupt_saved_preferences_are_sanitized(self):
        p=player(level=10);p.spell_circle_choices={'magic_missile':1,'burning_hands':99,'shield':1,'cure_wounds':1,'longstrider':True}
        scale.sanitize_choices(p);self.assertEqual(p.spell_circle_choices,{'magic_missile':1})
        for raw in (None,[],42,'broken'):
            p.spell_circle_choices=raw;scale.sanitize_choices(p);self.assertEqual(p.spell_circle_choices,{})

    def test_next_upgrade_uses_correct_name_free_delta_and_cap(self):
        self.assertEqual(scale.next_upgrade(player(level=1),'magic_missile'),'Poziom 10: +1 pocisk')
        self.assertIn('Poziom 20: +1k8',scale.next_upgrade(player(level=1),'ray_of_frost'))
        self.assertEqual(scale.next_upgrade(player(level=1000000),'magic_missile'),'')
        self.assertEqual(scale.next_upgrade(player(level=1),'shield'),'')


class ScalingReceipts(unittest.TestCase):
    def receipt(self,cls,level):
        p=player(cls,level);level_up.record(p,level,level)
        return p,level_up.pending(p)['pending_level_ups'][0]

    def test_magic_missile_one_projectile_not_old_new_or_extra_die(self):
        _,event=self.receipt('mage',10)
        rows=[r for r in event['rows'] if r['label']=='Magiczny pocisk']
        self.assertIn({'id':'spell_shots_magic_missile','label':'Magiczny pocisk','gain':'+1','unit':'pocisk','icon':'assets/spells/magic_missile.svg'},rows)
        self.assertFalse(any('obraże' in r.get('unit','') for r in rows))
        self.assertTrue(any(r['unit']=='do kosztu many' and r['gain']=='+10' for r in rows))

    def test_burning_hands_one_die_separate_line(self):
        _,event=self.receipt('mage',10)
        self.assertTrue(any(r['label']=='Płonące dłonie' and r['gain']=='+1k6' and r['unit']=='do obrażeń' for r in event['rows']))

    def test_heal_dice_and_ability_bonus_separate_lines(self):
        _,event=self.receipt('druid',20)
        rows=[r for r in event['rows'] if r['label']=='Leczenie ran']
        self.assertTrue(any(r['gain']=='+2k8' and r['unit']=='do leczenia' for r in rows))
        self.assertTrue(any(r['gain']=='+1' and r['unit']=='do leczenia' for r in rows))

    def test_duration_gain_appears_only_on_actual_mark_threshold(self):
        for level,n in [(40,4200),(80,9600)]:
            _,event=self.receipt('ranger',level)
            self.assertTrue(any(r['label']=='Znak łowcy' and r.get('unit')=='tur trwania efektu' and r['gain']==f'+{n}' for r in event['rows']))
        _,event=self.receipt('ranger',20)
        self.assertFalse(any(r['label']=='Znak łowcy' for r in event['rows']))

    def test_longstrider_only_targets_not_duration(self):
        _,event=self.receipt('mage',10)
        rows=[r for r in event['rows'] if r['label']=='Długonogi']
        self.assertTrue(any(r['unit']=='cel' and r['gain']=='+1' for r in rows))
        self.assertFalse(any('trwania' in r['unit'] for r in rows))

    def test_second_wind_flat_increment_only_at_fifth_level(self):
        for level,present in [(4,False),(5,True),(6,False),(10,True)]:
            _,event=self.receipt('knight',level)
            rows=[r for r in event['rows'] if r['id']=='second_wind']
            self.assertEqual(bool(rows),present)
            if rows:self.assertEqual(rows[0]['gain'],'+1')

    def test_freedom_level_40_reports_one_added_ally(self):
        changes=scale.level_gains(player('druid',39),player('druid',40),'freedom_of_movement')
        self.assertEqual([(c['metric'],c['amount']) for c in changes],[('allies',1),('mana',10)])

    def test_non_scalable_and_unchanged_spells_do_not_add_noise(self):
        _,event=self.receipt('mage',21)
        self.assertEqual([r['id'] for r in event['rows'] if r['id'].startswith('spell_')],['spell_restore_mana_arcane_recovery'])

    def test_every_single_level_has_separate_gains(self):
        p=player(level=20);level_up.record(p,10,20)
        events=level_up.pending(p)['pending_level_ups']
        self.assertEqual([e['level'] for e in events],list(range(10,21)))
        self.assertEqual([e['level'] for e in events if any(r['id']=='spell_shots_magic_missile' for r in e['rows'])],[10,20])

    def test_selected_lower_rank_does_not_hide_new_capability(self):
        p=player(level=20);p.spell_circle_choices={'magic_missile':1};level_up.record(p,20,20)
        self.assertTrue(any(r['id']=='spell_shots_magic_missile' for r in level_up.pending(p)['pending_level_ups'][0]['rows']))

    def test_old_saved_receipts_do_not_acquire_retroactive_scaling(self):
        p=player(level=10);level_up.record(p,10,10);p.level_up_batches[0].pop('spell_scaling_version');p._level_up_cache=None
        event=level_up.pending(p)['pending_level_ups'][0]
        self.assertFalse(any(r['id']=='spell_shots_magic_missile' for r in event['rows']))
        p.level=11;level_up.record(p,11,11)
        self.assertEqual(len(p.level_up_batches),2)

    def test_gain_payload_contains_no_before_after_or_zero_rows(self):
        for cls in ('mage','druid','ranger','knight'):
            for level in (5,10,20,30,40,50,60,80,100):
                _,event=self.receipt(cls,level)
                for row in event['rows']:
                    self.assertNotIn(row['gain'],('+0','0'));self.assertNotIn('before',row);self.assertNotIn('after',row)
                    self.assertNotIn('→',json.dumps(row,ensure_ascii=False))


class ScalingCombat(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.GameRules.setUp
    tearDown=fixtures.GameRules.tearDown
    player=fixtures.GameRules.player
    enemy=fixtures.GameRules.enemy
    account=fixtures.GameRules.account

    async def test_real_auto_missiles_cost_damage_and_visual_count(self):
        p=self.player('mage',20);mana=p.mana;before=self.e.hp
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(before-self.e.hp,20);self.assertEqual(mana-p.mana,50)
        effect=next(e for e in self.g.effects if e.get('kind')=='spell' and e.get('spell_id')=='magic_missile')
        self.assertEqual((effect['shots'],effect['visual']['shots'],effect['cast_circle']),(5,5,3))
        self.assertEqual(len(p.combat_log),5);self.assertEqual(p.spell_history,['magic_missile'])

    async def test_maximum_missile_count_eleven_really_damages(self):
        p=self.player('mage',80);before=self.e.hp
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(before-self.e.hp,44)
        self.assertEqual(next(e for e in self.g.effects if e.get('spell_id')=='magic_missile')['shots'],11)

    async def test_base_selection_preserves_three_cheap_missiles(self):
        p=self.player('mage',80);scale.choose_circle(p,'magic_missile',1);mana=p.mana
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(self.e.hp,987);self.assertEqual(mana-p.mana,20)

    async def test_not_enough_mana_never_silently_casts_weaker_spell(self):
        p=self.player('mage',20);p.mana=20
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(p.mana,20);self.assertEqual(self.e.hp,999);self.assertFalse(p.spell_history)
        scale.choose_circle(p,'magic_missile',1)
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(p.mana,0);self.assertEqual(self.e.hp,987)

    async def test_fireball_real_scaled_damage_not_cosmetic(self):
        p=self.player('mage',30);self.g.combat_rng=Dice(1,3)
        await self.g.cast_spell(p,'fireball',self.e.id)
        self.assertEqual(self.e.hp,972);self.assertEqual(p.last_roll['damage_dice'],'9k6')

    async def test_scorching_ray_each_added_ray_has_separate_attack(self):
        p=self.player('mage',20);self.e.x=1240
        await self.g.cast_spell(p,'scorching_ray',self.e.id)
        self.assertEqual(self.g.combat_rng.checks,4)
        self.assertEqual(len(p.combat_log),4)
        self.assertTrue(all(r['damage_dice']=='2k6' for r in p.combat_log))

    async def test_cure_rolls_actual_healing_dice_and_modifier_once(self):
        p=self.player('druid',20);p.hp=1
        await self.g.cast_spell(p,'cure_wounds')
        self.assertEqual(p.last_roll['damage_dice'],'6k8+4')
        self.assertEqual(len(p.last_roll['damage_rolls']),6);self.assertEqual(p.hp,23)

    async def test_second_wind_does_not_double_add_caster_level(self):
        p=self.player('knight',10);p.hp=1
        await self.g.cast_spell(p,'second_wind')
        self.assertEqual((p.last_roll['damage_dice'],p.hp),('1k10+3',7))

    async def test_moonbeam_keeps_original_strength_after_levelling(self):
        p=self.player('druid',10);self.g.combat_rng=Dice(1,3)
        await self.g.cast_spell(p,'moonbeam',self.e.id)
        self.g.tick_dnd(.05);self.assertEqual(self.e.hp,993)
        p.level=20;self.clock.advance();self.g.tick_dnd(.05)
        self.assertEqual(self.e.hp,987);self.assertEqual(p.last_roll['damage_dice'],'2k10')
        self.assertEqual(self.g.spell_fields[0]['profile']['cast_circle'],2)

    async def test_moonbeam_uses_paid_higher_rank(self):
        p=self.player('druid',30);self.g.combat_rng=Dice(1,3);mana=p.mana
        await self.g.cast_spell(p,'moonbeam',self.e.id);self.g.tick_dnd(.05)
        self.assertEqual(self.e.hp,987);self.assertEqual(p.last_roll['damage_dice'],'4k10');self.assertEqual(mana-p.mana,60)

    async def test_repeat_lightning_cannot_gain_free_upcast(self):
        p=self.player('druid',20);self.g.combat_rng=Dice(1,3)
        await self.g.cast_spell(p,'call_lightning',self.e.id);until=p.concentration_until
        p.level=30;p.mana=0;self.clock.advance();before=self.e.hp
        await self.g.cast_spell(p,'call_lightning',self.e.id)
        self.assertEqual(before-self.e.hp,9);self.assertEqual(p.mana,0)
        self.assertEqual(p.last_roll['damage_dice'],'3k10');self.assertEqual(p.concentration_until,until)
        self.assertTrue(scale.client_profiles(p)['call_lightning']['recast_active'])

    async def test_changing_power_does_not_change_active_repeated_spell(self):
        p=self.player('druid',30);scale.choose_circle(p,'call_lightning',3)
        await self.g.cast_spell(p,'call_lightning',self.e.id)
        scale.choose_circle(p,'call_lightning',4);self.clock.advance()
        self.assertEqual(scale.resolve(p,'call_lightning')['dice'],[3,10,0])
        self.g.break_concentration(p)
        self.assertEqual(scale.resolve(p,'call_lightning')['dice'],[4,10,0])

    async def test_stop_concentration_clears_fields_no_resource_refund(self):
        p=self.player('druid',30)
        await self.g.cast_spell(p,'moonbeam',self.e.id);mana=p.mana
        await self.g.on_packet(p.ws,{'type':'stop_concentration'})
        self.assertFalse(p.concentration_profile);self.assertFalse(self.g.spell_fields);self.assertEqual(p.mana,mana)

    async def test_longstrider_scales_number_of_nearby_allies(self):
        p=self.player('druid',10);q=self.player('knight',10,'2');r=self.player('knight',10,'3')
        p.party_id=q.party_id=r.party_id='same';q.x=p.x+30;r.x=p.x+45
        mana=p.mana
        await self.g.cast_spell(p,'longstrider',target_id=q.id)
        self.assertIn('longstrider',q.buffs);self.assertIn('longstrider',p.buffs);self.assertNotIn('longstrider',r.buffs)
        self.assertEqual(q.buffs['longstrider']['until']-self.clock(),1800);self.assertEqual(mana-p.mana,30)
        self.assertEqual(q.buffs['longstrider']['spell_id'],'longstrider')

    async def test_longstrider_does_not_touch_strangers_or_out_of_range(self):
        p=self.player('druid',80);q=self.player('knight',10,'2');r=self.player('knight',10,'3')
        p.party_id=r.party_id='party';r.x=p.x+1000
        await self.g.cast_spell(p,'longstrider')
        self.assertIn('longstrider',p.buffs);self.assertNotIn('longstrider',q.buffs);self.assertNotIn('longstrider',r.buffs)

    async def test_longstrider_keeps_pvp_support_safety(self):
        p=self.player('druid',30);q=self.player('knight',30,'2');p.party_id=q.party_id='p';q.pvp_combat_until=self.clock()+20
        await self.g.cast_spell(p,'longstrider')
        self.assertIn('longstrider',p.buffs);self.assertNotIn('longstrider',q.buffs)

    async def test_chain_hits_seven_distinct_targets_at_ninth_circle(self):
        p=self.player('mage',80);self.g.line_clear=lambda *_:True
        self.e.x=p.x+120
        enemies=[self.e]+[self.enemy('dummy'+str(n),x=self.e.x+n*8,y=self.e.y+20) for n in range(1,9)]
        await self.g.cast_spell(p,'chain_lightning',self.e.id)
        self.assertEqual(sum(e.hp<999 for e in enemies),7)
        self.assertEqual(len(next(e for e in self.g.effects if e.get('spell_id')=='chain_lightning')['targets']),7)

    async def test_hunters_mark_real_scaled_duration_and_fixed_bonus(self):
        p=self.player('ranger',60)
        await self.g.cast_spell(p,'hunters_mark',self.e.id)
        self.assertEqual(p.concentration_until-self.clock(),14400)
        before=self.e.hp;await self.g.attack(p,enemy_id=self.e.id)
        self.assertEqual(before-self.e.hp,22)
        self.assertEqual(p.last_roll['mark_rolls'],[3])

    async def test_scaled_status_still_clears_when_concentration_breaks(self):
        p=self.player('druid',30);q=self.player('knight',30,'2');p.party_id=q.party_id='same'
        await self.g.cast_spell(p,'stoneskin',target_id=q.id)
        self.assertEqual(q.buffs['stoneskin']['spell_id'],'stoneskin')
        self.g.break_concentration(p);self.assertNotIn('stoneskin',q.buffs)

    async def test_freedom_really_protects_two_party_members_at_circle_five(self):
        p=self.player('druid',40);q=self.player(pid='2',level=40);r=self.player(pid='3',level=40)
        p.party_id=q.party_id=r.party_id='party';q.x=1140;r.x=1120
        for actor in (p,q,r):actor.buffs['restrained']={'until':self.clock()+20}
        mana=p.mana
        await self.g.cast_spell(p,'freedom_of_movement',target_id=q.id)
        self.assertEqual(p.mana,mana-70)
        for actor in (p,q):
            self.assertIn('freedom',actor.buffs);self.assertNotIn('restrained',actor.buffs)
        self.assertNotIn('freedom',r.buffs);self.assertIn('restrained',r.buffs)

    async def test_auto_scaled_missiles_respect_pvp_safety(self):
        p=self.player('mage',20);q=self.player('knight',20,'2');q.hp=q.max_hp;before=q.hp;mana=p.mana
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(q.hp,before);self.assertEqual(p.mana,mana)
        p.pvp_safety=False
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(before-q.hp,20);self.assertEqual(mana-p.mana,50)

    async def test_shield_blocks_entire_upcast_salvo(self):
        p=self.player('mage',20);q=self.player('mage',20,'2');p.pvp_safety=False;q.shield_armed=True
        before=q.hp;mana=q.mana
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(q.hp,before);self.assertEqual(mana-q.mana,20)
        self.assertTrue(all(r.get('shielded') for r in p.combat_log))

    async def test_scaled_area_retains_friendly_fire_protections(self):
        p=self.player('mage',30);q=self.player('knight',30,'2');q.x=self.e.x;p.party_id=q.party_id='same';p.pvp_safety=False
        before=q.hp;await self.g.cast_spell(p,'fireball',self.e.id)
        self.assertEqual(q.hp,before);self.assertLess(self.e.hp,999)

    async def test_queued_spell_uses_current_cost_without_duplicate_shots(self):
        p=self.player('mage',20);await self.g.select_combat_target(p,{'enemy_id':self.e.id})
        await self.g.attack(p,enemy_id=self.e.id);before=self.e.hp;mana=p.mana
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(p.mana,mana);self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(before-self.e.hp,20);self.assertEqual(mana-p.mana,50)

    async def test_favorite_key_uses_selected_real_spell_rank(self):
        p=self.player('mage',20);p.spell_history=['magic_missile']*3;mana=p.mana
        await self.g.ability(p,enemy_id=self.e.id)
        self.assertEqual(mana-p.mana,50);self.assertEqual(self.e.hp,979)

    async def test_power_choice_packet_is_owner_scoped_and_persistent(self):
        p=self.player('mage',20);q=self.player('mage',20,'2');self.account(p)
        await self.g.on_packet(p.ws,{'type':'spell_power','spell_id':'magic_missile','circle':1,'player_id':q.id})
        self.assertEqual(p.spell_circle_choices,{'magic_missile':1});self.assertEqual(q.spell_circle_choices,{})
        saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?',(int(p.id),)).fetchone()[0])
        self.assertEqual(saved['spell_circle_choices'],{'magic_missile':1})
        restored=self.player('mage',20,'3');restored.spell_circle_choices=saved['spell_circle_choices'];self.g.migrate_dnd(restored,saved)
        self.assertEqual(scale.resolve(restored,'magic_missile')['shots'],3)

    async def test_profiles_are_private_not_leaked_to_other_players(self):
        p=self.player('mage',20)
        self.assertNotIn('spell_profiles',p.public(self.clock()))
        self.assertEqual(p.public(self.clock(),private=True)['spell_profiles']['magic_missile']['shots'],5)

    async def test_old_save_migrates_to_auto_no_xp_or_mana_reset(self):
        p=self.player('mage',20);p.mana=17;p.xp=15
        saved=p.save_data();saved.pop('spell_circle_choices',None)
        self.g.migrate_dnd(p,saved)
        self.assertEqual((p.mana,p.xp,p.level),(17,15,20));self.assertEqual(scale.resolve(p,'magic_missile')['shots'],5)
