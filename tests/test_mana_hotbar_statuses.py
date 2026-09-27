"""0.8.4: weighted slot mana, ten-level gates, complete hotbars and visible timed effects."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.server import Player, ENEMY_TYPES, player_speed
from server import dnd_content as dnd, combat_rules as rules
import test_dnd as base
import test_pursuit_cantrips as pursuit


class ManaCatalogue(unittest.TestCase):
    def test_level_one_two_first_circle_casts(self):
        for cls in ('mage','druid'):
            p=Player('1','Test',class_id=cls)
            self.assertEqual(p.max_mana,40)
            self.assertEqual(p.max_mana//dnd.SPELLS['longstrider']['mana'],2)

    def test_slot_table_and_costs(self):
        self.assertEqual(dnd.MANA_COSTS,(0,20,30,50,60,70,90,100,110,130))
        self.assertEqual(len(dnd.FULL_CASTER_SLOTS),20)
        self.assertEqual(dnd.FULL_CASTER_SLOTS[0],(2,))
        self.assertEqual(dnd.FULL_CASTER_SLOTS[2],(4,2))
        self.assertEqual(dnd.FULL_CASTER_SLOTS[4],(4,3,2))
        self.assertEqual(dnd.FULL_CASTER_SLOTS[-1],(4,3,3,3,3,2,2,1,1))

    def test_weighted_budget_at_milestones(self):
        for cls in ('mage','druid'):
            for lv,slots,mana in ((1,(2,),40),(5,(3,),84),(10,(4,2),140),(20,(4,3,2),270),(30,(4,3,3,1),380)):
                with self.subTest(cls=cls,level=lv):
                    p=Player('1','Test',class_id=cls,level=lv)
                    self.assertEqual(dnd.mana_slot_budget(cls,lv),slots)
                    self.assertEqual(p.max_mana,mana)

    def test_circle_unlocks_and_budget_agree_at_every_level(self):
        for cls in ('mage','druid','ranger'):
            for lv in range(1,150):
                with self.subTest(cls=cls,level=lv):
                    self.assertEqual(len(dnd.mana_slot_budget(cls,lv)),dnd.circle_for(cls,lv))

    def test_focus_bonus_is_separate_from_slot_budget(self):
        p=Player('1','Test',class_id='mage',mastery={'focus':3})
        self.assertEqual(p.max_mana,52)
        self.assertEqual(dnd.mana_budget_info(p)['base'],40)
        self.assertEqual(dnd.mana_budget_info(p)['bonus'],12)
        self.assertTrue(dnd.mana_budget_info(p)['shared'])

    def test_mana_growth_is_bounded_at_tabletop_level_twenty(self):
        self.assertEqual(Player('1','T',class_id='mage',level=95).max_mana,Player('1','T',class_id='mage',level=9999).max_mana)

    def test_all_non_feature_costs_follow_circle(self):
        for key,spec in dnd.SPELLS.items():
            if not spec.get('feature'):
                self.assertEqual(spec['mana'],0 if spec.get('free_cast') else dnd.MANA_COSTS[spec['circle']],key)

    def test_ranger_has_early_magic_but_slower_later_circles(self):
        for lv,circle in ((1,1),(19,1),(20,2),(39,2),(40,3),(60,4),(80,5),(100,5)):
            self.assertEqual(dnd.circle_for('ranger',lv),circle)
        self.assertEqual(dnd.mana_slot_budget('ranger',20),(4,2))

    def test_longstrider_rounds_and_additive_speed_metadata(self):
        spell=dnd.SPELLS['longstrider']
        self.assertEqual(spell['duration_rounds'],600)
        self.assertEqual(spell['tabletop_duration'],3600)
        self.assertEqual(spell['duration'],600*rules.ROUND_SECONDS)
        self.assertEqual(spell['speed_bonus_feet'],10)
        self.assertFalse(spell.get('concentration',False))
        self.assertEqual(spell['range'],dnd.SPELLS['cure_wounds']['range'])


class CompleteHotbars(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    def assert_complete(self,p):
        keys=[key for key in p.hotbar if key]
        self.assertEqual(set(keys),{key for key in dnd.SPELLS if dnd.spell_allowed(p,key)})
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(len(p.hotbar)%24,0)

    def test_initial_mage_has_twelve_unlocked_spells_and_features(self):
        p=self.player('mage');self.assert_complete(p)
        self.assertEqual(len(p.hotbar),24)
        self.assertEqual(sum(bool(k) for k in p.hotbar),12)
        self.assertEqual(p.hotbar[8],'shocking_grasp')

    def test_initial_druid_has_eight_unlocked_spells(self):
        p=self.player('druid');self.assert_complete(p)
        self.assertEqual(len(p.hotbar),24)
        self.assertIn('healing_word',p.hotbar);self.assertIn('longstrider',p.hotbar)

    def test_no_locked_feature_placeholders_on_ranger_or_knight(self):
        for cls in ('ranger','knight'):
            p=self.player(cls);self.assert_complete(p)
            self.assertEqual('hunters_mark' in p.hotbar,cls=='ranger')
            self.assertNotIn('animal_companion',p.hotbar)

    def test_all_levels_get_every_current_spell_and_feature(self):
        for cls in ('mage','druid','ranger','knight'):
            p=self.player(cls)
            for lv in (1,9,10,19,20,30,40,50,60,70,80,95,100):
                p.level=lv;p.public(self.clock(),private=True)
                self.assert_complete(p)

    def test_old_bar_retains_valid_positions_and_replaces_locks(self):
        p=self.player('mage');p.hotbar=['magic_missile','','fire_bolt','scorching_ray','','fire_bolt','cure_wounds','fireball']
        dnd.sync_hotbar(p)
        self.assertEqual(p.hotbar[0],'magic_missile');self.assertEqual(p.hotbar[2],'fire_bolt')
        self.assert_complete(p)

    async def test_rebinding_swaps_spells_without_losing_any(self):
        p=self.player('mage');self.account(p)
        before=p.hotbar[:]
        await self.g.bind_spell(p,0,'shocking_grasp')
        self.assertEqual(p.hotbar[0],'shocking_grasp');self.assertEqual(p.hotbar[8],before[0]);self.assert_complete(p)
        saved=json.loads(self.g.db.execute('SELECT data FROM accounts').fetchone()[0])
        q=self.g.load_player(p.id,p.name,p.ws,saved)
        self.assertEqual(q.hotbar,p.hotbar)

    async def test_locked_rebind_rejected_without_mutation(self):
        p=self.player('mage');before=p.hotbar[:]
        await self.g.bind_spell(p,0,'fireball')
        self.assertEqual(p.hotbar,before)

    def test_oversized_corrupt_or_duplicate_bar_is_sanitized(self):
        p=self.player('mage')
        p.hotbar=['invalid',None,{},'fire_bolt','fire_bolt']*100
        dnd.sync_hotbar(p)
        self.assert_complete(p)
        self.assertLessEqual(len(p.hotbar),dnd.HOTBAR_MAX_SLOTS)

    def test_level_up_appends_without_moving_existing_spells(self):
        p=self.player('mage');p.hotbar[0],p.hotbar[6]=p.hotbar[6],p.hotbar[0];before=p.hotbar[:9]
        p.level=10;packet=p.public(self.clock(),private=True)
        self.assertEqual(packet['hotbar'][:9],before)
        self.assertIn('scorching_ray',p.hotbar);self.assertIn('misty_step',p.hotbar)
        self.assertNotIn('fireball',p.hotbar);self.assert_complete(p)


class ManaGameplay(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    async def test_two_paid_spells_then_only_free_cantrip(self):
        p=self.player('mage')
        for expected in (20,0):
            await self.g.cast_spell(p,'magic_missile',self.e.id)
            self.assertEqual(p.mana,expected);self.clock.advance()
        hp=self.e.hp
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(self.e.hp,hp);self.assertEqual(p.mana,0)
        await self.g.cast_spell(p,'fire_bolt',self.e.id)
        self.assertLess(self.e.hp,hp);self.assertEqual(p.mana,0)

    async def test_mixed_circle_distribution_spends_full_budget(self):
        p=self.player('mage',10);p.spell_circle_choices['magic_missile']=1
        for spell in ['magic_missile']*4+['scorching_ray']*2:
            await self.g.cast_spell(p,spell,self.e.id);self.clock.advance()
        self.assertEqual(p.mana,0)

    async def test_defensive_buffs_use_same_starting_budget(self):
        p=self.player('mage')
        await self.g.cast_spell(p,'longstrider');self.clock.advance()
        await self.g.cast_spell(p,'mage_armor');self.clock.advance()
        self.assertEqual(p.mana,0);self.assertEqual(set(p.buffs),{'longstrider','mage_armor'})
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(self.e.hp,999)

    def test_no_passive_regeneration_during_pve_or_pvp(self):
        self.e.alive=False
        for field in ('combat_until','pvp_combat_until'):
            p=self.player('mage');p.mana=0;setattr(p,field,self.clock()+60)
            for _ in range(50):self.g.step(.05)
            self.assertEqual(p.mana,0)

    async def test_buff_cast_delays_out_of_combat_recovery(self):
        p=self.player('mage');self.e.alive=False
        await self.g.cast_spell(p,'longstrider')
        for _ in range(20):self.g.step(.05)
        self.assertEqual(p.mana,20)
        self.clock.advance(11.9);self.g.step(.05);self.assertEqual(p.mana,20)
        self.clock.advance(.2);self.g.step(.05);self.assertGreater(p.mana,20)

    def test_regeneration_rate_is_pool_relative_and_safe_is_faster(self):
        self.e.alive=False;p=self.player('mage',20);p.mana=0
        with patch.object(self.g,'in_safe',return_value=False):self.g.step(.05)
        field=p.mana;self.assertAlmostEqual(field,p.max_mana*.05/240)
        p.mana=0
        with patch.object(self.g,'in_safe',return_value=True):self.g.step(.05)
        self.assertAlmostEqual(p.mana,p.max_mana*.05/20);self.assertGreater(p.mana,field)

    def test_mana_regeneration_does_not_exceed_capacity(self):
        self.e.alive=False;p=self.player('mage');p.mana=p.max_mana-.001
        self.g.step(.05);self.assertEqual(p.mana,p.max_mana)

    def test_old_mana_ratio_migrates_once(self):
        for cls,oldmax in (('mage',55),('druid',50)):
            p=self.player(cls);saved=p.save_data();saved.pop('mana_rules_version');saved['mana']=oldmax/2
            q=self.g.load_player(p.id,p.name,p.ws,saved)
            self.assertEqual(q.mana,20);self.assertEqual(q.mana_rules_version,dnd.MANA_RULES_VERSION)
            again=self.g.load_player(p.id,p.name,p.ws,q.save_data())
            self.assertEqual(again.mana,q.mana)

    def test_empty_mana_migrates_without_free_refill(self):
        p=self.player('mage');saved=p.save_data();saved.pop('mana_rules_version');saved['mana']=0
        q=self.g.load_player(p.id,p.name,p.ws,saved);self.assertEqual(q.mana,0)

    async def test_recovery_delay_survives_save_load(self):
        p=self.player('mage');await self.g.cast_spell(p,'longstrider');saved=p.save_data()
        q=self.g.load_player(p.id,p.name,p.ws,saved)
        self.assertEqual(q.mana_recovery_until,self.clock()+12);self.assertEqual(q.mana,20)

    def test_shield_needs_twenty_mana_and_delays_recovery(self):
        p=self.player('mage');p.shield_armed=True;p.mana=19
        self.assertFalse(self.g.shield_blocks_missiles(p));self.assertEqual(p.mana,19)
        p.mana=20;self.assertTrue(self.g.shield_blocks_missiles(p))
        self.assertEqual(p.mana,0);self.assertEqual(p.mana_recovery_until,self.clock()+12)


class LongstriderAndStatuses(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    async def test_lasts_exactly_six_hundred_game_rounds(self):
        p=self.player('mage');await self.g.cast_spell(p,'longstrider')
        started=self.clock();self.assertEqual(p.buffs['longstrider']['until'],started+1800)
        self.clock.advance(1799.99);p.current_wall_time=self.clock()
        self.assertTrue(rules.active_buff(p,'longstrider'))
        self.clock.advance(.01);p.current_wall_time=self.clock()
        self.assertFalse(rules.active_buff(p,'longstrider'))
        self.assertNotIn('longstrider',[s['id'] for s in p.public(self.clock())['status_effects']])

    async def test_basic_attacks_do_not_cancel_longstrider(self):
        p=self.player('mage');await self.g.cast_spell(p,'longstrider');until=p.buffs['longstrider']['until']
        self.clock.advance();self.g.hit_enemy(p,self.e)
        self.assertEqual(p.buffs['longstrider']['until'],until);self.assertFalse(p.concentration)

    async def test_damage_does_not_cancel_longstrider_or_require_its_concentration(self):
        p=self.player('mage',20);await self.g.cast_spell(p,'longstrider')
        self.g.combat_rng=base.Dice(20,1);self.g.hit_player(self.e,p)
        self.assertTrue(p.alive);self.assertIn('longstrider',p.buffs)
        self.assertFalse(p.concentration)

    async def test_another_concentration_spell_keeps_longstrider(self):
        p=self.player('druid',10);await self.g.cast_spell(p,'longstrider');until=p.buffs['longstrider']['until']
        self.clock.advance();self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',self.e.id)
        self.assertEqual(p.concentration,'entangle');self.assertEqual(p.buffs['longstrider']['until'],until)
        self.g.break_concentration(p)
        self.assertIn('longstrider',p.buffs)

    async def test_recast_refreshes_duration_without_stacking_speed(self):
        p=self.player('mage');base_speed=p.speed
        await self.g.cast_spell(p,'longstrider');buffed=p.speed
        surface_ratio=base_speed/player_speed(p.level)
        self.assertAlmostEqual(buffed-base_speed,dnd.LONGSTRIDER_SPEED_BONUS*surface_ratio)
        self.clock.advance();await self.g.cast_spell(p,'longstrider')
        self.assertEqual(p.speed,buffed);self.assertEqual(p.buffs['longstrider']['until'],self.clock()+1800)

    async def test_friendly_touch_range_and_pvp_support_rules(self):
        p=self.player('druid');q=self.player('knight',1,'2');p.party_id=q.party_id='team'
        q.x=p.x+150;mana=p.mana
        await self.g.cast_spell(p,'longstrider',target_id=q.id)
        self.assertNotIn('longstrider',q.buffs);self.assertEqual(p.mana,mana)
        q.x=p.x+50;await self.g.cast_spell(p,'longstrider',target_id=q.id)
        self.assertIn('longstrider',q.buffs);self.assertNotIn('longstrider',p.buffs)
        self.assertEqual(p.mana,mana-20)

    async def test_status_packet_has_seconds_rounds_description_and_no_owner_id(self):
        p=self.player('mage');await self.g.cast_spell(p,'longstrider')
        for private in (False,True):
            effect=next(s for s in p.public(self.clock(),private=private)['status_effects'] if s['id']=='longstrider')
            self.assertEqual(effect['remaining'],1800);self.assertEqual(effect['rounds'],600)
            self.assertFalse(effect['concentration']);self.assertTrue(effect['description'])
            self.assertEqual(effect['spell_id'],'longstrider');self.assertNotIn('owner',effect)

    async def test_target_enemy_effects_expire_and_expose_status_details(self):
        p=self.player('mage');await self.g.cast_spell(p,'ray_of_frost',self.e.id)
        effect=next(s for s in self.e.public(self.clock())['status_effects'] if s['id']=='slow')
        self.assertEqual(effect['rounds'],1);self.assertTrue(effect['harmful'])
        self.assertEqual(effect['spell_id'],'ray_of_frost')
        self.clock.advance()
        self.assertNotIn('slow',self.e.public(self.clock())['statuses'])
        self.assertFalse(self.e.public(self.clock())['status_effects'])

    async def test_target_player_effect_visible_in_public_pvp_snapshot(self):
        p=self.player('mage',20);q=self.player('knight',20,'2');q.x=1200;p.pvp_safety=False
        self.g.combat_rng=base.Dice(20,1)
        await self.g.cast_spell(p,'ray_of_frost',target_id=q.id)
        effects=q.public(self.clock())['status_effects']
        self.assertIn('slow',[s['id'] for s in effects])

    async def test_concentration_has_its_spell_name_and_remaining_rounds(self):
        p=self.player('druid');self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',self.e.id)
        effect=next(s for s in p.public(self.clock())['status_effects'] if s['id']=='concentration')
        self.assertIn('Oplątanie',effect['name']);self.assertEqual(effect['rounds'],10)
        self.assertEqual(effect['spell_id'],'entangle');self.assertTrue(effect['concentration'])

    async def test_armed_shield_is_not_mistaken_for_active_ac_buff(self):
        p=self.player('mage');await self.g.cast_spell(p,'shield')
        effect=p.public(self.clock())['status_effects'][0]
        self.assertEqual(effect['id'],'shield_ready');self.assertIsNone(effect['remaining'])
        self.assertNotIn('shield',p.buffs)

    async def test_forms_and_temporary_hp_have_visible_statuses(self):
        p=self.player('druid',40);await self.g.cast_spell(p,'wild_shape_bear')
        effects=p.public(self.clock())['status_effects'];ids={s['id'] for s in effects}
        self.assertIn('wild_shape',ids);self.assertIn('temp_hp',ids)


class ShorterInitialAggro(unittest.IsolatedAsyncioTestCase):
    setUp=pursuit.Pursuit.setUp
    tearDown=pursuit.Pursuit.tearDown
    enemy=pursuit.Pursuit.enemy
    step=pursuit.Pursuit.step

    def test_small_monsters_have_twenty_five_percent_lower_aggro(self):
        for kind in ('rat','wolf','goblin','spider','skeleton','bandit_archer','wisp'):
            spec=ENEMY_TYPES[kind]
            self.assertEqual(spec['aggro'],round(spec['base_aggro']*.75),kind)

    def test_medium_monsters_have_twelve_percent_lower_aggro(self):
        for kind in ('bear','ghoul'):
            spec=ENEMY_TYPES[kind]
            self.assertEqual(spec['aggro'],round(spec['base_aggro']*.88),kind)

    def test_strong_monsters_and_boss_keep_radius(self):
        for kind in ('guardian','ogre','boss'):
            spec=ENEMY_TYPES[kind]
            self.assertEqual(spec['aggro'],spec['base_aggro'],kind)

    def test_weak_monster_does_not_acquire_from_old_radius(self):
        self.p.x,self.p.y=self.e.x+330,self.e.y
        self.step()
        self.assertFalse(self.e.chase_id)
        self.p.x=self.e.x+260
        self.step()
        self.assertEqual(self.e.chase_id,self.p.id)

    def test_damage_still_provokes_beyond_new_initial_radius(self):
        self.p.x,self.p.y=self.e.x+500,self.e.y
        self.g.provoke_enemy(self.e,self.p)
        self.step()
        self.assertEqual(self.e.chase_id,self.p.id)

    def test_pursuit_does_not_end_at_new_aggro_boundary(self):
        self.p.x,self.p.y=self.e.x+250,self.e.y
        self.step();self.p.x=self.e.x+500;old=self.e.x
        self.step()
        self.assertEqual(self.e.chase_id,self.p.id)
        self.assertGreater(self.e.x,old)


if __name__=='__main__':unittest.main()
