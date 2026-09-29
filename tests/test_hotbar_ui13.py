"""Grouped hotbar compatibility, no lost spells and constellation resource guards."""
import json
import re
import unittest
import test_dnd as base
from aiohttp.test_utils import TestClient, TestServer
from server.server import Game, Player, create_app
from server import dnd_content as dnd, druid_circles as circles, spell_scaling


class GroupedHotbar(unittest.TestCase):
    def player(self, level=15, circle='stars', cls='druid'):
        p = Player('1', 'GroupedQA', class_id=cls, level=level)
        p.druid_circle = circle if cls == 'druid' else ''
        p.current_wall_time = 1000
        p.hp = p.max_hp; p.mana = p.max_mana
        dnd.sync_hotbar(p)
        return p

    def test_level15_stars_six_variants_become_two_slots(self):
        p = self.player()
        bar = dnd.grouped_hotbar(p)
        self.assertEqual(sum(bool(x) for x in p.hotbar), 21)
        self.assertEqual(sum(bool(x) for x in bar), 17)
        self.assertEqual(bar.count('group_wild_shape'), 1)
        self.assertEqual(bar.count('group_starry_form'), 1)
        self.assertFalse(any(x.startswith('circle_star_') or x.startswith('wild_shape_') for x in bar))

    def test_all_unlocks_remain_represented_through_level100(self):
        for cls, circle in [('druid',c) for c in ('','land','moon','sea','stars')]+[('mage',''),('ranger',''),('knight','')]:
            p = self.player(1,circle,cls)
            for level in range(1,101):
                p.level = level; dnd.sync_hotbar(p)
                raw = [x for x in p.hotbar if x]
                groups = [x for x in dnd.grouped_hotbar(p) if x]
                allowed = [x for x in dnd.SPELLS if dnd.spell_allowed(p,x)]
                self.assertEqual(set(raw),set(allowed),(cls,circle,level))
                self.assertEqual(set(groups),{dnd.hotbar_group_key(x) for x in allowed},(cls,circle,level))
                self.assertEqual(len(groups),len(set(groups)))
                self.assertEqual(len(dnd.grouped_hotbar(p))%24,0)

    def test_archer_arrow_appears_inside_same_group_without_moving_other_keys(self):
        p = self.player(); before = dnd.grouped_hotbar(p)
        p.buffs['starry_form'] = dict(until=2000)
        circles.runtime(p)['starry_form'] = 'archer'
        dnd.sync_hotbar(p)
        self.assertIn('circle_star_arrow',p.hotbar)
        self.assertEqual(before,dnd.grouped_hotbar(p))
        p.buffs.clear();dnd.sync_hotbar(p)
        self.assertEqual(before,dnd.grouped_hotbar(p))

    def test_whole_group_moves_with_any_member_and_is_saved_as_real_spells(self):
        p = self.player()
        self.assertTrue(dnd.bind_grouped_hotbar(p,0,'circle_star_dragon'))
        self.assertEqual(dnd.grouped_hotbar(p)[0],'group_starry_form')
        self.assertTrue(all(not key or key in dnd.SPELLS for key in p.hotbar))
        self.assertTrue(dnd.bind_grouped_hotbar(p,23,'circle_star_chalice'))
        self.assertEqual(dnd.grouped_hotbar(p)[23],'group_starry_form')
        before = list(dnd.grouped_hotbar(p))
        saved = json.loads(json.dumps(p.hotbar))
        q = self.player(); q.hotbar = saved; dnd.sync_hotbar(q)
        self.assertEqual(dnd.grouped_hotbar(q),before)
        self.assertEqual(set(x for x in q.hotbar if x),set(x for x in dnd.SPELLS if dnd.spell_allowed(q,x)))

    def test_invalid_bind_does_not_change_layout(self):
        p = self.player();before = p.hotbar.copy()
        for slot,key in [(True,'shillelagh'),(-1,'shillelagh'),(999,'shillelagh'),(0,'fireball'),(0,'group_unknown'),(0,{}),(0,'')]:
            self.assertFalse(dnd.bind_grouped_hotbar(p,slot,key))
            self.assertEqual(p.hotbar,before)

    def test_shape_exhaustion_and_free_high_level_switch_have_explicit_costs(self):
        p = self.player();circles.state(p)['shape_spent']=2
        profiles = spell_scaling.client_profiles(p)
        for key in ('circle_star_archer','circle_star_chalice','circle_star_dragon'):
            self.assertEqual(profiles[key]['uses_remaining'],0)
            self.assertEqual(profiles[key]['resource_cost'],1)
        p.level=45;p.buffs['starry_form']=dict(until=2000);circles.runtime(p)['starry_form']='archer'
        circles.state(p)['shape_spent']=circles.shape_max(p)
        profiles=spell_scaling.client_profiles(p)
        self.assertTrue(profiles['circle_star_archer']['already_active'])
        self.assertEqual(profiles['circle_star_chalice']['resource_cost'],0)
        self.assertEqual(profiles['circle_star_arrow']['resource_cost'],0)
        self.assertFalse(circles.feature_ready(p,'circle_star_archer'))

    def test_only_explicit_point_spells_are_flagged(self):
        for key in ('fog_cloud','web','wall_of_stone','sleep','shatter','conjure_animals'):
            self.assertTrue(dnd.SPELLS[key]['ground_target'])
        for key in ('circle_star_archer','healing_word','hold_person','tree_stride','thunderwave'):
            self.assertFalse(dnd.SPELLS[key].get('ground_target',False))

    def test_non_druid_bars_are_unchanged(self):
        for cls in ('mage','ranger','knight'):
            p=self.player(80,cls=cls)
            self.assertEqual(dnd.grouped_hotbar(p),p.hotbar)


class StarActivation(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.p=self.player('druid',15)
        self.p.druid_circle='stars';self.g.migrate_druid_circle(self.p)
    def tearDown(self):self.g.db.close()
    def advance(self):
        self.clock.advance();self.p.current_wall_time=self.clock()
    async def test_same_constellation_never_spends_twice(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.assertEqual(circles.shape_remaining(self.p),1)
        self.advance()
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.assertEqual(circles.shape_remaining(self.p),1)
        self.advance()
        await self.g.cast_circle_feature(self.p,'circle_star_chalice')
        self.assertEqual(circles.shape_remaining(self.p),0)
    async def test_arrow_does_not_consume_remaining_shape_uses(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.advance();circles.state(self.p)['shape_spent']=2
        await self.g.cast_circle_feature(self.p,'circle_star_arrow')
        self.assertEqual(circles.shape_remaining(self.p),0)
        self.assertEqual(circles.starry_form(self.p),'archer')
    async def test_grouped_bind_keeps_legacy_spell_data(self):
        await self.g.bind_grouped_spell(self.p,2,'circle_star_dragon')
        state=self.p.public(self.clock(),private=True)
        self.assertEqual(state['grouped_hotbar'][2],'group_starry_form')
        self.assertIn('circle_star_dragon',state['hotbar'])
        self.assertNotIn('group_starry_form',state['hotbar'])

class BrowserAssets(unittest.IsolatedAsyncioTestCase):
    async def test_every_index_script_and_stylesheet_is_served_by_production_routes(self):
        async with TestClient(TestServer(create_app(':memory:'))) as client:
            response = await client.get('/')
            self.assertEqual(response.status, 200)
            html = await response.text()
            paths = re.findall(r'(?:src|href)=["\']([^"\']+\.(?:js|css)(?:\?[^"\']*)?)["\']', html)
            paths = ['/' + path.lstrip('/') for path in paths]
            self.assertIn('/hotbar_ui.js', paths)
            self.assertIn('/hotbar_ui.css', paths)
            for path in paths:
                with self.subTest(path=path):
                    asset = await client.get(path)
                    self.assertEqual(asset.status, 200)
                    self.assertTrue(await asset.read())
                    self.assertEqual(asset.headers['Cache-Control'], 'no-cache')
                    self.assertIn(asset.content_type, ('text/javascript', 'application/javascript', 'text/css'))


if __name__=='__main__':unittest.main()
