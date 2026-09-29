"""5E/SRD-based combat content; Bractwo's mana, timing and level gates are homebrew.
See docs/RULES_0.8.md and LICENSE-SRD.txt. Descriptions are original Polish summaries.
"""
CLASS_SPECS = {
    'knight': dict(name='Rycerz', description='Wojownik: miecz, wytrzymałość i dodatkowe ataki.', weapon='sword', hp=12, hp_growth=1.6, mana=30, mana_growth=1,
                   damage=7.5, armor=0, hit_die=10, ability_name='Drugi oddech', ability_cost=5, ability_cooldown=30,
                   attributes=dict(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10), primary='strength', saves=['strength','constitution'], default_ability='second_wind'),
    'ranger': dict(name='Łowca', description='Łuk i I krąg od początku. Darmowy Znak łowcy; wilczy towarzysz od poziomu 10.', weapon='bow', hp=12, hp_growth=1.6, mana=40, mana_growth=0,
                   damage=7.5, armor=0, hit_die=10, ability_name='Znak łowcy', ability_cost=0, ability_cooldown=30,
                   attributes=dict(strength=12, dexterity=16, constitution=14, intelligence=10, wisdom=14, charisma=10), primary='dexterity', saves=['strength','dexterity'], default_ability='hunters_mark'),
    'mage': dict(name='Czarodziej', description='Różdżka: iskra 1k4. Darmowe sztuczki i I krąg od 1. poziomu.', weapon='staff', hp=8, hp_growth=1.2, mana=40, mana_growth=0,
                   damage=2.5, armor=0, hit_die=6, ability_name='Promień mrozu', ability_cost=0, ability_cooldown=0,
                   attributes=dict(strength=8, dexterity=14, constitution=14, intelligence=16, wisdom=12, charisma=10), primary='intelligence', saves=['intelligence','wisdom'], default_ability='ray_of_frost'),
    'druid': dict(name='Druid', description='Laska wręcz, I krąg magii natury od 1. poziomu; przemiana od 5.', weapon='staff', hp=10, hp_growth=1.4, mana=40, mana_growth=0,
                   damage=5.5, armor=0, hit_die=8, ability_name='Shillelagh', ability_cost=0, ability_cooldown=0,
                   attributes=dict(strength=14, dexterity=12, constitution=14, intelligence=10, wisdom=16, charisma=10), primary='wisdom', saves=['intelligence','wisdom'], default_ability='shillelagh'),
}

# Circle I at creation, then a new circle at each ten-level milestone.
FULL_CASTER_CIRCLE_LEVELS = (1, 10, 20, 30, 40, 50, 60, 70, 80)
RANGER_CIRCLE_LEVELS = (1, 20, 40, 60, 80)

# Mana is a shared weighted budget, not separate tabletop slot counters.
# Each row is the full-caster slot distribution from SRD 5.2.1.
MANA_COSTS = (0, 20, 30, 50, 60, 70, 90, 100, 110, 130)
FULL_CASTER_SLOTS = (
    (2,), (3,), (4,2), (4,3), (4,3,2), (4,3,3), (4,3,3,1), (4,3,3,2),
    (4,3,3,3,1), (4,3,3,3,2), (4,3,3,3,2,1), (4,3,3,3,2,1),
    (4,3,3,3,2,1,1), (4,3,3,3,2,1,1), (4,3,3,3,2,1,1,1), (4,3,3,3,2,1,1,1),
    (4,3,3,3,2,1,1,1,1), (4,3,3,3,3,1,1,1,1),
    (4,3,3,3,3,2,1,1,1), (4,3,3,3,3,2,2,1,1),
)
# Preserve old milestone totals, but distribute the gains between them.
# 95 remains the full-caster cap (tabletop level 20); a knight stays at 30.
MANA_RULES_VERSION = 3
MANA_GROWTH_LEVELS = (1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95)
MANA_RECOVERY_DELAY = 12.0
MANA_RECOVERY_FIELD_SECONDS = 240.0
MANA_RECOVERY_SAFE_SECONDS = 20.0
HOTBAR_ROW_SIZE = 12
HOTBAR_PAGE_SIZE = 24
HOTBAR_MAX_SLOTS = 96
TABLETOP_ROUND_SECONDS = 6.0
GAME_ROUND_SECONDS = 3.0
UNITS_PER_FOOT = 32.0 / 5.0
LONGSTRIDER_ROUNDS = 600
LONGSTRIDER_SPEED_BONUS = 10 * UNITS_PER_FOOT / GAME_ROUND_SECONDS


def mana_slot_budget(class_id, level):
    if class_id in ('mage', 'druid'):
        return FULL_CASTER_SLOTS[min(20, max(1, 1 + int(level)//5))-1]
    if class_id == 'ranger':
        # 2024 half-caster slots: tabletop 1/5/9/13/17 => game 1/20/40/60/80.
        effective = min(20, max(1, 1 + int(level)//5))
        return FULL_CASTER_SLOTS[(effective-1)//2]
    return ()


def legacy_base_mana(class_id, level):
    """Pre-0.8.16 budget, retained for migration and old advancement receipts."""
    slots = mana_slot_budget(class_id, level)
    return sum(n*MANA_COSTS[i+1] for i,n in enumerate(slots)) if slots else int(CLASS_SPECS[class_id]['mana'])


MANA_CHECKPOINTS = {cls: tuple((level, legacy_base_mana(cls, level))
                    for level in MANA_GROWTH_LEVELS) for cls in CLASS_SPECS}


def interpolate_growth(level, checkpoints):
    """Whole points, nearest integer (halves up), clamped to the end anchors.

    Compute from the absolute level, never by repeatedly adding rounded gains:
    multi-level awards, reloads and consecutive level-ups must give equal totals.
    """
    level = max(1, int(level))
    if level <= checkpoints[0][0]:
        return checkpoints[0][1]
    for (lo, start), (hi, end) in zip(checkpoints, checkpoints[1:]):
        if level <= hi:
            width = hi-lo
            return start + (2*(end-start)*(level-lo)+width)//(2*width)
    return checkpoints[-1][1]


def base_mana(class_id, level, version=MANA_RULES_VERSION):
    if version < MANA_RULES_VERSION:
        return legacy_base_mana(class_id, level)
    return interpolate_growth(level, MANA_CHECKPOINTS[class_id])


def max_mana(p):
    base = base_mana(p.class_id, p.level, getattr(p, 'mana_rules_version', MANA_RULES_VERSION))
    return base + max(0, min(20, int(p.mastery.get('focus', 0))))*4


def mana_budget_info(p):
    version = getattr(p, 'mana_rules_version', MANA_RULES_VERSION)
    base = base_mana(p.class_id, p.level, version)
    # Slots still describe the old tabletop reference, NOT limits on each circle
    # and NOT the current interpolated pool. Clients display base/bonus instead.
    return dict(slots=list(mana_slot_budget(p.class_id, p.level)),
                base=base, bonus=max_mana(p)-base, costs=list(MANA_COSTS), shared=True,
                progression='per_level' if version >= MANA_RULES_VERSION else 'weighted_slots',
                next_level_gain=base_mana(p.class_id, p.level+1, version)-base,
                slots_are_reference=version >= MANA_RULES_VERSION)

# An explicit implementation catalogue, not the entire tabletop spell list.
SPELLS = {}

def add(key, name, english, circle, classes, kind, description, **extra):
    SPELLS[key] = dict(name=name, english=english, words=english, circle=circle,
        class_ids=classes.split(), min_level=1 if circle==0 else FULL_CASTER_CIRCLE_LEVELS[circle-1],
        mana=0 if circle==0 else MANA_COSTS[circle],
        cooldown=0, action='action', kind=kind, description=description, range=310,
        radius=0, effect='magic_bolt', source='SRD 5.2.1', **extra)

add('fire_bolt','Ognisty pocisk','Fire Bolt',0,'mage','attack','Rzut ataku czarem; 1k10 ognia. Więcej kości na poziomach 20/50/80.',dice=[1,10,0], damage_type='fire',scales=True)
add('ray_of_frost','Promień mrozu','Ray of Frost',0,'mage','attack','1k8 zimna; trafiony cel porusza się wolniej przez jedną rundę.',dice=[1,8,0],damage_type='cold',scales=True,slow=3)
add('shocking_grasp','Porażający uścisk','Shocking Grasp',0,'mage','attack','Czar w zwarciu: 1k8 błyskawic. Trafiony cel nie wykona reakcji przez rundę.',dice=[1,8,0],damage_type='lightning',scales=True,melee=True,no_reactions=3)
add('acid_splash','Rozprysk kwasu','Acid Splash',0,'mage','save','1k6 kwasu w małym obszarze. Obrona ZRĘ: brak obrażeń.',dice=[1,6,0],damage_type='acid',scales=True,save='dexterity',save_half=False,area=True)
add('shillelagh','Shillelagh · magiczna laska','Shillelagh',0,'druid','buff','Przez 60 s laska atakuje Mądrością zamiast Siłą; kość k8, później k10/k12/2k6.',buff='shillelagh',duration=60)
add('produce_flame','Wytworzenie płomienia','Produce Flame',0,'druid','attack','Miotany płomień: 1k8 ognia. Sztuczka nie zastępuje podstawowej walki laską.',dice=[1,8,0],damage_type='fire',scales=True)
add('thorn_whip','Ciernisty bicz','Thorn Whip',0,'druid','attack','1k6 kłutych; przyciąga mniejszego przeciwnika do 64 jednostek. Atak czarem wręcz na odległość.',dice=[1,6,0],damage_type='piercing',scales=True,melee=True,pull=64)
add('starry_wisp','Gwiaździsty ognik','Starry Wisp',0,'druid','attack','1k8 promienistych. Trafiony przeciwnik zostaje oznaczony światłem przez rundę.',dice=[1,8,0],damage_type='radiant',scales=True,glow=3)

add('magic_missile','Magiczny pocisk','Magic Missile',1,'mage','missiles','Trzy automatycznie trafiające pociski, każdy 1k4+1 mocy. Tarcza je zatrzymuje.',dice=[1,4,1],damage_type='force',shots=3)
add('burning_hands','Płonące dłonie','Burning Hands',1,'mage','save','Stożek przed postacią: 3k6 ognia; obrona ZRĘ daje połowę.',dice=[3,6,0],damage_type='fire',save='dexterity',save_half=True,area=True,shape='cone')
add('shield','Tarcza','Shield',1,'mage','reaction','Włącz/wyłącz automatyczną reakcję. Gdy może zatrzymać trafienie: 20 many i +5 KP na 3 s. Chroni też przed Magicznym pociskiem.',buff='shield')
add('mage_armor','Zbroja maga','Mage Armor',1,'mage','buff','Bez zbroi lub w kurtce: bazowa KP 13 + Zręczność przez 10 minut.',buff='mage_armor',duration=600)
add('cure_wounds','Leczenie ran','Cure Wounds',1,'druid ranger','heal','Dotyk: leczy 2k8 + Mądrość. Domyślnie siebie; zaznacz członka drużyny, by go uleczyć.',dice=[2,8,0],add_ability=True)
add('healing_word','Uzdrawiające słowo','Healing Word',1,'druid','heal','Akcja dodatkowa: leczy 2k4 + Mądrość siebie lub wskazanego członka drużyny.',dice=[2,4,0],add_ability=True)
add('entangle','Oplątanie','Entangle',1,'druid','control','Korzenie unieruchamiają po nieudanej obronie SIŁ; ponawiana obrona co rundę. Koncentracja do 30 s.',save='strength',concentration=True,duration=30,area=True,buff='restrained')
add('hunters_mark','Znak łowcy','Hunter’s Mark',1,'ranger','mark','Zaznaczony przeciwnik otrzymuje dodatkowe 1k6 mocy przy każdym trafieniu łowcy. Koncentracja do 60 s.',dice=[1,6,0],damage_type='force',concentration=True,duration=60)
add('longstrider','Długonogi','Longstrider',1,'mage druid ranger','buff','Dotyk: szybkość +10 stóp przez godzinę świata D&D (600 rund = 30 min gry). Bez koncentracji; atak, obrażenia i inne czary nie przerywają. Nie skraca rundy.',buff='longstrider',duration=LONGSTRIDER_ROUNDS*GAME_ROUND_SECONDS,duration_rounds=LONGSTRIDER_ROUNDS,tabletop_duration=3600,speed_bonus_feet=10)

add('scorching_ray','Palący promień','Scorching Ray',2,'mage','attack','Trzy niezależne rzuty ataku przeciw temu samemu celowi; każdy promień zadaje 2k6 ognia.',dice=[2,6,0],damage_type='fire',shots=3)
add('misty_step','Mglisty krok','Misty Step',2,'mage','teleport','Akcja dodatkowa: teleport do widocznego, wolnego punktu przed postacią, maks. 192 jednostki.')
add('moonbeam','Promień księżyca','Moonbeam',2,'druid','field','Pole na wskazanym celu: 2k10 promienistych co rundę; obrona KON daje połowę. Koncentracja do 30 s.',dice=[2,10,0],damage_type='radiant',save='constitution',save_half=True,concentration=True,duration=30,area=True)
add('barkskin','Dębowa skóra','Barkskin',2,'druid ranger','buff','Akcja dodatkowa: KP nie mniejsza niż 17 przez 60 s.',buff='barkskin',duration=60)
add('spike_growth','Kolczasty wzrost','Spike Growth',2,'druid ranger','field','Kolce: 2k4 kłutych za każde 64 jednostki ruchu w polu, maksymalnie 4 razy na 3 s. Brak rzutu obronnego. Koncentracja do 30 s.',dice=[2,4,0],damage_type='piercing',movement_damage=True,movement_step=64,movement_tick_cap=4,concentration=True,duration=30,area=True)

add('fireball','Kula ognia','Fireball',3,'mage','save','Eksplozja w miejscu celu: 8k6 ognia; obrona ZRĘ daje połowę.',dice=[8,6,0],damage_type='fire',save='dexterity',save_half=True,area=True)
add('lightning_bolt','Błyskawica','Lightning Bolt',3,'mage','save','Linia od postaci przez wskazany cel: 8k6 błyskawic; obrona ZRĘ daje połowę.',dice=[8,6,0],damage_type='lightning',save='dexterity',save_half=True,area=True,shape='line')
add('call_lightning','Wezwanie błyskawicy','Call Lightning',3,'druid','save','3k10 błyskawic w małym obszarze; obrona ZRĘ daje połowę. Przez koncentrację następne wezwania nie kosztują many.',dice=[3,10,0],damage_type='lightning',save='dexterity',save_half=True,area=True,concentration=True,duration=30,recast=True)
add('protection_from_energy','Ochrona przed energią','Protection from Energy',3,'druid ranger mage','buff','Wybrany tutaj wariant ognia: połowa obrażeń od ognia przez 60 s. Koncentracja.',buff='resist_fire',concentration=True,duration=60)
add('plant_growth','Rozrost roślin','Plant Growth',3,'druid ranger','field','Gęstwina: przeciwnicy w obszarze poruszają się czterokrotnie wolniej. Pole trwa 30 s; nie wymaga koncentracji.',duration=30,area=True,growth=True)

add('blight','Uschnięcie','Blight',4,'mage druid','save','Pojedynczy cel: 8k8 nekrotycznych; obrona KON daje połowę. Nie działa na nieumarłych i konstrukty.',dice=[8,8,0],damage_type='necrotic',save='constitution',save_half=True,exclude_types=['undead','construct'])
add('ice_storm','Lodowa burza','Ice Storm',4,'mage druid','save','Obszar gradu: 2k10 obuchowych + 4k6 zimna; obrona ZRĘ daje połowę. Spowalnia na rundę.',dice=[2,10,0],extra_dice=[4,6,0],damage_type='bludgeoning',extra_type='cold',save='dexterity',save_half=True,area=True,slow=3)
add('freedom_of_movement','Swoboda ruchu','Freedom of Movement',4,'druid ranger','buff','Przez 60 s ignorujesz kary trudnego terenu, magiczne spowolnienie i unieruchomienie.',buff='freedom',duration=60)
add('stoneskin','Kamienna skóra','Stoneskin',4,'mage druid ranger','buff','Przez 60 s połowa obrażeń obuchowych, ciętych i kłutych. Koncentracja; koszt składnika: 100 złota.',buff='stoneskin',concentration=True,duration=60,gold=100)

add('cone_of_cold','Stożek zimna','Cone of Cold',5,'mage druid','save','Szeroki stożek: 8k8 zimna; obrona KON daje połowę.',dice=[8,8,0],damage_type='cold',save='constitution',save_half=True,area=True,shape='cone')
add('mass_cure_wounds','Masowe leczenie ran','Mass Cure Wounds',5,'druid','heal','Leczy ciebie i rannych członków drużyny w pobliżu: 5k8 + Mądrość.',dice=[5,8,0],add_ability=True,party=True)
add('conjure_volley','Przywołanie salwy','Conjure Volley',5,'ranger','save','Deszcz strzał w obszarze celu: 8k8 mocy; obrona ZRĘ daje połowę.',dice=[8,8,0],damage_type='force',save='dexterity',save_half=True,area=True)

add('chain_lightning','Łańcuch błyskawic','Chain Lightning',6,'mage','save','Cel i maks. trzech sąsiadów: 10k8 błyskawic; obrona ZRĘ daje połowę.',dice=[10,8,0],damage_type='lightning',save='dexterity',save_half=True,area=True,max_targets=4)
add('sunbeam','Promień słońca','Sunbeam',6,'mage druid','save','Linia światła: 6k8 promienistych; obrona KON daje połowę, porażka oślepia na rundę. Koncentracja pozwala powtarzać bez many.',dice=[6,8,0],damage_type='radiant',save='constitution',save_half=True,area=True,shape='line',blind=3,concentration=True,duration=30,recast=True)
add('heal','Uzdrowienie','Heal',6,'druid','heal','Przywraca 70 HP sobie lub wskazanemu sojusznikowi. Stała wartość wynika z tego czaru, nie z rzutu obrażeń.',flat_heal=70)

add('finger_of_death','Palec śmierci','Finger of Death',7,'mage','save','7k8+30 nekrotycznych przeciw jednemu celowi; obrona KON daje połowę. W tej adaptacji nie tworzy zombie.',dice=[7,8,30],damage_type='necrotic',save='constitution',save_half=True)
add('fire_storm','Burza ognia','Fire Storm',7,'druid','save','Ognisty obszar wokół celu: 7k10 ognia; obrona ZRĘ daje połowę.',dice=[7,10,0],damage_type='fire',save='dexterity',save_half=True,area=True)

add('sunburst','Rozbłysk słońca','Sunburst',8,'mage druid','save','12k6 promienistych w obszarze; obrona KON daje połowę. Porażka oślepia, z nową obroną co rundę.',dice=[12,6,0],damage_type='radiant',save='constitution',save_half=True,area=True,blind=30)
add('incendiary_cloud','Zapalająca chmura','Incendiary Cloud',8,'mage druid','field','Chmura: 10k8 ognia co rundę, obrona ZRĘ daje połowę. Koncentracja do 30 s; w adaptacji pole jest nieruchome.',dice=[10,8,0],damage_type='fire',save='dexterity',save_half=True,area=True,concentration=True,duration=30)

add('meteor_swarm','Rój meteorów','Meteor Swarm',9,'mage','save','Cztery pobliskie eksplozje: 20k6 ognia + 20k6 obuchowych; obrona ZRĘ daje połowę. Jeden cel otrzymuje obrażenia tylko raz.',dice=[20,6,0],extra_dice=[20,6,0],damage_type='fire',extra_type='bludgeoning',save='dexterity',save_half=True,area=True,shape='meteors')
add('foresight','Przewidywanie','Foresight',9,'mage druid','buff','Przez 120 s ułatwienie własnych ataków i obron; przeciwnicy mają utrudnienie ataku przeciw tobie.',buff='foresight',duration=120)

add('ensnaring_strike','Uderzenie oplątujące','Ensnaring Strike',1,'ranger','weapon_trigger',
    'Przygotuj oplątanie następnego trafienia bronią. Mana i akcja dodatkowa są zużywane dopiero po trafieniu. Obrona SIŁ chroni; duże stworzenia mają ułatwienie. Pnącza unieruchamiają i ranią co rundę. Cel może poświęcić akcję na próbę wyrwania się. Koncentracja.',
    dice=[1,6,0], damage_type='piercing', save='strength', concentration=True, duration=30, duration_rounds=10, buff='restrained')
SPELLS['ensnaring_strike'].update(action='bonus', source='Mechanika 2024; opis i implementacja własna Bractwa')
SPELLS['hunters_mark'].update(mana=0, cooldown=30, free_cast=True)
SPELLS['longstrider']['class_min_levels']={'ranger':5}

# Class features deliberately marked as adaptations, not misrepresented as spells.
add('second_wind','Drugi oddech','Second Wind',0,'knight','heal','Zdolność wojownika: odzyskaj 1k10 + poziom bojowy HP; odnowienie 30 s.',dice=[1,10,0],feature=True)
add('animal_companion','Zew towarzysza','Animal Companion',0,'ranger','companion','Od poziomu 10: wezwij wilka. Walczy z wybranym przeciwnikiem, także graczem po odblokowaniu PvP; może zginąć; ponowne wezwanie po 45 s.',feature=True)
add('wild_shape_wolf','Dziki kształt · wilk','Wild Shape',0,'druid','shape','Od poziomu 20: wilk, ugryzienie 2k4+2 i tymczasowe HP. Brak czarów w formie; użyj ponownie, by powrócić.',feature=True,form='wolf')
add('wild_shape_bear','Dziki kształt · niedźwiedź','Wild Shape',0,'druid','shape','Od poziomu 40: niedźwiedź, dwa ataki 2k6+4 na rundę i tymczasowe HP. Brak czarów w formie.',feature=True,form='bear')

for key in ('shillelagh','healing_word','hunters_mark','misty_step','barkskin','second_wind','wild_shape_wolf','wild_shape_bear'):
    SPELLS[key]['action']='bonus'
for key in ('shield',): SPELLS[key]['action']='reaction'
for key, gate, mana, cooldown in [('second_wind',1,5,30),('animal_companion',10,8,45),('wild_shape_wolf',20,10,60),('wild_shape_bear',40,16,60)]:
    SPELLS[key].update(min_level=gate,mana=mana,cooldown=cooldown,source='Zdolność klasy · adaptacja Bractwa')
SPELLS['wild_shape_wolf']['duration']=90
SPELLS['wild_shape_bear']['duration']=90
for key, radius in [('acid_splash',45),('entangle',128),('moonbeam',64),('spike_growth',128),('fireball',145),('call_lightning',64),('plant_growth',190),('ice_storm',150),('mass_cure_wounds',300),('conjure_volley',220),('chain_lightning',150),('fire_storm',190),('sunburst',230),('incendiary_cloud',130),('meteor_swarm',110)]:
    SPELLS[key]['radius']=radius
for key,r in [('shocking_grasp',108),('thorn_whip',192),('produce_flame',192),('cure_wounds',108),('healing_word',300),('burning_hands',140),('cone_of_cold',360),('lightning_bolt',480),('sunbeam',420),('meteor_swarm',600),('entangle',380),('moonbeam',420),('longstrider',108)]:
    SPELLS[key]['range']=r
SPELLS['protection_from_energy']['class_ids']=['druid','ranger','mage']

# Explicit ground geometry and presentation (SRD dimensions, 32 units / 5 feet).
# Casting distances and targeting remain Bractwo's adaptation.
for _key, _radius in {
    'acid_splash':32, 'moonbeam':32, 'spike_growth':128, 'fireball':128,
    'call_lightning':32, 'plant_growth':640, 'ice_storm':128, 'mass_cure_wounds':192,
    'conjure_volley':256, 'chain_lightning':192, 'sunburst':384,
    'incendiary_cloud':128, 'meteor_swarm':256,
}.items(): SPELLS[_key]['radius'] = _radius
SPELLS['burning_hands'].update(range=96, width=96)
SPELLS['cone_of_cold'].update(range=384, width=384)
SPELLS['lightning_bolt'].update(range=640, width=32)
SPELLS['sunbeam'].update(range=384, width=32)
SPELLS['entangle'].update(shape='square', width=128, radius=91)
SPELLS['fire_storm'].update(shape='cubes', cube_size=64, radius=173)
SPELLS['fire_storm']['description']='Dziesięć połączonych ognistych sześcianów wokół celu: 7k10 ognia; obrona ZRĘ daje połowę.'
SPELLS['chain_lightning']['shape']='chain'
SPELLS['meteor_swarm']['meteor_offset']=160
PALETTES = {
    'fire':['#ff7739','#ffd276','#fff5d1'], 'cold':['#46b9ff','#a0eaff','#f7ffff'],
    'lightning':['#7777ff','#c6c3ff','#ffffff'], 'force':['#a981ff','#ecc6ff','#ffffff'],
    'acid':['#76bd36','#c4f878','#f4ffd7'], 'radiant':['#eaba53','#fff2b7','#ffffff'],
    'necrotic':['#843fad','#c17cf0','#f0ccff'], 'piercing':['#54743e','#a7d674','#eefbb8'],
    'nature':['#53a365','#b2eaa2','#f2ffce'], 'arcane':['#608acc','#b6d2ff','#ffffff'],
}
for _key,_s in SPELLS.items():
    _s['id']=_key
    _s.setdefault('shape','circle' if _s.get('area') or _s.get('party') else 'single')
    _theme=_s.get('damage_type','nature' if 'druid' in _s['class_ids'] else 'arcane')
    _theme = _theme if _theme in PALETTES else 'arcane'
    if _key=='moonbeam': _theme='cold'
    if _s.get('area'): _style='area'
    elif _s['kind']=='missiles': _style='missiles'
    elif _key in ('ray_of_frost','scorching_ray','shocking_grasp','finger_of_death','thorn_whip'): _style='beam'
    elif _s['kind'] in ('attack','save','mark'): _style='projectile'
    elif _s['kind']=='heal': _style='heal'
    elif _s['kind']=='teleport': _style='teleport'
    elif _s['kind'] in ('shape','companion'): _style='summon'
    else: _style='aura'
    if _key=='chain_lightning': _style='chain'
    _s['visual']={'style':_style,'theme':_theme,'colors':PALETTES[_theme], 'shots':_s.get('shots',1)}
    if _key=='ensnaring_strike':_s['visual']['style']='vines'
    if _key=='hunters_mark':_s['visual']['style']='mark'
    _s['icon']='assets/spells/'+_key+'.svg'
    _s['effect']='spell'

# Who may receive this effect; offensive PvP always rechecks the server's safety rules.
for key,spec in SPELLS.items():
    spec['targeting'] = ('self' if key in ('second_wind','shillelagh') or spec['kind'] in ('reaction','teleport','shape','companion','weapon_trigger')
        else 'party' if spec.get('party') else 'ally' if spec['kind'] in ('heal','buff') else 'hostile')
    spec['pvp'] = True
    if spec['kind']=='buff' and spec['targeting']=='ally':
        spec['description'] += ' Cel: ty lub wskazany członek drużyny.'

# Current dice/counts/durations are delivered by the server per character.
SPELLS['hunters_mark']['duration'] = 600 * GAME_ROUND_SECONDS
SPELLS['fire_bolt']['description'] = 'Ognisty pocisk trafia po udanym rzucie ataku czarem. Sztuczka rośnie na poziomach 20, 50 i 80.'
SPELLS['ray_of_frost']['description'] = 'Zimny promień. Trafiony cel porusza się wolniej przez jedną rundę.'
SPELLS['shocking_grasp']['description'] = 'Porażenie w zwarciu. Trafiony cel nie może wykonać reakcji przez rundę.'
SPELLS['acid_splash']['description'] = 'Kwas rozpryskuje się w małym obszarze. Udana obrona ZRĘ chroni przed obrażeniami.'
SPELLS['produce_flame']['description'] = 'Miotany płomień. Darmowa sztuczka z rzutem ataku czarem.'
SPELLS['thorn_whip']['description'] = 'Ciernisty bicz zadaje obrażenia kłute i przyciąga mniejszego przeciwnika do 10 stóp. Rzut ataku czarem wręcz.'
SPELLS['starry_wisp']['description'] = 'Promienisty ognik. Trafiony przeciwnik zostaje oznaczony światłem przez rundę.'
SPELLS['shillelagh']['description'] = 'Magiczna laska atakuje Mądrością zamiast Siłą. Jej kość obrażeń rośnie na poziomach 20, 50 i 80.'
SPELLS['magic_missile']['description'] = 'Pociski mocy trafiają automatycznie. Każdy zadaje 1k4+1 obrażeń. Tarcza zatrzymuje całą salwę.'
SPELLS['burning_hands']['description'] = 'Płomienie w stożku przed postacią. Udana obrona ZRĘ zmniejsza obrażenia o połowę.'
SPELLS['cure_wounds']['description'] = 'Dotyk przywraca zdrowie. Domyślnie leczysz siebie; zaznacz członka drużyny, aby uleczyć jego.'
SPELLS['healing_word']['description'] = 'Akcja dodatkowa. Przywraca zdrowie tobie lub wskazanemu członkowi drużyny.'
SPELLS['scorching_ray']['description'] = 'Ogniste promienie. Każdy wymaga osobnego rzutu ataku i zadaje 2k6 obrażeń.'
SPELLS['moonbeam']['description'] = 'Promieniste pole rani co rundę. Udana obrona KON zmniejsza obrażenia o połowę. Wymaga koncentracji.'
SPELLS['fireball']['description'] = 'Ognista eksplozja wokół celu. Udana obrona ZRĘ zmniejsza obrażenia o połowę.'
SPELLS['lightning_bolt']['description'] = 'Błyskawica w linii od postaci przez cel. Udana obrona ZRĘ zmniejsza obrażenia o połowę.'
SPELLS['call_lightning']['description'] = 'Wezwij błyskawicę w małym obszarze. Obrona ZRĘ zmniejsza obrażenia o połowę. Kolejne wezwania przy utrzymanej koncentracji nie kosztują many.'
SPELLS['blight']['description'] = 'Nekrotyczna energia wysysa życie. Udana obrona KON zmniejsza obrażenia o połowę.'
SPELLS['ice_storm']['description'] = 'Grad zadaje obrażenia obuchowe i od zimna; udana obrona ZRĘ zmniejsza je o połowę. Spowalnia na rundę. Wyższy krąg wzmacnia tylko grad.'
SPELLS['cone_of_cold']['description'] = 'Mroźny stożek przed postacią. Udana obrona KON zmniejsza obrażenia o połowę.'
SPELLS['mass_cure_wounds']['description'] = 'Przywraca zdrowie tobie i maksymalnie pięciu członkom drużyny w obszarze.'
SPELLS['chain_lightning']['description'] = 'Błyskawica przeskakuje z pierwszego celu na pobliskich przeciwników. Udana obrona ZRĘ zmniejsza obrażenia o połowę.'
SPELLS['heal']['description'] = 'Przywraca zdrowie tobie lub wskazanemu sojusznikowi, bez rzutu kośćmi.'
SPELLS['hunters_mark']['description'] = 'Oznacz przeciwnika: każde twoje trafienie rzutem ataku zadaje mu dodatkowe 1k6 mocy. Bez many; odnowienie 30 s, również przy zmianie celu. Wymaga koncentracji. Atak i leczenie jej nie przerywają. Wyższe kręgi wydłużają czas, nie zwiększają obrażeń.'
SPELLS['longstrider']['description'] = 'Dotyk: szybkość +10 stóp. Atak, obrażenia i inne czary nie przerywają efektu. Bez koncentracji. Wyższy krąg obejmuje więcej członków drużyny w zasięgu dotyku, nie wydłuża czasu.'
SPELLS['second_wind']['description'] = 'Akcja dodatkowa: odzyskaj 1k10 + poziom bojowy HP. Premia rośnie co 5 poziomów postaci. Odnowienie: 30 s.'

# Preference order only. sync_hotbar removes locked spells, fills gaps and appends
# every unlocked spell. Two rows of twelve buttons make one bank.
DEFAULT_HOTBARS = {
    'knight':['second_wind'],
    'ranger':['hunters_mark','ensnaring_strike','cure_wounds','longstrider','animal_companion','spike_growth','barkskin','stoneskin','conjure_volley'],
    'mage':['fire_bolt','ray_of_frost','acid_splash','magic_missile','shield','burning_hands','mage_armor','longstrider','shocking_grasp'],
    'druid':['shillelagh','thorn_whip','produce_flame','cure_wounds','entangle','healing_word','longstrider','starry_wisp'],
}


def hotbar_signature(p):
    try:from . import druid_circles as dc
    except ImportError:import druid_circles as dc
    return (p.class_id,p.level,getattr(p,'druid_circle',''),getattr(p,'form',''),dc.land(p),dc.starry_form(p),dc.feature_allowed(p,'circle_wrath_strike'),dc.active(p,'grappled'))

def sync_hotbar(p):
    """Preserve valid custom positions, but never hide unlocked spells off-bar."""
    raw = p.hotbar if isinstance(p.hotbar, list) else []
    bar=[];seen=set()
    for key in raw[:HOTBAR_MAX_SLOTS]:
        valid=isinstance(key,str) and key not in seen and spell_allowed(p,key)
        bar.append(key if valid else '')
        if valid:seen.add(key)
    ordered=list(dict.fromkeys(DEFAULT_HOTBARS[p.class_id]+list(SPELLS)))
    missing=[key for key in ordered if key not in seen and spell_allowed(p,key)]
    for i,key in enumerate(bar):
        if not key and missing:bar[i]=missing.pop(0)
    bar.extend(missing)
    while bar and not bar[-1]:bar.pop()
    size=max(HOTBAR_PAGE_SIZE,((len(bar)+HOTBAR_PAGE_SIZE-1)//HOTBAR_PAGE_SIZE)*HOTBAR_PAGE_SIZE)
    p.hotbar=bar+['']*(size-len(bar))
    p._hotbar_level=hotbar_signature(p)
    return p.hotbar


# Browser-only projection. The saved legacy hotbar remains a list of real spells,
# so existing native clients and player databases keep their previous format.
HOTBAR_GROUPS = {
    'group_wild_shape': dict(name='Dziki kształt', icon='assets/spells/wild_shape_wolf.svg'),
    'group_starry_form': dict(name='Gwiezdna postać', icon='assets/spells/starry_wisp.svg'),
}


def hotbar_group_key(key):
    if not isinstance(key, str): return ''
    if key.startswith('wild_shape_') or key == 'beast_trample': return 'group_wild_shape'
    if key in ('circle_star_archer', 'circle_star_chalice', 'circle_star_dragon', 'circle_star_arrow'):
        return 'group_starry_form'
    return key


def hotbar_group_catalog():
    return {key: dict(spec, members=[spell for spell in SPELLS if hotbar_group_key(spell) == key])
            for key, spec in HOTBAR_GROUPS.items()}


def grouped_hotbar(p):
    """Merge variants, not unrelated spells; keep intentional empty/custom slots."""
    bar, seen = [], set()
    for spell in p.hotbar:
        if not spell:
            bar.append('')
            continue
        if not spell_allowed(p, spell): continue
        key = hotbar_group_key(spell)
        if key in seen: continue
        seen.add(key)
        bar.append(key)
    while bar and not bar[-1]: bar.pop()
    size = max(HOTBAR_PAGE_SIZE, ((len(bar)+HOTBAR_PAGE_SIZE-1)//HOTBAR_PAGE_SIZE)*HOTBAR_PAGE_SIZE)
    return bar + ['']*(size-len(bar))


def bind_grouped_hotbar(p, slot, spell):
    """Swap visible groups and expand back to real spell IDs for persistence."""
    if type(slot) is not int or not isinstance(spell, str): return False
    bar = grouped_hotbar(p)
    if not 0 <= slot < len(bar): return False
    key = hotbar_group_key(spell)
    if key not in bar or not key: return False
    if spell not in HOTBAR_GROUPS and not spell_allowed(p, spell): return False
    previous = bar.index(key)
    bar[previous], bar[slot] = bar[slot], key
    members = {}
    for current in p.hotbar:
        if current and spell_allowed(p, current):
            members.setdefault(hotbar_group_key(current), []).append(current)
    expanded = []
    for entry in bar:
        expanded.extend(members.get(entry, ['']))
    # Validate before assigning; do not truncate a high-level character's spells.
    while expanded and not expanded[-1]: expanded.pop()
    if len(expanded) > HOTBAR_MAX_SLOTS: return False
    p.hotbar = expanded
    sync_hotbar(p)
    return True


def spell_level(spec, class_id):
    override = spec.get('class_min_levels', {}).get(class_id)
    if override is not None:return override
    return RANGER_CIRCLE_LEVELS[spec['circle']-1] if class_id=='ranger' and 0 < spec['circle'] <= len(RANGER_CIRCLE_LEVELS) else spec['min_level']


def circle_for(class_id, level):
    """Highest unlocked circle, using the same gates as the spell catalogue."""
    gates = RANGER_CIRCLE_LEVELS if class_id=='ranger' else FULL_CASTER_CIRCLE_LEVELS if class_id in ('mage','druid') else ()
    return sum(level >= gate for gate in gates)


def spell_allowed(p, key):
    s=SPELLS.get(key)
    try:
        from . import druid_circles as dc
    except ImportError:
        import druid_circles as dc
    if not s:return False
    if key=='beast_trample':
        try:from . import caster_rules
        except ImportError:import caster_rules
        return bool(caster_rules.form_spec(p).get('trample'))
    if key=='escape_grapple':return dc.active(p,'grappled')
    if key in dc.SPELL_FEATURES:return dc.feature_allowed(p,key)
    if key in dc.bonus_spells(p):return True
    if key.startswith('wild_shape_') and hasattr(dc,'form_allowed'):return dc.form_allowed(p,key)
    return bool(s and p.class_id in s['class_ids'] and p.level>=spell_level(s,p.class_id))


for _s in SPELLS.values():
    _s['class_levels']={_cls:spell_level(_s,_cls) for _cls in _s['class_ids']}


def configure(content, classes, potions):
    classes.clear(); classes.update(CLASS_SPECS)
    content.SPELLS = SPELLS
    content.RUNES = {}  # Old Tibian runes no longer bypass class/circle requirements.
    content.PROMOTIONS = {'knight':'Mistrz miecza','ranger':'Mistrz łowów','mage':'Arcymag','druid':'Arcydruid'}
    content.MILESTONES = [(1,'I krąg / sztuczki i broń','Czarodziej, druid i łowca: I krąg od początku. Kości obrażeń, KP i cechy. Sztuczki nie kosztują many.'),
        (8,'Rejsy i PvP','Dostęp do statków i świadomie włączanego PvP poza osadami.'),
        (10,'II krąg / wilczy towarzysz','Czarodziej i druid: II krąg. Łowca: wilczy towarzysz.'),
        (20,'III krąg / dodatkowy atak','Czarodziej i druid: III krąg (Kula ognia / Wezwanie błyskawicy). Łowca: II krąg. Rycerz i łowca: 2 ataki.'),
        (30,'IV krąg','Uschnięcie, Lodowa burza i Kamienna skóra.'),
        (40,'V krąg','Czarodziej i druid: V krąg. Łowca: III krąg.'),
        (50,'VI krąg / 3 ataki','Rycerz: 3 ataki. Czarodziej i druid: VI krąg.'),
        (60,'VII krąg','Palec śmierci i Burza ognia; łowca: IV krąg.'),
        (70,'VIII krąg','Rozbłysk słońca i Zapalająca chmura.'),
        (80,'IX krąg','Rój meteorów i Przewidywanie; łowca: V krąg. Ostatni wzrost kości sztuczek.'),
        (95,'4 ataki rycerza','Rycerz wykonuje 4 niezależne rzuty ataku w jednej akcji.'),
        (100,'Dalsza wędrówka','Poziomy postaci nadal nie mają limitu.')]
    for i, dice in enumerate(([2,4,2],[4,4,4],[8,4,8],[10,4,20]),1):
        key='health_potion'+('' if i==1 else '_'+str(i))
        potions[key].update(dice=dice,restore=int(dice[0]*(dice[1]+1)/2+dice[2]))


# Small client-independent status catalogue. Timers are sent by the server,
# including public enemy/PvP target effects; no account or owner IDs are exposed.
STATUS_SPECS = {
    'longstrider': dict(name='Długonogi', icon='»', description='+10 stóp szybkości. Atak nie przerywa. Bez koncentracji.', harmful=False),
    'shillelagh': dict(name='Magiczna laska', icon='♧', description='Laska używa Mądrości i wzmocnionej kości obrażeń.', harmful=False),
    'mage_armor': dict(name='Zbroja maga', icon='◇', description='Bazowa KP 13 + Zręczność bez noszonej zbroi.', harmful=False),
    'shield': dict(name='Tarcza', icon='⬡', description='+5 KP; zatrzymuje Magiczny pocisk.', harmful=False),
    'barkskin': dict(name='Dębowa skóra', icon='♧', description='KP nie spada poniżej 17.', harmful=False),
    'resist_fire': dict(name='Ochrona przed ogniem', icon='♨', description='Połowa obrażeń od ognia. Koncentracja.', harmful=False),
    'freedom': dict(name='Swoboda ruchu', icon='»', description='Ignorujesz trudny teren, magiczne spowolnienie i unieruchomienie.', harmful=False),
    'stoneskin': dict(name='Kamienna skóra', icon='◆', description='Połowa obrażeń obuchowych, ciętych i kłutych. Koncentracja.', harmful=False),
    'foresight': dict(name='Przewidywanie', icon='✧', description='Ułatwienie ataków i obron; wrogowie mają utrudnienie trafienia.', harmful=False),
    'restrained': dict(name='Unieruchomienie', icon='⌁', description='Nie możesz się poruszać. Ataki są utrudnione; ataki w ciebie ułatwione. Ponawiasz obronę co rundę.', harmful=True),
    'slow': dict(name='Spowolnienie', icon='❄', description='Szybkość ruchu zmniejszona o połowę.', harmful=True),
    'growth': dict(name='Gęstwina', icon='♧', description='Szybkość ruchu zmniejszona czterokrotnie w polu roślin.', harmful=True),
    'blind': dict(name='Oślepienie', icon='◉', description='Utrudnienie własnych ataków; ułatwienie ataków w ciebie.', harmful=True),
    'no_reactions': dict(name='Brak reakcji', icon='×', description='Nie możesz uruchomić reakcji, w tym Tarczy.', harmful=True),
    'glow': dict(name='Świetlny ślad', icon='✧', description='Cel oznaczony blaskiem Gwiaździstego ognika.', harmful=True),
}


def status_effects(conditions, now, player=None):
    from math import ceil
    result=[]
    for key,value in conditions.items():
        remaining=max(0,value.get('until',0)-now)
        if remaining<=0:continue
        info=STATUS_SPECS.get(key,dict(name=key,icon='✦',description='',harmful=bool(value.get('hostile'))))
        if key == 'starry_form':
            try:
                from . import druid_circles as circles
            except ImportError:
                import druid_circles as circles
            form = circles.starry_form(player) if player is not None else value.get('form', '')
            label, description = {
                'archer': ('Łucznik', 'Przycisk Strzała wystrzeliwuje gwiezdny pocisk bez many i kolejnych użyć przemiany. Powrót do druida: ▾ przy tym przycisku.'),
                'chalice': ('Kielich', 'Czary leczące za manę uruchamiają dodatkowe leczenie. Powrót do druida: przycisk Kielich albo ▾.'),
                'dragon': ('Smok', 'Stabilizuje koncentrację oraz testy Inteligencji i Mądrości. Powrót do druida: przycisk Smok albo ▾.'),
            }.get(form, ('Gwiezdna postać', 'Powrót do druida: ▾ w grupie gwiezdnych postaci.'))
            info = dict(name='Gwiezdna postać · '+label, icon='✧', description=description, harmful=False)
        elif value.get('spell_id')=='hunters_mark':
            info=dict(name='Znak łowcy',icon='⌖',description='Trafienia oznaczającego łowcy zadają dodatkowe 1k6 mocy. Zniknie po utracie jego koncentracji.',harmful=True)
        elif value.get('spell_id')=='ensnaring_strike':
            dice=value.get('profile',{}).get('dice',[1,6,0])
            info=dict(name='Uderzenie oplątujące',icon='⌁',description=f'Nie możesz się ruszać. {dice[0]}k{dice[1]} kłutych co rundę. Własne ataki utrudnione; ataki w ciebie ułatwione. Wyrwanie się wymaga akcji i próby Siły.',harmful=True,escape_action=True)
        result.append(dict(id=key,**info,remaining=round(remaining,2),rounds=ceil(remaining/GAME_ROUND_SECONDS),
            concentration=bool(value.get('concentration')),spell_id=value.get('spell_id','')))
    if player is not None:
        if player.concentration and player.concentration_until>now:
            spec=getattr(player,'concentration_profile',{}) or SPELLS.get(player.concentration,{})
            remaining=player.concentration_until-now
            result.append(dict(id='concentration',name='Koncentracja: '+spec.get('name',player.concentration),
                icon='◎',description=(spec.get('power_summary','')+' · '+spec.get('description','')).strip(' ·'),remaining=round(remaining,2),rounds=ceil(remaining/GAME_ROUND_SECONDS),
                harmful=False,concentration=True,spell_id=player.concentration))
        if getattr(player,'ensnaring_armed',False):
            result.append(dict(id='ensnaring_ready',name='Uderzenie oplątujące: gotowe',icon='⌁',remaining=None,rounds=None,harmful=False,
                spell_id='ensnaring_strike',description='Przy następnym trafieniu bronią zużyjesz manę i akcję dodatkową, zastępując obecny czar koncentracyjny. Kliknij czar ponownie, aby anulować.'))
        if player.shield_armed:
            result.append(dict(id='shield_ready',name='Tarcza: reakcja',icon='⬡',remaining=None,rounds=None,harmful=False,
                description='Włączona; zużywa 20 many przy reakcji, nie przy włączeniu. Nie działa bez many, w przemianie ani przy blokadzie reakcji.'))
        if player.form and player.form_until>now:
            remaining=player.form_until-now
            result.append(dict(id='wild_shape',name='Postać: '+{'wolf':'wilk','cat':'kot','black_bear':'niedźwiedź czarny','bear':'niedźwiedź brunatny'}.get(player.form,player.form),
                icon='♞',description='Brak rzucania czarów. Ponownie użyj przemiany, by powrócić.',harmful=False,
                remaining=round(remaining,2),rounds=ceil(remaining/GAME_ROUND_SECONDS)))
        if player.temp_hp>0:
            result.append(dict(id='temp_hp',name='Tymczasowe HP: '+str(int(player.temp_hp)),icon='♥',harmful=False,
                description='Dodatkowa osłona pochłania obrażenia przed właściwym zdrowiem.',remaining=None,rounds=None))
    return result


def sanitize_spell_history(p):
    raw=getattr(p,'spell_history',[])
    p.spell_history=[k for k in raw[-100:] if isinstance(k,str) and spell_allowed(p,k)] if isinstance(raw,list) else []


def record_spell_use(p,key):
    if spell_allowed(p,key):
        p.spell_history=(getattr(p,'spell_history',[])+[key])[-100:]


def favorite_spell(p):
    from collections import Counter
    history=[k for k in getattr(p,'spell_history',[]) if spell_allowed(p,k)]
    if history:
        counts=Counter(history);maximum=max(counts.values())
        return next(k for k in reversed(history) if counts[k]==maximum)
    preferred=CLASS_SPECS[p.class_id]['default_ability']
    if spell_allowed(p,preferred):return preferred
    return next((k for k in DEFAULT_HOTBARS[p.class_id] if spell_allowed(p,k)),'')

# Higher-circle target count is resolved on the server; do not promise a duration increase.
SPELLS['freedom_of_movement']['description'] = 'Chroni przed magicznym spowolnieniem i unieruchomieniem. Wyższy krąg obejmuje kolejnego członka drużyny w zasięgu dotyku.'
