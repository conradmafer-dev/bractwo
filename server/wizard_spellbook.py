"""Wizard learning and preparation, independent of transport and rest timers.

The book holds levelled spells only. Cantrips and class actions keep their own
rules. Learning credits retain the spell-circle ceiling from the level at which
they were earned; an exhausted catalogue never turns old credits into new ones.
"""
try:
    from . import dnd_content as dnd
except ImportError:
    import dnd_content as dnd

VERSION = 1
PREPARED_LIMITS = (4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 18, 19, 21, 22, 23, 24, 25)
SCHOOLS = ('evocation', 'abjuration', 'divination', 'illusion')
# Schools are explicit: damage type alone does not establish a spell's school.
SPELL_SCHOOLS = {
    'magic_missile': 'evocation', 'burning_hands': 'evocation',
    'shield': 'abjuration', 'mage_armor': 'abjuration', 'alarm': 'abjuration',
    'longstrider': 'transmutation', 'find_familiar': 'conjuration',
    'scorching_ray': 'evocation', 'misty_step': 'conjuration',
    'fireball': 'evocation', 'lightning_bolt': 'evocation',
    'protection_from_energy': 'abjuration', 'blight': 'necromancy',
    'ice_storm': 'evocation', 'stoneskin': 'transmutation',
    'cone_of_cold': 'evocation', 'chain_lightning': 'evocation',
    'sunbeam': 'evocation', 'finger_of_death': 'necromancy',
    'sunburst': 'evocation', 'incendiary_cloud': 'conjuration',
    'meteor_swarm': 'evocation', 'foresight': 'divination',
}


def _int(value, default=0, maximum=20):
    return min(maximum, max(0, value)) if type(value) is int else default


def _level(p):
    return max(1, _int(getattr(p, 'level', 1), default=1))


def _watermark(value, current):
    # Zero is legitimate only as the initial ungranted watermark. Invalid
    # saved values must not become zero and reissue already-spent budgets.
    return value if type(value) is int and 0 <= value <= 20 else current


def prepared_limit(level):
    return PREPARED_LIMITS[max(1, _int(level, default=1))-1]


def is_book_spell(key):
    s = dnd.SPELLS.get(key) if isinstance(key, str) else None
    return bool(s and 'mage' in s.get('class_ids', ()) and not s.get('feature')
                and type(s.get('circle')) is int and 1 <= s['circle'] <= 9)


def _eligible(p, key):
    return (getattr(p, 'class_id', '') == 'mage' and is_book_spell(key)
            and _level(p) >= dnd.spell_level(dnd.SPELLS[key], 'mage'))


def _catalog(p):
    return [key for key in dnd.SPELLS if _eligible(p, key)]


def _state(p):
    data = getattr(p, 'wizard_spellbook', None)
    return data if isinstance(data, dict) and type(data.get('version')) is int and data['version'] == VERSION else None


def _missing(p):
    data = getattr(p, 'wizard_spellbook', None)
    return data is None or data == {}


def _clean_keys(p, values):
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(key for key in values[:len(dnd.SPELLS)] if _eligible(p, key)))


def knows(p, key):
    if not _eligible(p, key):
        return False
    data = _state(p)
    return bool(getattr(p, '_legacy_wizard_catalog', False)) if data is None else key in _clean_keys(p, data.get('known'))


def prepared(p, key):
    if not _eligible(p, key):
        return False
    data = _state(p)
    if data is None:
        return bool(getattr(p, '_legacy_wizard_catalog', False))
    known = set(_clean_keys(p, data.get('known')))
    if key not in known:
        return False
    selected = [k for k in _clean_keys(p, data.get('prepared')) if k in known]
    return key in selected[:prepared_limit(_level(p))]


def ritual_allowed(p, key):
    return bool(knows(p, key) and dnd.SPELLS[key].get('ritual'))


def _school(p):
    key = getattr(p, 'wizard_school', '')
    return key if (getattr(p, 'class_id', '') == 'mage' and getattr(p, 'promoted', False)
                   and _level(p) >= 3 and isinstance(key, str) and key in SCHOOLS) else ''


def _grant_specs(level, school=''):
    rows = [dict(id='base:1', level=1, max_circle=1, school='', count=6)]
    for earned in range(2, level+1):
        rows.append(dict(id=f'base:{earned}', level=earned,
                         max_circle=dnd.circle_for('mage', earned), school='', count=2))
    if school:
        rows.append(dict(id=f'{school}:3', level=3, max_circle=2, school=school, count=2))
        for earned in range(5, min(17, level)+1, 2):
            rows.append(dict(id=f'{school}:{earned}', level=earned,
                             max_circle=dnd.circle_for('mage', earned), school=school, count=1))
    return rows


def _fresh():
    return dict(version=VERSION, known=[], prepared=[], grants=[], granted_level=0,
                savant_school='', savant_granted_level=0, preparation_level=0,
                free_preparations=0, legacy_migrated=False)


def migrate(p, legacy=False):
    """Initialize once; legacy characters retain every formerly unlocked spell."""
    if getattr(p, 'class_id', '') != 'mage':
        p.wizard_spellbook = {}
        return
    if _state(p) is not None:
        sync(p)
        return
    missing = _missing(p)
    p.wizard_spellbook = data = _fresh()
    if legacy:
        data['known'] = _catalog(p)
        hotbar = getattr(p, 'hotbar', [])
        preferred = _clean_keys(p, hotbar)
        preferred = preferred + dnd.DEFAULT_HOTBARS['mage'] + data['known']
        data['prepared'] = _clean_keys(p, preferred)[:prepared_limit(_level(p))]
        data.update(granted_level=_level(p), preparation_level=_level(p),
                    savant_school=_school(p), savant_granted_level=_level(p) if _school(p) else 0,
                    legacy_migrated=True)
    elif not missing:
        # A malformed saved version is not permission to mint a fresh budget.
        data.update(granted_level=_level(p), preparation_level=_level(p),
                    savant_school=_school(p), savant_granted_level=_level(p) if _school(p) else 0)
    sync(p)


def sync(p):
    """Sanitize persisted fields and add only genuinely new level entitlements."""
    if getattr(p, 'class_id', '') != 'mage':
        return
    if _state(p) is None:
        migrate(p)
        return
    data = _state(p)
    level = _level(p)
    old_level = _watermark(data.get('granted_level'), level)
    old_preparation = _watermark(data.get('preparation_level'), level)
    old_school = data.get('savant_school', '')
    old_school = old_school if isinstance(old_school, str) and old_school in SCHOOLS else ''
    old_savant = _watermark(data.get('savant_granted_level'), level)
    school = _school(p)
    data['known'] = _clean_keys(p, data.get('known'))
    data['prepared'] = [key for key in _clean_keys(p, data.get('prepared'))
                        if key in data['known']][:prepared_limit(level)]
    free = _int(data.get('free_preparations'), maximum=25)
    if old_preparation < level:
        free += prepared_limit(level) - (prepared_limit(old_preparation) if old_preparation else 0)
    data['free_preparations'] = min(free, prepared_limit(level)-len(data['prepared']))
    saved = data.get('grants', [])
    old_grants = {}
    if isinstance(saved, list):
        for row in saved[:40]:
            if isinstance(row, dict) and isinstance(row.get('id'), str) and row['id'] not in old_grants:
                old_grants[row['id']] = row.get('remaining')
    rows = []
    for spec in _grant_specs(level, school):
        ceiling = old_savant if school == old_school else 0
        new = spec['level'] > (ceiling if spec['school'] else old_level)
        remaining = spec['count'] if new else _int(old_grants.get(spec['id']), maximum=spec['count'])
        rows.append({**spec, 'remaining': remaining})
    data.update(grants=rows, granted_level=max(old_level, level),
                preparation_level=max(old_preparation, level), legacy_migrated=data.get('legacy_migrated') is True)
    if school:
        data.update(savant_school=school, savant_granted_level=max(old_savant if school == old_school else 0, level))
    else:
        data.update(savant_school=old_school, savant_granted_level=old_savant)


def _matches(grant, key):
    return (grant.get('remaining', 0) > 0 and dnd.SPELLS[key]['circle'] <= grant['max_circle']
            and (not grant['school'] or SPELL_SCHOOLS.get(key) == grant['school']))


def learn(p, key):
    if getattr(p, 'class_id', '') != 'mage':
        return 'Księga czarów jest zdolnością czarodzieja.'
    sync(p)
    data = _state(p)
    if not _eligible(p, key):
        return 'Wybierz dostępny czar czarodzieja I–IX kręgu.'
    if key in data['known']:
        return 'Ten czar jest już w twojej księdze.'
    matches = [row for row in data['grants'] if _matches(row, key)]
    if not matches:
        return 'Brak wyboru nauki pozwalającego poznać ten czar.'
    grant = min(matches, key=lambda row: (row['max_circle'], not bool(row['school']), row['level']))
    grant['remaining'] -= 1
    data['known'].append(key)
    return ''


def _validate_list(p, keys):
    if not isinstance(keys, list) or len(keys) > prepared_limit(_level(p)):
        return 'Przekroczono limit przygotowanych czarów.'
    if any(not isinstance(key, str) for key in keys) or len(set(keys)) != len(keys):
        return 'Lista czarów musi zawierać różne prawidłowe czary.'
    if any(not knows(p, key) for key in keys):
        return 'Przygotuj tylko poznane czary z własnej księgi.'
    return ''


def fill(p, keys):
    """Spend earned empty slots; existing preparations can never be replaced."""
    if getattr(p, 'class_id', '') != 'mage':
        return 'Księga czarów jest zdolnością czarodzieja.'
    sync(p)
    reason = _validate_list(p, keys)
    if reason:
        return reason
    data = _state(p)
    if not set(data['prepared']).issubset(keys):
        return 'Wymiana przygotowanych czarów wymaga odpoczynku.'
    additions = len(keys)-len(data['prepared'])
    if additions > data['free_preparations']:
        return 'Brak nowych miejsc przygotowania; zmień listę podczas długiego odpoczynku.'
    data['prepared'] = list(keys)
    data['free_preparations'] -= additions
    return ''


def validate_rest(p, kind, plan):
    if plan is None or plan == {}:
        return ''
    if getattr(p, 'class_id', '') != 'mage' or _state(p) is None:
        return 'Przygotowywanie czarów wymaga księgi czarodzieja.'
    if not isinstance(plan, dict):
        return 'Nieprawidłowy wybór przygotowania czarów.'
    if kind == 'long' and set(plan) == {'prepared'}:
        return _validate_list(p, plan['prepared'])
    if kind != 'short' or set(plan) != {'memorize'} or _level(p) < 5:
        return 'Memorize Spell wymaga poziomu 5 i krótkiego odpoczynku.'
    pair = plan['memorize']
    if not isinstance(pair, dict) or set(pair) != {'forget', 'prepare'}:
        return 'Wybierz dokładnie jeden czar do zastąpienia i jeden do przygotowania.'
    old, new = pair['forget'], pair['prepare']
    if not isinstance(old, str) or not isinstance(new, str) or old == new:
        return 'Wybierz dwa różne czary z księgi.'
    if not prepared(p, old) or not knows(p, new) or prepared(p, new):
        return 'Zastąp jeden przygotowany czar innym poznanym, nieprzygotowanym czarem.'
    return ''


def finish_rest(p, kind, plan):
    reason = validate_rest(p, kind, plan)
    if reason or not plan:
        return reason
    data = _state(p)
    if kind == 'long':
        data['prepared'] = list(plan['prepared'])
    else:
        pair = plan['memorize']
        data['prepared'] = [pair['prepare'] if key == pair['forget'] else key for key in data['prepared']]
    data['free_preparations'] = 0
    return ''


def signature(p):
    data = _state(p)
    if data is None:
        return ('legacy' if getattr(p, '_legacy_wizard_catalog', False) else 'uninitialized' if _missing(p) else 'invalid',)
    return (VERSION, tuple(_clean_keys(p, data.get('known'))),
            tuple(_clean_keys(p, data.get('prepared'))[:prepared_limit(_level(p))]))


def sheet(p):
    """Read-only owner snapshot; migrations, level-ups and choices call sync."""
    enabled = getattr(p, 'class_id', '') == 'mage'
    data = _state(p)
    known = _clean_keys(p, data.get('known')) if enabled and data else []
    known_set = set(known)
    selected = [key for key in _clean_keys(p, data.get('prepared')) if key in known_set][:prepared_limit(_level(p))] if enabled and data else []
    grants = []
    if enabled and data:
        saved = data.get('grants', [])
        available = {}
        if isinstance(saved, list):
            for row in saved[:40]:
                if isinstance(row, dict) and isinstance(row.get('id'), str) and row['id'] not in available:
                    available[row['id']] = row.get('remaining')
        grants = [{**spec, 'remaining': _int(available.get(spec['id']), maximum=spec['count'])}
                  for spec in _grant_specs(_level(p), _school(p))]
    unlearned = [key for key in _catalog(p) if key not in known] if enabled else []
    choices = [key for key in unlearned if any(_matches(row, key) for row in grants)]
    credits = sum(row['remaining'] for row in grants)
    limited = (credits > len(choices) or any(row['remaining'] and not any(_matches(row, key) for key in unlearned) for row in grants))
    return dict(enabled=enabled, known=known, prepared=selected,
                prepared_limit=prepared_limit(_level(p)) if enabled else 0,
                free_preparations=min(_int(data.get('free_preparations'), maximum=25), prepared_limit(_level(p))-len(selected)) if enabled and data else 0,
                learning_choices=choices, learning_credits=credits, pending_learning=bool(choices),
                learning_grants=[dict(row) for row in grants if row['remaining']],
                memorize_available=enabled and _level(p) >= 5,
                legacy_migrated=bool(enabled and data and data.get('legacy_migrated') is True),
                catalog_limited=bool(enabled and limited))
