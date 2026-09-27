"""Layout wiring and HTTP regression tests. Visual/browser checks live in browser_089_smoke.py.
Godot checks here inspect source only, not GDScript compilation or engine layout.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import unittest
from aiohttp.test_utils import TestClient, TestServer
from server.server import create_app
ROOT=Path(__file__).resolve().parents[1]

class Tree(HTMLParser):
    def __init__(self):
        super().__init__();self.stack=[];self.ids={};self.counts=Counter();self.children={}
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs);ident=attrs.get('id');key=ident or attrs.get('class',tag)
        if ident:
            self.ids[ident]={'tag':tag,'parents':list(self.stack),'attrs':attrs};self.counts[ident]+=1
        if self.stack:self.children.setdefault(self.stack[-1],[]).append(key)
        if tag not in {'img','link','meta','input','br','hr','source','area','wbr'}:self.stack.append(key)
    def handle_endtag(self, tag):
        if self.stack:self.stack.pop()

class HUDStructure(unittest.TestCase):
    def setUp(self):
        self.html=(ROOT/'web/index.html').read_text();self.tree=Tree();self.tree.feed(self.html)
    def test_control_ids_stay_unique(self):
        self.assertTrue(all(v==1 for v in self.tree.counts.values()))
        for key in ['healthPotion','manaPotion','abilityButton','bookSpell','chatInput','effectsPanel']:
            self.assertIn(key,self.tree.ids)
    def test_potions_are_between_chat_and_spells_in_shared_dock(self):
        self.assertEqual(self.tree.children['actionDock'],['chat-wrap','quickbar','spellbar'])
        self.assertEqual(self.tree.children['quickbar'],['healthPotion','manaPotion'])
    def test_favorite_follows_book_in_same_non_scrolling_toolbar(self):
        self.assertEqual(self.tree.children['book-favorite-controls'],['bookSpell','abilityButton'])
        self.assertNotIn('hotbar-viewport',self.tree.ids['abilityButton']['parents'])
        self.assertIn('hotbar-toolbar',self.tree.ids['abilityButton']['parents'])
    def test_statuses_keep_detail_and_accessible_owners_without_row_labels(self):
        self.assertNotIn('class="effects-label"',self.html)
        self.assertEqual(self.tree.ids['ownEffectsRow']['attrs']['aria-label'],'Twoje statusy')
        self.assertEqual(self.tree.ids['targetEffectsRow']['attrs']['aria-label'],'Statusy zaznaczonego celu')
        for key in ['closeEffectDetail','effectDetailName','effectDetailText']:self.assertIn(key,self.tree.ids)
    def test_override_loads_last_and_keeps_no_shared_status_background(self):
        self.assertGreater(self.html.index('hud_layout.css'),self.html.index('loot_ui.css'))
        css=(ROOT/'web/hud_layout.css').read_text()
        self.assertIn('background: none; border: 0;',css)
        self.assertIn('box-shadow: none; backdrop-filter: none; pointer-events: none;',css)
    def test_godot_has_moved_existing_controls_and_individual_status_buttons_source_only(self):
        code=(ROOT/'client/scripts/main.gd').read_text()
        self.assertEqual(code.count('ability_button = _button('),1)
        self.assertIn('menus.add_child(ability_button)',code)
        self.assertNotIn('combat.add_child(ability_button)',code)
        self.assertIn('potion_strip.add_child(potion_button)',code)
        self.assertIn('status_strip = VBoxContainer.new()',code)
        self.assertNotIn('own_effects_label',code)
        self.assertIn('button.pressed.connect(_show_effect.bind(button))',code)

class HUDHTTP(unittest.IsolatedAsyncioTestCase):
    async def test_new_css_is_served_on_real_route_with_cache_revalidation(self):
        async with TestClient(TestServer(create_app(':memory:'))) as client:
            resp=await client.get('/hud_layout.css')
            self.assertEqual(resp.status,200)
            self.assertEqual(await resp.read(),(ROOT/'web/hud_layout.css').read_bytes())
            self.assertEqual(resp.headers['Cache-Control'],'no-cache')
            self.assertIn('text/css',resp.headers['Content-Type'])
            resp=await client.get('/');self.assertIn('hud_layout.css',await resp.text())

if __name__=='__main__':unittest.main()
