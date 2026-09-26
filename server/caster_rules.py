"""Wizard/druid feature catalogue. Times and Mystic's +1 are Bractwo rules.

No rest counters, no duplicate training feats, no automatic medium-armor gift.
Ritual tags are explicit: e.g. Longstrider is NOT made free by this subsystem.
"""
from math import ceil
from functools import lru_cache

VERSION=1
ARCANE_COOLDOWN=180
SHAPE_COOLDOWN=60
ORDERS={
    'warden':dict(name='Strażnik',description='Średnie pancerze i broń żołnierska.',icon='assets/feats/warden.svg'),
    'magician':dict(name='Mistyk natury',description='+1 do ataku czarami druida i ST ich obrony.',icon='assets/feats/magician.svg'),
}
FORMS={
    'wolf':dict(name='Wilk',level=5,ac=12,attributes={'strength':14,'dexterity':15,'constitution':12},
        attacks=[[1,6,2]],damage='piercing',attack_bonus=4,speed=40,cr='1/4',trait='Taktyka watahy · przewraca mniejsze cele',size='medium'),
    'cat':dict(name='Kot',level=5,ac=12,attributes={'strength':3,'dexterity':15,'constitution':10},
        attacks=[[0,1,1]],damage='slashing',attack_bonus=4,speed=40,cr='0',trait='Szybka, niewielka postać zwiadowcza',size='tiny'),
    'black_bear':dict(name='Niedźwiedź czarny',level=15,ac=11,attributes={'strength':15,'dexterity':12,'constitution':14},
        attacks=[[1,6,2],[1,6,2]],attack_types=['slashing','slashing'],damage='slashing',attack_bonus=4,speed=30,cr='1/2',trait='Dwa uderzenia pazurami',size='medium'),
    'bear':dict(name='Niedźwiedź brunatny',level=35,ac=11,attributes={'strength':17,'dexterity':12,'constitution':15},
        attacks=[[1,8,3],[1,4,3]],attack_types=['piercing','slashing'],damage='piercing',attack_bonus=5,speed=40,cr='1',trait='Ugryzienie i pazury · 2 ataki',size='large'),
}

def effective_level(p):return min(20,max(1,1+int(p.level)//5))
@lru_cache(maxsize=20)
def _slot_recovery_amount(class_level):
    # Original recoverable-slot value supplies the unchanged milestone totals.
    # Ranks VI+ remain excluded, and no per-rank slot counters are introduced.
    try: from . import dnd_content as dnd
    except ImportError: import dnd_content as dnd
    cap=ceil(class_level/2);best=[0]*(cap+1)
    for rank,count in enumerate(dnd.FULL_CASTER_SLOTS[class_level-1][:5],1):
        for _ in range(count):
            for budget in range(cap,rank-1,-1):best[budget]=max(best[budget],best[budget-rank]+dnd.MANA_COSTS[rank])
    return max(best)


@lru_cache(maxsize=1)
def _recovery_checkpoints():
    try: from . import dnd_content as dnd
    except ImportError: import dnd_content as dnd
    return tuple((level, _slot_recovery_amount(min(20, 1+level//5)))
                 for level in dnd.MANA_GROWTH_LEVELS)


def recovery_amount(p):
    try: from . import dnd_content as dnd
    except ImportError: import dnd_content as dnd
    if getattr(p, 'mana_rules_version', dnd.MANA_RULES_VERSION) < dnd.MANA_RULES_VERSION:
        return _slot_recovery_amount(effective_level(p))
    return dnd.interpolate_growth(p.level, _recovery_checkpoints())
def form_duration(p):return effective_level(p)*900.0  # half-level hours, 6s -> 3s rounds

def form_spec(p):return FORMS.get(getattr(p,'form',''),{})
def spell_path_bonus(p):return int(p.class_id=='druid' and getattr(p,'primal_order','')=='magician')


def configure(spells,classes,statuses):
    def add(key,name,kind,classes_,level=1,**extra):
        s=dict(id=key,name=name,english=name,words=name,circle=0,class_ids=classes_,class_levels={c:level for c in classes_},
            class_min_levels={c:level for c in classes_},min_level=level,kind=kind,action='action',mana=0,cooldown=0,
            range=128,radius=0,shape='self',targeting='self',feature=True,source='SRD 5.2.1 · adaptacja Bractwa',
            description='',icon=f'assets/spells/{key}.svg',effect='spell',visual=dict(style=kind,theme='nature' if 'druid' in classes_ else 'force',colors=['#438c86','#b8e5cf','#eaffee'],shots=1))
        s.update(extra);spells[key]=s
    classes['mage']['description']='Sztuczki, I krąg, rytuały i Odzyskanie mocy od początku.'
    classes['druid']['description']='Strażnik lub Mistyk natury. Lekki pancerz, tarcze i przemiany od poziomu 5.'
    add('arcane_recovery','Odzyskanie mocy','recovery',['mage'],action='bonus',cooldown=ARCANE_COOLDOWN,
        description='Natychmiast odzyskujesz część many, także w walce i w ruchu. Akcja dodatkowa. Odnowienie 180 s.',
        visual=dict(style='recovery',theme='force',colors=['#546bb2','#aacfff','#eef7ff'],shots=1))
    add('alarm','Alarm','ritual_alarm',['mage'],circle=1,mana=20,feature=False,ritual=True,ritual_seconds=10,
        channel_seconds=3,duration=14400,description='Zabezpiecza obszar wokół miejsca rzucenia. Ostrzega o wejściu potwora lub obcego gracza. Rytuał: 10 s, bez many.',radius=64,shape='square')
    add('find_familiar','Przywołanie chowańca','familiar',['mage'],circle=1,mana=20,gold=10,feature=False,
        ritual=True,ritual_seconds=40,channel_seconds=30,
        description='Przywołuje sowę. Nie atakuje: pomaga i rozpoznaje pobliskie zagrożenia. Rzucanie 30 s; rytuał 40 s bez many. Składnik: 10 złota.')
    add('speak_with_animals','Rozmowa ze zwierzętami','animal_speech',['druid'],circle=1,mana=20,feature=False,
        ritual=True,ritual_seconds=10,channel_seconds=3,duration=300,
        description='Przez 100 rund rozumiesz spokojne zwierzęta. Podejdź do zwierzęcia i użyj E. Nie uspokaja atakujących potworów. Rytuał: 10 s bez many.')
    add('wild_companion','Dziki towarzysz','wild_familiar',['druid'],5,cooldown=SHAPE_COOLDOWN,
        description='Przywołuje leśną sowę bez many i składników. Nie atakuje. Wspólne odnowienie z przemianami: 60 s.')
    for form,f in FORMS.items():
        key='wild_shape_'+form
        add(key,'Dziki kształt · '+f['name'].lower(),'shape',['druid'],f['level'],action='bonus',form=form,
            cooldown=SHAPE_COOLDOWN,description=f['trait']+'. Nie rzucasz czarów; zachowujesz koncentrację. Wspólne odnowienie przemian: 60 s.',duration=1800)
    statuses.update(
        ritual_channel=dict(name='Rytuał',icon='◈',description='Nie ruszaj się do końca rzucania.',harmful=False),
        speak_with_animals=dict(name='Rozmowa ze zwierzętami',icon='♧',description='Podejdź do spokojnego zwierzęcia i użyj E.',harmful=False),
        familiar_help=dict(name='Pomoc chowańca',icon='◉',description='Następny atak przeciw wskazanemu celowi ma ułatwienie.',harmful=False),
        ritual_alarm=dict(name='Alarm',icon='♢',description='Obszar jest zabezpieczony. Otrzymasz ostrzeżenie o wejściu obcego stworzenia.',harmful=False),
    )


def feature_rows(p):
    result=[]
    def feature(key,name,description,level=1):
        if p.level>=level:result.append(dict(id=key,name=name,description=description,icon=f'assets/spells/{key}.svg',level=level,automatic=True))
    if p.class_id=='mage':
        feature('arcane_recovery','Odzyskanie mocy',f'+{recovery_amount(p)} many · natychmiast · akcja dodatkowa · odnowienie 180 s')
        feature('alarm','Rytuały','Alarm i Przywołanie chowańca. Rytuały nie zużywają many.')
    if p.class_id=='druid':
        feature('speak_with_animals','Druidyczny','Odczytujesz znaki druidów; znasz Rozmowę ze zwierzętami.')
        feature('wild_shape_wolf','Dziki kształt','Przemiany · wspólne odnowienie 60 s',5)
        feature('wild_companion','Dziki towarzysz','Leśny chowaniec; nie wykonuje ataków.',5)
    return result


def sheet(p):
    return dict(order=getattr(p,'primal_order',''),order_pending=p.class_id=='druid' and not getattr(p,'primal_order',''),
        orders=[dict(id=k,**v) for k,v in ORDERS.items()] if p.class_id=='druid' else [],
        features=feature_rows(p),forms=[dict(id=k,**v,unlocked=p.level>=v['level'],temp_hp=effective_level(p)) for k,v in FORMS.items()] if p.class_id=='druid' else [],
        familiar=getattr(p,'familiar_state',{}),channel=({k:v for k,v in getattr(p,'casting_channel',{}).items() if k in ('key','name','total','ritual')}|dict(remaining=round(max(0,getattr(p,'casting_channel',{}).get('until',0)-p.current_wall_time),1))) if getattr(p,'casting_channel',{}) else {},legacy_medium_grace=bool(getattr(p,'legacy_medium_grace',False)),recovery_amount=recovery_amount(p) if p.class_id=='mage' else 0)
