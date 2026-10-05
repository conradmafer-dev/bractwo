"""Promotion archetypes: D&D 2014 combat features, with Bractwo turns.

Selection and remaining resources are private to the owner. This release adds
the starting combat package; the catalogue deliberately lists only implemented
features, not an entire tabletop subclass progression.
"""
try:
    from .profession_rules import PROMOTION_LEVEL
except ImportError:
    from profession_rules import PROMOTION_LEVEL

ARCHETYPES = {
    'battle_master': dict(name='Mistrz Bitewny', class_id='knight', description='Wybierz trzy manewry. Kości przewagi odnawiasz podczas krótkiego lub długiego odpoczynku.'),
    'champion': dict(name='Czempion', class_id='knight', description='Trafienia krytyczne bronią przy naturalnym 19–20. Od poziomu 15: 18–20. Nie obejmuje czarów i towarzysza.'),
    'hunter': dict(name='Hunter · Myśliwy', class_id='ranger', description='Wybierz jedną technikę polowania. Dotychczasowe czary i wilczy towarzysz pozostają dostępne.'),
}
MANEUVERS = {
    'precision': dict(name='Precyzyjny atak', english='Precision Attack', kind='offense', description='Przygotuj wsparcie następnego pudła bronią: kość przewagi dodaje się do rzutu trafienia przed rozstrzygnięciem. Trafienie i naturalna 1 nie zużywają przygotowania ani kości. Nie zwiększa obrażeń.'),
    'riposte': dict(name='Riposta', english='Riposte', kind='reaction', description='Gdy widoczny przeciwnik chybi cię atakiem wręcz: reakcja i kość przewagi pozwalają na kontratak bronią wręcz. Przy trafieniu dodaj kość do obrażeń.'),
    'parry': dict(name='Parowanie', english='Parry', kind='reaction', description='Reakcja po otrzymaniu obrażeń ataku wręcz: zmniejsz obrażenia o kość przewagi + modyfikator Zręczności. Nie zatrzymuje strzał ani obrażeń obszarowych.'),
    'trip': dict(name='Powalający atak', english='Trip Attack', kind='offense', description='Przy następnym trafieniu bronią wydaj kość przewagi i dodaj ją do obrażeń. Cel Duży lub mniejszy: rzut obronny Siły albo powalenie.'),
    'menacing': dict(name='Zastraszający atak', english='Menacing Attack', kind='offense', description='Przy następnym trafieniu bronią wydaj kość przewagi i dodaj ją do obrażeń. Obrona Mądrości albo przerażenie: utrudnione ataki i testy cech przy widocznym wojowniku oraz zakaz zbliżania się do niego do końca jego następnej tury.'),
}
PREY = {
    'colossus_slayer': dict(name='Pogromca kolosów', english='Colossus Slayer', description='Raz na turę, gdy trafisz bronią cel, który przed trafieniem miał mniej niż maksymalne HP: +1k8 obrażeń. Działa niezależnie od rozmiaru celu.'),
    'horde_breaker': dict(name='Rozbijacz hord', english='Horde Breaker', description='Raz na 3 sekundy po ataku bronią automatycznie atakujesz jeszcze jednego przeciwnika obok celu, w odległości do 1 pola. Działa także z łukiem. Drugi przeciwnik musi być w zasięgu broni; dodatkowy atak może chybić.'),
    'giant_killer': dict(name='Zabójca olbrzymów', english='Giant Killer', description='Reakcja po ataku widocznego przeciwnika Dużego lub większego w odległości do 5 stóp: kontratak bronią, niezależnie od trafienia przeciwnika.'),
}


def state(p):
    if not isinstance(getattr(p, 'martial_state', None), dict): p.martial_state = {}
    return p.martial_state


def path(p):
    key = getattr(p, 'martial_archetype', '')
    if (not isinstance(key, str) or key not in ARCHETYPES
            or ARCHETYPES[key]['class_id'] != getattr(p, 'class_id', '')
            or not getattr(p, 'promoted', False) or p.level < PROMOTION_LEVEL): return ''
    return key


def _level(p):
    try: from . import combat_rules
    except ImportError: import combat_rules
    return combat_rules.effective_level(p)


def maximum(p):
    return 4 + int(_level(p) >= 7) + int(_level(p) >= 15) if path(p) == 'battle_master' else 0


def die_sides(p):
    level = _level(p)
    return 12 if level >= 18 else 10 if level >= 10 else 8


def spent(p):
    value = state(p).get('superiority_spent', 0)
    return max(0, value) if type(value) is int else maximum(p)


def remaining(p): return max(0, maximum(p) - spent(p))


def spend(p):
    if remaining(p) < 1: return False
    state(p)['superiority_spent'] = spent(p) + 1
    return True


def knows(p, key):
    learned = state(p).get('maneuvers', [])
    return path(p) == 'battle_master' and isinstance(key, str) and key in MANEUVERS and isinstance(learned, list) and key in learned


def hunter_choice(p):
    key = state(p).get('hunter_choice', '')
    return key if path(p) == 'hunter' and isinstance(key, str) and key in PREY else ''


def critical_threshold(p):
    return (18 if _level(p) >= 15 else 19) if path(p) == 'champion' and not getattr(p, 'form', '') else 20


def actions_available(p, now=None):
    now = getattr(p, 'current_wall_time', 0) if now is None else now
    disabled = ('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending', 'polymorph')
    return bool(p.alive and not getattr(p, 'disconnected', False) and not getattr(p, 'form', '')
                and not getattr(p, 'rest_state', {}) and not getattr(p, 'casting_channel', {})
                and not any(p.buffs.get(key, {}).get('until', 0) > now for key in disabled))


def selection_reason(p, now=None):
    now = getattr(p, 'current_wall_time', 0) if now is None else now
    if p.class_id not in ('knight', 'ranger'): return 'Ta specjalizacja należy do wojownika lub łowcy.'
    if getattr(p, 'martial_archetype', ''): return 'Specjalizacja została już wybrana na stałe.'
    if p.level < PROMOTION_LEVEL: return f'Wymagany poziom {PROMOTION_LEVEL}.'
    if not p.promoted: return 'Najpierw kup promocję u mistrza profesji.'
    if not actions_available(p, now): return 'Wybierz specjalizację po odrodzeniu, odpoczynku lub zakończeniu przemiany i rzucania czarów.'
    if p.combat_until > now: return 'Wybierz specjalizację poza walką.'
    return ''


def sheet(p):
    if p.class_id not in ('knight', 'ranger'): return {}
    selected = getattr(p, 'martial_archetype', '')
    key = selected if isinstance(selected, str) and selected in ARCHETYPES and ARCHETYPES[selected]['class_id'] == p.class_id else ''
    active = path(p); data = state(p); reason = selection_reason(p)
    learned = data.get('maneuvers', []) if isinstance(data.get('maneuvers', []), list) else []
    icon = lambda id_: f'assets/feats/martial_{id_}.svg'
    return dict(id=key, name=ARCHETYPES.get(key, {}).get('name', ''), active=bool(active),
        eligible=not reason, pending=not reason, selection_reason=reason,
        required_level=PROMOTION_LEVEL, promotion_met=bool(p.promoted), required_promotion=True,
        options=[dict(id=id_, **spec, icon=icon(id_)) for id_, spec in ARCHETYPES.items() if spec['class_id'] == p.class_id],
        prey=hunter_choice(p), prey_options=[dict(id=id_, **spec, icon=icon(id_)) for id_, spec in PREY.items()],
        maneuvers=[dict(id=id_, **spec, learned=id_ in learned, icon=icon(id_)) for id_, spec in MANEUVERS.items()],
        dice=dict(remaining=remaining(p), maximum=maximum(p), sides=die_sides(p)),
        armed_maneuver=data.get('offense', '') if active == 'battle_master' else '',
        reaction=data.get('reaction', '') if active == 'battle_master' else '',
        actions_available=bool(active and actions_available(p)), critical_threshold=critical_threshold(p),
        source='D&D 5e 2014 · początkowe zdolności bojowe',
        scaling='Kości: 4k8 od poziomu 3; 5k8 od 7; 5k10 od 10; 6k10 od 15; 6k12 od 18.' if key == 'battle_master' else '')


def configure(spells, statuses):
    for key, spec in MANEUVERS.items():
        id_ = 'martial_' + key
        spells[id_] = dict(id=id_, name=spec['name'], english=spec['english'], words=spec['name'],
            circle=0, kind='martial_feature', action='toggle', targeting='self', shape='self',
            feature=True, martial_maneuver=key, class_ids=['knight'], min_level=PROMOTION_LEVEL,
            class_levels={'knight': PROMOTION_LEVEL}, class_min_levels={'knight': PROMOTION_LEVEL},
            mana=0, cooldown=0, range=0, pvp=False, description=spec['description'],
            icon=f'assets/feats/martial_{key}.svg', source='D&D 5e 2014 · manewr Mistrza Bitewnego',
            effect='spell', visual=dict(style='buff', theme='steel', colors=['#dfb654', '#fff2b0'], shots=1))
    statuses['frightened'] = dict(name='Przerażenie', icon='!', harmful=True,
        description='Gdy źródło strachu jest widoczne: utrudnione ataki i testy cech. Nie możesz dobrowolnie zbliżać się do źródła strachu.')
