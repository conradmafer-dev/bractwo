"""Retired mana supplies cannot reappear through catalogs, old saves or packets."""
import copy
import unittest
from server.server import Player, ITEMS, POTIONS, ENEMY_TYPES, MERCHANT, QUESTS, make_item
from server import inventory_rules as inv, loot_tables, loot_content
import test_inventory_windows_0810 as base
from test_dnd import WS


RETIRED = ('mana_potion', 'mana_potion_2', 'mana_potion_3', 'mana_potion_4')


class FixedRandom:
    def __init__(self, value): self.value = value
    def random(self): return self.value


def old_stack(template, uid):
    return {'uid': uid, 'template': template, 'slot': 'potion', 'quantity': 12,
            'potion_kind': 'mana', 'name': 'Mikstura many'}


class Catalog(unittest.TestCase):
    def test_catalog_rewards_and_authored_loot_only_expose_health(self):
        self.assertEqual(set(POTIONS), {'health_potion', 'health_potion_2', 'health_potion_3', 'health_potion_4'})
        self.assertFalse(any(inv.retired_potion(key) for key in ITEMS))
        self.assertTrue(all(ITEMS[key]['potion_kind'] == 'health' for key in POTIONS))
        self.assertEqual(MERCHANT['prices'], {'health_potion': 15})
        for quest in QUESTS:
            self.assertTrue(set(quest['reward'].get('potions', {})).issubset(POTIONS))
        for kind, spec in ENEMY_TYPES.items():
            entries = [entry for entry in spec['loot']['entries'] if entry['kind'] == 'potion']
            self.assertEqual(len(entries), 0 if kind in loot_content.NO_POTIONS else 1)
            for entry in entries:
                self.assertIn(entry['template'], POTIONS)
                self.assertEqual(entry['chance'], .15 if spec.get('boss') else .04)
            self.assertFalse(any(inv.retired_potion(template) for _, template in loot_tables.roll('mage', spec, FixedRandom(0))))

    def test_legacy_loot_keeps_health_probability_without_mana(self):
        spec = {'loot': {'tier': 4, 'family': 'beast', 'equipment_chance': 0,
                        'trophy_chance': 0, 'potion_chance': .2, 'unique_chance': 0, 'legendary_chance': 0}}
        self.assertEqual(loot_tables.roll('mage', spec, FixedRandom(.099)), [('potion', 'health_potion_2')])
        self.assertEqual(loot_tables.roll('mage', spec, FixedRandom(.1)), [])


class SavedSupplies(unittest.IsolatedAsyncioTestCase):
    setUp = base.Supplies.setUp
    tearDown = base.Supplies.tearDown

    def test_loaded_bags_remove_retired_stacks_preserve_health_q_and_other_items(self):
        p = self.p
        inv.add(p, 'health_potion_2', 2, make_item, 40)
        p.potion_slots = {'q': 'health_potion_2', 'r': 'mana_potion'}
        p.depot = [make_item('mummy_wand')]
        inventory, depot = copy.deepcopy(p.inventory), copy.deepcopy(p.depot)
        saved = copy.deepcopy(p.save_data())
        saved['inventory'] += [old_stack(key, 'bag_'+key) for key in RETIRED]
        saved['depot'] += [old_stack(key, 'depot_'+key) for key in RETIRED]
        saved['potions'] = {'health_potion': 999, 'mana_potion': 999}
        saved['loot_discoveries'] = {'mana_potion': ['goblin'], 'mummy_wand': ['mummy']}
        loaded = self.g.load_player(p.id, p.name, WS(), saved)
        self.assertEqual(loaded.inventory, inventory)
        self.assertEqual(loaded.depot, depot)
        self.assertEqual(loaded.potion_slots, {'q': 'health_potion_2'})
        self.assertEqual(loaded.loot_discoveries, {'mummy_wand': ['mummy']})
        self.assertEqual(loaded.potions['health_potion'], 3)
        self.assertFalse(set(RETIRED) & loaded.potions.keys())
        again = self.g.load_player(p.id, p.name, WS(), copy.deepcopy(loaded.save_data()))
        self.assertEqual(again.inventory, inventory)
        self.assertEqual(again.depot, depot)
        self.assertEqual(again.potion_slots, loaded.potion_slots)

    def test_retired_q_falls_back_and_empty_q_is_preserved(self):
        for old_q, expected in [('mana_potion', 'health_potion'), ('mana_potion_4', 'health_potion'), ('', '')]:
            saved = copy.deepcopy(self.p.save_data())
            saved['potion_slots'] = {'q': old_q, 'r': 'health_potion'}
            loaded = self.g.load_player(self.p.id, self.p.name, WS(), saved)
            self.assertEqual(loaded.potion_slots, {'q': expected})

    def test_old_count_only_save_imports_health_once_and_ignores_mana(self):
        p = Player('old', 'Old', WS())
        trophy = make_item('loot_trophy_rat')
        p.inventory = [trophy]
        p.potions = {'health_potion': 105, 'mana_potion': 200, 'mana_potion_2': 20}
        inv.ensure(p, ITEMS, POTIONS, make_item)
        self.assertEqual(inv.count(p, 'health_potion'), 105)
        self.assertEqual(p.inventory[0], trophy)
        self.assertFalse(any(inv.retired_potion(item['template']) for item in p.inventory))
        saved = copy.deepcopy(p.save_data())
        inv.ensure(p, ITEMS, POTIONS, make_item)
        self.assertEqual(p.save_data(), saved)

    async def test_mana_and_r_commands_cannot_buy_bind_consume_or_restore(self):
        p = self.p
        p.hp, p.mana = 1, 0
        p.mana_recovery_until = 1200
        p.rest_cooldown_until = 1150
        before = copy.deepcopy(p.save_data())
        for key in RETIRED:
            for command in ({'type': 'buy', 'item': key}, {'type': 'potion', 'item': key},
                            {'type': 'potion_bind', 'slot': 'q', 'item': key}):
                await self.g.on_packet(p.ws, command)
        await self.g.on_packet(p.ws, {'type': 'potion_bind', 'slot': 'r', 'item': 'health_potion'})
        p.potion_slots['r'] = 'health_potion'  # Forged/legacy binding is normalized before use.
        await self.g.on_packet(p.ws, {'type': 'potion', 'slot': 'r', 'item': 'health_potion'})
        self.assertEqual(p.save_data(), before)
        await self.g.on_packet(p.ws, {'type': 'potion', 'slot': 'q'})
        self.assertGreater(p.hp, 1)
        self.assertEqual((p.mana, p.mana_recovery_until, p.rest_cooldown_until), (0, 1200, 1150))


if __name__ == '__main__':
    unittest.main()
