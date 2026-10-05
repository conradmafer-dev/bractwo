"""Four focused discovery checks; no server startup, browser or player database."""
import ast
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import discovery_rules
from progression import near

SOURCE = ast.parse((ROOT / 'server/server.py').read_text(encoding='utf-8'))


def method(class_name, method_name, scope):
    cls = next(n for n in SOURCE.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    fn = deepcopy(next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name))
    fn.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<production-method>', 'exec'), scope)
    return scope[method_name]


def fixture():
    landmarks = [dict(id='old_mill', name='Mill', x=200, y=200, radius=90, reward=dict(xp=20, gold=8))]
    content = SimpleNamespace(
        REGIONS=[dict(x=0, y=0, w=10000, h=10000, min_level=1)],
        HUNTING_GROUNDS=[dict(id='hunt', name='Hunt', x=1000, y=1000, members=['wolf'])],
        STAIRS=[dict(id='near_mill', name='Steps', x=220, y=200, to_floor=1),
                dict(id='cave', name='Cave', x=4000, y=1000, floor=-1, to_floor=0, min_level=4)],
        CITIES=[dict(id='town', x=0, y=0)], SPAWNS=[('wolf', 1000, 1000, 0)],
        QUESTS_REF=[dict(objectives=[dict(type='discover', target='hunt', x=0, y=0)])])
    enemies = dict(wolf=dict(name='Wolf', level=1))
    return content, landmarks, [], enemies


class DiscoveryChecks(unittest.TestCase):
    def test_catalog_complete_preserves_saved_ids_and_gold(self):
        scope = {name: importlib.import_module(name) for name in (
            'living_world', 'vertical_world', 'loot_tables', 'combat_rules', 'loot_content', 'hunt_content', 'dnd_content')}
        scope['content'] = importlib.import_module('world_content')
        scope['math'] = math
        # Execute only real catalogue definitions/configuration before discovery setup.
        start = next(i for i, n in enumerate(SOURCE.body) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Tuple) and any(isinstance(e, ast.Name) and e.id == 'WIDTH' for e in t.elts)
                             for t in n.targets))
        stop = next(i for i, n in enumerate(SOURCE.body) if isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                    and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == 'discovery_rules')
        nodes = [n for n in SOURCE.body[start:stop] if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<production-world-catalogue>', 'exec'), scope)
        content, points, zones, enemies = (scope[k] for k in ('content', 'LANDMARKS', 'ZONES', 'ENEMY_TYPES'))
        baseline_zip = ROOT.parent / 'BRACTWO_0.8.18_UI_07_RAILWAY_GITHUB_READY.zip'
        with zipfile.ZipFile(baseline_zip) as archive:
            previous = ast.parse(archive.read('server/server.py').decode('utf-8'))
        old_game = next(n for n in previous.body if isinstance(n, ast.ClassDef) and n.name == 'Game')
        old_init = next(n for n in old_game.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
        old_loop = next(n for n in old_init.body if isinstance(n, ast.For) and isinstance(n.iter, ast.Call)
                        and isinstance(n.iter.func, ast.Name) and n.iter.func.id == 'enumerate'
                        and isinstance(n.iter.args[0], ast.List))
        # The opening balance pass removes only two bridge wisps and the
        # nearest spider; all retained kinds, coordinates and order stay put.
        removed = {('wisp', 1940, 1010), ('wisp', 1880, 1530), ('spider', 2100, 1490)}
        self.assertEqual(content.STARTER_SPAWNS,
                         [s for s in ast.literal_eval(old_loop.iter.args[0]) if s not in removed])
        self.assertEqual(len(content.STARTER_SPAWNS), 25)
        new_game = next(n for n in SOURCE.body if isinstance(n, ast.ClassDef) and n.name == 'Game')
        new_init = next(n for n in new_game.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
        new_loop = next(n for n in new_init.body if isinstance(n, ast.For) and isinstance(n.iter, ast.Call)
                        and isinstance(n.iter.args[0], ast.Attribute) and n.iter.args[0].attr == 'STARTER_SPAWNS')
        # Keep the same ID format. Enemy indices are transient and rebuilt on
        # startup; removing residents does not change saved quest/character IDs.
        self.assertEqual(ast.dump(ast.Module(body=old_loop.body, type_ignores=[])),
                         ast.dump(ast.Module(body=new_loop.body, type_ignores=[])))
        self.assertEqual(ast.dump(old_loop.target), ast.dump(new_loop.target))
        historical = {p['id']: p['reward'].get('gold', 0) for p in points}
        discovery_rules.configure(content, points, zones, enemies)
        index = {p['id']: p for p in points}
        self.assertEqual(len(points), len(index))
        self.assertTrue(all(p['reward']['xp'] > 0 for p in points))
        self.assertTrue(all(ident in index and index[ident]['reward']['gold'] == gold for ident, gold in historical.items()))
        named_grounds = [g for g in content.HUNTING_GROUNDS if g.get('name')]
        for entity in named_grounds + content.STAIRS + content.CITIES:
            point = index[entity['discovery_id']]
            self.assertEqual(point.get('floor', 0), entity.get('floor', 0))
            self.assertLessEqual(math.hypot(point['x']-entity['x'], point['y']-entity['y']), point['radius'])
        rewards = [p['reward']['xp'] for p in points]
        sample_ids = ['old_mill', 'fortress', named_grounds[0]['discovery_id'], max(points, key=lambda p:p['reward']['xp'])['id']]
        print(json.dumps(dict(catalogue=dict(historical=len(historical), total=len(points), named_grounds=len(named_grounds),
                         stairs=len(content.STAIRS), cities=len(content.CITIES), starter_spawns_preserved=len(content.STARTER_SPAWNS),
                         xp_min=min(rewards), xp_max=max(rewards),
                         examples={ident:index[ident]['reward'] for ident in sample_ids})), ensure_ascii=True))

    def test_configure_idempotent_unique_and_updates_objective(self):
        args = fixture()
        discovery_rules.configure(*args)
        once = deepcopy(args)
        discovery_rules.configure(*args)
        self.assertEqual(args, once)
        content, points, _, _ = args
        self.assertEqual(len(points), len({p['id'] for p in points}))
        self.assertEqual(content.STAIRS[0]['discovery_id'], 'old_mill')
        self.assertEqual(content.QUESTS_REF[0]['objectives'][0]['x'], 1000)
        self.assertEqual(next(p for p in points if p['id']=='old_mill')['reward']['gold'], 8)

    def test_xp_increases_with_distance_biome_enemy_and_boss(self):
        xp = discovery_rules.discovery_xp
        baseline = xp(5, 5, 500)
        self.assertGreater(xp(5, 5, 5000), baseline)
        self.assertGreater(xp(10, 5, 500), baseline)
        self.assertGreater(xp(5, 10, 500), baseline)
        self.assertGreaterEqual(xp(1, 0, 0, 200), 200)
        normal, boss = fixture(), fixture()
        boss[3]['wolf']['boss'] = True
        discovery_rules.configure(*normal)
        discovery_rules.configure(*boss)
        find = lambda args: next(p['reward']['xp'] for p in args[1] if p['id']=='hunt')
        self.assertGreater(find(boss), find(normal))
        content = SimpleNamespace(REGIONS=[], HUNTING_GROUNDS=[], STAIRS=[], CITIES=[], SPAWNS=[],
                                  STARTER_SPAWNS=[('legacy', 1000, 1000)], QUESTS_REF=[])
        points = [dict(id='surface', x=1000, y=1000, floor=0), dict(id='below', x=1000, y=1000, floor=-1)]
        discovery_rules.configure(content, points, [], {'legacy':dict(name='Legacy', hp=27)})
        self.assertEqual(points[0]['discovery_difficulty']['enemy_level'], 3)
        self.assertEqual(points[1]['discovery_difficulty']['enemy_level'], 0)
        self.assertGreater(points[0]['reward']['xp'], points[1]['reward']['xp'])

    def test_actual_discovery_awards_once_on_correct_floor_and_survives_reload(self):
        player_class = next(n for n in SOURCE.body if isinstance(n, ast.ClassDef) and n.name == 'Player')
        save_node = next(n for n in player_class.body if isinstance(n, ast.FunctionDef) and n.name == 'save_data')
        keys = next(ast.literal_eval(n) for n in ast.walk(save_node) if isinstance(n, ast.Tuple)
                    and len(n.elts) > 20 and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.elts))
        class TestPlayer(SimpleNamespace):
            def __init__(self, pid, name, ws):
                super().__init__(**dict.fromkeys(keys, 0))
                self.id, self.name, self.ws = pid, name, ws
                self.discoveries, self.inventory, self.depot, self.unjust_kills, self.aggressors = [], [], [], [], {}
                self.hp = self.mana = self.max_hp = self.max_mana = 100
                self.class_id, self.spec, self.alive = 'druid', {'weapon':'staff'}, True
        scope = dict(near=near, json=json, Player=TestPlayer, ITEMS={}, POTIONS={}, make_item=lambda:None,
                     inventory_rules=SimpleNamespace(ensure=lambda *args:None), SPAWN={'x':0,'y':0})
        TestPlayer.save_data = method('Player', 'save_data', scope)
        fake = SimpleNamespace(db=sqlite3.connect(':memory:'), save_score=lambda p:None,
                               migrate_dnd=lambda *args:None, migrate_fighter=lambda *args:None,
                               migrate_caster=lambda *args:None, blocked=lambda *args, **kw:False, now=lambda:0)
        fake.db.execute('CREATE TABLE accounts (id TEXT PRIMARY KEY, data TEXT)')
        fake.db.execute('INSERT INTO accounts VALUES (?, ?)', ('p', '{}'))
        calls = []
        def award(p, xp, gold):
            calls.append((xp, gold)); p.xp += xp; p.gold += gold
        fake.award = award
        fake.save_player = lambda p: method('Game', 'save_player', scope)(fake, p)
        discover = method('Game', 'discover_landmarks', scope)
        load = method('Game', 'load_player', scope)
        def point(ident, floor):
            return dict(id=ident, x=50, y=50, floor=floor, radius=90, reward={'xp':40,'gold':8})
        fake.landmark_cells = {(0,0,0):[point('surface',0)], (-1,0,0):[point('cave',-1)]}
        p = TestPlayer('p', 'Tester', None); p.x = p.y = 50
        discover(fake, p); discover(fake, p)
        self.assertEqual((p.discoveries, p.xp, p.gold, len(calls)), (['surface'], 40, 8, 1))
        saved = json.loads(fake.db.execute('SELECT data FROM accounts WHERE id=?', ('p',)).fetchone()[0])
        p = load(fake, 'p', 'Tester', None, saved)
        discover(fake, p)
        self.assertEqual((p.discoveries, p.xp, len(calls)), (['surface'], 40, 1))
        p.floor = -1
        discover(fake, p); discover(fake, p)
        self.assertEqual((p.discoveries, p.xp, p.gold, len(calls)), (['surface','cave'], 80, 16, 2))
        fake.db.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
