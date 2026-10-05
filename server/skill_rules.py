"""D&D 2024 skills with character levels using the D&D numbering.

The eighteen skills, class picks, proficiency and Expertise follow the 2024
rules. Choosing any two background skills is Bractwo's custom-origin adapter;
there are no skill ranks or skill points awarded at every character level.
Only selection identifiers are saved. Bonuses and available choices are always
recomputed from authoritative class, level, ability scores and purchased feats.
"""

VERSION = 1
ABILITY_NAMES = {
    'strength': 'Siła', 'dexterity': 'Zręczność', 'constitution': 'Kondycja',
    'intelligence': 'Inteligencja', 'wisdom': 'Mądrość', 'charisma': 'Charyzma',
}

# Concise original Polish descriptions, not reproduced rules text.
SKILLS = {
    'acrobatics': dict(name='Akrobatyka', ability='dexterity', description='Utrzymanie równowagi i pokonywanie niebezpiecznych przejść.'),
    'animal_handling': dict(name='Opieka nad zwierzętami', ability='wisdom', description='Uspokajanie zwierząt i odczytywanie ich zachowania.'),
    'arcana': dict(name='Wiedza tajemna', ability='intelligence', description='Rozpoznawanie magii, run i nadnaturalnych istot.'),
    'athletics': dict(name='Atletyka', ability='strength', description='Siłowe pokonywanie przeszkód, wspinaczka i uwalnianie się z chwytów.'),
    'deception': dict(name='Oszustwo', ability='charisma', description='Wiarygodne blefowanie i wprowadzanie rozmówcy w błąd.'),
    'history': dict(name='Historia', ability='intelligence', description='Odczytywanie dawnych przekazów i rozpoznawanie historycznych śladów.'),
    'insight': dict(name='Intuicja', ability='wisdom', description='Rozpoznawanie intencji, kłamstw i podejrzanego zachowania.'),
    'intimidation': dict(name='Zastraszanie', ability='charisma', description='Wywieranie presji na rozmówców za pomocą groźby.'),
    'investigation': dict(name='Śledztwo', ability='intelligence', description='Łączenie wskazówek i badanie mechanizmów lub ukrytych schowków.'),
    'medicine': dict(name='Medycyna', ability='wisdom', description='Rozpoznawanie dolegliwości i udzielanie pomocy rannym.'),
    'nature': dict(name='Przyroda', ability='intelligence', description='Rozpoznawanie roślin, zwierząt i zjawisk naturalnych.'),
    'perception': dict(name='Percepcja', ability='wisdom', description='Dostrzeganie ukrytych zagrożeń, szczegółów i śladów.'),
    'performance': dict(name='Występy', ability='charisma', description='Przyciąganie uwagi publiczności muzyką, opowieścią lub pokazem.'),
    'persuasion': dict(name='Perswazja', ability='charisma', description='Przekonywanie rozmówców argumentami i negocjowanie porozumienia.'),
    'religion': dict(name='Religia', ability='intelligence', description='Rozpoznawanie kultów, świętych znaków i natury nieumarłych.'),
    'sleight_of_hand': dict(name='Zwinne dłonie', ability='dexterity', description='Precyzyjne manipulowanie drobnymi przedmiotami i mechanizmami.'),
    'stealth': dict(name='Skradanie', ability='dexterity', description='Ukrywanie się i omijanie czujnych przeciwników.'),
    'survival': dict(name='Przetrwanie', ability='wisdom', description='Tropienie, orientacja w terenie i odnajdywanie zasobów.'),
}
CLASS_SKILLS = {
    'knight': ('acrobatics', 'animal_handling', 'athletics', 'history', 'insight', 'intimidation', 'persuasion', 'perception', 'survival'),
    'ranger': ('animal_handling', 'athletics', 'insight', 'investigation', 'nature', 'perception', 'stealth', 'survival'),
    'mage': ('arcana', 'history', 'insight', 'investigation', 'medicine', 'nature', 'religion'),
    'druid': ('arcana', 'animal_handling', 'insight', 'medicine', 'nature', 'perception', 'religion', 'survival'),
}
CLASS_PICKS = {'knight': 2, 'ranger': 3, 'mage': 2, 'druid': 2}
SCHOLAR_SKILLS = ('arcana', 'history', 'investigation', 'medicine', 'nature', 'religion')
SOURCES = ('class', 'background', 'skilled', 'expertise')
SOURCE_NAMES = {'class': 'Klasa', 'background': 'Pochodzenie', 'skilled': 'Atut: Wszechstronny', 'expertise': 'Ekspertyza'}


def _rules():
    try:
        from . import combat_rules
    except ImportError:
        import combat_rules
    return combat_rules


def _gear():
    try:
        from . import equipment_rules
    except ImportError:
        import equipment_rules
    return equipment_rules


def limits(p):
    """Limits are grants, never client-supplied counters."""
    class_id = getattr(p, 'class_id', '')
    level = _rules().effective_level(p)
    gear = _gear()
    # active_feats includes every legal instance of the repeatable Skilled feat.
    skilled = min(18, 3 * sum(gear.feat_key(key) == 'skilled' for key in gear.active_feats(p)))
    expertise = (1 + 2 * (level >= 9)) if class_id == 'ranger' and level >= 2 else int(class_id == 'mage' and level >= 2)
    return dict(class_=CLASS_PICKS.get(class_id, 0), background=2 if class_id in CLASS_PICKS else 0,
                skilled=skilled, expertise=expertise)


def _limit(grants, source):
    return grants['class_' if source == 'class' else source]


def can_add_skilled(p):
    """Only offer an additional feat when all three granted skills can be used.

    Bractwo currently implements the skill branch of Skilled, not tool training.
    Reserve the complete class/background budgets even when their picks remain
    unspent, so choosing feats first cannot leave unusable class choices.
    """
    grants = limits(p)
    return grants['class_'] > 0 and grants['class_'] + grants['background'] + grants['skilled'] + 3 <= len(SKILLS)


def _leaves_class_choices(p, skill_id, known, selected, grants):
    remaining = grants['class_'] - len(selected['class'])
    available = set(CLASS_SKILLS.get(getattr(p, 'class_id', ''), ())) - known - {skill_id}
    return len(available) >= remaining


def state(p):
    """Return a bounded, valid snapshot without mutating a sheet reader's player.

    Arbitrary legacy `skill_proficiencies` is deliberately not imported: previous
    versions never provided a player choice or validated source for that field.
    """
    raw = getattr(p, 'skill_training', {})
    if not isinstance(raw, dict):
        raw = {}
    grants = limits(p)
    result = {source: [] for source in SOURCES}
    proficient = set()
    for source in ('class', 'background', 'skilled'):
        values = raw.get(source, [])
        if not isinstance(values, list):
            continue
        allowed = CLASS_SKILLS.get(getattr(p, 'class_id', ''), ()) if source == 'class' else SKILLS
        for value in values[:64]:
            if len(result[source]) >= _limit(grants, source):
                break
            if (isinstance(value, str) and value in allowed and value not in proficient
                    and (source == 'class' or _leaves_class_choices(p, value, proficient, result, grants))):
                result[source].append(value)
                proficient.add(value)
    expertise = raw.get('expertise', [])
    if isinstance(expertise, list):
        for value in expertise[:64]:
            if len(result['expertise']) >= grants['expertise']:
                break
            if (isinstance(value, str) and value in proficient and value not in result['expertise']
                    and (getattr(p, 'class_id', '') != 'mage' or value in SCHOLAR_SKILLS)):
                result['expertise'].append(value)
    return result


def normalize(p):
    p.skill_training = state(p)
    return p.skill_training


def proficient_skills(p):
    selected = state(p)
    return set(selected['class'] + selected['background'] + selected['skilled'])


def expertise_skills(p):
    return set(state(p)['expertise'])


def bonus(p, skill_id, ability=None):
    """Stable skill bonus; the caller applies conditions, Guidance and roll dice.

    Ability overrides support real contextual checks, e.g. Strength (Acrobatics)
    or Wisdom (Religion), without giving a different skill proficiency.
    """
    if not isinstance(skill_id, str) or skill_id not in SKILLS:
        raise ValueError('Unknown skill')
    chosen_ability = SKILLS[skill_id]['ability'] if ability is None else ability
    if not isinstance(chosen_ability, str) or chosen_ability not in ABILITY_NAMES:
        raise ValueError('Unknown ability')
    selected = state(p)
    trained = skill_id in selected['class'] + selected['background'] + selected['skilled']
    multiplier = 2 if skill_id in selected['expertise'] else int(trained)
    rules = _rules()
    return rules.ability_modifier(p, chosen_ability) + multiplier * rules.proficiency(p) + rules.gear.feat_rules.skill_bonus(p,skill_id)


def _options(p, source, selected, grants):
    if len(selected[source]) >= _limit(grants, source):
        return []
    known = set(selected['class'] + selected['background'] + selected['skilled'])
    if source == 'expertise':
        allowed = SCHOLAR_SKILLS if getattr(p, 'class_id', '') == 'mage' else SKILLS
        return [key for key in allowed if key in known and key not in selected['expertise']]
    allowed = CLASS_SKILLS.get(getattr(p, 'class_id', ''), ()) if source == 'class' else SKILLS
    return [key for key in allowed if key not in known
            and (source == 'class' or _leaves_class_choices(p, key, known, selected, grants))]


def choose(p, source, skill_id):
    """Commit one legal pick; None means success, otherwise a Polish error.

    Session/action/combat checks and persistence belong to the game command
    handler. This function has no I/O and never accepts a bonus or pick budget.
    """
    if not isinstance(source, str) or source not in SOURCES:
        return 'Nieprawidłowe źródło szkolenia.'
    if not isinstance(skill_id, str) or skill_id not in SKILLS:
        return 'Nieprawidłowa umiejętność.'
    if getattr(p, 'class_id', '') not in CLASS_SKILLS or not getattr(p, 'class_chosen', True):
        return 'Najpierw wybierz klasę postaci.'
    selected, grants = state(p), limits(p)
    if len(selected[source]) >= _limit(grants, source):
        return 'Nie masz dostępnego wyboru z tego źródła.'
    if skill_id not in _options(p, source, selected, grants):
        return 'Ta umiejętność nie jest dostępna w tym wyborze.'
    selected[source].append(skill_id)
    p.skill_training = selected
    return None


def sheet(p):
    """Only attach this payload to the owning player's character sheet."""
    rules = _rules()
    selected, grants = state(p), limits(p)
    known = set(selected['class'] + selected['background'] + selected['skilled'])
    expert = set(selected['expertise'])
    ability_modifiers = {key: (score - 10) // 2 for key, score in rules.attributes(p).items()}
    proficiency = rules.proficiency(p)
    rows = []
    for key, spec in SKILLS.items():
        value = ability_modifiers[spec['ability']] + proficiency * (2 if key in expert else int(key in known)) + rules.gear.feat_rules.skill_bonus(p,key)
        rows.append(dict(id=key, **spec, ability_name=ABILITY_NAMES[spec['ability']],
                         bonus=value, passive=10 + value, proficient=key in known, expertise=key in expert,
                         sources=[SOURCE_NAMES[source] for source in SOURCES if key in selected[source]]))
    descriptions = {
        'class': 'Wybierz biegłości z listy swojej klasy. Każda dodaje premię z biegłości do testu.',
        'background': 'Wybierz dwie biegłości wynikające z pochodzenia. W Bractwie samodzielnie dobierasz tę parę.',
        'skilled': 'Każde wybranie atutu Wszechstronny daje trzy nowe biegłości w umiejętnościach.',
        'expertise': ('Uczony: od poziomu 2 wybierz jedną ze swoich biegłości naukowych. Ekspertyza podwaja premię z biegłości.'
                      if p.class_id == 'mage' else
                      'Od poziomu 2 wybierz jedną ekspertyzę, a od 9 dwie kolejne. Ekspertyza podwaja premię z biegłości.'),
    }
    choices = []
    row_by_id = {row['id']: row for row in rows}
    for source in ('class', 'background', 'expertise', 'skilled'):
        if source == 'skilled' and not grants['skilled']:
            continue
        if source == 'expertise' and p.class_id not in ('ranger', 'mage'):
            continue
        options = _options(p, source, selected, grants)
        choices.append(dict(source=source, name=SOURCE_NAMES[source], description=descriptions[source],
                            total=_limit(grants, source), remaining=max(0, _limit(grants, source) - len(selected[source])),
                            selected=list(selected[source]), options=[dict(id=key, name=SKILLS[key]['name'],
                                ability=SKILLS[key]['ability'], ability_name=ABILITY_NAMES[SKILLS[key]['ability']],
                                bonus=row_by_id[key]['bonus']) for key in options]))
    return dict(version=VERSION, effective_level=rules.effective_level(p), proficiency_bonus=proficiency,
                description='Test: 1k20 + modyfikator cechy + biegłość, jeśli ją znasz. Ekspertyza: podwójna biegłość. Nie otrzymujesz rang za każdy poziom.',
                skills=rows, choices=choices)
