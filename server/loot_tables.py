"""Server-owned species loot; chances are independent, per eligible player.

Bosses guarantee tier-based equipment; named family items roll separately.
Trophies are valuable trade goods, never equippable. Potions use existing stacks.
"""
RARITIES = {'common': 'Pospolity', 'uncommon': 'Niepospolity', 'rare': 'Rzadki',
            'epic': 'Epicki', 'legendary': 'Legendarny'}
FAMILIES = {
    'beast': ('Kieł łowcy', 9, 'Znak Łowcy', 2, ['rat', 'boar', 'wolf', 'bear', 'frost_wolf', 'crocodile', 'nightmare']),
    'vermin': ('Gruczoł jadowy', 12, 'Jadowy Splot', 2, ['spider', 'spitting_spider', 'scorpion', 'scarab']),
    'raider': ('Znak rabusiów', 15, 'Przysięga Banity', 3, ['goblin', 'bandit', 'bandit_archer', 'orc', 'orc_shaman', 'orc_king', 'elf', 'dwarf']),
    'undead': ('Pył grobowy', 24, 'Pieczęć Krypty', 4, ['skeleton', 'skeleton_archer', 'ghoul', 'mummy', 'vampire', 'necromancer', 'lich', 'lich_king', 'sand_queen']),
    'stone': ('Rdzeń skalny', 32, 'Serce Granitu', 3, ['guardian', 'boss', 'troll', 'ogre', 'cyclops', 'golem', 'minotaur', 'ancient_guardian', 'harpy']),
    'frost': ('Odłamek wiecznego lodu', 48, 'Lodowe Dziedzictwo', 6, ['ice_elemental', 'frost_giant', 'ice_queen']),
    'dragon': ('Smocza łuska', 65, 'Smocza Przysięga', 7, ['dragon', 'dragon_lord', 'ancient_dragon']),
    'abyss': ('Żar otchłani', 80, 'Szept Otchłani', 8, ['demon', 'abyss_walker', 'abyss_lord', 'fire_elemental', 'wisp']),
}


def configure(items, enemies, tier_levels):
    classes = ['knight', 'paladin', 'mage', 'druid']
    for family, (trophy, value, name, tier, kinds) in FAMILIES.items():
        items[f'trophy_{family}'] = {'name': trophy, 'slot': 'trophy', 'class_ids': [], 'min_level': 1,
                                    'value': value, 'rarity': 'uncommon', 'description': 'Trofeum. Kupcy skupują je za złoto; można przechować w depozycie.'}
        for vocation in classes:
            base = items[f'{vocation}_weapon_{tier}']
            items[f'unique_{family}_{vocation}'] = {**base, 'name': f'{name} · '+{'knight': 'ostrze', 'paladin': 'łuk', 'mage': 'różdżka', 'druid': 'kostur'}[vocation],
                'attack': base.get('attack', 0)+max(2, tier*2), 'value': base['value']*3, 'rarity': 'rare' if tier < 6 else 'epic',
                'description': 'Rzadki łup charakterystyczny dla tej rodziny potworów.'}
        base = items['hunter_ring'] if tier <= 3 else items[f'ring_{tier}']
        items[f'unique_{family}_ring'] = {**base, 'name': name+' · pierścień', 'attack': base.get('attack', 0)+2,
            'armor': base.get('armor', 0)+2, 'value': base['value']*3, 'rarity': 'rare' if tier < 6 else 'epic',
            'description': 'Rzadki pierścień. Pasuje do każdej profesji.'}
    items['relic_summit'] = {**items['ring_9'], 'name': 'Relikt Władców Szczytów', 'attack': 33, 'armor': 12,
                           'value': 18000, 'rarity': 'legendary', 'description': 'Legendarny relikt. Wymaga poziomu 110. Bardzo rzadki łup z bossów poziomu 110+.'}
    for kind, spec in enemies.items():
        family = next((f for f, values in FAMILIES.items() if kind in values[4]), 'stone')
        tier = spec.get('tier', 3 if spec.get('boss') else 2 if kind in ('wisp', 'guardian', 'goblin', 'spider', 'skeleton') else 1)
        # High-tier loot never appears on a weak creature merely sharing a family.
        if kind in ('ogre', 'harpy'):
            tier = max(t for t, minimum in tier_levels.items() if minimum <= spec['level'])
        unique_tier = FAMILIES[family][3]
        unique_level = tier_levels[unique_tier]
        eligible = spec.get('level', 8 if kind == 'boss' else 1) >= unique_level
        spec['loot'] = {'family': family, 'tier': tier, 'equipment_chance': 1.0 if spec.get('boss') else .12,
                        'trophy_chance': .8 if spec.get('boss') else .24,
                        'potion_chance': .35 if spec.get('boss') else .07,
                        'unique_chance': (.08 if spec.get('boss') else .015) if eligible else 0,
                        'legendary_chance': .002 if spec.get('boss') and spec.get('level', 0) >= 110 else 0}


def ordinary(vocation, tier, rng):
    armor = ['cloth', 'leather', 'scale'][tier-1] if tier <= 3 else f'armor_{tier}'
    ring = ('copper_ring' if tier == 1 else 'hunter_ring') if tier <= 3 else f'ring_{tier}'
    return rng.choice([f'{vocation}_weapon_{tier}', armor, ring])


def unique(vocation, family, rng):
    return f'unique_{family}_{vocation}' if rng.random() < .65 else f'unique_{family}_ring'


def roll(vocation, spec, rng):
    table = spec['loot']; result = []
    if rng.random() < table['equipment_chance']:
        result.append(('item', ordinary(vocation, table['tier'], rng)))
    if rng.random() < table['trophy_chance']:
        result.append(('item', 'trophy_'+table['family']))
    if rng.random() < table['potion_chance']:
        suffix = '_3' if table['tier'] >= 7 else '_2' if table['tier'] >= 4 else ''
        result.append(('potion', rng.choice(['health_potion', 'mana_potion'])+suffix))
    if rng.random() < table['unique_chance']:
        result.append(('item', unique(vocation, table['family'], rng)))
    if rng.random() < table['legendary_chance']:
        result.append(('item', 'relic_summit'))
    return result


def cache(vocation, level, tier_levels, rng):
    tier = max(t for t, minimum in tier_levels.items() if minimum <= level)
    families = [f for f, v in FAMILIES.items() if tier_levels[v[3]] <= level]
    family = rng.choice(families or ['beast'])
    result = [('item', ordinary(vocation, tier, rng)), ('item', 'trophy_'+family)]
    if families and rng.random() < .06:
        result.append(('item', unique(vocation, family, rng)))
    return result
