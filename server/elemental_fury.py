"""Druid Elemental Fury (2024): a class choice, independent of ASI and circle.

Rules source: D&D Beyond 2024 Basic Rules, Druid, levels 7 and 15.
Spell ranges retain Bractwo's existing base distances; the 300-foot increase
uses the established geometry conversion (32 world units per 5 feet). A spell
with range Self/Touch does not qualify, including Produce Flame's hurl action.
"""
REQUIRED_LEVEL = 7
UPGRADE_LEVEL = 15
RANGE_BONUS_FEET = 300
UNITS_PER_FOOT = 32 / 5
OPTIONS = {
    'potent_spellcasting': dict(name='Potężne sztuczki', english='Potent Spellcasting',
        icon='assets/spells/starry_wisp.svg',
        upgrade_description='Poziom 15: +300 stóp zasięgu sztuczek druida o zasięgu co najmniej 10 stóp; bez Dotyku i Siebie.',
        description='Dodajesz modyfikator Mądrości do obrażeń sztuczek druida. Od poziomu 15: +300 stóp zasięgu sztuczek o zasięgu co najmniej 10 stóp; nie dotyczy Dotyku ani Siebie.'),
    'primal_strike': dict(name='Pierwotne uderzenie', english='Primal Strike',
        icon='assets/spells/wild_shape_wolf.svg',
        upgrade_description='Poziom 15: dodatkowe obrażenia rosną do 2k8, nadal raz w swojej turze.',
        description='Raz w swojej turze po trafieniu bronią lub atakiem bestii w Dzikim kształcie: +1k8 zimna, ognia, błyskawic albo grzmotu. Typ wybierasz dla każdego trafienia. Od poziomu 15: +2k8.'),
}
DAMAGE_TYPES = {'cold':'Zimno', 'fire':'Ogień', 'lightning':'Błyskawice', 'thunder':'Grzmot'}
# Official spell range, rather than the adapted interaction/hurl distance.
# Circle spells also count as druid spells for the character receiving them.
CANTRIP_RANGES = {'produce_flame':0, 'thorn_whip':30, 'starry_wisp':60,
                 'shillelagh':0, 'guidance':0, 'fire_bolt':120,
                 'ray_of_frost':60, 'acid_splash':60, 'shocking_grasp':0}


def choice(p):
    selected = getattr(p, 'elemental_fury', '')
    return selected if (getattr(p, 'class_id', '') == 'druid'
        and getattr(p, 'level', 0) >= REQUIRED_LEVEL and isinstance(selected, str) and selected in OPTIONS) else ''


def damage_type(p):
    selected = getattr(p, 'elemental_damage_type', 'cold')
    return selected if isinstance(selected, str) and selected in DAMAGE_TYPES else 'cold'


def sanitize(p):
    p.elemental_fury = choice(p)
    p.elemental_damage_type = damage_type(p)


def strike_enabled(p):
    try: from . import druid_circles as circles
    except ImportError: import druid_circles as circles
    return circles.state(p).get('elemental_strike_enabled', True) is not False


def sheet(p):
    is_druid = getattr(p, 'class_id', '') == 'druid'
    selected = choice(p)
    return dict(id=selected, name=OPTIONS[selected]['name'] if selected else '',
        pending=is_druid and p.level >= REQUIRED_LEVEL and not selected,
        required_level=REQUIRED_LEVEL, upgrade_level=UPGRADE_LEVEL,
        upgraded=is_druid and p.level >= UPGRADE_LEVEL,
        upgrade_description=OPTIONS[selected]['upgrade_description'] if selected else '',
        options=[dict(id=key, **spec) for key, spec in OPTIONS.items()] if is_druid else [],
        damage_type=damage_type(p),
        strike_enabled=strike_enabled(p),
        damage_types=[dict(id=key, name=name) for key, name in DAMAGE_TYPES.items()] if selected == 'primal_strike' else [],
        strike_dice=[2 if p.level >= UPGRADE_LEVEL else 1, 8, 0] if selected == 'primal_strike' else [],
        range_bonus_feet=RANGE_BONUS_FEET if selected == 'potent_spellcasting' and p.level >= UPGRADE_LEVEL else 0)


def druid_cantrip(p, spec):
    if getattr(p, 'class_id', '') != 'druid' or spec.get('circle', 0) != 0 or spec.get('feature'):
        return False
    try: from . import druid_circles as circles
    except ImportError: import druid_circles as circles
    return 'druid' in spec.get('class_ids', ()) or spec.get('id') in circles.bonus_spells(p)


def augment_spell(p, spec):
    """Apply once to a fresh profile; flat Wisdom is never doubled on a critical."""
    if not druid_cantrip(p, spec): return
    key = spec.get('id')
    tabletop_range = spec.get('tabletop_range_feet', CANTRIP_RANGES.get(key))
    if tabletop_range is not None: spec['tabletop_range_feet'] = tabletop_range
    if choice(p) != 'potent_spellcasting': return
    if spec.get('dice') and spec.get('damage_type') and spec.get('kind') != 'heal':
        try: from . import combat_rules as rules
        except ImportError: import combat_rules as rules
        bonus = rules.ability_modifier(p, 'wisdom')
        spec['dice'][2] += bonus
        spec['elemental_fury_damage_bonus'] = bonus
    if p.level >= UPGRADE_LEVEL and isinstance(tabletop_range, (int, float)) and tabletop_range >= 10:
        spec['range'] = spec.get('range', 0) + int(RANGE_BONUS_FEET * UNITS_PER_FOOT)
        spec['elemental_fury_range_bonus_feet'] = RANGE_BONUS_FEET


def primal_strike(p, result, rng, now, *, weapon=True):
    """Append a separately resisted critical-eligible rider once in an own turn."""
    if (not weapon or not result.get('hit') or result.get('check') != 'attack'
            or choice(p) != 'primal_strike' or not strike_enabled(p)): return False
    if getattr(p, '_off_turn_attack', False): return False
    token = getattr(p, '_feat_turn_until', 0)
    if not isinstance(token, (int, float)) or token <= now: return False
    try: from . import combat_rules as rules, druid_circles as circles
    except ImportError: import combat_rules as rules, druid_circles as circles
    # Arcane implements and unarmed attacks are not weapon attacks. Polymorph
    # replaces the character's features, while Wild Shape retains this one.
    if getattr(p, 'form', ''):
        if not circles.wild_shape_active(p): return False
    else:
        held = rules.gear.weapon(p)
        if not held or rules.gear.is_focus(held): return False
    state = circles.state(p)
    if state.get('elemental_strike_turn') == token: return False
    dice = (2 if p.level >= UPGRADE_LEVEL else 1, 8, 0)
    extra = rules.roll_damage(rng, dice, result.get('critical', False))
    components = result.setdefault('damage_components',
        [dict(type=result.get('damage_type', rules.damage_type(p)), damage=result['damage'])])
    components.append(dict(type=damage_type(p), damage=extra['damage']))
    result['damage'] += extra['damage']
    result['damage_dice'] += ' + ' + rules.dice_text(dice) + ' (Pierwotne uderzenie)'
    result['elemental_strike_rolls'] = extra['damage_rolls']
    result['elemental_damage_type'] = damage_type(p)
    rules.record_damage_roll(result, extra, 'Pierwotne uderzenie')
    state['elemental_strike_turn'] = token
    return True
