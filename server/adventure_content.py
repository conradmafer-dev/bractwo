"""UI_19 authored expeditions, local stories and SRD 5.2.1 creatures.

Call after continent_world.configure and all legacy monster/loot configuration,
before discovery_rules.configure. All new IDs are prefixed ``adv_``. Existing
lists are append-only, including SPAWNS whose indices are live monster IDs.
Creature statistics: official SRD 5.2.1, pp. 259, 286, 295, 344 and 349.
https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf
"""
from copy import deepcopy
import math

ATTRIBUTES=('strength','dexterity','constitution','intelligence','wisdom','charisma')
MONSTERS={
    'adv_giant_bat':dict(name='Olbrzymi nietoperz',english='Giant Bat',source='wolf',level=8,
        hp=22,hp_dice=[4,10,0],ac=13,ab=5,speed=10,fly=60,blindsight=120,cr='1/4',xp=50,
        attributes=[15,16,11,2,12,6],size='large',creature_type='beast',
        attacks=[dict(name='Ugryzienie',dice=[1,6,3],type='piercing')],palette=['#52485d','#ad93b0','#edb892']),
    'adv_flying_sword':dict(name='Ożywiony latający miecz',english='Animated Flying Sword',source='guardian',level=12,
        hp=14,hp_dice=[4,6,0],ac=17,ab=4,speed=5,fly=50,hover=True,blindsight=60,cr='1/4',xp=50,
        attributes=[12,15,11,1,5,1],saves={'dexterity':4},size='small',creature_type='construct',
        immunities=['poison','psychic'],condition_immunities=['charmed','deafened','exhaustion','frightened','paralyzed','petrified','poisoned'],
        attacks=[dict(name='Cięcie',dice=[1,8,2],type='slashing')],palette=['#455d68','#c2dde0','#80e7df']),
    'adv_animated_armor':dict(name='Ożywiona zbroja',english='Animated Armor',source='guardian',level=18,
        hp=33,hp_dice=[6,8,6],ac=18,ab=4,speed=25,blindsight=60,cr='1',xp=200,
        attributes=[14,11,13,1,3,1],size='medium',creature_type='construct',
        immunities=['poison','psychic'],condition_immunities=['charmed','deafened','exhaustion','frightened','paralyzed','petrified','poisoned'],
        attacks=[dict(name='Uderzenie',dice=[1,6,2],type='bludgeoning')]*2,palette=['#40515a','#a3b8ba','#68d1bd']),
    'adv_gargoyle':dict(name='Gargulec',english='Gargoyle',source='guardian',level=25,
        hp=67,hp_dice=[9,8,27],ac=15,ab=4,speed=30,fly=60,flyby=True,darkvision=60,cr='2',xp=450,
        attributes=[15,11,16,6,11,7],size='medium',creature_type='elemental',
        immunities=['poison'],condition_immunities=['exhaustion','petrified','poisoned'],
        attacks=[dict(name='Pazury',dice=[2,4,2],type='slashing')]*2,palette=['#5b6665','#abb3a6','#cae6ac']),
    'adv_grick':dict(name='Grick',english='Grick',source='spider',level=22,
        hp=54,hp_dice=[12,8,0],ac=14,ab=4,speed=30,climb=30,darkvision=60,cr='2',xp=450,
        attributes=[14,14,11,3,14,5],size='medium',creature_type='aberration',
        attacks=[dict(name='Dziób',dice=[2,6,2],type='piercing'),dict(name='Macki',dice=[1,10,2],type='slashing',grapple_dc=12)],
        palette=['#514f43','#96927b','#d5b477']),
    'adv_ogre_zombie':dict(name='Zombie ogra',english='Ogre Zombie',source='ogre',level=25,
        hp=85,hp_dice=[9,10,36],ac=8,ab=6,speed=30,darkvision=60,cr='2',xp=450,
        attributes=[19,6,18,3,6,5],saves={'wisdom':0},size='large',creature_type='undead',undead_fortitude=True,
        immunities=['poison'],condition_immunities=['exhaustion','poisoned'],
        attacks=[dict(name='Uderzenie',dice=[2,8,4],type='bludgeoning')],palette=['#596949','#a4ad7e','#dac2a0']),
}

# The continent owns these locations and clears their approaches before this pass.
DEFAULT_ANCHORS={
    'starter_ruins':(8400,5600,8),'forest_shrine':(34300,33500,18),
    'royal_catacombs':(60200,35400,32),'dune_observatory':(114000,11500,42),
    'volcanic_fissure':(116000,33800,60),'frost_hollow':(88400,56100,75),
    'dragon_watch':(116500,56600,90),'obsidian_archive':(87800,80100,110),
}
SITES={
    'starter_ruins':dict(name='Piwnice Złamanego Dzwonu',biome='ruins',floors=[-10],theme='cellar',
        mobs=['adv_giant_bat','adv_flying_sword'],rooms=['Przedsionek dzwonnika','Skład starych lin','Sala bez dzwonu'],
        description='Pod zawaloną dzwonnicą zostały narzędzia jej ostatnich opiekunów.'),
    'forest_shrine':dict(name='Jaskinie Szeptającego Korzenia',biome='forest',floors=[-19,-20,-21,-22],theme='cave',
        mobs=['adv_giant_bat','adv_grick'],rooms=['Studnia korzeni','Podziemne jezioro','Komora ślepych ech','Serce starego korzenia'],
        description='Cztery połączone głębokości: rozwidlenia, boczne komory i kamienne mostki między korzeniami.'),
    'royal_catacombs':dict(name='Katakumby Siedmiu Imion',biome='ruins',floors=[-16,-17,-18],theme='catacomb',
        mobs=['adv_animated_armor','adv_ogre_zombie','adv_flying_sword'],rooms=['Krużganek pamięci','Galeria chorągwi','Nekropolia bez króla'],
        description='Rozległe katakumby o trzech poziomach. Boczny krużganek łączy kaplice z główną nawą.'),
    'dune_observatory':dict(name='Komnata Zagubionego Południka',biome='desert',floors=[-11],theme='observatory',
        mobs=['adv_flying_sword','adv_gargoyle'],rooms=['Schody piasku','Sala soczewek','Kamienny południk'],
        description='Dawni astronomowie przechowali ostatnią mapę nieba pod wydmą.'),
    'volcanic_fissure':dict(name='Sztolnia Czerwonego Oddechu',biome='lava',floors=[-12],theme='mine',
        mobs=['adv_animated_armor','fire_elemental'],rooms=['Szlak kilofów','Pęknięty piec','Ostatnia komora górników'],
        description='Pęknięta sztolnia kryje ślady załogi, która przed laty zamknęła podziemny piec.'),
    'frost_hollow':dict(name='Schronisko pod Lodowym Łukiem',biome='snow',floors=[-13],theme='ice',
        mobs=['adv_gargoyle','frost_wolf'],rooms=['Zasypany korytarz','Izba straży','Izba ostatniego ognia'],
        description='W lodzie zachowały się drogowskazy i schronienie dawnej wyprawy ratunkowej.'),
    'dragon_watch':dict(name='Krypta Strażników Grani',biome='mountain',floors=[-14],theme='watch',
        mobs=['adv_gargoyle','dragon'],rooms=['Próg strażników','Pęknięta przysięga','Komnata kamiennego oka'],
        description='Strażnica obserwowała smocze szczyty. Jej dokumenty ukryto poniżej skalnego gniazda.'),
    'obsidian_archive':dict(name='Archiwum Wygaszonych Pieczęci',biome='obsidian',floors=[-15],theme='archive',
        mobs=['adv_animated_armor','adv_ogre_zombie','obsidian_knight'],rooms=['Rejestr przybyszów','Aleja czarnych ksiąg','Sala wygaszonej pieczęci'],
        description='Kamienne regały przechowują imiona ludzi wymazanych z kronik pogranicza.'),
}

# id, site, name, role, relative position, greeting, two distinct conversation topics.
NPC_DATA=[
 ('nela','starter_ruins','Nela Dzwonniczka','Pamięć dawnej wieży',(-150,150),
  'Dzwon zamilkł, ale nocą nadal drżą liny. Nie szukam bohatera do legendy. Szukam kogoś, kto sprawdzi, co zostało pod schodami.',
  [('dzwon','Co stało się z dzwonem?','Pękł w noc ewakuacji. Ojciec przeciął linę, żeby kamień nie runął na uchodźców. Potem ktoś zamknął dolne drzwi od środka.'),('droga','Jak bezpiecznie zejść?','Pierwsza komora jest spokojniejsza. Za regałem zaczyna się kolonia nietoperzy. Metaliczny świst oznacza, że strażnicy nadal działają.')]),
 ('tymon','starter_ruins','Tymon Powroźnik','Rzemieślnik w drodze',(-290,270),
  'Nie każdy porzucony przedmiot jest skarbem. Czasem to jedyny ślad po czyjejś ostatniej robocie.',
  [('liny','Czy rozpoznasz stare liny?','Rozpoznam węzeł mojego mistrza. Wiązał dodatkową pętlę tam, gdzie inni oszczędzali konopie. Na pewno zostawił znak w składzie.'),('nela','Dlaczego pomagasz Neli?','Jej ojciec ocalił mój warsztat. Długów wobec zmarłych nie spłaca się złotem. Można za to pomóc tym, którzy zostali.')]),
 ('bera','forest_shrine','Bera Zbieraczka','Opiekunka leśnych źródeł',(-160,190),
  'Woda z korzeni smakuje teraz kamieniem. Jaskinie nie są złe, lecz coś przerwało ich dawny rytm.',
  [('woda','Skąd płynie źródło?','Z jeziora na drugim poziomie. Korzenie prowadzą dalej do serca lasu. Omijaj gardziele, w których echo wraca zbyt szybko.'),('grick','Co kryje się w ciemności?','Gricki wyglądają jak kawałek mokrej skały, dopóki nie otworzą macek. Ich chwyt da się zerwać; nie próbuj przebiec przez nie z zablokowanymi nogami.')]),
 ('jaro','forest_shrine','Jaro Mierniczy','Badacz podziemnych przejść',(-320,310),
  'Zaznaczyłem trzy powroty i jedno wyjście. Czwarty poziom wciąż pozostaje białą plamą na mojej mapie.',
  [('mapa','Czy te korytarze mają koniec?','Mają. Boczne pętle wracają do głównej drogi, a schody są oznaczone tym samym kamieniem. Najgłębsze zejście znajdziesz za komorą ech.'),('znaki','Co oznaczają nacięcia?','Jedno nacięcie prowadzi ku powierzchni. Dwa wskazują zejście. Stare znaki na korzeniach opisują wodę, a nie drogę — łatwo je pomylić.')]),
 ('matylda','royal_catacombs','Matylda Kronikarka','Strażniczka siedmiu imion',(-150,160),
  'Każdy nagrobek ma imię. Jeśli go nie odczytamy, za sto lat pozostanie tylko mur.',
  [('imiona','Kim było siedmioro?','Nie królewskim rodem. To siedmioro ludzi, którzy otworzyli bramy podczas wielkiego pożaru. Późniejsi władcy przywłaszczyli ich kryptę.'),('zbroje','Dlaczego zbroje atakują?','Strzegą pieczęci, nie właścicieli grobów. Nie myślą i nie czują strachu. Ich puste przyłbice nie potrzebują światła.')]),
 ('idzi','royal_catacombs','Brat Idzi','Latarnik nekropolii',(-290,285),
  'Zapalam te lampy nie dla umarłych, tylko dla ludzi, którzy chcą wrócić na górę.',
  [('ogry','Co jest na dole?','Ogry pracowały tu jako tragarze. Ktoś obudził ich ciała bez zgody dusz. Promienisty cios albo dokładne trafienie powstrzymuje ich uparty powrót.'),('lampy','Jak rozpoznać drogę powrotną?','Schody mają dwie lampy. Kaplice jedną. Jeśli widzisz trzy, dotarłeś do dawnego miejsca pożegnania, a nie do wyjścia.')]),
 ('faris','dune_observatory','Faris Astrolabista','Badacz pustynnego nieba',(-180,190),
  'Wydma przesunęła się o sto kroków, lecz południk pod nią nadal wskazuje to samo niebo.',
  [('niebo','Po co komu stare obserwatorium?','Kierunki nie kończą się wraz z drogą. Dawna soczewka pozwalała wyznaczyć przejścia przez pustynię, gdy wiatr usuwał ślady.'),('szczyt','Co jest na wzgórzu?','Kamienny pierścień służył do porównywania cienia z gwiazdami. Schody widać po prawej od wejścia do komnaty.')]),
 ('pola','volcanic_fissure','Pola Żużelniczka','Ostatnia dziedziczka sztolni',(-170,170),
  'Mój dziadek zamknął piec i wrócił sam. Przez całe życie mówił, że reszta załogi wybrała inną drogę. Chcę poznać prawdę.',
  [('piec','Dlaczego piec wciąż świeci?','Ogień nie jest zwykłym paleniskiem. Nie dolewaj niczego do szczeliny i nie ufaj pancerzom stojącym przy ścianie.'),('zaloganci','Czego szukasz w sztolni?','Tablicy zmian. Górnicy ryli na niej nazwiska, zanim zeszli pod ziemię. Kamień powinien przetrwać to, czego nie przetrzymał papier.')]),
 ('wera','frost_hollow','Wera Zimny Szlak','Przewodniczka po lodowej wyspie',(-180,170),
  'Nie ścigaj wilka w zamieci. Najpierw znajdź schronienie, potem dowiedz się, dokąd prowadzą jego ślady.',
  [('schronienie','Czy ktoś jeszcze tu mieszka?','W schronisku zostały ławy i resztki opału. Ostatnia wyprawa oznaczyła drogę na wzgórze, zanim śnieg zakrył ich obóz.'),('gargulce','Czy rzeźby są bezpieczne?','Nie. Gargulce mają skrzydła i potrafią oderwać się od skały. Trucizna nie ruszy ich kamiennego ciała.')]),
 ('oskar','dragon_watch','Oskar Strażnik Grani','Dziedzic opuszczonej strażnicy',(-170,170),
  'Smoki nie potrzebują murów. To ludzie budują wieże, żeby poczuć się więksi od własnego strachu.',
  [('przysiega','Co obiecywali strażnicy?','Obserwować i ostrzegać, nie prowokować. Przysięga zniknęła, gdy młody dowódca zapragnął pierwszej łuski na tarczy.'),('gran','Jak dotrzeć na grań?','Dwa tarasy nad wejściem prowadzą do kamiennego oka. Krypta leży niżej. Każda droga ma schody powrotne.')]),
 ('ada','obsidian_archive','Ada Archiwistka','Poszukiwaczka wymazanych zapisów',(-150,150),
  'Czarne księgi nie są przeklęte. Przeklęci byli ludzie, którzy zdecydowali, czyje imiona z nich wytrzeć.',
  [('archiwum','Dlaczego zbudowano je tak daleko?','Żeby nikt nie zadawał pytań. Ochronę powierzono pancerzom, a dokumenty zamieniono w kamienne tablice.'),('pieczec','Czym jest wygaszona pieczęć?','Śladem po zamkniętym przejściu. Nie próbujemy go otworzyć — chcemy odczytać listę ludzi, którzy przez nie nie wrócili.')]),
 ('eryk','obsidian_archive','Eryk Bez Herbu','Były strażnik archiwum',(-310,280),
  'Kiedyś mówiłem przybyszom, że nie mają prawa wejść. Teraz mogę przynajmniej wskazać im właściwe drzwi.',
  [('sluzba','Dlaczego porzuciłeś straż?','Zobaczyłem nazwisko siostry na liście, którą kazano spalić. Nie była zdrajczynią. Była kartografką.'),('obrona','Co zatrzyma dawną straż?','Ożywione zbroje nie ustąpią przed strachem ani trucizną. Zwykły plan, dobra pozycja i droga odwrotu są bardziej użyteczne niż krzyk.')]),
]


def configure_monsters(enemies):
    for key,data in MONSTERS.items():
        spec=deepcopy(enemies[data['source']]);attacks=deepcopy(data['attacks']);first=attacks[0]
        attrs=dict(zip(ATTRIBUTES,data['attributes']));saves={a:(v-10)//2 for a,v in attrs.items()};saves.update(data.get('saves',{}))
        dice=first['dice'];average=dice[0]*(dice[1]+1)/2+dice[2]
        spec.update(name=data['name'],level=data['level'],hp=data['hp'],hp_dice=data['hp_dice'][:],armor_class=data['ac'],
            attack_bonus=data['ab'],damage_dice=dice[:],melee_dice=dice[:],special_dice=dice[:],damage=average,melee_damage=average,
            damage_type=first['type'],speed=data['speed']*100/30,walking_speed_ft=data['speed'],
            attributes=attrs,saves=saves,save_bonus=saves['constitution'],save_dc=12,creature_type=data['creature_type'],
            size=1.28 if data['size']=='large' else .8 if data['size']=='small' else 1.0,creature_size=data['size'],
            boss=False,combat_role='melee',range=32,melee_range=32,attack_interval=3.0,ranged_interval=3.0,
            aggro=330,base_aggro=330,leash=900,wander=90,respawn=60,windup=.4,xp=data['xp'],gold=4+data['level']//2,
            cr=data['cr'],dnd_source='SRD 5.2.1',content_version='UI_19',adventure_attacks=attacks,
            sprite=f'assets/monsters/adventure/{key}.svg',sprite_frame_width=80,sprite_frame_height=80,sprite_frames=4,
            appearance='adventure',color=data['palette'][0],immunities=data.get('immunities',[])[:],resistances=[],
            condition_immunities=data.get('condition_immunities',[])[:],fly=data.get('fly',0),climb=data.get('climb',0),
            hover=data.get('hover',False),blindsight=data.get('blindsight',0),darkvision=data.get('darkvision',0),
            flyby=data.get('flyby',False),undead_fortitude=data.get('undead_fortitude',False))
        spec.pop('projectile',None);spec.pop('special_range',None)
        family='undead' if data['creature_type']=='undead' else 'beast' if data['creature_type']=='beast' else 'stone'
        drops=[dict(kind='item',template='trophy_'+family,chance=.32)]
        if key=='adv_flying_sword':drops.append(dict(kind='item',template='knight_weapon_1',chance=.03))
        if key=='adv_animated_armor':drops.append(dict(kind='item',template='scale',chance=.02))
        if key=='adv_ogre_zombie':drops.append(dict(kind='potion',template='health_potion',chance=.04))
        spec['loot_origin']='Trofea z wyprawy'
        spec['loot']=dict(family=family,tier=1 if data['level']<15 else 2,equipment_chance=0,trophy_chance=0,
                          potion_chance=0,unique_chance=0,legendary_chance=0,entries=drops,independent=True)
        enemies[key]=spec


def _anchor(content,key):
    raw=getattr(content,'ADVENTURE_ANCHORS',{}).get(key,DEFAULT_ANCHORS[key])
    if isinstance(raw,dict):return raw['x'],raw['y'],raw.get('level',raw.get('recommended_level',DEFAULT_ANCHORS[key][2]))
    return tuple(raw[:3])


def _link(content,ident,name,origin,target):
    for suffix,a,b in [('down',origin,target),('up',target,origin)]:
        content.STAIRS.append(dict(id='adv_'+ident+'_'+suffix,name=name,x=a[0],y=a[1],floor=a[2],
            to_x=b[0],to_y=b[1],to_floor=b[2],radius=62,min_level=1))


def _landmark(landmarks,ident,name,x,y,floor,biome,level,description):
    point=dict(id='adv_'+ident,name=name,x=x,y=y,floor=floor,radius=76,biome=biome,
        recommended_level=level,description=description,reward=dict(xp=0,gold=0),adventure=True)
    landmarks.append(point);return point


def _room(x,y,w,h,**extra):return dict(x=x,y=y,w=w,h=h,**extra)


def _layout(x,y,large=False,cave=False,variant=0):
    # Rectangular collision pieces overlap at every doorway. Cave chambers use
    # overlapping unequal rooms rather than a decorative unwalkable polygon.
    if not large:
        chambers=[_room(x-130,y-100,290,270),_room(x+300,y-220,330,310),_room(x+760,y-50,330,320)]
        halls=[_room(x+130,y-15,200,110),_room(x+550,y-75,260,110)]
        return chambers+halls,chambers
    chambers=[_room(x-150,y-130,320,300),_room(x+280,y-260,350,310),_room(x+760,y-140,370,350),
              _room(x+1260,y-240,370,330),_room(x+1260,y+350,380,320),_room(x+750,y+450,350,330),
              _room(x+220,y+380,360,340),_room(x+650,y+970,470,360)]
    halls=[_room(x+140,y-35,175,110),_room(x+595,y-45,205,110),_room(x+1085,y-55,215,110),
           _room(x+1380,y+45,120,350),_room(x+1040,y+500,270,110),_room(x+535,y+500,260,120),
           _room(x+30,y+110,120,420),_room(x+95,y+445,180,120),_room(x+850,y+720,120,300)]
    if cave:
        chambers += [_room(x+370,y+10,260,210),_room(x+1020,y+530,260,210),_room(x+690,y+1060,220,370)]
    return chambers+halls,chambers


def _add_site(content,obstacles,landmarks,zones,key):
    site=SITES[key];x,y,level=_anchor(content,key);large=len(site['floors'])>1
    entry=_landmark(landmarks,key+'_entrance',site['name']+' · wejście',x,y,0,site['biome'],level,site['description'])
    _link(content,key+'_entry',site['name']+' · wejście / powierzchnia',(x,y,0),(x,y,site['floors'][0]))
    points={};floors=site['floors']
    for index,floor in enumerate(floors):
        rooms,chambers=_layout(x,y,large,site['theme']=='cave',index)
        minx=min(r['x'] for r in rooms);miny=min(r['y'] for r in rooms)
        maxx=max(r['x']+r['w'] for r in rooms);maxy=max(r['y']+r['h'] for r in rooms)
        area=dict(id=f'adv_{key}_floor_{abs(floor)}',name=site['name']+' · '+(site['rooms'][index] if large else site['rooms'][0]),
            floor=floor,rooms=rooms,x=minx,y=miny,w=maxx-minx,h=maxy-miny,color={'cave':'#6a7766','ice':'#819caa','mine':'#795f51','archive':'#56535f'}.get(site['theme'],'#837668'),
            min_level=level+index*3,max_level=level+15+index*3,theme=site['theme'],adventure=True,local_depth=index+1)
        content.DUNGEONS.append(area);zones.append(dict(area))
        count=4 if large else 3
        selected=[chambers[0],chambers[2],chambers[4],chambers[7]] if large else chambers
        for n,room in enumerate(selected[:count]):
            px,py=room['x']+room['w']/2,room['y']+room['h']/2
            label=(site['rooms'][index]+' · '+['kamień wejścia','boczna komora','stary znak','najdalsza sala'][n]) if large else site['rooms'][n]
            ident=f'{key}_{index+1}_{n+1}'
            point=_landmark(landmarks,ident,label,px,py,floor,site['biome'],level+index*3,
                site['description']+' Odkrycie tego miejsca zapisuje się w dzienniku podróży.')
            points[(index,n)]=point
        for n,room in enumerate(chambers[1:]):
            if n>7:continue
            kind=site['mobs'][(index+n)%len(site['mobs'])]
            content.SPAWNS.append((kind,room['x']+room['w']*.58,room['y']+room['h']*.58,floor))
            if large and n%2==0:content.SPAWNS.append((site['mobs'][0],room['x']+85,room['y']+room['h']-70,floor))
            # Low props mark rooms but leave the central walking route open.
            obstacles.append(dict(x=room['x']+room['w']-70,y=room['y']+25,w=42,h=32,floor=floor,type='rock' if site['theme']=='cave' else 'ruin',adventure=True))
        if not large:
            # Local kill objectives require two guards; both are initially
            # present, so the longer global respawn never forces a quest wait.
            room=chambers[1]
            content.SPAWNS.append((site['mobs'][0],room['x']+85,room['y']+room['h']-70,floor))
            # The final room can house a guardian as well as its lesser guards.
            # Every declared species must exist, including quest targets.
            present={s[0] for s in content.SPAWNS if s[3]==floor}
            for n,kind in enumerate(k for k in site['mobs'] if k not in present):
                room=chambers[-1]
                content.SPAWNS.append((kind,room['x']+90+n*65,room['y']+room['h']-75,floor))
        last=selected[-1];end=(last['x']+last['w']-65,last['y']+last['h']-65,floor)
        if index+1<len(floors):_link(content,f'{key}_depth_{index+1}',site['name']+f' · poziom {index+1} / {index+2}',end,(x,y,floors[index+1]))
        if index==len(floors)-1:
            cache=dict(points[(index,count-1)],id='adv_'+key+'_cache',name=site['name']+' · skrytka',
                x=last['x']+65,y=last['y']+last['h']-65,action='cache',radius=60,min_level=level,
                description='Skrytka z wyposażeniem. E poza walką; osobiste odnowienie 30 minut.',reward=dict(xp=0,gold=0))
            content.POIS.append(cache);landmarks.append(cache)
    return dict(entry=entry,points=points,site=site,x=x,y=y,level=level)


def _add_hill(content,obstacles,landmarks,zones,key):
    x,y,level=_anchor(content,key);cx,cy=x+420,y-260
    name={'dune_observatory':'Wzgórze Południka','frost_hollow':'Wzgórze Białych Chorągwi','dragon_watch':'Wzgórze Kamiennego Oka'}[key]
    for floor,(w,h) in enumerate([(500,430),(290,245)],1):
        room=_room(cx-w/2,cy-h/2,w,h)
        area=dict(room,id=f'adv_hill_{key}_{floor}',name=name,floor=floor,rooms=[room],color='#a9a898',
            min_level=level,max_level=level+15,adventure=True)
        content.ELEVATIONS.append(area);zones.append(dict(area))
        obstacles.append(dict(room,floor=floor-1,type='terrace',height=floor,site='adv_'+key,adventure=True))
        _link(content,f'hill_{key}_{floor}',name+f' · taras {floor}',
              (cx,cy+h/2+55,floor-1),(cx,cy+h/2-55,floor))
        ledge_y=cy+165 if floor==1 else cy-20
        content.SPAWNS.append(('adv_gargoyle',cx-90,ledge_y,floor))
        _landmark(landmarks,f'hill_{key}_{floor}',name+f' · taras {floor}',cx+75,ledge_y,floor,'mountain',level,
            'Punkt widokowy połączony schodami z niższym tarasem. Powrót prowadzi tym samym szlakiem.')
    content.ROADS.append([[x,y+200],[x+180,y+200],[cx,cy+430/2+55]])


def _npc(npcs,content,row):
    ident,site,name,role,offset,greeting,topics=row;x,y,_=_anchor(content,site)
    entry=dict(id='adv_'+ident,name=name,role=role,x=x+offset[0],y=y+offset[1],floor=0,radius=135,
        dialogue=dict(greeting=greeting,topics=[dict(id=k,title=title,text=text) for k,title,text in topics],
            quest_offer='Porozmawiajmy o wyprawie. Konkretne cele i nagrody znajdziesz poniżej.',
            quest_progress='Wróć, gdy zbierzesz wszystkie wskazane ślady. Dziennik pokaże, czego jeszcze brakuje.',
            quest_complete='Twoja wyprawa coś zmieniła. Zapiszmy to, zanim pamięć znowu ustąpi ciszy.'),
        appearance='traveler',adventure=True,site_id='adv_'+site)
    npcs.append(entry);return entry


def _discover(point,label=None):return dict(type='discover',target=point['id'],label=label or point['name'],required=1,x=point['x'],y=point['y'],floor=point['floor'])
def _kill(content,kind,site,amount):
    x,y,_=_anchor(content,site);floors=SITES[site]['floors']
    candidates=[s for s in content.SPAWNS if s[0]==kind and s[3] in floors]
    target=min(candidates,key=lambda s:math.hypot(s[1]-x,s[2]-y))
    return dict(type='kill',target=kind,label=content.ENEMIES[kind]['name'],required=amount,x=target[1],y=target[2],floor=target[3])


def _quests(content,quests,sites):
    def q(ident,npc,title,text,site,objectives,requires=(),item=None):
        level=sites[site]['level'];reward=dict(xp=90+level*9,gold=35+level*4)
        if item:reward['item']=item
        else:reward['potions']={'health_potion':1}
        quests.append(dict(id='adv_'+ident,npc_id='adv_'+npc,title=title,description=text,
            min_level=1,requires=['adv_'+r for r in requires],objectives=objectives,reward=reward,
            recommended_level=level,adventure=True,site_id='adv_'+site))
    s=sites['starter_ruins'];p=s['points']
    q('bell_1','nela','Dzwon, który nie wrócił','Odkryj zejście i przedsionek dawnej dzwonnicy. Nela chce wiedzieć, czy droga do składu nadal istnieje.','starter_ruins',[_discover(s['entry']),_discover(p[(0,0)])])
    q('bell_2','tymon','Węzeł powroźnika','Odszukaj skład lin i przepędź nietoperze. Tymon rozpozna tam ślady pracy swojego mistrza.','starter_ruins',[_discover(p[(0,1)]),_kill(content,'adv_giant_bat','starter_ruins',2)],['bell_1'])
    q('bell_3','nela','Ostatni znak dzwonnika','Dotrzyj do sali bez dzwonu i pokonaj latający miecz blokujący dalsze przejście. Wróć do Neli z wiadomością.','starter_ruins',[_discover(p[(0,2)]),_kill(content,'adv_flying_sword','starter_ruins',1)],['bell_2'],'ring_swimming')
    s=sites['forest_shrine'];p=s['points']
    q('roots_1','bera','Źródło spod korzeni','Odnajdź podziemne jezioro na drugim poziomie i oczyść przejście z gricków.','forest_shrine',[_discover(p[(1,3)]),_kill(content,'adv_grick','forest_shrine',2)])
    q('roots_2','jaro','Tam, gdzie milknie echo','Zejdź przez komorę ech do czwartego poziomu i odnajdź serce starego korzenia. Jaro dokończy mapę powrotów.','forest_shrine',[_discover(p[(2,3)]),_discover(p[(3,3)])],['roots_1'],'ring_free_action')
    s=sites['royal_catacombs'];p=s['points']
    q('names_1','matylda','Pierwsze z siedmiu imion','Zbadaj boczny krużganek i galerię chorągwi na drugim poziomie katakumb.','royal_catacombs',[_discover(p[(0,1)]),_discover(p[(1,1)])])
    q('names_2','idzi','Lampy dla powracających','Ucisz ożywione pancerze i zombie ogra, które odcinają drogę przez nekropolię.','royal_catacombs',[_kill(content,'adv_animated_armor','royal_catacombs',2),_kill(content,'adv_ogre_zombie','royal_catacombs',1)],['names_1'])
    q('names_3','matylda','Nekropolia bez króla','Odczytaj ślady w bocznej kaplicy i najdalszej sali trzeciego poziomu. Matylda przywróci imiona prawdziwych gospodarzy.','royal_catacombs',[_discover(p[(2,2)]),_discover(p[(2,3)])],['names_2'],'ring_protection')
    s=sites['dune_observatory'];p=s['points']
    q('meridian_1','faris','Soczewka pod piaskiem','Odkryj salę soczewek i usuń latające miecze pilnujące pustego obserwatorium.','dune_observatory',[_discover(p[(0,1)]),_kill(content,'adv_flying_sword','dune_observatory',2)])
    hill=next(a for a in content.ELEVATIONS if a['id']=='adv_hill_dune_observatory_2')
    hp=dict(id='adv_hill_dune_observatory_2',name='Szczyt Wzgórza Południka',x=hill['x']+hill['w']/2+75,y=hill['y']+hill['h']/2-20,floor=2)
    q('meridian_2','faris','Ten sam cień, inne niebo','Odnajdź podziemny południk, a potem porównaj go ze znakiem na szczycie wzgórza.','dune_observatory',[_discover(p[(0,2)]),_discover(hp)],['meridian_1'],'mithral_chain_mail')
    s=sites['volcanic_fissure'];p=s['points']
    q('embers_1','pola','Tablica ostatniej zmiany','Dotrzyj do pękniętego pieca i przepędź ożywione zbroje. Pola czeka na ślad po załodze.','volcanic_fissure',[_discover(p[(0,1)]),_kill(content,'adv_animated_armor','volcanic_fissure',2)])
    q('embers_2','pola','Nie wszyscy wrócili','Sprawdź ostatnią komorę górników i pokonaj żywiołaka ognia, zanim zaniesiesz Poli wieści.','volcanic_fissure',[_discover(p[(0,2)]),_kill(content,'fire_elemental','volcanic_fissure',1)],['embers_1'],'ring_resistance_fire')
    s=sites['frost_hollow'];p=s['points']
    q('frost_1','wera','Ostatni ogień','Odszukaj izbę straży i stare miejsce ogniska. Wera oznaczy schronienie na szlaku.','frost_hollow',[_discover(p[(0,1)]),_discover(p[(0,2)])])
    q('frost_2','wera','Kamień ponad zamiecią','Pokonaj gargulce w schronisku i znajdź oba tarasy Wzgórza Białych Chorągwi.','frost_hollow',[_kill(content,'adv_gargoyle','frost_hollow',2),dict(type='discover',target='adv_hill_frost_hollow_2',label='Szczyt Białych Chorągwi',required=1,x=s['x']+495,y=s['y']-280,floor=2)],['frost_1'],'ring_warmth')
    s=sites['dragon_watch'];p=s['points']
    q('watch_1','oskar','Przysięga obserwatorów','Odszukaj pękniętą przysięgę i kamienne oko w krypcie dawnych strażników.','dragon_watch',[_discover(p[(0,1)]),_discover(p[(0,2)])])
    q('watch_2','oskar','Ostrzec, nie prowokować','Oczyść kryptę z gargulców i dotrzyj na górny taras strażnicy. Z wysokości Oskar odczyta dawny system ostrzegania.','dragon_watch',[_kill(content,'adv_gargoyle','dragon_watch',2),dict(type='discover',target='adv_hill_dragon_watch_2',label='Szczyt Kamiennego Oka',required=1,x=s['x']+495,y=s['y']-280,floor=2)],['watch_1'],'magic_shield_1')
    s=sites['obsidian_archive'];p=s['points']
    q('archive_1','ada','Ludzie spoza kronik','Odnajdź rejestr przybyszów oraz aleję czarnych ksiąg. Ada porówna te zapisy z miejskimi kronikami.','obsidian_archive',[_discover(p[(0,0)]),_discover(p[(0,1)])])
    q('archive_2','eryk','Imię kartografki','Dotrzyj do wygaszonej pieczęci i pokonaj obsydianowego strażnika. Eryk czeka na prawdę o swojej siostrze.','obsidian_archive',[_discover(p[(0,2)]),_kill(content,'obsidian_knight','obsidian_archive',1)],['archive_1'],'ring_resistance_poison')


def configure(content,obstacles,landmarks,zones,enemies,npcs,quests):
    if any(q['id']=='adv_bell_1' for q in quests):return
    configure_monsters(enemies)
    for kind in MONSTERS:
        for entry in enemies[kind]['loot']['entries']:
            if entry['kind']=='item':
                content.ITEMS[entry['template']].setdefault('sources',[]).append(dict(kind=kind,name=enemies[kind]['name'],chance=entry['chance']))
    # Keep an explicit route into each reserved approach; no world-wide relocation.
    for key in SITES:
        x,y,_=_anchor(content,key)
        obstacles[:]=[o for o in obstacles if o.get('floor',0)!=0 or o['x']+o['w']<x-370 or o['x']>x+100 or o['y']+o['h']<y-80 or o['y']>y+450]
    sites={key:_add_site(content,obstacles,landmarks,zones,key) for key in SITES}
    for key in ('dune_observatory','frost_hollow','dragon_watch'):_add_hill(content,obstacles,landmarks,zones,key)
    for row in NPC_DATA:_npc(npcs,content,row)
    _quests(content,quests,sites)
    content.ADVENTURES=[dict(id='adv_'+key,name=s['site']['name'],x=s['x'],y=s['y'],floor=0,level=s['level'],
        floors=s['site']['floors'][:],theme=s['site']['theme'],description=s['site']['description']) for key,s in sites.items()]
    return content.ADVENTURES
