"""Focused checks for automatic last-visited-city respawns (UI_18)."""
import json
import math
import unittest
from unittest.mock import patch

from test_dnd import Clock, WS
from server.server import Game, Player, content, LANDMARKS


class RespawnCityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Game(':memory:', clock=self.clock)
        self.addCleanup(self.game.db.close)
        for enemy in self.game.enemies.values():
            enemy.alive = False
            enemy.respawn_at = 0
        self.game.legacy_enemies = []
        self.player = Player('1', 'CityTest', WS(), level=2, gold=100000,
                             x=1100, y=1180)
        self.game.starter(self.player)
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana
        self.player.current_wall_time = self.clock()
        # Revisits must work independently of one-time discovery rewards.
        self.player.discoveries = [point['id'] for point in LANDMARKS]
        self.game.players[self.player.id] = self.player
        with self.game.db:
            self.game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',
                                 (1, self.player.name, 'citytest', b'salt', b'hash',
                                  json.dumps(self.player.save_data())))

    def saved(self):
        return json.loads(self.game.db.execute(
            'SELECT data FROM accounts WHERE id=1').fetchone()[0])

    def place(self, city, floor=0):
        self.player.x, self.player.y, self.player.floor = city['x'], city['y'], floor
        self.player.dx = self.player.dy = 0
        self.player.input_time = -10

    def test_walking_into_each_city_records_and_commits_once(self):
        for index, city in enumerate(content.CITIES):
            with self.subTest(city=city['id']):
                self.player.home_city = content.CITIES[(index+1) % len(content.CITIES)]['id']
                # Find a real, walkable entrance at the city boundary.
                for degrees in range(0, 360, 5):
                    angle = math.radians(degrees)
                    dx, dy = math.cos(angle), math.sin(angle)
                    outside = (city['x'] + dx*(city['radius']+1),
                               city['y'] + dy*(city['radius']+1))
                    inside = (city['x'] + dx*(city['radius']-10),
                              city['y'] + dy*(city['radius']-10))
                    if not self.game.blocked(*outside) and not self.game.blocked(*inside):
                        break
                else:
                    self.fail('No walkable entrance for ' + city['id'])
                self.player.x, self.player.y = outside
                self.player.floor = 0
                self.player.dx, self.player.dy = -dx, -dy
                self.player.input_time = self.game.time
                with patch.object(self.game, 'save_player', wraps=self.game.save_player) as save:
                    self.game.step(.05)
                    self.assertTrue(self.game.in_safe(self.player))
                    self.assertEqual(self.player.home_city, city['id'])
                    self.assertEqual(self.saved()['home_city'], city['id'])
                    self.player.dx = self.player.dy = 0
                    self.game.step(.05)
                    self.assertEqual(save.call_count, 1)

    def test_return_to_previously_discovered_city_replaces_last_visit(self):
        first, second = content.CITIES[:2]
        for city in (first, second, first):
            self.place(city)
            self.game.step(.05)
            self.assertEqual(self.player.home_city, city['id'])
        self.player.x, self.player.y = 1100, 1180
        self.assertFalse(self.game.in_safe(self.player))
        self.game.step(.05)
        self.assertEqual(self.player.home_city, first['id'])
        self.assertEqual(self.saved()['home_city'], first['id'])

    def test_wrong_floor_and_dead_position_do_not_replace_home(self):
        first, second = content.CITIES[:2]
        self.player.home_city = first['id']
        self.place(second, floor=-1)
        self.game.step(.05)
        self.assertEqual(self.player.home_city, first['id'])
        self.place(second)
        self.player.hp = 0
        self.player.respawn_until = self.clock()+4
        self.game.persist()
        self.game.step(.05)
        self.assertEqual(self.player.home_city, first['id'])
        self.assertEqual(self.saved()['home_city'], first['id'])

    async def test_captain_trip_records_destination_before_next_tick(self):
        first, second = content.CITIES[:2]
        captain = next(n for n in content.NPCS
                       if n.get('service') == 'captain' and n['city_id'] == first['id'])
        self.player.x, self.player.y = captain['x'], captain['y']
        await self.game.expansion_command(self.player, 'travel', {'city_id': second['id']})
        self.assertEqual((self.player.x, self.player.y), (second['x'], second['y']))
        self.assertEqual(self.player.home_city, second['id'])
        self.assertEqual(self.saved()['home_city'], second['id'])

    def test_saved_visit_survives_reload_and_drives_death_respawn(self):
        city = content.CITIES[-1]
        self.place(city)
        self.game.step(.05)
        self.player.x, self.player.y = 1100, 1180
        self.game.persist()
        # Fresh Game instance represents a server restart; no old player object.
        restarted = Game(':memory:', clock=self.clock)
        self.addCleanup(restarted.db.close)
        loaded = restarted.load_player('1', 'CityTest', WS(), self.saved())
        self.assertEqual(loaded.home_city, city['id'])
        self.game.players['1'] = loaded
        self.game.damage_player(loaded, 10000, rolled=True)
        self.assertFalse(loaded.alive)
        self.assertEqual(loaded.respawn_until, self.clock()+4)
        self.clock.advance(3.9)
        self.game.step(.05)
        self.assertFalse(loaded.alive)
        self.clock.advance(.2)
        self.game.step(.05)
        self.assertEqual((loaded.x, loaded.y, loaded.floor), (city['x'], city['y'], 0))
        self.assertEqual((loaded.hp, loaded.mana), (loaded.max_hp, loaded.max_mana))
        self.assertEqual(loaded.home_city, city['id'])

    def test_login_in_city_updates_legacy_save_but_dead_save_keeps_home(self):
        first, second = content.CITIES[:2]
        self.place(second)
        self.player.home_city = first['id']
        saved = self.player.save_data()
        loaded = self.game.load_player('1', 'CityTest', WS(), saved)
        self.assertEqual(loaded.home_city, second['id'])
        saved['hp'] = 0
        saved['respawn_until'] = self.clock()+4
        loaded = self.game.load_player('1', 'CityTest', WS(), saved)
        self.assertEqual(loaded.home_city, first['id'])


if __name__ == '__main__':
    unittest.main()
