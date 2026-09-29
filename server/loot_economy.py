"""UI20: mundane local shops and rare, species-owned expedition equipment.

Configure after all creatures and the canonical magic catalog. Merchant requests
are explicit lists, never all items with a price. Percentages are independent
per eligible player kill, as in loot_tables.roll.
"""

# Six offers in Brzezina: supplies plus ordinary woodland equipment.
SHOP_STOCK = {
    'przystan': ['health_potion', 'cloth', 'knight_weapon_1', 'ranger_weapon_1', 'mage_weapon_1', 'druid_weapon_1', 'wooden_shield'],
    'brzezina': ['health_potion', 'health_potion_2', 'druid_leather', 'ranger_weapon_1', 'druid_weapon_1', 'wooden_shield'],
    'zloty_port': ['health_potion', 'health_potion_2', 'knight_weapon_1', 'training_greatsword', 'fighter_chain_mail', 'fighter_shield'],
    'mrozna_przystan': ['health_potion_2', 'health_potion_3', 'hide_armor', 'training_maul', 'ranger_weapon_1', 'fighter_shield'],
    'popielny_port': ['health_potion_3', 'health_potion_4', 'training_greatsword', 'fighter_chain_mail', 'fighter_shield'],
    'solna_przystan': ['health_potion', 'health_potion_2', 'druid_leather', 'ranger_weapon_1', 'wooden_shield'],
    'zarowe_nabrzeze': ['health_potion_2', 'training_maul', 'training_greatsword', 'fighter_chain_mail'],
    'przelom_rzeki': ['health_potion', 'cloth', 'ranger_weapon_1', 'druid_weapon_1'],
    'przystan_cieni': ['health_potion_2', 'health_potion_3', 'mage_weapon_1', 'druid_weapon_1', 'cloth'],
    'bazaltowa_straznica': ['health_potion_3', 'training_greatsword', 'fighter_chain_mail', 'fighter_shield'],
}
MUNDANE_PRICES = {'cloth': 18, 'knight_weapon_1': 15, 'ranger_weapon_1': 15,
                  'mage_weapon_1': 15, 'druid_weapon_1': 15}
MUNDANE_ICONS = {'cloth': 'armor', 'knight_weapon_1': 'weapon', 'ranger_weapon_1': 'bow',
                 'mage_weapon_1': 'staff', 'druid_weapon_1': 'nature_staff'}

# New magic items previously sold by towns now have concrete monster sources.
# Existing named equipment remains in its original tables; these add purposeful
# alternatives in the new crypts and bosses guarding UI19 adventure locations.
RARE_DROPS = {
    'bandit_captain': [('ring_swimming', 1), ('ring_protection', 1), ('magic_longsword_1', 3)],
    'orc_shaman': [('magic_quarterstaff_1', .6), ('ring_resistance_lightning', .3)],
    'thorn_shaman': [('ring_resistance_poison', .3), ('ring_free_action', .2)],
    'crypt_guard': [('magic_longsword_1', .6), ('magic_shield_1', .5)],
    'elf': [('magic_longbow_1', .6), ('mithral_chain_mail', .4)],
    'dwarf': [('adamantine_chain_mail', .5), ('magic_shield_1', .4), ('ring_warmth', .2)],
    'necromancer': [('ring_resistance_necrotic', .3)],
    'frost_ranger': [('ring_resistance_cold', .3), ('mithral_chain_mail', .4)],
    'obsidian_knight': [('adamantine_chain_mail', .5)],
    'demon': [('ring_resistance_fire', .3)],
    'lich_king': [('magic_chain_mail_1', 1.5)],
    'ice_queen': [('ring_warmth', 2), ('ring_resistance_cold', 1.5)],
    'ancient_dragon': [('ring_resistance_fire', 2)],
    'sand_queen': [('ring_resistance_poison', 2)],
    # Animated, still-armed guardians from the preceding adventure update.
    'adv_flying_sword': [('magic_longsword_1', .3)],
    'adv_animated_armor': [('magic_chain_mail_1', .2)],
    'exp_dune_skeleton': [('crypt_blade', 1.2), ('sentry_chainmail', 2.5)],
    'exp_crypt_archer': [('crypt_bow', 1.5), ('magic_longbow_1', .8)],
    'exp_sand_revenant': [('crypt_plate', 1), ('crypt_breastplate', 1.5), ('magic_longsword_1', .8)],
    'exp_tomb_acolyte': [('mummy_wand', 2), ('hierophant_robe', 1), ('ring_resistance_necrotic', .3)],
    'exp_scarab_keeper': [('sand_halfplate', 5), ('hierophant_wand', 4), ('magic_shield_1', 2.5), ('ring_resistance_poison', 2)],
    'exp_sunless_pharaoh': [('lich_wand', 4), ('lich_robe', 4), ('crypt_plate', 5), ('magic_chain_mail_1', 3), ('ring_protection', 2)],
    'exp_root_warden': [('thorn_staff', 6), ('thorn_leather', 5), ('magic_quarterstaff_1', 4), ('ring_free_action', 2), ('ring_resistance_lightning', 1.5)],
    'exp_sevenfold_regent': [('crypt_blade', 5), ('crypt_bow', 4), ('crypt_breastplate', 5), ('ring_protection', 2), ('ring_resistance_necrotic', 2)],
    'exp_ember_overseer': [('dragon_scale', 4), ('adamantine_chain_mail', 3.5), ('magic_shield_1', 3), ('ring_resistance_fire', 2)],
    'exp_obsidian_librarian': [('ancient_plate', 3), ('obsidian_greatsword', 4), ('obsidian_plate', 4), ('lich_wand', 5), ('magic_chain_mail_1', 3), ('ring_resistance_necrotic', 2)],
}


def refresh_shops(content):
    """Also runs before the final item catalog exists; repeated calls are safe."""
    items = content.ITEMS
    for key, price in MUNDANE_PRICES.items():
        if key in items:
            items[key]['price'] = price
            items[key]['icon'] = 'assets/equipment/' + MUNDANE_ICONS[key] + '.svg'
    for npc in content._continent_npcs:
        if npc.get('service') != 'merchant':
            continue
        city_id = npc.get('city_id', '')
        if npc['id'].startswith('focus_trader_'):
            requested = ['mage_weapon_1', 'druid_weapon_1', 'health_potion_2']
            npc['role'] = 'Podstawowe fokusy i zapasy na wyprawę'
        else:
            requested = SHOP_STOCK.get(city_id, SHOP_STOCK['przystan'])
        npc['stock'] = [key for key in requested if key in items and 'price' in items[key]]
    content.STARTER_MERCHANT_STOCK[:] = [key for key in SHOP_STOCK['przystan']
                                       if key in items and 'price' in items[key]]


def configure(items, enemies):
    for kind, rows in RARE_DROPS.items():
        if kind not in enemies:
            continue
        enemy = enemies[kind]
        entries = enemy['loot']['entries']
        by_template = {entry['template']: entry for entry in entries}
        for template, percent in rows:
            if template not in items:
                raise ValueError('Nieznany rzadki łup: ' + template)
            if items[template].get('min_level', 1) > enemy.get('level', 1):
                raise ValueError('Łup przekracza poziom potwora: ' + kind + '/' + template)
            entry = dict(kind='item', template=template, chance=percent / 100)
            if template in by_template:
                by_template[template].update(entry)
            else:
                entries.append(entry)
                by_template[template] = entry
        enemy['loot_origin'] = 'Rzadkie relikty i wyposażenie strażnika' if enemy.get('boss') else 'Ekwipunek i rzadkie znaleziska'
    # The same ceilings apply to old aliases and new canonical ring templates.
    # Rebuild item sources only after final probabilities have been applied.
    for item in items.values():
        item.pop('sources', None)
    for kind, enemy in enemies.items():
        for entry in enemy.get('loot', {}).get('entries', []):
            item = items.get(entry['template'])
            if not item:
                raise ValueError('Nieznany szablon łupu: ' + entry['template'])
            if item.get('slot') == 'ring' and item.get('magic_id'):
                entry['chance'] = min(entry['chance'], .02 if enemy.get('boss') else .003)
            if entry['kind'] == 'item':
                item.setdefault('sources', []).append(dict(kind=kind, name=enemy['name'], chance=entry['chance']))
