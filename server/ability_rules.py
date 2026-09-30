"""One-time point-buy allocation. Budgets follow SRD 5.2; Bractwo has a custom origin.

Existing class templates remain until their owner explicitly replaces them.
Background ability freedom is Bractwo's custom origin, not a named SRD background.
"""
ABILITIES = {'strength':'Siła','dexterity':'Zręczność','constitution':'Kondycja',
             'intelligence':'Inteligencja','wisdom':'Mądrość','charisma':'Charyzma'}
COSTS = {8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9}
ARRAYS = {'knight':(15,14,13,8,10,12),'ranger':(12,15,13,8,14,10),
          'mage':(8,12,13,15,14,10),'druid':(8,12,14,13,15,10)}


def validate(scores, background):
    if not isinstance(scores,dict) or set(scores)!=set(ABILITIES):
        return 'Wybierz wszystkie sześć cech.'
    if any(type(v) is not int or v not in COSTS for v in scores.values()):
        return 'Początkowa wartość cechy musi wynosić od 8 do 15.'
    if sum(COSTS[v] for v in scores.values())!=27:
        return 'Rozdziel dokładnie 27 punktów według kosztu cech.'
    if not isinstance(background,dict) or any(k not in ABILITIES for k in background):
        return 'Wybierz prawidłowe premie pochodzenia.'
    if any(type(v) is not int or not 0<=v<=2 for v in background.values()):
        return 'Premia pochodzenia wynosi 0, 1 albo 2.'
    if sorted(v for v in background.values() if v) not in ([1,2],[1,1,1]):
        return 'Pochodzenie daje +2 i +1 do różnych cech albo +1 do trzech cech.'
    return ''


def valid_build(p):
    value=getattr(p,'ability_build',{})
    return value if isinstance(value,dict) and not validate(value.get('scores'),value.get('background')) else {}


def base_scores(p):
    build=valid_build(p)
    return {a:build['scores'][a]+build['background'].get(a,0) for a in ABILITIES} if build else dict(p.spec['attributes'])


def sheet(p):
    build=valid_build(p)
    initial=dict(zip(ABILITIES,ARRAYS.get(p.class_id,ARRAYS['knight'])))
    return dict(chosen=bool(build),points=27,costs=COSTS,
                defaults=dict(p.spec['attributes']),scores=base_scores(p),
                initial_scores=initial,initial_background={p.spec['primary']:2,'constitution':1},
                abilities=[dict(id=k,name=v) for k,v in ABILITIES.items()],background_points=3,
                description='Jednorazowy wybór: 27 punktów zakupu cech i 3 punkty pochodzenia. Zastępuje początkowe cechy klasy; wybrane atuty pozostają.')


def choose(p,scores,background):
    if valid_build(p):return 'Cechy początkowe zostały już wybrane.'
    reason=validate(scores,background)
    if reason:return reason
    try: from . import equipment_rules as gear
    except ImportError: import equipment_rules as gear
    bonuses=gear.feat_ability_bonuses(p)
    if any(scores[a]+background.get(a,0)+bonuses.get(a,0)>20 for a in ABILITIES):
        return 'Ten przydział wraz z posiadanymi atutami przekracza limit cechy 20.'
    p.ability_build={'scores':dict(scores),'background':{k:v for k,v in background.items() if v}}
    return ''
