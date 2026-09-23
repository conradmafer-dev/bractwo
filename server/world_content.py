"""Hand-authored continent layout and deterministic hunting grounds for Bractwo 0.4.

Levels on the atlas are recommendations. Only the final descent has a level gate.
No player-dependent scaling, downloaded assets, or global random generation.
"""
import math
import random

VERSION = '0.5.0'
WIDTH, HEIGHT = 16000, 9216
REGIONS, CITIES, STAIRS, DUNGEONS, SPAWNS, ROADS = [], [], [], [], [], []
PROMOTIONS = {'knight':'Elitarny Rycerz', 'paladin':'Królewski Paladyn',
              'mage':'Mistrz Magii', 'druid':'Starszy Druid'}
MILESTONES = [
    (1, 'Trening przez walkę', 'Udane trafienia rozwijają broń; zużyta mana rozwija magię, otrzymane ciosy — obronę.'),
    (8, 'Leczenie, przyspieszenie i statki', 'Dwa nowe czary oraz rejsy między pięcioma miastami. Kup zapasy przed długą wyprawą.'),
    (12, 'Runy', 'Kupuj runy bojowe. Mag i druid mogą tworzyć je z many oraz punktów duszy.'),
    (20, 'Promocja profesji', 'Mistrz w mieście nadaje wyższą rangę za 2000 złota: szybsza regeneracja i 200 punktów duszy.'),
    (30, 'Zaawansowany czar profesji', 'Nowa technika każdej klasy: wir, salwa, fala ognia lub lodu. Wymaga promocji.'),
    (40, 'Błogosławieństwo', 'Za 500 złota zmniejsza o połowę stratę złota i PD przy kolejnej śmierci bez czerwonej czaszki.'),
    (50, 'Specjalizacja', 'Promowana postać otrzymuje punkt co 5 poziomów. Wybieraj siłę, witalność lub skupienie.'),
    (60, 'Kontrakty na bossów', 'Jednorazowe wyprawy po potężną broń; bossowie odradzają się także po odebraniu nagrody.'),
    (80, 'Mistrzowski czar', 'Najsilniejsza technika twojej profesji — wymaga promocji i dużego zapasu many.'),
    (100, 'Pieczęć Otchłani', 'Dostęp do najgłębszej sali pod Morzem Popiołu. Zalecana drużyna poziomu 120+.'),
]
SPELLS = {
    'mend': {'name':'Lekkie leczenie', 'words':'exura', 'min_level':8, 'mana':20, 'cooldown':3, 'kind':'heal', 'description':'Odnawia 35 + 3 × poziom + 2 × poziom magii zdrowia.'},
    'haste': {'name':'Przyspieszenie', 'words':'utani hur', 'min_level':8, 'mana':35, 'cooldown':24, 'kind':'haste', 'description':'Zwiększa szybkość ruchu o 30% na 15 sekund.'},
}
for cls,names in {
    'knight': [('whirl','Wir ostrzy','exori','sword'),('fury','Furia rycerza','exori gran','sword')],
    'paladin': [('volley','Salwa strzał','exevo mas san','piercing_arrow'),('sunburst','Słoneczna salwa','exevo gran mas san','piercing_arrow')],
    'mage': [('flame_wave','Fala ognia','exevo flam hur','fire_ring'),('inferno','Wielkie piekło','exevo gran mas flam','fire_ring')],
    'druid': [('ice_wave','Fala lodu','exevo frigo hur','ice_ring'),('winter','Wieczna zima','exevo gran mas frigo','ice_ring')],
}.items():
    for i,(key,name,words,effect) in enumerate(names):
        SPELLS[key] = {'name':name,'words':words,'min_level':30 if i==0 else 80,
            'mana':60 if i==0 else 150,'cooldown':8 if i==0 else 16,'kind':'area',
            'class_ids':[cls],'promotion':True,'effect':effect,
            'radius':160 if cls=='knight' else 280, 'multiplier':2.4 if i==0 else 4.5,
            'description':('Uderza pobliskie potwory. ' if cls=='knight' else 'Uderza potwory w obszarze. ')+('Spowalnia je na 4 sekundy.' if cls=='druid' else 'Nie trafia przez ściany ani między piętrami.')}
RUNES = {
    'fire': {'name':'Runa ognistej kuli','min_level':12,'price':35,'mana':70,'soul':4,'effect':'fire_ring','radius':180,'power':1.5},
    'ice': {'name':'Runa lodowej burzy','min_level':30,'price':80,'mana':120,'soul':7,'effect':'ice_ring','radius':220,'power':2.1},
    'death': {'name':'Runa nagłej śmierci','min_level':60,'price':180,'mana':220,'soul':12,'effect':'magic_bolt','radius':0,'power':4.2},
}
TIER_LEVELS = {1:1,2:3,3:8,4:20,5:35,6:50,7:70,8:90,9:110}


def configure(items, zones, npcs, landmarks, quests, enemies, obstacles, merchant):
    # References to authoritative catalogues, also used by progression.py.
    global ITEMS, NPCS, LANDMARKS, ENEMIES
    ITEMS, NPCS, LANDMARKS, ENEMIES = items, npcs, landmarks, enemies
    definitions = [
      ('Marchie Przystani','meadow',1,8,'#7dad50',['rat','wolf','goblin']),
      ('Bory Szeptów','forest',6,12,'#558650',['troll','bandit','wolf']),
      ('Wyżyna Orków','orc',12,20,'#a08d50',['orc','orc_shaman','troll']),
      ('Złote Wybrzeże','desert',20,35,'#d7bd77',['scarab','minotaur','bandit']),
      ('Wydmy Zapomnianych','desert',30,45,'#c5a264',['mummy','scarab','minotaur']),
      ('Bagna Trzcin','swamp',8,16,'#608f7e',['crocodile','spider','troll']),
      ('Zielona Dolina','forest',12,22,'#6c9e66',['elf','bandit','orc']),
      ('Cmentarz Królów','ruins',25,40,'#8d9a8b',['vampire','necromancer','skeleton']),
      ('Pustynne Grobowce','desert',35,55,'#ab946e',['mummy','necromancer','golem']),
      ('Wulkaniczne Pustkowia','lava',50,70,'#9c6854',['fire_elemental','dragon','golem']),
      ('Równiny Minotaurów','meadow',16,28,'#8f9f54',['minotaur','orc_shaman','bandit']),
      ('Góry Żelaznego Serca','mountain',25,40,'#85928d',['dwarf','golem','minotaur']),
      ('Śnieżna Granica','snow',40,60,'#afcbd1',['frost_wolf','ice_elemental','golem']),
      ('Kraina Lodowej Korony','snow',60,85,'#cedde1',['ice_elemental','frost_giant','frost_wolf']),
      ('Smocze Urwiska','mountain',75,100,'#998477',['dragon','dragon_lord','frost_giant']),
      ('Miasto Pod Korzeniami','ruins',35,50,'#789484',['necromancer','vampire','elf']),
      ('Królestwo Bez Słońca','ruins',50,70,'#77758e',['lich','vampire','nightmare']),
      ('Rozdarcie Demonów','lava',70,95,'#8d625f',['demon','fire_elemental','nightmare']),
      ('Obsydianowy Bastion','obsidian',90,120,'#655d79',['demon','dragon_lord','ancient_guardian']),
      ('Morze Popiołu','obsidian',110,150,'#796878',['ancient_guardian','abyss_walker','demon']),
    ]
    for i,(name,biome,low,high,color,kinds) in enumerate(definitions):
        x,y=(i%5)*3200,(i//5)*2304
        r={'id':f'region_{i}','name':name,'x':x,'y':y,'w':3200,'h':2304,
           'floor':0,'biome':biome,'color':color,'min_level':low,'max_level':high,'kinds':kinds}
        REGIONS.append(r)
        if i: zones.append(dict(r))
    # Four distant hubs, with the original town unchanged.
    for ident,name,x,y,region in [('przystan','Przystań',560,1180,0),
      ('brzezina','Brzezina',4000,3456,6),('zloty_port','Złoty Port',10400,1152,3),
      ('mrozna_przystan','Mroźna Przystań',10400,5760,13),('popielny_port','Popielny Port',13600,8064,19)]:
        city={'id':ident,'name':name,'x':x,'y':y,'floor':0,'radius':260,'region_id':f'region_{region}'}
        CITIES.append(city)
        landmarks.append({**city,'id':f'city_{ident}','radius':120,'biome':'town',
            'description':f'{name}: świątynia, kupiec, bank, depozyt i kapitan. Statki kursują między wszystkimi pięcioma miastami.', 'reward':{'xp':20,'gold':10}})
        if ident!='przystan':
            zones.append({**city,'id':f'town_{ident}','x':x-290,'y':y-270,'w':580,'h':540,'color':'#b0ad87'})
            for dx,dy in [(-220,-190),(120,-195),(-230,135),(135,145)]:
                obstacles.append({'x':x+dx,'y':y+dy,'w':100,'h':76,'floor':0,'type':'house'})
            npcs.append({'id':f'merchant_{ident}','name':f'Kupiec · {name}','role':'Kupiec','service':'merchant','city_id':ident,'x':x+120,'y':y,'radius':150,'floor':0,'prices':merchant['prices']})
        for service,label,dx,dy in [('captain','Kapitan',-90,120),('bank','Bankier',-120,-15),('master','Mistrz profesji',50,-160)]:
            npcs.append({'id':f'{service}_{ident}','name':f'{label} · {name}','role':label,'service':service,'city_id':ident,'x':x+dx,'y':y+dy,'radius':125,'floor':0})
        for yoff in (-1,1):
            ROADS.append([[x,y],[x,region//5*2304+1152],[region%5*3200+1600,region//5*2304+1152]])
    for row in range(4): ROADS.append([[0,row*2304+1152],[WIDTH,row*2304+1152]])
    for col in range(5): ROADS.append([[col*3200+1600,2304 if col==0 else 0],[col*3200+1600,HEIGHT]])
    specs = [
      ('troll','Troll leśny',7,'goblin','#74985a'),('bandit','Rozbójnik',10,'goblin','#af795d'),
      ('orc','Ork wojownik',15,'goblin','#4e9b59'),('orc_shaman','Ork szaman',20,'wisp','#a0c174'),
      ('crocodile','Krokodyl bagienny',12,'wolf','#61935c'),('elf','Elf łowca',18,'goblin','#87c5a0'),
      ('minotaur','Minotaur',25,'guardian','#ba926c'),('scarab','Złoty skarabeusz',28,'spider','#d5b347'),
      ('mummy','Mumia',35,'skeleton','#d5bd8e'),('vampire','Wampir',40,'goblin','#b781a8'),
      ('necromancer','Nekromanta',40,'skeleton','#a281b9'),('dwarf','Krasnoludzki strażnik',30,'guardian','#cd986b'),
      ('golem','Żelazny golem',45,'guardian','#a7b8b5'),('frost_wolf','Wilk polarny',42,'wolf','#d8edf0'),
      ('ice_elemental','Żywiołak lodu',60,'wisp','#9ee7f7'),('fire_elemental','Żywiołak ognia',55,'wisp','#ffad63'),
      ('dragon','Smok',65,'dragon','#71b960'),('frost_giant','Lodowy olbrzym',78,'guardian','#a3cbe0'),
      ('lich','Licz',70,'skeleton','#b993df'),('nightmare','Koszmar',80,'wolf','#9c81c7'),
      ('dragon_lord','Smoczy władca',95,'dragon','#e68761'),('demon','Demon',100,'demon','#d67876'),
      ('ancient_guardian','Pradawny strażnik',120,'guardian','#c3b48c'),('abyss_walker','Wędrowiec Otchłani',140,'demon','#aa8ee2')]
    for key,name,level,appearance,color in specs:
        enemies[key]={'name':name,'hp':round(50+14*level+.10*level*level),
          'damage':round(7+level*1.12),'range':170 if appearance=='wisp' or key in ('elf','necromancer','lich') else 65,
          'speed':min(112,60+level*.4),'xp':round(20+level*5),'gold':round(5+level*1.5),
          'respawn':35+level//2,'aggro':200,'leash':330,'level':level,'tier':max(t for t,l in TIER_LEVELS.items() if l<=level),
          'appearance':appearance,'color':color}
    bosses=[('orc_king','Król Orków',28,'goblin','#d2b267'),('sand_queen','Królowa Piasków',50,'spider','#ecd375'),
      ('lich_king','Król Nieumarłych',75,'skeleton','#b8a2e0'),('ice_queen','Królowa Lodu',95,'wisp','#c1f5ff'),
      ('ancient_dragon','Pradawny Smok',110,'dragon','#efa066'),('abyss_lord','Władca Otchłani',150,'demon','#d094f5')]
    for key,name,level,appearance,color in bosses:
        enemies[key]={'name':name,'hp':level*90,'damage':level*1.6,'range':100,'speed':55,'xp':level*45,'gold':level*12,
          'respawn':180,'aggro':300,'leash':530,'level':level,'tier':max(t for t,l in TIER_LEVELS.items() if l<=level),
          'appearance':appearance,'color':color,'boss':True}
    for cls,noun in [('knight','Miecz'),('paladin','Łuk'),('mage','Kostur'),('druid','Laska')]:
        for tier,adj,damage,value in [(4,'weterana',23,150),(5,'runiczny',38,280),(6,'żywiołów',60,500),(7,'królewski',90,850),(8,'pradawny',125,1400),(9,'otchłani',170,2200)]:
            items[f'{cls}_weapon_{tier}']={**items[f'{cls}_weapon_3'],'name':f'{noun} {adj}',
              'attack':damage,'min_level':TIER_LEVELS[tier],'value':value,'rarity':'epic' if tier>=6 else 'rare'}
    for tier in range(4,10):
        items[f'armor_{tier}']={**items['scale'],'name':f'Pancerz { ["weterana","runiczny","żywiołów","królewski","pradawny","otchłani"][tier-4]}',
          'armor':[11,18,28,40,54,70][tier-4],'min_level':TIER_LEVELS[tier],'value':tier*tier*14,'rarity':'epic' if tier>=6 else 'rare'}
        items[f'ring_{tier}']={**items['hunter_ring'],'name':f'Pierścień kręgu {tier}', 'attack':tier*3,'armor':tier-1,
          'min_level':TIER_LEVELS[tier],'value':tier*tier*9,'rarity':'epic' if tier>=6 else 'rare'}
    rng=random.Random(40421)
    for i,r in enumerate(REGIONS[1:],1):
        x,y=r['x'],r['y']
        for j,(dx,dy) in enumerate([(900,520),(2480,1740)]):
            landmarks.append({'id':f'land_{i}_{j}','name':f'{r["name"]} · '+('Stary obóz' if j==0 else 'Kamienny krąg'),
              'x':x+dx,'y':y+dy,'floor':0,'radius':95,'biome':r['biome'],'recommended_level':r['min_level'],
              'description':f'Łowisko poziomów {r["min_level"]}–{r["max_level"]}. Droga prowadzi do sąsiednich krain. Wrogowie: '+', '.join(enemies[k]['name'] for k in r['kinds'])+'.',
              'reward':{'xp':30+r['min_level']*2,'gold':10+r['min_level']//2}})
        for gy in (330,710,1570,1970):
            for gx in (300,700,1100,2090,2510,2860):
                px,py=x+gx+rng.randint(-65,65),y+gy+rng.randint(-65,65)
                if any(math.hypot(px-c['x'],py-c['y'])<600 for c in CITIES):continue
                SPAWNS.append((rng.choice(r['kinds']),px,py,0))
        # Sparse, real blocking groves / rock outcrops; main roads and POIs are clear.
        for dx,dy in [(1800,360),(420,1830),(2770,850)]:
            if any(math.hypot(x+dx-c['x'],y+dy-c['y'])<520 for c in CITIES):continue
            obstacles.append({'x':x+dx,'y':y+dy,'w':100,'h':80,'floor':0,'type':'grove' if r['biome'] in ('forest','meadow') else 'rock'})
        low=r['min_level']; target=r['kinds'][0]
        giver=min(CITIES,key=lambda c:math.hypot(c['x']-(x+1600),c['y']-(y+1152)))
        quests.append({'id':f'hunt_{i}','title':f'Łowcy: {r["name"]}','description':f'Odkryj obóz i pokonaj 12 przeciwników: {enemies[target]["name"]}.',
          'npc_id':f'master_{giver["id"]}','requires':[],'min_level':low,
          'objectives':[{'type':'discover','target':f'land_{i}_0','label':'Odkryj stary obóz','required':1,'x':x+900,'y':y+520,'floor':0},
                        {'type':'kill','target':target,'label':enemies[target]['name'],'required':12,'x':x+700,'y':y+710,'floor':0}],
          'reward':{'xp':low*60,'gold':low*20,'item':f'class_weapon_{max(t for t,l in TIER_LEVELS.items() if l<=low)}'}})
    # Ten accessible dungeons, each with two floors, connected rooms and a return stair.
    sites=[(0,1000,2010,'Kopalnia Pod Młynem','rat','goblin',None),
      (1,2300,450,'Groty Trolli','troll','orc',None),(2,2400,1800,'Twierdza Orków','orc','orc_shaman','orc_king'),
      (4,2200,550,'Piramida Słońca','scarab','mummy','sand_queen'),
      (7,2300,500,'Krypty Królów','vampire','necromancer','lich_king'),
      (11,2350,500,'Głębokie Kopalnie','dwarf','golem',None),
      (13,2200,1800,'Pałac Lodu','ice_elemental','frost_giant','ice_queen'),
      (14,2300,450,'Gniazdo Pradawnego','dragon','dragon_lord','ancient_dragon'),
      (17,2400,1800,'Otchłań Demonów','demon','nightmare',None),
      (19,2250,450,'Serce Otchłani','ancient_guardian','abyss_walker','abyss_lord')]
    for i,dx,dy,name,weak,strong,boss in sites:
        r=REGIONS[i];x,y=r['x']+dx,r['y']+dy
        def stair(sid,label,sx,sy,floor,tx,ty,to_floor,level=1):
            STAIRS.append({'id':sid,'name':label,'x':sx,'y':sy,'floor':floor,'to_x':tx,'to_y':ty,'to_floor':to_floor,'radius':80,'min_level':level})
        stair(f'down_{i}',f'{name} · zejście',x,y,0,x,y,-1)
        stair(f'up_{i}',f'{name} · wyjście',x,y,-1,x,y+85,0)
        for floor in (-1,-2):
            # Rooms joined by a 120px corridor, no fake traversable walls.
            rooms=[{'x':x-130,'y':y-150,'w':380,'h':360},{'x':x+240,'y':y-50,'w':160,'h':120},
                   {'x':x+360,'y':y-180,'w':400,'h':440}]
            DUNGEONS.append({'id':f'dungeon_{i}_{floor}','name':name,'floor':floor,'rooms':rooms,'x':x-130,'y':y-180,'w':890,'h':440,'color':'#666479' if floor==-2 else '#898170'})
            zones.append({**DUNGEONS[-1],'min_level':r['min_level']+(5 if floor==-2 else 0),'max_level':r['max_level']+10})
            for j,(ox,oy) in enumerate([(110,50),(460,-90),(630,30),(510,160)]):
                SPAWNS.append((weak if floor==-1 else strong,x+ox,y+oy,floor))
            landmarks.append({'id':f'delve_{i}_{floor}','name':f'{name} · piętro {abs(floor)}','x':x+520,'y':y+40,'floor':floor,'radius':100,'biome':'dungeon',
              'description':'Połączone komnaty i odradzający się przeciwnicy. Wracasz tą samą drogą; schody obsługujesz pod E.',
              'reward':{'xp':80+r['min_level']*4,'gold':25+r['min_level']}})
        stair(f'deep_{i}',f'{name} · głębiej',x+680,y+190,-1,x+10,y,-2,100 if i==19 else 1)
        stair(f'return_{i}',f'{name} · wyżej',x,y,-2,x+660,y+95,-1)
        if boss:
            SPAWNS.append((boss,x+630,y+120,-2))
            giver=min(CITIES,key=lambda c:math.hypot(c['x']-x,c['y']-y))
            quests.append({'id':f'contract_{boss}','title':f'Kontrakt: {enemies[boss]["name"]}',
              'description':f'Wyprawa do {name}, drugie piętro pod ziemią. Wróć do mistrza po nagrodę. Boss odradza się co 180 sekund.',
              'npc_id':f'master_{giver["id"]}','requires':[],'min_level':max(60,enemies[boss]['level']-20),
              'objectives':[{'type':'kill','target':boss,'label':enemies[boss]['name'],'required':1,'x':x+630,'y':y+120,'floor':-2}],
              'reward':{'xp':enemies[boss]['level']*90,'gold':enemies[boss]['level']*25,'item':f'class_weapon_{enemies[boss]["tier"]}'}})


def expand_wilderness(zones, npcs, landmarks, obstacles):
    """Expand distances, keeping settlement and dungeon geometry human-sized.

    Town streets do not become kilometres wide. Original 0.3 coordinates remain
    valid. Wilderness is populated by deterministic clusters, indexed by server.
    """
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = 128000, 92160
    old_cities={c['id']:(c['x'],c['y']) for c in CITIES}
    def continent(x,y):
        if x<3200 and y<2304:return x,y
        return x*8,y*10
    for r in REGIONS:
        r['x']*=8;r['y']*=10;r['w']=25600;r['h']=23040
    for c in CITIES:c['x'],c['y']=continent(c['x'],c['y'])
    for n in npcs:
        if n['id']=='captain_przystan':n['x'],n['y']=560,1390
        if n.get('city_id'):
            old=old_cities[n['city_id']];city=next(c for c in CITIES if c['id']==n['city_id'])
            n['x'],n['y']=city['x']+n['x']-old[0],city['y']+n['y']-old[1]
    shifts={}
    for s in STAIRS:
        index=int(s['id'].split('_')[-1])
        if s['id'].startswith('down_'):
            nx,ny=continent(s['x'],s['y']);shifts[index]=(nx-s['x'],ny-s['y'])
    for s in STAIRS:
        dx,dy=shifts[int(s['id'].split('_')[-1])]
        s['x']+=dx;s['y']+=dy;s['to_x']+=dx;s['to_y']+=dy
    for d in DUNGEONS:
        dx,dy=shifts[int(d['id'].split('_')[1])];d['x']+=dx;d['y']+=dy
        for room in d['rooms']:room['x']+=dx;room['y']+=dy
    for z in zones:
        ident=z['id']
        if ident.startswith('region_'):
            z.update(REGIONS[int(ident.split('_')[1])])
        elif ident.startswith('town_'):
            city=next(c for c in CITIES if c['id']==ident[5:]);z['x'],z['y']=city['x']-290,city['y']-270
        elif ident.startswith('dungeon_'):
            d=next(d for d in DUNGEONS if d['id']==ident);z.update(d)
    for o in obstacles:
        old=next(((ident,xy) for ident,xy in old_cities.items() if ident!='przystan' and math.hypot(o['x']-xy[0],o['y']-xy[1])<420),None)
        if old:
            city=next(c for c in CITIES if c['id']==old[0]);o['x']+=city['x']-old[1][0];o['y']+=city['y']-old[1][1]
        else:o['x'],o['y']=continent(o['x'],o['y'])
    for l in landmarks:
        if l['id'].startswith('delve_'):
            dx,dy=shifts[int(l['id'].split('_')[1])];l['x']+=dx;l['y']+=dy
        elif l['id'].startswith('city_'):
            city=next(c for c in CITIES if c['id']==l['id'][5:]);l['x'],l['y']=city['x'],city['y']
        else:l['x'],l['y']=continent(l['x'],l['y'])
    for q in QUESTS_REF:
        for o in q['objectives']:
            if o.get('floor',0)<0:
                # Boss objective shares its dungeon centre shift.
                index=next(int(s['id'].split('_')[-1]) for s in STAIRS if s['id'].startswith('down_') and q['id']=='contract_'+BOSS_FOR_DUNGEON.get(int(s['id'].split('_')[-1]),''))
                dx,dy=shifts[index];o['x']+=dx;o['y']+=dy
            elif 'x' in o:o['x'],o['y']=continent(o['x'],o['y'])
    old=list(SPAWNS);SPAWNS.clear()
    for kind,x,y,floor in old:
        if floor<0:
            index=next(i for i in shifts if any(d['id']==f'dungeon_{i}_{floor}' and d['x']-shifts[i][0]<=x<=d['x']-shifts[i][0]+d['w'] and d['y']-shifts[i][1]<=y<=d['y']-shifts[i][1]+d['h'] for d in DUNGEONS))
            dx,dy=shifts[index];SPAWNS.append((kind,x+dx,y+dy,floor))
        else:
            nx,ny=continent(x,y);SPAWNS.append((kind,nx,ny,0))
    ROADS.clear()
    for row in range(4):ROADS.append([[0,row*23040+11520],[WIDTH,row*23040+11520]])
    for col in range(5):ROADS.append([[col*25600+12800,0],[col*25600+12800,HEIGHT]])
    for c in CITIES:
        region=next(r for r in REGIONS if r['id']==c['region_id'])
        ROADS.append([[c['x'],c['y']],[c['x'],region['y']+11520],[region['x']+12800,region['y']+11520]])
    rng=random.Random(4041600)
    for ri,r in enumerate(REGIONS):
        kinds=r['kinds'] if ri else ['rat','wolf','goblin','boar']
        for row in range(8):
            for col in range(9):
                x=r['x']+1300+col*2780+rng.randint(-220,220)
                y=r['y']+1300+row*2860+rng.randint(-220,220)
                if ri==0 and x<3400 and y<2500:continue
                if any(math.hypot(x-c['x'],y-c['y'])<900 for c in CITIES):continue
                if any(math.hypot(x-s['x'],y-s['y'])<700 for s in STAIRS if s['floor']==0):continue
                kind=kinds[(row+col)%len(kinds)]
                HUNTING_GROUNDS.append({'x':x,'y':y,'kind':kind,'region_id':r['id'],'floor':0})
                for j in range(5):
                    angle=j*math.tau/5
                    SPAWNS.append((kind,round(x+math.cos(angle)*190),round(y+math.sin(angle)*190),0))
                # Ruined enclosure with two wide entries, and distinct field decoration.
                if (row+col)%3==0:
                    obstacles.extend([{'x':x-300,'y':y-300,'w':120,'h':75,'floor':0,'type':'grove' if r['biome'] in ('forest','meadow') else 'rock'},
                                      {'x':x+230,'y':y+200,'w':100,'h':90,'floor':0,'type':'rock'}])
                if row==2 and col==2 or row==5 and col==6:
                    landmarks.append({'id':f'wild_{ri}_{row}','name':r['name']+(' · Opuszczona strażnica' if row==2 else ' · Zapomniany krąg'),
                       'x':x,'y':y,'floor':0,'radius':100,'biome':r['biome'],
                       'description':f'Daleko od miast. Tutejsze łowiska są przeznaczone na poziomy {r["min_level"]}–{r["max_level"]}. Zaplanuj drogę powrotną i zabierz mikstury.',
                       'reward':{'xp':60+r['min_level']*3,'gold':20+r['min_level']}})
    # Ordinary surface cave entrances are navigable from the regional road grid.
    for s in STAIRS:
        if s['floor']==0:
            ry=int(s['y']//23040)*23040+11520
            ROADS.append([[s['x'],s['y']],[s['x'],ry]])


HUNTING_GROUNDS=[]
QUESTS_REF=[]
BOSS_FOR_DUNGEON={2:'orc_king',4:'sand_queen',7:'lich_king',13:'ice_queen',14:'ancient_dragon',19:'abyss_lord'}
