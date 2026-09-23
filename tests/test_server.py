"""Protocol and authority checks for the open-world RPG 0.3.

Run: python -m unittest discover -s tests -v
Real local WebSockets and a disposable SQLite database are used. Fixture positions,
levels and inventory isolate individual rules; attacks, trading and party actions
always travel through the same protocol as a client.
"""

import asyncio
import contextlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest import mock

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import server as server_module


class Clock:
    def __init__(self):
        self.value = 1_800_000_000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class AuthoritativeServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="open-world-test-")
        self.db_path = str(Path(self.directory.name) / "world.sqlite3")
        self.clock = Clock()
        self.client = None
        await self.start_server()

    async def asyncTearDown(self):
        if self.client is not None:
            await self.client.close()
        self.directory.cleanup()

    async def start_server(self):
        self.app = server_module.create_app(self.db_path, clock=self.clock)
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()
        self.game = self.app["game"]
        # Run deterministic steps explicitly; HTTP/WebSocket processing stays live.
        self.game.task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.game.task

    async def restart(self):
        await self.client.close()
        self.client = None
        await self.start_server()

    async def packet(self, ws, kind, predicate=None):
        async with asyncio.timeout(3):
            while True:
                message = await ws.receive()
                self.assertEqual(message.type, WSMsgType.TEXT, str(message))
                data = json.loads(message.data)
                if data.get("type") == kind and (predicate is None or predicate(data)):
                    return data

    async def connect(self, name, *, create=True, password="testpass123", class_id="knight"):
        ws = await self.client.ws_connect("/ws")
        await ws.send_json({"type": "hello", "name": name, "password": password,
                            "create": create, "class_id": class_id})
        welcome = await self.packet(ws, "welcome")
        return ws, self.game.players[welcome["id"]], welcome

    async def sync(self, ws):
        await ws.send_json({"type": "ping"})
        await self.packet(ws, "pong")

    async def command(self, ws, kind, **data):
        await ws.send_json({"type": kind, **data})
        await self.sync(ws)

    def state(self, player):
        return next(p for p in self.game.snapshot(for_player=player)["players"]
                    if p["id"] == player.id)

    def place(self, player, x=1200, y=1800, level=None):
        player.x, player.y = float(x), float(y)
        if level is not None:
            player.level = level
            player.hp, player.mana = player.max_hp, player.max_mana
        return player

    def elapsed(self, seconds):
        self.clock.advance(seconds)
        self.game.step(.05)

    def enemy_fixture(self, player, kind="wolf", hp=None, offset=55):
        enemy = next(e for e in self.game.enemies.values() if e.kind == kind)
        enemy.x, enemy.y = player.x + offset, player.y
        enemy.hp = enemy.max_hp if hp is None else hp
        enemy.alive = True
        enemy.contributors.clear()
        enemy.ready = enemy.aoe_ready = self.game.time + 1_000
        return enemy

    def give_item(self, player, template):
        # Inventory fixtures use the documented wire/save shape, not stat overrides.
        item = dict(self.game.metadata()["items"][template])
        item.update(uid="fixture-" + player.id + "-" + str(len(player.inventory)), template=template)
        player.inventory.append(item)
        return item

    async def disconnect(self, ws, player, *, remains=False):
        await ws.close()
        async with asyncio.timeout(2):
            while (player.id in self.game.players and
                   self.game.players[player.id].ws is not None):
                await asyncio.sleep(.005)
        self.assertEqual(player.id in self.game.players, remains)

    async def test_two_clients_share_world_but_never_private_inventory_or_credentials(self):
        first, p1, _ = await self.connect("ExplorerOne")
        second, p2, _ = await self.connect("ExplorerTwo", class_id="druid")
        # Exercise actual personalized periodic broadcasts, not only a helper.
        self.game.task = asyncio.create_task(self.game.run())
        ids = {p1.id, p2.id}
        for ws, own in ((first, p1), (second, p2)):
            snapshot = await self.packet(ws, "state", lambda data: ids <= {
                p["id"] for p in data["players"]})
            self.assertNotIn("testpass123", json.dumps(snapshot))
            for player in snapshot["players"]:
                self.assertFalse({"password", "password_hash", "salt"} & player.keys())
                if player["id"] == own.id:
                    self.assertIn("inventory", player)
                    self.assertIn("potions", player)
                    self.assertIn("quests", player)
                    self.assertIn("discoveries", player)
                else:
                    self.assertNotIn("inventory", player)
                    self.assertNotIn("potions", player)
                    self.assertNotIn("quests", player)
                    self.assertNotIn("discoveries", player)

    async def test_authentication_required_wrong_password_and_duplicate_session_rejected(self):
        anonymous = await self.client.ws_connect("/ws")
        await anonymous.send_json({"type": "attack"})
        await self.packet(anonymous, "error")
        self.assertFalse(self.game.players)
        owner, player, _ = await self.connect("AccountOwner")
        for password in ("incorrect-password", "testpass123"):
            other = await self.client.ws_connect("/ws")
            await other.send_json({"type": "hello", "name": "AccountOwner",
                                   "password": password, "create": False})
            await self.packet(other, "error")
            await other.close()
        self.assertEqual(set(self.game.players), {player.id})
        await self.sync(owner)

    async def test_untrusted_input_cannot_teleport_change_stats_or_multiply_speed(self):
        ws, player, _ = await self.connect("SpeedTester")
        self.place(player)
        before = (player.x, player.y, player.hp, player.xp, player.gold)
        await self.command(ws, "input", x=0, y=0, position={"x": 2999, "y": 1999},
                           hp=999999, xp=999999, gold=999999, speed=999999, level=999999, class_id="mage")
        self.assertEqual((player.x, player.y, player.hp, player.xp, player.gold), before)
        self.assertEqual(player.class_id, "knight")
        await self.command(ws, "input", x=1_000_000, y=1_000_000)
        self.game.step(.05)
        distance = math.hypot(player.x-before[0], player.y-before[1])
        self.assertGreater(distance, 0)
        self.assertLessEqual(distance, self.state(player)["speed"]*.05 + 1e-5)

    async def test_malformed_packets_leave_finite_live_character(self):
        ws, player, _ = await self.connect("PacketTester")
        for raw in ("{broken-json", "[]", "null", "42",
                    '{"type":"input","x":"wrong","y":0}',
                    '{"type":"input","x":NaN,"y":0}'):
            await ws.send_str(raw)
            await self.sync(ws)
            self.assertTrue(math.isfinite(player.x) and math.isfinite(player.y))
        self.assertIn(player.id, self.game.players)

    async def test_four_classes_have_distinct_stats_and_permanent_choice(self):
        stats = {}
        for class_id in ("knight", "paladin", "mage", "druid"):
            ws, player, welcome = await self.connect("Class" + class_id, class_id=class_id)
            state = self.state(player)
            self.assertEqual(state["class_id"], class_id)
            self.assertTrue(state["class_chosen"])
            self.assertGreater(state["max_mana"], 0)
            self.assertTrue(state["ability_name"])
            stats[class_id] = state
            await self.command(ws, "choose_class", class_id="mage" if class_id != "mage" else "knight")
            await self.command(ws, "weapon", weapon="staff")
            self.assertEqual(player.class_id, class_id)
            self.assertEqual(set(welcome["world"]["classes"]), {"knight", "paladin", "mage", "druid"})
        self.assertGreater(stats["knight"]["max_hp"], stats["mage"]["max_hp"])
        self.assertGreater(stats["mage"]["max_mana"], stats["knight"]["max_mana"])
        self.assertEqual(stats["paladin"]["weapon"], "bow")

    async def test_high_levels_keep_advancing_without_a_fixed_cap(self):
        _, player, _ = await self.connect("Veteran")
        player.level = 1000
        player.xp = server_module.xp_next(player.level)-1
        previous_max = player.max_hp
        self.game.award(player, 2, 0)
        self.assertEqual(player.level, 1001)
        self.assertEqual(player.xp, 1)
        self.assertGreater(player.max_hp, previous_max)
        self.assertGreater(server_module.xp_next(1002), server_module.xp_next(1001))

    async def test_bridge_and_dungeon_are_open_without_relics_but_river_blocks(self):
        ws, player, welcome = await self.connect("OpenMap")
        self.assertFalse(welcome["world"].get("chests"))
        self.assertFalse(self.game.blocked(1590, 1152))
        self.assertFalse(self.game.blocked(2515, 1475))
        self.assertTrue(self.game.blocked(1590, 950))
        for x, y, dx, dy, boundary in ((1470, 1152, 1, 0, 1700),
                                     (2515, 1410, 0, 1, 1530)):
            self.place(player, x, y)
            for frame in range(52 if dx else 29):
                if frame % 6 == 0:
                    await self.command(ws, "input", x=dx, y=dy)
                self.game.step(.05)
            self.assertGreater(player.x if dx else player.y, boundary)
        await self.command(ws, "input", x=0, y=0)
        before = (player.level, player.xp, player.gold)
        await self.command(ws, "relic", relic="roots")
        self.assertEqual((player.level, player.xp, player.gold), before)

    async def test_boss_respawn_rewards_each_kill_once(self):
        ws, player, _ = await self.connect("RepeatBoss")
        self.place(player, 2500, 1900, level=10)
        boss = self.enemy_fixture(player, "boss", hp=1, offset=40)
        await self.command(ws, "attack")
        self.assertFalse(boss.alive)
        self.assertEqual(player.boss_kills, 1)
        rewarded = (player.level, player.xp, player.gold, player.kills, len(player.inventory))
        await self.game.defeat(boss)
        await self.command(ws, "attack")
        self.assertEqual((player.level, player.xp, player.gold, player.kills, len(player.inventory)), rewarded)
        # Expire the real respawn timer: no fixture resurrection of this encounter.
        for _ in range(2500):
            self.clock.advance(.05)
            self.game.step(.05)
            if boss.alive:
                break
        self.assertTrue(boss.alive, "Boss must respawn for repeat farming")
        self.place(player, boss.x-40, boss.y)
        boss.hp = 1
        self.elapsed(2)
        await self.command(ws, "attack")
        self.assertFalse(boss.alive)
        self.assertEqual(player.boss_kills, 2)
        self.assertGreater(player.gold, rewarded[2])

    async def test_login_uses_progress_saved_while_password_hash_is_running(self):
        old_ws, player, _ = await self.connect("LoginRaceHero")
        player.gold, player.xp = 3, 2
        self.game.persist()
        next_ws = await self.client.ws_connect("/ws")
        hash_started, resume_hash = threading.Event(), threading.Event()
        original_hash = self.game.password_hash

        def paused_hash(password, salt):
            hash_started.set()
            if not resume_hash.wait(timeout=5):
                raise RuntimeError("Test did not release password hash worker")
            return original_hash(password, salt)

        with mock.patch.object(self.game, "password_hash", side_effect=paused_hash):
            try:
                await next_ws.send_json({"type": "hello", "name": "LoginRaceHero",
                                         "password": "testpass123", "create": False})
                self.assertTrue(await asyncio.to_thread(hash_started.wait, 2))
                player.gold, player.xp = 321, 17
                await self.disconnect(old_ws, player)
            finally:
                resume_hash.set()
            welcome = await self.packet(next_ws, "welcome")
        saved = self.game.players[welcome["id"]]
        self.assertEqual((saved.gold, saved.xp), (321, 17))


    async def test_pvp_requires_explicit_target_safety_off_maturity_and_outside_town(self):
        ws1, first, _ = await self.connect("PeacefulOne")
        ws2, second, _ = await self.connect("PeacefulTwo")
        self.place(first, 1200, 1800, level=8)
        self.place(second, 1250, 1800, level=8)
        original = second.hp
        await self.command(ws1, "attack", target_id=second.id)
        self.assertEqual(second.hp, original, "Safety defaults to enabled")
        await self.command(ws1, "pvp_safety", enabled=False)
        self.elapsed(2)
        await self.command(ws1, "attack")
        self.assertEqual(second.hp, original, "PvE auto-target must never select a player")
        second.level = 7
        self.elapsed(2)
        await self.command(ws1, "attack", target_id=second.id)
        self.assertEqual(second.hp, original, "Characters below level 8 are protected")
        second.level = 8
        first.level = 7
        self.elapsed(2)
        await self.command(ws1, "attack", target_id=second.id)
        self.assertEqual(second.hp, original, "Protected beginners cannot initiate PvP")
        self.place(first, 560, 1180, level=8)
        self.place(second, 610, 1180, level=8)
        self.elapsed(2)
        await self.command(ws1, "attack", target_id=second.id)
        self.assertEqual(second.hp, second.max_hp, "Town is a safe zone")
        self.place(first, 1200, 1800)
        self.place(second, 1250, 1800)
        self.elapsed(2)
        await self.command(ws1, "attack", target_id=second.id)
        self.assertLess(second.hp, second.max_hp)
        self.assertEqual(self.state(first)["skull"], "white")
        self.assertEqual(self.state(second)["skull"], "none")
        self.assertGreater(self.state(first)["combat_remaining"], 0)
        self.assertGreater(self.state(second)["combat_remaining"], 0)

    async def test_retaliation_against_marked_attacker_is_clean_and_killer_gets_no_xp(self):
        attacker_ws, attacker, _ = await self.connect("Aggressor")
        victim_ws, victim, _ = await self.connect("Defender")
        self.place(attacker, 1200, 1800, level=10)
        self.place(victim, 1250, 1800, level=10)
        await self.command(attacker_ws, "pvp_safety", enabled=False)
        await self.command(victim_ws, "pvp_safety", enabled=False)
        await self.command(attacker_ws, "attack", target_id=victim.id)
        self.assertEqual(self.state(attacker)["skull"], "white")
        hp = attacker.hp
        await self.command(victim_ws, "attack", target_id=attacker.id)
        self.assertLess(attacker.hp, hp)
        self.assertEqual(self.state(victim)["skull"], "none")
        victim.hp, victim.gold, victim.xp = 1, 200, 50
        attacker.gold, attacker.xp = 41, 7
        self.elapsed(2)
        await self.command(attacker_ws, "attack", target_id=victim.id)
        self.assertFalse(victim.alive)
        self.assertEqual(self.state(attacker)["unjust_kills"], 1,
                         "A victim defending itself does not justify its murder")
        self.assertEqual((attacker.xp, attacker.gold), (7, 41))
        self.assertEqual((victim.xp, victim.gold), (45, 190))
        self.assertEqual(victim.level, 10, "Death removes progress, never a level")

    async def test_three_unjust_kills_make_persistent_red_skull_and_restart_does_not_expire_it(self):
        attacker_ws, attacker, _ = await self.connect("SerialAttacker")
        self.place(attacker, 1200, 1800, level=12)
        await self.command(attacker_ws, "pvp_safety", enabled=False)
        for index in range(3):
            _, victim, _ = await self.connect("CrimeVictim" + str(index))
            self.place(victim, 1250, 1800, level=8)
            victim.hp = 1
            self.elapsed(2)
            await self.command(attacker_ws, "attack", target_id=victim.id)
            self.assertFalse(victim.alive)
            self.assertEqual(self.state(attacker)["unjust_kills"], index+1)
        state = self.state(attacker)
        self.assertEqual(state["skull"], "red")
        self.assertGreater(state["skull_remaining"], 23*60*60)
        await self.restart()
        attacker_ws, attacker, _ = await self.connect("SerialAttacker", create=False)
        state = self.state(attacker)
        self.assertEqual(state["skull"], "red")
        self.assertEqual(state["unjust_kills"], 3)
        self.assertTrue(state["pvp_safety"], "Reconnect restores the safety switch")
        # A clean character may defend against an already-red aggressor.
        defender_ws, defender, _ = await self.connect("RedDefender")
        self.place(attacker, 1200, 1800)
        self.place(defender, 1250, 1800, level=12)
        await self.command(attacker_ws, "pvp_safety", enabled=False)
        await self.command(defender_ws, "pvp_safety", enabled=False)
        self.elapsed(2)
        await self.command(attacker_ws, "attack", target_id=defender.id)
        await self.command(defender_ws, "attack", target_id=attacker.id)
        self.assertEqual(self.state(defender)["skull"], "none")
        defender.hp = 1
        self.elapsed(2)
        await self.command(attacker_ws, "attack", target_id=defender.id)
        self.assertFalse(defender.alive)
        self.assertEqual(self.state(attacker)["unjust_kills"], 4)
        self.assertGreater(self.state(attacker)["skull_remaining"], 23*60*60)

    async def test_combat_logout_leaves_targetable_avatar_and_reconnect_preserves_damage(self):
        attacker_ws, attacker, _ = await self.connect("LogoutAttacker")
        victim_ws, victim, _ = await self.connect("LogoutVictim")
        self.place(attacker, 1200, 1800, level=10)
        self.place(victim, 1250, 1800, level=10)
        await self.command(attacker_ws, "pvp_safety", enabled=False)
        await self.command(attacker_ws, "attack", target_id=victim.id)
        damaged_hp = victim.hp
        await self.disconnect(victim_ws, victim, remains=True)
        self.assertTrue(self.state(victim)["disconnected"])
        self.elapsed(2)
        await self.command(attacker_ws, "attack", target_id=victim.id)
        self.assertLess(victim.hp, damaged_hp, "The disconnected avatar remains targetable")
        before = (victim.x, victim.y, victim.hp)
        victim_ws, restored, _ = await self.connect("LogoutVictim", create=False)
        self.assertIs(restored, victim)
        self.assertEqual((restored.x, restored.y, restored.hp), before)
        self.assertFalse(self.state(restored)["disconnected"])
        # Move a tagged victim to the outer safe-zone boundary, then try to enter.
        self.place(victim, 825, 1180)
        await self.command(victim_ws, "input", x=-1, y=0)
        self.game.step(.05)
        self.assertGreaterEqual(math.hypot(victim.x-560, victim.y-1180), 260)
        await self.command(victim_ws, "input", x=0, y=0)
        await self.disconnect(victim_ws, victim, remains=True)
        self.elapsed(21)
        self.assertNotIn(victim.id, self.game.players,
                         "An offline avatar can leave only when combat expires")


    async def test_class_abilities_spend_mana_have_cooldowns_and_fulfil_combat_roles(self):
        ws, knight, _ = await self.connect("ShieldKnight", class_id="knight")
        self.place(knight, level=8)
        self.game.damage_player(knight, 60)
        ordinary_loss = knight.max_hp-knight.hp
        knight.hp = knight.max_hp
        shield_target = self.enemy_fixture(knight)
        mana = knight.mana
        await self.command(ws, "ability")
        self.assertLess(knight.mana, mana)
        self.game.damage_player(knight, 60)
        self.assertLess(knight.max_hp-knight.hp, ordinary_loss)
        after = knight.mana
        await self.command(ws, "ability")
        self.assertEqual(knight.mana, after, "Cooldown must reject repeated spending/casting")
        self.assertGreater(self.state(knight)["ability_cooldown"], 0)
        shield_target.alive = False

        ws, paladin, _ = await self.connect("StrongArcher", class_id="paladin")
        self.place(paladin)
        boss = self.enemy_fixture(paladin, "boss", offset=100)
        hp = boss.hp
        await self.command(ws, "attack")
        normal_damage = hp-boss.hp
        self.assertGreater(normal_damage, 0)
        hp, mana = boss.hp, paladin.mana
        await self.command(ws, "ability")
        self.assertGreater(hp-boss.hp, normal_damage)
        self.assertLess(paladin.mana, mana)

        ws, mage, _ = await self.connect("AreaMage", class_id="mage")
        self.place(mage)
        first = self.enemy_fixture(mage, "wolf", offset=50)
        second = self.enemy_fixture(mage, "wisp", offset=80)
        mana = mage.mana
        bystander_hp = knight.hp
        await self.command(ws, "ability")
        self.assertLess(first.hp, first.max_hp)
        self.assertLess(second.hp, second.max_hp)
        self.assertLess(mage.mana, mana)
        self.assertEqual(knight.hp, bystander_hp, "PvE AoE must not hit players")

    async def test_party_requires_acceptance_shares_only_nearby_xp_and_druid_heals_party(self):
        leader_ws, leader, _ = await self.connect("PartyKnight")
        support_ws, support, _ = await self.connect("PartyDruid", class_id="druid")
        distant_ws, distant, _ = await self.connect("PartyRemote", class_id="mage")
        outsider_ws, outsider, _ = await self.connect("PartyOutsider")
        self.place(leader, 1200, 1800)
        self.place(support, 1240, 1800)
        self.place(outsider, 1260, 1800)
        self.place(distant, 2800, 1100)
        await self.command(support_ws, "party_accept", leader_id=leader.id)
        self.assertFalse(self.state(support)["party_id"], "An unsolicited acceptance is rejected")
        for member_ws, member in ((support_ws, support), (distant_ws, distant)):
            await self.command(leader_ws, "party_invite", target_id=member.id)
            invite = await self.packet(member_ws, "party_invite")
            self.assertEqual(invite["leader_id"], leader.id)
            await self.command(member_ws, "party_accept", leader_id=leader.id)
            self.assertEqual(self.state(member)["party_id"], leader.id)
        boss = self.enemy_fixture(leader, "wolf", hp=1)
        await self.command(leader_ws, "attack")
        self.assertFalse(boss.alive)
        self.assertGreater(leader.xp, 0)
        self.assertGreater(support.xp, 0, "Nearby support shares experience without dealing damage")
        self.assertGreater(leader.xp + support.xp, server_module.ENEMY_TYPES["wolf"]["xp"])
        self.assertEqual(distant.xp, 0)
        self.assertEqual(outsider.xp, 0)
        for player in (leader, support, outsider):
            player.hp = 10
        mana = support.mana
        await self.command(support_ws, "ability")
        self.assertGreater(leader.hp, 10)
        self.assertGreater(support.hp, 10)
        self.assertEqual(outsider.hp, 10)
        self.assertLess(support.mana, mana)
        hp_after, mana_after = leader.hp, support.mana
        await self.command(support_ws, "ability")
        self.assertEqual((leader.hp, support.mana), (hp_after, mana_after))
        await self.command(support_ws, "party_leave")
        self.assertFalse(self.state(support)["party_id"])
        self.assertNotIn(support.id, self.state(leader)["party_members"])


    async def test_legacy_save_preserves_progress_and_allows_exactly_one_class_choice_in_town(self):
        ws, player, _ = await self.connect("LegacyHero")
        pid = player.id
        await self.disconnect(ws, player)
        old_save = {"x": 560, "y": 1180, "hp": 90, "level": 7, "xp": 17,
                    "gold": 321, "weapon": "staff", "kills": 40, "boss_kills": 1,
                    "relics": ["roots", "heart"], "chests": ["roots_chest"],
                    "heart_cooldown_until": 0, "attack_cooldown_until": 0}
        with self.game.db:
            self.game.db.execute("UPDATE accounts SET data=? WHERE id=?", (json.dumps(old_save), pid))
        await self.restart()
        ws, player, _ = await self.connect("LegacyHero", create=False)
        state = self.state(player)
        self.assertEqual((player.level, player.xp, player.gold), (7, 17, 321))
        self.assertFalse(state["class_chosen"])
        self.assertFalse(state.get("relics"))
        self.place(player)
        await self.command(ws, "choose_class", class_id="druid")
        self.assertFalse(self.state(player)["class_chosen"])
        self.place(player, 560, 1180)
        await self.command(ws, "choose_class", class_id="druid")
        self.assertEqual(player.class_id, "druid")
        self.assertTrue(self.state(player)["class_chosen"])
        await self.command(ws, "choose_class", class_id="mage")
        self.assertEqual(player.class_id, "druid")
        await self.restart()
        _, player, _ = await self.connect("LegacyHero", create=False)
        self.assertEqual((player.level, player.xp, player.gold, player.class_id), (7, 17, 321, "druid"))
        self.assertTrue(self.state(player)["class_chosen"])


    async def test_equipment_enforces_owner_class_level_and_changes_actual_damage(self):
        ws, player, welcome = await self.connect("EquipmentKnight")
        self.place(player, level=30)
        items = welcome["world"]["items"]
        knight_templates = [(key, spec) for key, spec in items.items()
                            if spec["slot"] == "weapon" and "knight" in spec["class_ids"] and spec["min_level"] <= player.level]
        strongest = max(knight_templates, key=lambda entry: entry[1].get("attack", 0))[0]
        weapon = self.give_item(player, strongest)
        foreign_key = next(key for key, spec in items.items()
                           if spec["slot"] == "weapon" and "knight" not in spec["class_ids"])
        foreign = self.give_item(player, foreign_key)
        boss = self.enemy_fixture(player, "boss", offset=55)
        before_hp = boss.hp
        await self.command(ws, "attack")
        unarmed_damage = before_hp-boss.hp
        baseline = self.state(player)["attack"]
        await self.command(ws, "equip", uid=weapon["uid"])
        equipped = self.state(player)
        self.assertEqual(equipped["equipment"]["weapon"], weapon["uid"])
        self.assertGreater(equipped["attack"], baseline)
        self.elapsed(2)
        before_hp = boss.hp
        await self.command(ws, "attack")
        self.assertGreater(before_hp-boss.hp, unarmed_damage)
        await self.command(ws, "equip", uid=weapon["uid"])
        self.assertEqual(self.state(player)["attack"], equipped["attack"], "No repeated bonus stacking")
        for uid in (foreign["uid"], "someone-elses-uid"):
            await self.command(ws, "equip", uid=uid)
            self.assertEqual(self.state(player)["equipment"]["weapon"], weapon["uid"])
        await self.command(ws, "unequip", slot="weapon")
        self.assertLess(self.state(player)["attack"], equipped["attack"])
        player.level = 1
        self.assertGreater(items[strongest]["min_level"], 1)
        await self.command(ws, "equip", uid=weapon["uid"])
        self.assertNotEqual(self.state(player)["equipment"].get("weapon"), weapon["uid"])

    async def test_shop_sale_is_once_only_and_potions_have_persistent_cooldown(self):
        ws, player, welcome = await self.connect("CarefulTrader")
        items = welcome["world"]["items"]
        template = next(key for key, spec in items.items() if spec["slot"] == "ring")
        item = self.give_item(player, template)
        player.gold = 200
        self.place(player)
        await self.command(ws, "sell", uid=item["uid"])
        self.assertEqual(player.gold, 200, "Selling requires merchant proximity")
        merchant = welcome["world"]["merchant"]
        self.place(player, merchant["x"], merchant["y"])
        await self.command(ws, "sell", uid=item["uid"])
        paid = player.gold
        self.assertGreater(paid, 200)
        await self.command(ws, "sell", uid=item["uid"])
        self.assertEqual(player.gold, paid)
        self.assertNotIn(item["uid"], [entry["uid"] for entry in self.state(player)["inventory"]])
        original_count = self.state(player)["potions"]["health_potion"]
        await self.command(ws, "buy", item="health_potion")
        await self.command(ws, "buy", item="health_potion")
        self.assertEqual(self.state(player)["potions"]["health_potion"], original_count+2)
        self.assertLess(player.gold, paid)
        self.place(player)
        player.hp = 1
        await self.command(ws, "potion", item="health_potion")
        after = self.state(player)
        self.assertGreater(player.hp, 1)
        player.hp = 1
        await self.command(ws, "potion", item="health_potion")
        self.assertEqual(player.hp, 1)
        self.assertEqual(self.state(player)["potions"], after["potions"])
        await self.restart()
        ws, player, _ = await self.connect("CarefulTrader", create=False)
        self.assertEqual(player.hp, 1, "Login cannot heal a saved living character")
        await self.command(ws, "potion", item="health_potion")
        self.assertEqual(player.hp, 1, "Restart cannot reset potion cooldown")
        self.assertEqual(self.state(player)["potions"], after["potions"])
        self.elapsed(30)
        await self.command(ws, "potion", item="health_potion")
        self.assertGreater(player.hp, 1)


    async def test_red_death_loses_more_progress_transfers_one_loose_item_and_persists(self):
        _, criminal, _ = await self.connect("RedDeath")
        killer_ws, killer, _ = await self.connect("RedHunter")
        self.place(criminal, 1200, 1800, level=10)
        self.place(killer, 1250, 1800, level=10)
        criminal.red_until = self.clock()+86400
        criminal.unjust_kills = [self.clock()-3, self.clock()-2, self.clock()-1]
        criminal.hp, criminal.gold, criminal.xp = 1, 200, 50
        killer.gold, killer.xp = 41, 7
        loose = self.give_item(criminal, "copper_ring")
        equipped_before = dict(criminal.equipment)
        await self.command(killer_ws, "pvp_safety", enabled=False)
        await self.command(killer_ws, "attack", target_id=criminal.id)
        self.assertFalse(criminal.alive)
        self.assertEqual((criminal.gold, criminal.xp, criminal.level), (160, 40, 10))
        self.assertEqual((killer.gold, killer.xp), (41, 7), "PvP creates no gold or experience")
        self.assertEqual(self.state(killer)["skull"], "none")
        self.assertEqual(self.state(killer)["unjust_kills"], 0)
        self.assertEqual(criminal.equipment, equipped_before)
        self.assertNotIn(loose["uid"], [i["uid"] for i in criminal.inventory])
        self.assertIn(loose["uid"], [i["uid"] for i in killer.inventory])
        await self.restart()
        _, restored, _ = await self.connect("RedDeath", create=False)
        self.assertEqual((restored.gold, restored.xp, restored.level), (160, 40, 10))
        self.assertEqual(self.state(restored)["skull"], "red", "Dying/restarting cannot erase crimes")
        self.assertNotIn(loose["uid"], [i["uid"] for i in restored.inventory])
        _, killer, _ = await self.connect("RedHunter", create=False)
        self.assertEqual(sum(i["uid"] == loose["uid"] for i in killer.inventory), 1)

    async def test_attack_and_ability_cooldowns_survive_combat_reconnect_and_restart(self):
        ws, player, _ = await self.connect("CooldownKnight")
        self.place(player, level=8)
        boss = self.enemy_fixture(player, "boss", offset=55)
        await self.command(ws, "ability")
        await self.command(ws, "attack")
        mana = player.mana
        self.assertGreater(self.state(player)["ability_cooldown"], 0)
        await self.disconnect(ws, player, remains=True)
        ws, player, _ = await self.connect("CooldownKnight", create=False)
        hp = boss.hp
        await self.command(ws, "ability")
        await self.command(ws, "attack")
        self.assertEqual((player.mana, boss.hp), (mana, hp))
        await self.restart()
        ws, player, _ = await self.connect("CooldownKnight", create=False)
        boss = self.enemy_fixture(player, "boss", offset=55)
        hp = boss.hp
        await self.command(ws, "ability")
        await self.command(ws, "attack")
        self.assertEqual((player.mana, boss.hp), (mana, hp))
        self.elapsed(13)
        await self.command(ws, "ability")
        await self.command(ws, "attack")
        self.assertLess(player.mana, mana)
        self.assertLess(boss.hp, hp)


    async def test_monster_finisher_cannot_launder_a_recent_unjust_pvp_attack(self):
        ws, attacker, _ = await self.connect("MonsterLurer")
        _, victim, _ = await self.connect("LureVictim")
        self.place(attacker, 1200, 1800, level=8)
        self.place(victim, 1250, 1800, level=8)
        attacker.gold, attacker.xp = 41, 7
        victim.hp = 50
        await self.command(ws, "pvp_safety", enabled=False)
        await self.command(ws, "attack", target_id=victim.id)
        self.assertTrue(victim.alive)
        self.assertLess(victim.hp, 50)
        # Only the final hit is environmental; the preceding aggression used WS.
        self.game.damage_player(victim, 9999)
        self.assertFalse(victim.alive)
        self.assertEqual(self.state(attacker)["unjust_kills"], 1)
        self.assertEqual((attacker.gold, attacker.xp), (41, 7))
        self.elapsed(5)
        self.place(victim, 1250, 1800)
        victim.hp = 50
        await self.command(ws, "attack", target_id=victim.id)
        self.elapsed(21)
        self.game.damage_player(victim, 9999)
        self.assertEqual(self.state(attacker)["unjust_kills"], 1,
                         "An expired encounter must not attribute later environmental deaths")

    async def test_party_level_ratio_applies_to_every_rewarded_member(self):
        leader_ws, leader, _ = await self.connect("MiddleLevel")
        low_ws, low, _ = await self.connect("LowLevel")
        high_ws, high, _ = await self.connect("HighLevel")
        for player, level in ((leader, 3), (low, 1), (high, 9)):
            self.place(player, 1200, 1800, level=level)
        for ws, player in ((low_ws, low), (high_ws, high)):
            await self.command(leader_ws, "party_invite", target_id=player.id)
            await self.command(ws, "party_accept", leader_id=leader.id)
        enemy = self.enemy_fixture(leader, hp=1)
        await self.command(leader_ws, "attack")
        self.assertFalse(enemy.alive)
        self.assertGreater(leader.xp, 0)
        levels = [p.level for p in (leader, low, high) if p.xp > 0]
        self.assertLessEqual(max(levels), 3*min(levels),
                             "A level-3 intermediary must not bypass the level-1/9 sharing restriction")


    def advance_simulation(self, seconds):
        for _ in range(math.ceil(seconds/.05)):
            self.clock.advance(.05)
            self.game.step(.05)

    def quest(self, player, quest_id):
        return next(q for q in self.state(player)["quests"] if q["id"] == quest_id)

    def catalogue(self, key):
        value = self.game.metadata()[key]
        return list(value.values()) if isinstance(value, dict) else value

    def npc_for(self, player, quest_id):
        npc_id = self.quest(player, quest_id)["npc_id"]
        return next(n for n in self.catalogue("npcs") if n["id"] == npc_id)

    async def accept_quest(self, ws, player, quest_id):
        npc = self.npc_for(player, quest_id)
        self.place(player, npc["x"], npc["y"])
        await self.command(ws, "quest_accept", quest_id=quest_id)
        self.assertIn(self.quest(player, quest_id)["status"], ("active", "ready"))

    async def kill_rat(self, ws, player):
        self.place(player, 1200, 1800)
        rat = self.enemy_fixture(player, "rat", hp=1, offset=40)
        self.elapsed(2)
        await self.command(ws, "attack")
        self.assertFalse(rat.alive)

    async def finish_first_quest(self, ws, player):
        await self.accept_quest(ws, player, "q_rats")
        for _ in range(3):
            await self.kill_rat(ws, player)
        self.assertEqual(self.quest(player, "q_rats")["status"], "ready")
        npc = self.npc_for(player, "q_rats")
        self.place(player, npc["x"], npc["y"])
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual(self.quest(player, "q_rats")["status"], "claimed")

    async def test_level_speed_increases_gradually_and_diagonal_motion_is_normalized(self):
        ws, player, _ = await self.connect("MeasuredWalker")
        previous = 0
        for level in (1, 10, 50, 100, 100000):
            self.place(player, level=level)
            speed = self.state(player)["speed"]
            expected = 100 + 90*(level-1)/(level+79)
            self.assertAlmostEqual(speed, expected, delta=.01)
            self.assertGreater(speed, previous)
            self.assertLess(speed, 190)
            previous = speed
        for level in (1, 10, 100):
            displacements = []
            for dx, dy in ((1, 0), (1000000, 1000000)):
                self.place(player, 1200, 1800, level=level)
                await self.command(ws, "input", x=dx, y=dy, speed=90000, level=90000)
                self.game.step(.05)
                displacements.append(math.hypot(player.x-1200, player.y-1800))
                self.assertEqual(player.level, level)
                self.assertAlmostEqual(displacements[-1], self.state(player)["speed"]*.05, delta=.001)
            self.assertAlmostEqual(*displacements, places=6)

    async def test_mage_projectile_locks_to_hit_target_while_movement_changes_facing(self):
        ws, mage, _ = await self.connect("MovingMage", class_id="mage")
        self.place(mage, 1200, 1800)
        enemy = self.enemy_fixture(mage, "wolf", offset=150)
        # Isolate this aiming regression from unrelated nearby wildlife.
        for other in self.game.enemies.values():
            if other is not enemy:
                other.alive = False
        initial_hp = enemy.hp
        await self.command(ws, "input", x=0, y=-1)
        await self.command(ws, "attack")
        snapshot = self.game.snapshot(for_player=mage)
        effects = [e for e in snapshot["effects"] if e["source_id"] == mage.id and e["kind"] == "magic_bolt"]
        self.assertEqual(len(effects), 1)
        effect = dict(effects[0])
        self.assertEqual(effect["target_id"], enemy.id)
        self.assertEqual((effect["x"], effect["y"]), (1200, 1800))
        self.assertEqual((effect["target_x"], effect["target_y"]), (enemy.x, enemy.y))
        self.assertLess(enemy.hp, initial_hp)
        self.assertAlmostEqual(self.state(mage)["attack_facing"][0], 1)
        await self.command(ws, "input", x=-1, y=0)
        self.game.step(.05)
        state = self.state(mage)
        self.assertEqual(state["facing"], [-1, 0])
        self.assertEqual(state["attack_facing"], [1, 0])
        self.assertIn(effect, self.game.snapshot(for_player=mage)["effects"])
        self.assertLess(mage.x, effect["x"], "Walking must not move the recorded projectile origin")
        hp_after = enemy.hp
        await self.command(ws, "attack")
        self.assertEqual(enemy.hp, hp_after, "A replay inside the cooldown causes no second hit")
        self.assertEqual(sum(e["id"] == effect["id"] for e in self.game.snapshot(for_player=mage)["effects"]), 1)
        self.advance_simulation(1.6)
        self.assertNotIn(effect["id"], [e["id"] for e in self.game.snapshot(for_player=mage)["effects"]])

    async def test_fire_circle_emits_server_effect_and_only_damages_monsters_in_range(self):
        ws, mage, _ = await self.connect("FireCircleMage", class_id="mage")
        _, observer, _ = await self.connect("FireObserver")
        self.place(mage, 1200, 1800)
        self.place(observer, 1200, 1840)
        inside = self.enemy_fixture(mage, "wolf", offset=100)
        outside = self.enemy_fixture(mage, "wisp", offset=400)
        inside_hp, outside_hp, observer_hp, mana = inside.hp, outside.hp, observer.hp, mage.mana
        await self.command(ws, "ability")
        effects = [e for e in self.game.snapshot(for_player=mage)["effects"]
                   if e["source_id"] == mage.id and e["kind"] == "fire_ring"]
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        self.assertEqual((effect["x"], effect["y"], effect["radius"]), (1200, 1800, 320))
        self.assertAlmostEqual(effect["duration"], .9)
        self.assertLess(inside.hp, inside_hp)
        self.assertEqual(outside.hp, outside_hp)
        self.assertEqual(observer.hp, observer_hp)
        self.assertLess(mage.mana, mana)
        self.assertIn(effect, self.game.snapshot(for_player=observer)["effects"])
        after = (inside.hp, outside.hp, mage.mana)
        await self.command(ws, "ability")
        await ws.send_json({"type": "effect", "kind": "fire_ring", "damage": 999999, "radius": 999999})
        await self.sync(ws)
        self.assertEqual((inside.hp, outside.hp, mage.mana), after)
        self.assertEqual(len([e for e in self.game.snapshot(for_player=mage)["effects"] if e["kind"] == "fire_ring"]), 1)

    async def test_chat_has_sender_id_sanitized_public_speech_and_expires(self):
        ws, speaker, _ = await self.connect("SpeakerHero")
        other, observer, _ = await self.connect("ChatObserver")
        await ws.send_json({"type": "chat", "text": "  Hej\n\u0001 świecie\t  "})
        for recipient in (ws, other):
            message = await self.packet(recipient, "chat")
            self.assertEqual(message["id"], speaker.id)
            self.assertEqual(message["name"], speaker.name)
            self.assertEqual(message["text"], "Hej świecie")
        state = next(p for p in self.game.snapshot(for_player=observer)["players"] if p["id"] == speaker.id)
        self.assertEqual(state["speech_text"], "Hej świecie")
        self.assertAlmostEqual(state["speech_until"]-self.game.time, 6)
        await ws.send_json({"type": "chat", "text": "too soon"})
        await self.packet(ws, "error")
        self.assertEqual(self.state(speaker)["speech_text"], "Hej świecie")
        self.advance_simulation(6.1)
        state = self.state(speaker)
        self.assertTrue(not state["speech_text"] or state["speech_until"] <= self.game.time)
        for invalid in ("x"*161, "\n\t ", {"text": "forged"}):
            await ws.send_json({"type": "chat", "text": invalid})
            await self.packet(ws, "error")
        await self.disconnect(ws, speaker)
        _, restored, _ = await self.connect("SpeakerHero", create=False)
        state = self.state(restored)
        self.assertTrue(not state["speech_text"] or state["speech_until"] <= self.game.time)

    async def test_quest_requires_npc_prerequisite_real_kills_and_single_reward(self):
        ws, player, _ = await self.connect("QuestExplorer")
        self.assertEqual(self.quest(player, "q_rats")["status"], "available")
        self.assertEqual(self.quest(player, "q_mill")["status"], "locked")
        npc = self.npc_for(player, "q_mill")
        self.place(player, npc["x"], npc["y"])
        await self.command(ws, "quest_accept", quest_id="q_mill")
        self.assertEqual(self.quest(player, "q_mill")["status"], "locked")
        await self.kill_rat(ws, player)
        await self.command(ws, "quest_accept", quest_id="q_rats")
        self.assertEqual(self.quest(player, "q_rats")["status"], "available", "Accepting requires NPC proximity")
        await self.accept_quest(ws, player, "q_rats")
        self.assertEqual(self.quest(player, "q_rats")["objectives"][0]["count"], 0, "Earlier kills are not retroactive")
        before = (player.xp, player.gold)
        await self.command(ws, "quest_claim", quest_id="q_rats", count=3, status="ready", xp=999999)
        self.assertEqual((player.xp, player.gold), before)
        for _ in range(3):
            await self.kill_rat(ws, player)
        self.assertEqual(self.quest(player, "q_rats")["status"], "ready")
        before = (player.level, player.xp, player.gold, dict(player.potions))
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual((player.level, player.xp, player.gold, player.potions), before, "Claim also requires NPC proximity")
        npc = self.npc_for(player, "q_rats")
        self.place(player, npc["x"], npc["y"])
        await self.command(ws, "quest_accept", quest_id="q_rats")
        self.assertEqual(self.quest(player, "q_rats")["status"], "ready", "Repeated accept cannot reset progress")
        reward = self.quest(player, "q_rats")["reward"]
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual(self.quest(player, "q_rats")["status"], "claimed")
        self.assertEqual(player.gold-before[2], reward["gold"])
        self.assertGreater(player.potions["health_potion"], before[3]["health_potion"])
        self.assertEqual(self.quest(player, "q_mill")["status"], "available")
        paid = (player.level, player.xp, player.gold, dict(player.potions), len(player.inventory))
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual((player.level, player.xp, player.gold, player.potions, len(player.inventory)), paid)

    async def test_active_quest_progress_and_claim_survive_restart(self):
        ws, player, _ = await self.connect("PersistentQuest")
        await self.accept_quest(ws, player, "q_rats")
        await self.kill_rat(ws, player)
        self.assertEqual(self.quest(player, "q_rats")["objectives"][0]["count"], 1)
        await self.restart()
        ws, player, _ = await self.connect("PersistentQuest", create=False)
        self.assertEqual(self.quest(player, "q_rats")["status"], "active")
        self.assertEqual(self.quest(player, "q_rats")["objectives"][0]["count"], 1)
        for _ in range(2):
            await self.kill_rat(ws, player)
        npc = self.npc_for(player, "q_rats")
        self.place(player, npc["x"], npc["y"])
        await self.command(ws, "quest_claim", quest_id="q_rats")
        paid = (player.level, player.xp, player.gold, dict(player.potions))
        await self.restart()
        ws, player, _ = await self.connect("PersistentQuest", create=False)
        self.assertEqual(self.quest(player, "q_rats")["status"], "claimed")
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual((player.level, player.xp, player.gold, player.potions), paid)

    async def test_discovery_is_once_only_persistent_and_counts_when_quest_accepted_later(self):
        ws, player, _ = await self.connect("MapExplorer")
        await self.finish_first_quest(ws, player)
        mill = next(m for m in self.catalogue("landmarks") if m["id"] == "old_mill")
        before = (player.level, player.xp, player.gold)
        self.place(player, mill["x"], mill["y"])
        self.game.step(.05)
        self.assertIn("old_mill", self.state(player)["discoveries"])
        discovered = (player.level, player.xp, player.gold)
        self.assertNotEqual(discovered, before, "A discovery supplies a real first-visit reward")
        self.place(player, 1200, 1800)
        self.game.step(.05)
        self.place(player, mill["x"], mill["y"])
        self.game.step(.05)
        self.assertEqual((player.level, player.xp, player.gold), discovered)
        await self.restart()
        ws, player, _ = await self.connect("MapExplorer", create=False)
        self.assertEqual(self.state(player)["discoveries"].count("old_mill"), 1)
        await self.accept_quest(ws, player, "q_mill")
        self.assertEqual(self.quest(player, "q_mill")["status"], "ready")
        await self.command(ws, "quest_claim", quest_id="q_mill")
        self.assertEqual(self.quest(player, "q_mill")["status"], "claimed")
        self.assertTrue(any(i["template"] == "knight_weapon_2" for i in player.inventory))

    async def test_full_inventory_preserves_guaranteed_quest_reward_until_slot_freed(self):
        ws, player, _ = await self.connect("FullBackpack", class_id="mage")
        await self.finish_first_quest(ws, player)
        await self.accept_quest(ws, player, "q_mill")
        mill = next(m for m in self.catalogue("landmarks") if m["id"] == "old_mill")
        self.place(player, mill["x"], mill["y"])
        self.game.step(.05)
        self.assertEqual(self.quest(player, "q_mill")["status"], "ready")
        while len(player.inventory) < server_module.INVENTORY_CAP:
            self.give_item(player, "copper_ring")
        npc = self.npc_for(player, "q_mill")
        self.place(player, npc["x"], npc["y"])
        before = (player.level, player.xp, player.gold)
        await self.command(ws, "quest_claim", quest_id="q_mill")
        self.assertEqual(self.quest(player, "q_mill")["status"], "ready")
        self.assertEqual((player.level, player.xp, player.gold), before)
        self.assertEqual(len(player.inventory), server_module.INVENTORY_CAP)
        player.inventory.pop()  # Free an unequipped fixture slot, as selling an item would.
        await self.command(ws, "quest_claim", quest_id="q_mill")
        self.assertEqual(self.quest(player, "q_mill")["status"], "claimed")
        self.assertEqual(sum(i["template"] == "mage_weapon_2" for i in player.inventory), 1)
        paid = (player.level, player.xp, player.gold, len(player.inventory))
        await self.command(ws, "quest_claim", quest_id="q_mill")
        self.assertEqual((player.level, player.xp, player.gold, len(player.inventory)), paid)

    async def test_party_quest_kill_credit_requires_acceptance_and_reward_eligibility(self):
        leader_ws, leader, _ = await self.connect("QuestLeader")
        support_ws, support, _ = await self.connect("QuestSupport", class_id="druid")
        remote_ws, remote, _ = await self.connect("QuestRemote")
        _, outsider, _ = await self.connect("QuestOutsider")
        for ws, player in ((leader_ws, leader), (support_ws, support), (remote_ws, remote)):
            await self.accept_quest(ws, player, "q_rats")
        for ws, player in ((support_ws, support), (remote_ws, remote)):
            await self.command(leader_ws, "party_invite", target_id=player.id)
            await self.command(ws, "party_accept", leader_id=leader.id)
        self.place(leader, 1200, 1800)
        self.place(support, 1220, 1800)
        self.place(outsider, 1230, 1800)
        self.place(remote, 2800, 1100)
        enemy = self.enemy_fixture(leader, "rat", hp=1, offset=40)
        await self.command(leader_ws, "attack")
        self.assertFalse(enemy.alive)
        for player in (leader, support):
            self.assertEqual(self.quest(player, "q_rats")["objectives"][0]["count"], 1)
        self.assertEqual(self.quest(remote, "q_rats")["objectives"][0]["count"], 0)
        self.assertEqual(self.quest(outsider, "q_rats")["status"], "available")
        self.assertEqual(self.quest(outsider, "q_rats")["objectives"][0]["count"], 0)

    async def test_quest_commands_reject_dead_players_unknown_ids_and_forged_progress(self):
        ws, player, _ = await self.connect("QuestAuthority")
        npc = self.npc_for(player, "q_rats")
        self.place(player, npc["x"], npc["y"])
        player.hp = 0
        player.respawn_until = self.clock()+100
        await self.command(ws, "quest_accept", quest_id="q_rats")
        self.assertEqual(self.quest(player, "q_rats")["status"], "available")
        player.hp, player.respawn_until = player.max_hp, 0
        before = (player.level, player.xp, player.gold)
        await self.command(ws, "quest_claim", quest_id="not-a-real-quest")
        await self.command(ws, "quest_accept", quest_id="not-a-real-quest")
        await self.command(ws, "input", x=0, y=0,
                           discoveries=["old_mill"],
                           quests=[{"id": "q_rats", "status": "ready"}],
                           quest_progress={"q_rats": {"accepted": True, "counts": [999]}})
        await self.command(ws, "quest_claim", quest_id="q_rats")
        self.assertEqual((player.level, player.xp, player.gold), before)
        self.assertEqual(self.quest(player, "q_rats")["status"], "available")
        self.assertNotIn("old_mill", self.state(player)["discoveries"])

    async def test_world_catalogue_has_diverse_reachable_landmarks_and_quest_targets(self):
        _, player, welcome = await self.connect("WorldCatalogue")
        self.assertGreaterEqual(len(self.catalogue("landmarks")), 5)
        self.assertGreaterEqual(len(self.state(player)["quests"]), 5)
        for landmark in self.catalogue("landmarks"):
            self.assertTrue(landmark["name"] and landmark["description"] and landmark["biome"])
            self.assertFalse(self.game.blocked(landmark["x"], landmark["y"], floor=landmark.get("floor", 0)), landmark["id"])
        for npc in self.catalogue("npcs"):
            self.assertFalse(self.game.blocked(npc["x"], npc["y"]), npc["id"])
        kinds = {e.kind for e in self.game.enemies.values()}
        self.assertTrue({"rat", "boar", "goblin", "spider", "skeleton", "wolf", "boss"} <= kinds)
        for quest in self.state(player)["quests"]:
            self.assertTrue(quest["objectives"] and quest["reward"])
            self.assertIn(quest["npc_id"], {n["id"] for n in self.catalogue("npcs")})


if __name__ == "__main__":
    unittest.main()
