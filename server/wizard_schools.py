"""Wizard school catalogue and owner-only state, with explicit Bractwo adaptations.

School milestones follow the same 3/6/10/14 progression as druid circles.
Unsupported narrative tabletop abilities are adapted to real combat features.
"""
try:
    from .profession_rules import PROMOTION_LEVEL
except ImportError:
    from profession_rules import PROMOTION_LEVEL

SCHOOLS = {
    'evocation': dict(name='Ewokacja', description='Niezawodne sztuczki, kontrolowane wybuchy i maksymalna moc czarów.'),
    'abjuration': dict(name='Odpychanie', description='Osobna magiczna osłona, ochrona drużyny i odporność na czary.'),
    'divination': dict(name='Wróżbiarstwo', description='Przepowiednie k20 zastępujące przyszłe rzuty oraz Trzecie oko.'),
    'illusion': dict(name='Iluzja', description='Sobowtóry, widmowy towarzysz i materialna osłona drużyny.'),
}
FEATURES = {
    'evocation': (
        ('potent_cantrip', 3, 'Potężne sztuczki', 'Zadają połowę obrażeń po pudle lub udanej obronie celu. Bez dodatkowych skutków pudła; Iskra różdżki nie jest sztuczką.'),
        ('sculpt_spells', 6, 'Rzeźbienie czarów', 'Obszarowe ewokacje z rzutem obronnym oszczędzają do 1 + krąg czaru niezaznaczonych graczy. Zaznaczony przeciwnik PvP pozostaje celem.'),
        ('empowered_evocation', 10, 'Wzmocniona ewokacja', 'Dodajesz modyfikator Inteligencji do jednego rzutu obrażeń ewokacji podczas rzucenia czaru.'),
        ('overchannel', 14, 'Przeciążenie', 'Przygotuj maksymalne kości następnego czaru z obrażeniami I–V kręgu. Pierwsze użycie na długi odpoczynek jest bezpieczne; kolejne zadają tobie 2k12 za krąg, następnie o 1k12 więcej za krąg. Tych obrażeń nie można pochłonąć.'),
    ),
    'abjuration': (
        ('arcane_ward', 3, 'Magiczna osłona', 'Płatny czar odpychania tworzy osłonę: 2 × efektywny poziom + Inteligencja. Kolejne odnawiają 2 HP osłony za krąg. Osłona pochłania obrażenia przed koncentracją i tymczasowymi HP; doładowanie: akcja dodatkowa, 20 many za 2 HP.'),
        ('projected_ward', 6, 'Projekcja osłony', 'Przygotuj ochronę wskazanego członka drużyny w 30 stopach. Reakcja zużywa twoją osłonę, pochłaniając jego obrażenia.'),
        ('ward_recovery', 10, 'Odbudowa osłony', 'Krótki odpoczynek w pełni odnawia utworzoną magiczną osłonę.'),
        ('spell_resistance', 14, 'Odporność na czary', 'Ułatwienie rzutów obronnych przeciw czarom i połowa otrzymywanych obrażeń czarów. Nie obejmuje zwykłych ataków ani każdego źródła ognia.'),
    ),
    'divination': (
        ('portent', 3, 'Przepowiednia', 'Po wyborze szkoły i długim odpoczynku otrzymujesz dwa wyniki k20. Przygotuj wybrany wynik przed własnym atakiem, własną obroną lub obroną celu twojego czaru. Najwyżej jedna przepowiednia na turę.'),
        ('efficient_portent', 6, 'Oszczędność wróżb', 'Zużycie przepowiedni przywraca 20 many, do jej maksymalnego poziomu.'),
        ('third_eye', 10, 'Trzecie oko', 'Akcja dodatkowa: przez 30 sekund widzisz przez magiczne zaciemnienie i Rozmycie. Nie widzisz przez ściany. Jedno użycie na krótki lub długi odpoczynek.'),
        ('greater_portent', 14, 'Wielka przepowiednia', 'Długi odpoczynek przygotowuje trzy wyniki k20 zamiast dwóch.'),
    ),
    'illusion': (
        ('improved_illusion', 3, 'Iluzoryczny sobowtór', 'Akcja dodatkowa: przez maksymalnie 30 sekund sobowtór utrudnia następny wymierzony w ciebie atak. Dwa użycia na długi odpoczynek.'),
        ('phantasmal_creature', 6, 'Widmowy towarzysz', 'Przywołaj walczącego widmowego wilka. Pierwsze przywołanie na długi odpoczynek jest darmowe i ma połowę HP; kolejne kosztują 30 many. Najwyżej jeden aktywny towarzysz.'),
        ('illusory_self', 10, 'Iluzoryczne ja', 'Przygotowana reakcja zamienia następne trafienie atakiem w pudło. Jedno użycie na krótki odpoczynek; zużyte użycie można przywrócić akcją dodatkową za 30 many.'),
        ('illusory_shelter', 14, 'Urzeczywistniona osłona', 'Akcja: nieruchoma osłona na 30 sekund w promieniu 15 stóp. Ty i członkowie drużyny wewnątrz otrzymujecie +2 KP i +2 do obrony Zręczności. Jedno użycie na długi odpoczynek; premia nie sumuje się z Sanktuarium natury.'),
    ),
}
SPELL_FEATURES = {
    'wizard_ward_recharge': ('abjuration', 3, 'Doładuj magiczną osłonę', 'bonus', 20),
    'wizard_third_eye': ('divination', 10, 'Trzecie oko', 'bonus', 0),
    'wizard_decoy': ('illusion', 3, 'Iluzoryczny sobowtór', 'bonus', 0),
    'wizard_phantasm': ('illusion', 6, 'Widmowy towarzysz', 'action', 30),
    'wizard_self_restore': ('illusion', 10, 'Przywróć Iluzoryczne ja', 'bonus', 30),
    'wizard_shelter': ('illusion', 14, 'Urzeczywistniona osłona', 'action', 0),
}


def school(p):
    key = getattr(p, 'wizard_school', '')
    return key if isinstance(key, str) and key in SCHOOLS and getattr(p, 'class_id', '') == 'mage' and getattr(p, 'promoted', False) and p.level >= PROMOTION_LEVEL else ''


def is_school(p, key): return school(p) == key


def state(p):
    if not isinstance(getattr(p, 'wizard_school_state', None), dict): p.wizard_school_state = {}
    return p.wizard_school_state


def runtime(p):
    if not isinstance(getattr(p, 'wizard_school_runtime', None), dict): p.wizard_school_runtime = {}
    return p.wizard_school_runtime


def feature_allowed(p, key):
    spec = SPELL_FEATURES.get(key)
    return bool(spec and school(p) == spec[0] and p.level >= spec[1])


def ward_max(p):
    if not is_school(p, 'abjuration'): return 0
    try: from . import combat_rules as rules
    except ImportError: import combat_rules as rules
    return max(0, 2 * rules.effective_level(p) + rules.ability_modifier(p, 'intelligence'))


def portent_max(p): return 3 if p.level >= 14 else 2


def public_visual(p, now):
    """Public presentation only; rolls, resources and prepared choices stay private."""
    if not school(p) or not p.alive: return {}
    data=state(p); live=runtime(p); shelter=live.get('shelter',{})
    return dict(ward_hp=max(0,data.get('ward_hp',0)), ward_max=ward_max(p),
        decoy=live.get('decoy_until',0)>now, decoy_remaining=max(0,live.get('decoy_until',0)-now),
        third_eye=live.get('third_eye_until',0)>now,
        shelter=dict(x=shelter['x'],y=shelter['y'],floor=shelter['floor'],radius=96,remaining=shelter['until']-now)
        if shelter and shelter.get('until',0)>now else None)


def configure(spells, statuses):
    for key, (owner, level, name, action, mana) in SPELL_FEATURES.items():
        feature_id = {'wizard_ward_recharge': 'arcane_ward', 'wizard_third_eye': 'third_eye', 'wizard_decoy': 'improved_illusion', 'wizard_phantasm': 'phantasmal_creature', 'wizard_self_restore': 'illusory_self', 'wizard_shelter': 'illusory_shelter'}[key]
        description = next(f[3] for f in FEATURES[owner] if f[0] == feature_id)
        if key=='wizard_ward_recharge':description='Akcja dodatkowa: przywróć 2 HP już utworzonej magicznej osłony za 20 many. Najpierw utwórz ją płatnym czarem odpychania, np. Pancerzem maga.'
        if key=='wizard_self_restore':description='Akcja dodatkowa: przywróć zużyte użycie Iluzorycznego ja za 30 many. Samo przywrócenie nie zużywa reakcji.'
        spells[key] = dict(id=key, name=name, english=name, words=name, circle=0, kind='wizard_feature', action=action,
            class_ids=['mage'], wizard_school=owner, class_levels={'mage': level}, class_min_levels={'mage': level}, min_level=level,
            mana=mana, cooldown=0, range=192, radius=96 if key == 'wizard_shelter' else 0,
            shape='self', targeting='self', feature=True, description=description,
            icon=f'assets/spells/{key}.svg', effect='spell', source='Szkoły czarodzieja · zasady Bractwa',
            visual=dict(style='buff', theme='force', colors=['#6c65b6', '#bda7ff', '#eff0ff'], shots=1))
    for key, name, icon in [('wizard_decoy', 'Iluzoryczny sobowtór', '◈'), ('wizard_third_eye', 'Trzecie oko', '◉'), ('wizard_shelter', 'Urzeczywistniona osłona', '◇')]:
        statuses[key] = dict(name=name, icon=icon, description='', harmful=False)


def sheet(p):
    if p.class_id != 'mage': return {}
    selected = getattr(p, 'wizard_school', '')
    key = selected if isinstance(selected, str) and selected in SCHOOLS else ''
    active = school(p); data = state(p); live = runtime(p)
    now = getattr(p, 'current_wall_time', 0)
    eligible = bool(p.level >= PROMOTION_LEVEL and p.promoted and not key)
    def rows(owner):
        return [dict(id=id_, level=level, name=name, description=description,
                     unlocked=bool(active == owner and p.level >= level)) for id_, level, name, description in FEATURES[owner]]
    options = [dict(id=id_, **spec, icon=f'assets/feats/wizard_{id_}.svg', features=rows(id_)) for id_, spec in SCHOOLS.items()]
    available = bool(p.alive and not p.form and not getattr(p, 'disconnected', False))
    resources = []; actions = []
    for id_, (owner, level, name, action, mana) in SPELL_FEATURES.items():
        if active == owner and p.level >= level:
            actions.append(dict(id=id_, spell_id=id_, name=name, kind='spell', enabled=available))
    if active == 'evocation' and p.level >= 14:
        actions.append(dict(id='overchannel', name='Przeciążenie', kind='toggle', enabled=available, value=bool(data.get('overchannel_armed'))))
        resources.append(dict(id='overchannel', name='Bezpieczne przeciążenie', maximum=1, remaining=int(not data.get('overchannel_used', 0))))
    if active == 'abjuration' and p.level >= 6:
        actions.append(dict(id='projected_ward', name='Projekcja osłony', kind='target', enabled=available, target_id=live.get('projected_ward_target', '')))
    portents = [dict(index=i, value=value, spent=value is None) for i, value in enumerate(data.get('portents', []))] if active == 'divination' else []
    if active == 'divination':
        resources.append(dict(id='portents', name='Przepowiednie', maximum=portent_max(p), remaining=sum(not x['spent'] for x in portents)))
        if p.level >= 10: resources.append(dict(id='third_eye', name='Trzecie oko', maximum=1, remaining=max(0, 1-data.get('third_eye_used', 0))))
    if active == 'illusion':
        resources.append(dict(id='decoy', name='Sobowtór', maximum=2, remaining=max(0, 2-data.get('decoy_spent', 0))))
        if p.level >= 6: resources.append(dict(id='phantasm', name='Darmowy widmowy towarzysz', maximum=1, remaining=max(0, 1-data.get('phantasm_spent', 0))))
        if p.level >= 10:
            resources.append(dict(id='illusory_self', name='Iluzoryczne ja', maximum=1, remaining=max(0, 1-data.get('self_spent', 0))))
            actions.append(dict(id='illusory_self', name='Iluzoryczne ja', kind='toggle', enabled=available, value=bool(data.get('self_armed'))))
        if p.level >= 14: resources.append(dict(id='shelter', name='Urzeczywistniona osłona', maximum=1, remaining=max(0, 1-data.get('shelter_spent', 0))))
    return dict(id=key, name=SCHOOLS.get(key, {}).get('name', ''), active=bool(active), eligible=eligible, pending=eligible,
        required_level=PROMOTION_LEVEL, required_promotion=True, promotion_met=bool(p.promoted),
        options=options, features=rows(key) if key else [], actions=actions, resources=resources,
        portents=portents, armed_portent=data.get('portent_armed'),
        ward=dict(hp=max(0, data.get('ward_hp', 0)), maximum=ward_max(p), created=bool(data.get('ward_created'))),
        projected_ward_target=live.get('projected_ward_target', ''),
        overchannel_armed=bool(data.get('overchannel_armed')), overchannel_used=data.get('overchannel_used', 0),
        illusory_self_armed=bool(data.get('self_armed')), third_eye_remaining=max(0, live.get('third_eye_until', 0)-now))
