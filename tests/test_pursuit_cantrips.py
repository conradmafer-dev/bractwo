"""0.8.2: no home-leash exploit, live spatial index, meaningful cantrips.

Movement tests use a flat, unobstructed arena unless the case explicitly tests
walls or real city protection. Damage tests call authoritative game actions.
"""
import asyncio
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_dnd as base
from server.server import Game, Player, Enemy, ENEMY_TYPES, ITEMS, make_item
from server import combat_rules as rules, dnd_content as dnd
from server.monster_ai import REGEN_DELAY_SECONDS, SIGHT_MEMORY_SECONDS, IDLE_REGEN_PER_SECOND


class Pursuit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = base.Clock()
        self.g = Game(':memory:', clock=self.clock)
        # Keep only our actors; no pre-existing encounters interfere with the arena.
        self.g.enemies.clear()
        self.g.legacy_enemies.clear()
        self.g.enemy_cells.clear()
        self.g.enemy_cell_keys.clear()
        self.g.chasing_enemies.clear()
        self.g.combat_rng = base.Dice(d20=1)
        self.g.time = 100
        self.p = Player('1', 'PursuitTester', base.WS(), level=100, x=10200, y=10000)
        self.p.hp = self.p.max_hp
        self.g.players[self.p.id] = self.p
        self.e = self.enemy()
        self.flat = patch.object(self.g, 'blocked', return_value=False)
        self.flat.start()

    def tearDown(self):
        self.flat.stop()
        self.g.db.close()

    def enemy(self, key='world_test', kind='wolf', x=10000, y=10000):
        e = Enemy(key, kind, x, y, ENEMY_TYPES[kind]['hp'], x, y)
        self.g.enemies[e.id] = e
        if not key.startswith('world_'):
            self.g.legacy_enemies.append(e)
        self.g.reindex_enemy(e)
        return e

    def step(self, ticks=1):
        for _ in range(ticks):
            self.clock.advance(.05)
            self.g.step(.05)

    def aggro(self):
        self.p.x, self.p.y = self.e.x+250, self.e.y
        self.step()
        self.assertEqual(self.e.chase_id, self.p.id)

    def test_spawn_boundary_does_not_break_chase(self):
        self.g.move(self.e, 800, 0)
        self.p.x, self.p.y = self.e.x+200, self.e.y
        self.assertGreater(self.p.x-self.e.home_x, ENEMY_TYPES[self.e.kind]['leash'])
        old = self.e.x
        self.step()
        self.assertGreater(self.e.x, old)
        self.assertEqual(self.e.chase_id, self.p.id)
        self.assertEqual(self.e.home_x, 10000)

    def test_relative_loss_distance_starts_local_search_not_immediate_return(self):
        self.aggro()
        self.g.move(self.e, 850, 0)
        self.p.x = self.e.x+ENEMY_TYPES[self.e.kind]['leash']+20
        position = (self.e.x, self.e.y)
        self.step(100)
        self.assertLessEqual(math.dist((self.e.x, self.e.y), position), 69)
        self.assertFalse(self.e.returning)
        self.assertFalse(self.e.chase_id)
        self.assertTrue(self.e.has_engaged)
        self.assertEqual((self.e.home_x, self.e.home_y), (10000, 10000))

    def test_waiting_monster_reacquires_from_current_position(self):
        self.aggro()
        self.g.move(self.e, 4000, 0)
        self.p.x = self.e.x+1200
        self.step()
        self.assertFalse(self.e.chase_id)
        old = self.e.x
        self.p.x = self.e.x+220
        self.step()
        self.assertEqual(self.e.chase_id, self.p.id)
        self.assertGreater(self.e.x, old)
        self.assertTrue(any(e['id']==self.e.id for e in self.g.snapshot(self.p)['enemies']))

    def test_repeated_old_boundary_crossings_never_force_retreat(self):
        self.aggro()
        self.g.move(self.e, 750, 0)
        for _ in range(20):
            self.p.x, self.p.y = self.e.x+250, self.e.y
            old = self.e.x
            self.step()
            self.assertGreater(self.e.x, old)
            self.assertEqual(self.e.chase_id, self.p.id)

    def test_long_chase_updates_index_without_duplicates(self):
        self.aggro()
        for _ in range(18):
            self.g.move(self.e, 700, 0)
            self.p.x, self.p.y = self.e.x+200, self.e.y
            self.step()
            queried = self.g.nearby_enemies(self.p, 400)
            self.assertEqual(sum(e is self.e for e in queried), 1)
            self.assertEqual(sum(self.e.id in bucket for bucket in self.g.enemy_cells.values()), 1)
            self.assertEqual(self.e.chase_id, self.p.id)
        at_spawn = SimpleNamespace(x=10000, y=10000, floor=0)
        self.assertNotIn(self.e, self.g.nearby_enemies(at_spawn, 100))

    def test_index_updates_on_spell_like_displacement(self):
        # All forced movement uses Game.move too, not only the AI mover.
        old_key = self.g.enemy_cell_keys[self.e.id]
        self.g.move(self.e, 3000, 1200)
        self.assertNotEqual(self.g.enemy_cell_keys[self.e.id], old_key)
        self.assertNotIn(old_key, self.g.enemy_cells)
        self.assertIn(self.e, self.g.nearby_enemies(self.e, 5))

    def test_boss_detects_pursued_target_across_two_cell_edges(self):
        self.e.kind = 'boss'
        self.e.x, self.e.y = 1024*10+1000, 10000
        self.g.reindex_enemy(self.e)
        self.p.x, self.p.y = self.e.x+1050, self.e.y
        self.assertEqual(int(self.p.x//1024)-int(self.e.x//1024), 2)
        self.g.provoke_enemy(self.e, self.p)
        old = self.e.x
        self.step()
        self.assertEqual(self.e.chase_id, self.p.id)
        self.assertGreater(self.e.x, old)

    def test_lose_target_on_death_without_return_or_attack_reset(self):
        self.aggro()
        pos = self.e.x, self.e.y
        self.e.ready = self.g.time+20
        ready = self.e.ready
        self.p.hp = 0
        self.p.respawn_until = self.clock()+100
        self.step()
        self.assertFalse(self.e.chase_id)
        self.assertEqual((self.e.x, self.e.y), pos)
        self.assertEqual(self.e.ready, ready)

    def test_lose_target_on_floor_change(self):
        self.aggro()
        self.p.floor = -1
        pos = self.e.x, self.e.y
        self.step()
        self.assertFalse(self.e.chase_id)
        self.assertEqual((self.e.x, self.e.y), pos)

    def test_lose_target_on_removal_even_outside_active_region(self):
        self.aggro()
        self.g.players.clear()
        pos = self.e.x, self.e.y
        self.step()
        self.assertFalse(self.e.chase_id)
        self.assertFalse(self.g.chasing_enemies)
        self.assertEqual((self.e.x, self.e.y), pos)

    def test_runaway_outside_simulation_drops_chase_then_waits(self):
        self.aggro()
        pos = self.e.x, self.e.y
        self.p.x += 10000
        self.step()
        self.assertFalse(self.g.chasing_enemies)
        self.assertFalse(self.e.chase_id)
        self.step(10)
        self.assertEqual((self.e.x, self.e.y), pos)

    def test_safe_city_stops_chase(self):
        self.aggro()
        self.g.move(self.e, 850-self.e.x, 1180-self.e.y)
        self.p.x, self.p.y = 560, 1180
        self.assertTrue(self.g.in_safe(self.p))
        pos = self.e.x, self.e.y
        self.step(20)
        self.assertFalse(self.e.chase_id)
        self.assertEqual((self.e.x, self.e.y), pos)

    def test_enemy_movement_cannot_enter_city(self):
        self.g.move(self.e, 850-self.e.x, 1180-self.e.y)
        self.g.move(self.e, -400, 0)
        self.assertFalse(self.g.in_safe(self.e))

    def test_last_seen_memory_expires_without_refresh_through_wall(self):
        self.aggro()
        last = self.e.last_seen_x, self.e.last_seen_y
        expiry = self.e.last_seen_until
        self.p.y += 100
        with patch.object(self.g, 'line_clear', return_value=False):
            self.step()
            self.assertEqual((self.e.last_seen_x, self.e.last_seen_y), last)
            self.assertEqual(self.e.last_seen_until, expiry)
            self.step(math.ceil(SIGHT_MEMORY_SECONDS/.05)+5)
            self.assertFalse(self.e.chase_id)
            stopped = self.e.x, self.e.y
            self.step(40)
            self.assertEqual((self.e.x, self.e.y), stopped)

    def test_fresh_monster_cannot_detect_through_wall(self):
        self.p.x = self.e.x+200
        with patch.object(self.g, 'line_clear', return_value=False):
            self.step()
        self.assertFalse(self.e.chase_id)
        self.assertFalse(self.e.has_engaged)

    def test_monsters_keep_initial_patrol_until_first_fight(self):
        self.p.x = self.e.x+1000
        pos = self.e.x, self.e.y
        self.step(100)
        self.assertFalse(self.e.has_engaged)
        self.assertGreater(math.dist(pos, (self.e.x, self.e.y)), 5)

    def test_losing_target_does_not_heal_and_delays_slow_recovery(self):
        self.aggro()
        self.e.hp = 3
        self.p.x = self.e.x+1200
        self.step()
        pos = self.e.x, self.e.y
        self.step(200)  # 10 s of disengagement: still no regen.
        self.assertEqual(self.e.hp, 3)
        self.step(80)  # After 12 s: only the ordinary 0.25 HP / s.
        self.assertGreater(self.e.hp, 3)
        self.assertLess(self.e.hp, 3.6)
        self.assertLessEqual(math.dist((self.e.x, self.e.y), pos), 69)
        self.assertFalse(self.e.returning)

    def test_reengagement_blocks_recovery_and_does_not_reset_cooldowns(self):
        self.aggro()
        self.e.hp = 3
        self.p.x = self.e.x+1200
        self.step(200)
        self.e.ready = self.g.time+20
        ready = self.e.ready
        self.p.x = self.e.x+200
        self.step(80)
        self.assertEqual(self.e.hp, 3)
        self.assertEqual(self.e.ready, ready)

    def test_zero_hp_enemy_neither_moves_nor_regenerates(self):
        self.aggro()
        pos = self.e.x, self.e.y
        self.e.hp = 0
        self.p.x += 1000
        self.step(260)
        self.assertEqual(self.e.hp, 0)
        self.assertEqual((self.e.x, self.e.y), pos)

    async def test_pending_death_finalizes_after_all_players_leave(self):
        self.aggro()
        self.e.hp = 0
        self.g.players.clear()
        await self.g.process_player_actions()
        self.assertFalse(self.e.alive)
        self.assertNotIn(self.e.id, self.g.chasing_enemies)

    async def test_far_death_respawns_at_original_location_not_waiting_point(self):
        self.aggro()
        home = self.e.home_x, self.e.home_y
        self.g.move(self.e, 4000, 0)
        self.e.hp = 0
        await self.g.defeat(self.e)
        self.assertEqual(self.g.enemy_cell_keys[self.e.id], (0, int(home[0]//1024), int(home[1]//1024)))
        self.p.x, self.p.y = home[0]+600, home[1]
        self.g.time = self.e.respawn_at+.1
        self.step()
        self.assertTrue(self.e.alive)
        self.assertEqual((self.e.x, self.e.y), home)
        self.assertEqual(self.e.hp, self.e.max_hp)
        self.assertFalse(self.e.has_engaged)
        self.assertFalse(self.e.chase_id)
        self.assertIn(self.e, self.g.nearby_enemies(self.p, 1000))

    def test_legacy_monsters_also_hold_after_loss(self):
        legacy = self.enemy('legacy_hold', x=14000)
        self.p.x, self.p.y = 14200, 10000
        self.step()
        self.assertEqual(legacy.chase_id, self.p.id)
        self.p.x += 1500
        pos = legacy.x, legacy.y
        self.step(10)
        self.assertEqual((legacy.x, legacy.y), pos)
        self.assertFalse(legacy.chase_id)

    def test_new_player_can_take_over_when_first_target_leaves(self):
        self.aggro()
        q = Player('2', 'NewTarget', base.WS(), level=100, x=self.e.x+260, y=self.e.y)
        q.hp = q.max_hp
        self.g.players[q.id] = q
        self.p.x += 10000
        self.step()
        self.assertEqual(self.e.chase_id, q.id)

    def test_pet_is_valid_target_and_disappearance_ends_pursuit(self):
        from server.dnd_game import Companion
        self.p.x = self.e.x+1000
        pet = Companion('pet:1', self.p.id, 'Wilk', self.e.x+200, self.e.y, 0, 25, 25, 4, 13, (2,4,2))
        self.g.companions[self.p.id] = pet
        self.g.provoke_enemy(self.e, pet)
        self.step()
        self.assertEqual(self.e.chase_id, pet.id)
        self.g.companions.clear()
        pos = self.e.x, self.e.y
        self.step()
        self.assertFalse(self.e.chase_id)
        self.assertEqual((self.e.x, self.e.y), pos)

    def test_melee_ranged_hybrid_and_boss_all_hold_after_loss(self):
        for kind in ('rat','wolf','bandit_archer','goblin','wisp','boss','lich_king'):
            with self.subTest(kind=kind):
                self.g.stop_enemy_chase(self.e)
                self.e.kind = kind
                self.e.hp = self.e.max_hp
                self.p.x, self.p.y = self.e.x+200, self.e.y
                self.g.provoke_enemy(self.e, self.p)
                self.step()
                self.assertEqual(self.e.chase_id, self.p.id)
                pos = self.e.x, self.e.y
                self.p.x = self.e.x+ENEMY_TYPES[kind]['leash']+30
                self.step(50)
                self.assertFalse(self.e.chase_id)
                self.assertEqual((self.e.x, self.e.y), pos)

    def test_tactical_ranged_step_not_bound_to_original_spawn(self):
        self.e.kind = 'bandit_archer'
        self.g.move(self.e, 4000, 0)
        self.p.x, self.p.y = self.e.x+70, self.e.y
        old = self.e.x
        self.step()
        self.assertLess(self.e.x, old)
        self.assertEqual(self.e.chase_id, self.p.id)


class CantripBalance(unittest.IsolatedAsyncioTestCase):
    setUp = base.GameRules.setUp
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    async def test_spark_is_fixed_but_fire_bolt_scales_and_remains_free(self):
        self.g.combat_rng = base.Dice(d20=15, die=10)
        self.e.x = 1300
        for level, count in ((1,1),(19,1),(20,2),(49,2),(50,3),(79,3),(80,4),(10000,4)):
            with self.subTest(level=level):
                p = self.player('mage', level)
                p.mana = 0
                self.e.hp = 999
                await self.g.attack(p, enemy_id=self.e.id)
                self.assertEqual(self.e.hp, 995)
                self.assertEqual(p.last_roll['damage_dice'], '1k4')
                self.assertEqual(p.last_roll['action'], 'Iskra różdżki')
                self.clock.advance()
                await self.g.cast_spell(p, 'fire_bolt', self.e.id)
                self.assertEqual(self.e.hp, 995-count*10)
                self.assertEqual(p.last_roll['damage_dice'], f'{count}k10')
                self.assertEqual(p.last_roll['action'], 'Ognisty pocisk')
                self.assertEqual(p.mana, 0)

    async def test_critical_spark_rolls_two_d4_not_two_d10(self):
        p = self.player('mage')
        self.e.x = 1300
        self.g.combat_rng = base.Dice(d20=20, die=20)
        await self.g.attack(p, enemy_id=self.e.id)
        self.assertTrue(p.last_roll['critical'])
        self.assertEqual(self.e.hp, 991)
        self.assertEqual(p.last_roll['damage_rolls'], [4,4])

    async def test_spark_and_cantrip_share_action_no_double_damage(self):
        p = self.player('mage', 1)
        self.e.x = 1300
        await self.g.attack(p, enemy_id=self.e.id)
        before = self.e.hp
        await self.g.cast_spell(p, 'fire_bolt', self.e.id)
        self.assertEqual(self.e.hp, before)
        self.assertEqual(p.pending_spell['spell'], 'fire_bolt')
        self.clock.advance()
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp, before-3)

    async def test_queued_cantrip_follows_manual_spark_without_auto_resuming(self):
        p = self.player('mage', 20)
        self.e.x = 1300
        self.g.combat_rng = base.Dice(d20=15, die=10)
        await self.g.select_combat_target(p, {'enemy_id':self.e.id})
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp, 999)
        await self.g.attack(p, enemy_id=self.e.id)
        self.assertEqual(self.e.hp, 995)
        await self.g.cast_spell(p, 'fire_bolt', self.e.id)
        self.clock.advance()
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp, 975)  # 20, not 20+4; only one action.
        self.assertEqual(p.last_roll['action'], 'Ognisty pocisk')
        self.clock.advance()
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp, 975)  # Wand never resumes unsolicited sparks.

    async def test_spark_and_cantrip_balance_same_in_unlocked_pvp(self):
        p = self.player('mage', 20)
        q = self.player('knight', 100, '2')
        q.x = 1300
        self.e.alive = False
        p.pvp_safety = False
        self.g.combat_rng = base.Dice(d20=15, die=10)
        hp = q.hp
        await self.g.attack(p, target_id=q.id)
        self.assertEqual(q.hp, hp-4)
        self.clock.advance()
        await self.g.cast_spell(p, 'fire_bolt', target_id=q.id)
        self.assertEqual(q.hp, hp-24)
        self.assertGreater(q.aggressors.get(p.id, 0), self.clock())

    async def test_pvp_lock_still_blocks_both_spark_and_cantrip(self):
        p = self.player('mage', 20)
        q = self.player('knight', 100, '2')
        q.x = 1300
        hp = q.hp
        await self.g.attack(p, target_id=q.id)
        await self.g.cast_spell(p, 'fire_bolt', target_id=q.id)
        self.assertEqual(q.hp, hp)
        self.assertEqual(p.attack_cooldown_until, 0)

    def test_all_wands_have_correct_dice_and_no_false_damage_bonus(self):
        items = [i for i in ITEMS.values() if i.get('slot')=='weapon' and i.get('class_ids')==['mage']]
        self.assertGreater(len(items), 10)
        for i in items:
            self.assertEqual(i['damage_dice'], '1k4')
            self.assertEqual(i['attack'], 0)
            self.assertIn('bez skalowania', i['description'])
        self.assertTrue(any(i['attack_bonus'] > 0 for i in items))

    def test_focus_still_improves_spell_accuracy_not_spark_damage(self):
        p = self.player('mage', 100)
        before = rules.spell_bonus(p)
        weapon = make_item('mage_weapon_9')
        p.inventory.append(weapon)
        p.equipment['weapon'] = weapon['uid']
        self.assertGreater(rules.spell_bonus(p), before)
        self.assertEqual(rules.weapon_dice(p), (1,4,0))
        self.assertEqual(p.public(self.clock(), self.g.time, True)['damage_dice'], '1k4')

    async def test_frost_cantrip_keeps_distinct_slow_and_scaling(self):
        p = self.player('mage', 20)
        self.e.x = 1300
        self.g.combat_rng = base.Dice(d20=15, die=10)
        await self.g.cast_spell(p, 'ray_of_frost', self.e.id)
        self.assertEqual(self.e.hp, 999-16)
        self.assertEqual(p.last_roll['damage_dice'], '2k8')
        self.assertTrue(self.g.enemy_condition(self.e, 'slow'))

    def test_other_classes_dice_unchanged(self):
        for cls, expected in (('knight',(1,8,3)), ('ranger',(1,8,3)), ('druid',(1,6,2))):
            self.assertEqual(rules.weapon_dice(self.player(cls)), expected)

    async def test_miss_still_engages_monster_and_suppresses_patrol(self):
        p = self.player('mage')
        self.g.combat_rng = base.Dice(d20=1)
        await self.g.attack(p, enemy_id=self.e.id)
        self.assertEqual(self.e.hp, 999)
        self.assertTrue(self.e.has_engaged)
        self.assertIn(self.e.id, self.g.chasing_enemies)
        self.assertGreater(self.e.regen_at, self.g.time)
