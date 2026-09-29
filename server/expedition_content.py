"""UI_20 original crypts and guardians, using the game's existing combat rules.

These are authored regional creatures, not claimed SRD stat blocks. Configure
after adventure_content and before discovery_rules; loot_economy owns rare loot.
Spawns and discoveries are append-only to preserve saved monster/quest IDs.
"""
from copy import deepcopy


# key: source, name, recommended level, HP, AC, attack, dice, speed, role,
# projectile, creature type, size, melee damage type. HP is deliberately fixed.
MONSTERS = {
    'exp_dune_skeleton': ('skeleton', 'Szkielet wydmowy', 35, 72, 14, 6, [2,6,2], 108, 'melee', None, 'undead', 1.05, 'slashing'),
    'exp_crypt_archer': ('skeleton_archer', 'Łucznik z piaskowej krypty', 40, 66, 13, 7, [2,6,3], 112, 'ranged', 'arrow', 'undead', 1.05, 'piercing'),
    'exp_sand_revenant': ('mummy', 'Upiór zasypanej straży', 45, 108, 15, 7, [2,8,3], 104, 'melee', None, 'undead', 1.18, 'slashing'),
    'exp_tomb_acolyte': ('necromancer', 'Balsamista bez twarzy', 50, 88, 13, 8, [2,8,3], 116, 'ranged', 'shadow', 'undead', 1.10, 'necrotic'),
    'exp_scarab_keeper': ('mummy_hierophant', 'Nefret, Strażniczka Skarabeuszy', 55, 310, 17, 8, [2,8,4], 122, 'hybrid', 'venom', 'undead', 1.55, 'slashing'),
    'exp_sunless_pharaoh': ('lich_king', 'Akharet, Król Zgasłego Słońca', 65, 410, 17, 9, [3,8,4], 126, 'hybrid', 'shadow', 'undead', 1.65, 'necrotic'),
    'exp_root_warden': ('guardian', 'Veyra, Serce Splątanych Korzeni', 32, 195, 15, 6, [2,8,3], 105, 'hybrid', 'venom', 'plant', 1.55, 'slashing'),
    'exp_sevenfold_regent': ('crypt_guard', 'Bezimienny Regent', 45, 275, 18, 7, [2,10,3], 112, 'hybrid', 'shadow', 'undead', 1.50, 'slashing'),
    'exp_ember_overseer': ('fire_elemental', 'Kormag, Nadzorca Wygasłego Pieca', 70, 450, 18, 9, [3,8,4], 127, 'hybrid', 'fire', 'construct', 1.65, 'bludgeoning'),
    'exp_obsidian_librarian': ('obsidian_knight', 'Sędzia Wygaszonych Imion', 115, 680, 20, 12, [3,10,5], 139, 'hybrid', 'shadow', 'construct', 1.70, 'slashing'),
}
BOSSES = frozenset(('exp_scarab_keeper','exp_sunless_pharaoh','exp_root_warden',
    'exp_sevenfold_regent','exp_ember_overseer','exp_obsidian_librarian'))
CRYPT_FLOORS = (-23, -24, -25)
CRYPT_NAME = 'Nekropolia Zgasłego Słońca'


def configure_monsters(enemies):
    for key, row in MONSTERS.items():
        source, name, level, hp, ac, attack, dice, speed, role, projectile, creature, size, damage_type = row
        boss = key in BOSSES
        spec = deepcopy(enemies[source])
        # Do not accidentally inherit another monster's official traits.
        for field in ('adventure_attacks', 'undead_fortitude', 'fly', 'hover', 'flyby', 'climb', 'blindsight', 'dnd_source'):
            spec.pop(field, None)
        save_bonus = 1 + level // 17
        spec.update(name=name, level=level, hp=hp, hp_dice=[hp,1,0], armor_class=ac,
            damage_dice=dice[:], melee_dice=dice[:], special_dice=[dice[0]+1,dice[1],dice[2]],
            attack_bonus=attack, damage=dice[0]*(dice[1]+1)/2+dice[2], melee_damage=dice[0]*(dice[1]+1)/2+dice[2],
            melee_damage_type=damage_type, damage_type=damage_type, speed=speed, size=size,
            boss=boss, combat_role=role, range=430 if projectile else 62, melee_range=66 if boss else 54,
            attack_interval=3.2 if boss else 3.0, ranged_interval=4.3 if boss else 3.4,
            windup=.72 if boss else .6, aggro=470 if boss else 350, base_aggro=470 if boss else 350,
            leash=1050 if boss else 780, wander=60 if boss else 110, respawn=210 if boss else 52,
            xp=level*29 if boss else 30+level*5, gold=level*3 if boss else 8+level,
            save_bonus=save_bonus, save_dc=12+level//20, saves={a:save_bonus for a in ('strength','dexterity','constitution','intelligence','wisdom','charisma')},
            creature_type=creature, creature_size='large' if boss else 'medium', darkvision=60 if creature=='undead' else 0,
            immunities=['poison'] if creature in ('undead','construct') else [], resistances=[],
            condition_immunities=['poisoned','exhaustion'] if creature in ('undead','construct') else [],
            content_version='UI_20', content_source='Autorski przeciwnik regionalny',
            sprite=f'assets/monsters/expeditions/{key}.svg', sprite_frame_width=80, sprite_frame_height=80,
            sprite_frames=4, appearance='adventure', color='#b5a075' if creature=='undead' else '#65547c')
        if projectile:
            spec['projectile'] = projectile
        else:
            spec.pop('projectile', None)
        if boss:
            spec['special_range'] = 620
        else:
            spec.pop('special_range', None)
        if key == 'exp_sand_revenant':
            spec['undead_fortitude'] = True
        if key == 'exp_ember_overseer':
            spec['immunities'].append('fire')
        family = 'undead' if creature=='undead' else 'stone' if creature=='construct' else 'beast'
        spec['loot_origin'] = 'Strażnik podziemi' if boss else 'Nieumarli pustynnej nekropolii'
        spec['loot'] = dict(family=family, tier=3, equipment_chance=0, trophy_chance=0, potion_chance=0,
            unique_chance=0, legendary_chance=0, independent=True,
            entries=[dict(kind='item', template='trophy_'+family, chance=.70 if boss else .32)])
        enemies[key] = spec


def _landmark(landmarks, ident, name, x, y, floor, level, description, **extra):
    row = dict(id=ident, name=name, x=x, y=y, floor=floor, radius=95,
        biome='desert' if floor in CRYPT_FLOORS or floor==0 else 'dungeon', recommended_level=level,
        description=description, reward=dict(xp=0,gold=0), expedition=True, **extra)
    landmarks.append(row)
    return row


def _link(content, ident, name, origin, target):
    for suffix, a, b in (('down',origin,target),('up',target,origin)):
        content.STAIRS.append(dict(id='exp_'+ident+'_'+suffix, name=name, x=a[0], y=a[1], floor=a[2],
            to_x=b[0], to_y=b[1], to_floor=b[2], radius=72, min_level=1, expedition=True))


# Each plan is an authored graph of unequal chambers. Corridors have turning
# points and overlap room centres, so all branches are real collision geometry.
PLANS = (
    dict(name='Aleja Zapomnianych', color='#a18e68',
        nodes=[(0,0,440,380),(720,-180,480,390),(1460,160,520,420),(2240,-320,450,470),
               (3110,-120,650,470),(3590,690,600,520),(2810,1160,500,510),(2020,840,500,440),
               (1170,1210,540,450),(400,820,490,530),(1140,2090,480,550),(2150,2240,570,520),
               (3180,2180,710,650)],
        edges=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,2),(7,8),(8,9),(9,0),(8,10),(10,11),(11,12),(12,6)],
        labels={2:'Dziedziniec połamanych steli',5:'Kaplica wyschniętej rzeki',9:'Boczne grobowce tragarzy',10:'Sarkofagi skrybów',12:'Brama dziewięciu dynastii'}),
    dict(name='Sale Balsamistów', color='#847657',
        nodes=[(0,0,480,400),(840,170,520,450),(1600,-240,570,510),(2490,120,520,460),
               (3320,-150,560,520),(3600,800,680,570),(2740,1220,480,470),(1860,850,570,530),
               (910,1150,460,520),(140,1440,500,460),(1750,1990,580,540),(2840,2210,740,660),
               (3700,2150,520,470)],
        edges=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,1),(7,8),(8,9),(9,0),(7,10),(10,11),(11,12),(12,5)],
        labels={2:'Magazyn wonnych żywic',4:'Cysterna pod wydmą',8:'Krużganek pustych masek',10:'Przedsionek skarabeuszy',11:'Tron Strażniczki Skarabeuszy'}),
    dict(name='Grobowce Dziewięciu Dynastii', color='#68616c',
        nodes=[(0,0,500,430),(800,-180,480,510),(1510,330,540,460),(2410,10,570,540),
               (3300,450,630,540),(3000,1450,530,530),(2150,1300,490,500),(1200,1130,560,550),
               (320,900,470,540),(1060,2150,570,600),(2020,2510,600,590),(3200,2740,900,800),
               (4010,1690,500,580)],
        edges=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,0),(7,2),(7,9),(9,10),(10,11),(11,12),(12,4)],
        labels={1:'Grobowiec dynastii kupców',3:'Biblioteka ostatniego słońca',8:'Studnia popiołu',9:'Kaplica dziewięciu koron',11:'Sala Zgasłego Słońca'}),
)


def _corridors(a, b, width, horizontal_first):
    ax, ay = a[:2]; bx, by = b[:2]
    bend = (bx,ay) if horizontal_first else (ax,by)
    rows=[]
    for (x1,y1),(x2,y2) in ((a[:2],bend),(bend,b[:2])):
        rows.append(dict(x=min(x1,x2)-width/2,y=min(y1,y2)-width/2,
            w=abs(x2-x1)+width,h=abs(y2-y1)+width,passage=True))
    return rows


def _bounds(area):
    rows=area['rooms'];area.update(x=min(r['x'] for r in rows),y=min(r['y'] for r in rows))
    area.update(w=max(r['x']+r['w'] for r in rows)-area['x'],h=max(r['y']+r['h'] for r in rows)-area['y'])


def _add_crypt(content, obstacles, landmarks, zones, npcs, quests):
    x,y,level=getattr(content,'UI20_CRYPT_ANCHOR',(115500,15500,38))
    description='Trzy rozległe poziomy, boczne grobowce i połączone krużganki. W głębi czekają Strażniczka Skarabeuszy oraz Król Zgasłego Słońca.'
    entry=_landmark(landmarks,'exp_crypt_entrance',CRYPT_NAME+' · wejście',x,y,0,level,description)
    obstacles[:]=[o for o in obstacles if o.get('floor',0)!=0 or not (o['x']+o['w']>x-380 and o['x']<x+380 and o['y']+o['h']>y-380 and o['y']<y+380)]
    _link(content,'crypt_entry',CRYPT_NAME+' · powierzchnia / poziom 1',(x,y,0),(x,y,CRYPT_FLOORS[0]))
    # The surface connection is short, on the same island as the observatory.
    anchor=getattr(content,'ADVENTURE_ANCHORS',{}).get('dune_observatory',dict(x=x-1500,y=y-4000))
    content.ROADS.append([[anchor['x'],anchor['y']+200],[x-450,anchor['y']+200],[x-450,y+180],[x,y+180],[x,y]])
    points={}
    for index,(floor,plan) in enumerate(zip(CRYPT_FLOORS,PLANS)):
        nodes=[(x+dx,y+dy,w,h) for dx,dy,w,h in plan['nodes']]
        rooms=[dict(x=cx-w/2,y=cy-h/2,w=w,h=h,chamber=True) for cx,cy,w,h in nodes]
        for edge_no,(a,b) in enumerate(plan['edges']):
            rooms.extend(_corridors(nodes[a],nodes[b],190 if edge_no%3 else 220,(edge_no+index)%2==0))
        area=dict(id=f'exp_crypt_{index+1}',name=CRYPT_NAME+' · '+plan['name'],floor=floor,
            rooms=rooms,color=plan['color'],min_level=level+index*10,max_level=level+22+index*10,
            theme='catacomb',expedition=True,local_depth=index+1)
        _bounds(area);content.DUNGEONS.append(area);zones.append(dict(area))
        _landmark(landmarks,f'exp_crypt_{index+1}_entry',plan['name']+' · schody powrotne',x,y,floor,level+index*10,
            'Kamienne schody prowadzą w górę. Boczne krużganki łączą się z głównym traktem.')
        for node,label in plan['labels'].items():
            cx,cy,w,h=nodes[node]
            points[index,node]=_landmark(landmarks,f'exp_crypt_{index+1}_room_{node}',label,cx,cy,floor,level+index*10,
                'Część pustynnej nekropolii. Nieumarli chronią dawne wyposażenie, a najcenniejszych przedmiotów strzegą władcy grobowców.')
        kinds=('exp_dune_skeleton','exp_crypt_archer','exp_sand_revenant','exp_tomb_acolyte')
        for node,(cx,cy,w,h) in enumerate(nodes[1:],1):
            # Returning stairs remain clear; later chambers mix melee and ranged
            # enemies without stacking a whole pack on a single coordinate.
            content.SPAWNS.append((kinds[(node+index)%4],cx-85,cy-55,floor))
            content.SPAWNS.append((kinds[(node+index+1)%4],cx+90,cy+65,floor))
            if node%4==0:
                content.SPAWNS.append(('mummy' if index==0 else 'crypt_guard',cx+10,cy+145,floor))
            # Corner props are safely outside all central connecting corridors.
            obstacles.append(dict(x=cx-w/2+35,y=cy-h/2+35,w=64,h=42,floor=floor,type='ruin',expedition=True))
        if index==1:
            cx,cy,_,_=nodes[11];content.SPAWNS.append(('exp_scarab_keeper',cx,cy+180,floor))
        elif index==2:
            cx,cy,_,_=nodes[11];content.SPAWNS.append(('exp_sunless_pharaoh',cx,cy+190,floor))
        last_node=12 if index==0 else 12 if index==1 else 11
        cx,cy,w,h=nodes[last_node]
        if index<2:
            _link(content,f'crypt_depth_{index+1}',CRYPT_NAME+f' · poziom {index+1} / {index+2}',
                (cx+w/2-95,cy+h/2-95,floor),(x,y,CRYPT_FLOORS[index+1]))
        else:
            cache=_landmark(landmarks,'exp_crypt_cache','Skarbiec Zgasłego Słońca',cx+w/2-100,cy+h/2-100,floor,65,
                'Skrytka w najgłębszej sali. E poza walką; osobiste odnowienie 30 minut.',action='cache',min_level=1)
            content.POIS.append(cache)
    npc_id='exp_samira'
    npcs.append(dict(id=npc_id,name='Samira Badaczka Grobowców',role='Kartografka nekropolii',x=x-150,y=y+170,floor=0,radius=145,
        appearance='traveler',expedition=True,dialogue=dict(greeting='Piasek odsłonił bramę trzech nekropolii. Królowie wciąż leżą poniżej, razem z bronią, której nie znajdziesz u miejskiego kupca.',
        topics=[dict(id='droga',title='Jak daleko sięgają krypty?',text='Trzy poziomy. Boczny korytarz często wraca do poprzedniej sali. Schody w dół leżą za dalekimi komorami, a każdymi da się wrócić.'),
                dict(id='wladcy',title='Kto strzeże skarbów?',text='Nefret pilnuje drugiego poziomu, Akharet trzeciego. Ich ataki obejmują oznaczone pola — zostaw sobie drogę odwrotu. Rzadkie przedmioty nie wypadają przy każdym zwycięstwie.')],
        quest_offer='Sprawdź cele wyprawy poniżej.',quest_progress='Dziennik pokaże, których komór jeszcze nie sprawdziliśmy.',quest_complete='Oznaczę te sale na mojej mapie. Dziękuję za wieści z głębi.')))
    for ident,title,text,objectives,requires,reward in (
        ('crypt_map','Drogi umarłych','Zbadaj trzy odległe komory pierwszego poziomu.',
            [dict(type='discover',target=points[0,n]['id'],label=points[0,n]['name'],required=1,x=points[0,n]['x'],y=points[0,n]['y'],floor=-23) for n in (5,10,12)],[],dict(xp=650,gold=120)),
        ('scarab_queen','Milczenie skarabeuszy','Pokonaj Nefret na drugim poziomie nekropolii.',
            [dict(type='kill',target='exp_scarab_keeper',label=MONSTERS['exp_scarab_keeper'][1],required=1,x=x+PLANS[1]['nodes'][11][0],y=y+PLANS[1]['nodes'][11][1]+180,floor=-24)],['exp_crypt_map'],dict(xp=1200,gold=240)),
        ('sunless_king','Ostatnie zgasłe słońce','Pokonaj Akhareta w najgłębszym królewskim grobowcu.',
            [dict(type='kill',target='exp_sunless_pharaoh',label=MONSTERS['exp_sunless_pharaoh'][1],required=1,x=x+PLANS[2]['nodes'][11][0],y=y+PLANS[2]['nodes'][11][1]+190,floor=-25)],['exp_scarab_queen'],dict(xp=1800,gold=320)),
    ):
        quests.append(dict(id='exp_'+ident,npc_id=npc_id,title=title,description=text,min_level=1,requires=requires,
            objectives=objectives,reward=reward,recommended_level=level,expedition=True,site_id='exp_crypt'))
    content.ADVENTURES.append(dict(id='exp_crypt',name=CRYPT_NAME,x=x,y=y,floor=0,level=level,
        floors=list(CRYPT_FLOORS),theme='catacomb',description=description))


GUARDIAN_SITES = (
    ('forest_shrine',-22,'exp_root_warden','Komora Żywego Splotu'),
    ('royal_catacombs',-18,'exp_sevenfold_regent','Tron Bezimiennego Regenta'),
    ('volcanic_fissure',-12,'exp_ember_overseer','Hala Ostatniego Pieca'),
    ('obsidian_archive',-15,'exp_obsidian_librarian','Sąd Wygaszonych Imion'),
)


def _add_guardian(content, obstacles, landmarks, zones, site, floor, kind, name):
    area=next(d for d in content.DUNGEONS if d['id']==f'adv_{site}_floor_{abs(floor)}')
    # Choose the eastern chamber, not a thin corridor. This extends the old
    # playable space without changing old stairs, points, or spawn indices.
    candidates=[r for r in area['rooms'] if r['w']>=290 and r['h']>=270]
    room=max(candidates,key=lambda r:r['x']+r['w'])
    edge=room['x']+room['w'];cy=room['y']+room['h']/2
    corridor=dict(x=edge-60,y=cy-110,w=590,h=220,passage=True)
    arena=dict(x=edge+430,y=cy-410,w=880,h=820,chamber=True,boss_room=True)
    area['rooms'].extend((corridor,arena));_bounds(area)
    zone=next(z for z in zones if z.get('id')==area['id']);zone.update(area)
    px,py=arena['x']+arena['w']*.6,cy
    content.SPAWNS.append((kind,px,py,floor))
    for offset in (-230,230):
        guard='adv_grick' if site=='forest_shrine' else 'adv_ogre_zombie' if site=='royal_catacombs' else 'fire_elemental' if site=='volcanic_fissure' else 'adv_animated_armor'
        content.SPAWNS.append((guard,arena['x']+230,py+offset,floor))
    _landmark(landmarks,'exp_guardian_'+site,name,px,py,floor,content.ENEMIES[kind]['level'],
        content.ENEMIES[kind]['name']+' strzeże rzadkiego wyposażenia w bocznej sali. Zapowiadane ataki obszarowe pozwalają wycofać się poza oznaczone pola.')
    for dy in (-300,265):
        obstacles.append(dict(x=arena['x']+arena['w']-100,y=cy+dy,w=60,h=35,type='ruin',floor=floor,expedition=True))


def configure(content, obstacles, landmarks, zones, enemies, npcs, quests):
    if any(d.get('id')=='exp_crypt_1' for d in content.DUNGEONS):
        return
    configure_monsters(enemies)
    _add_crypt(content,obstacles,landmarks,zones,npcs,quests)
    for row in GUARDIAN_SITES:
        _add_guardian(content,obstacles,landmarks,zones,*row)
    for kind in MONSTERS:
        positions=[s for s in content.SPAWNS if s[0]==kind]
        _,x,y,floor=positions[0]
        content.LOOT_HUNTS.append(dict(id='loot_hunt_'+kind,name=enemies[kind]['name'],kind=kind,x=x,y=y,floor=floor,
            region=CRYPT_NAME if floor in CRYPT_FLOORS else 'Strażnicy dawnych wypraw',level=enemies[kind]['level'],count=len(positions)))
    return {'floors':len(CRYPT_FLOORS),'new_monsters':len(MONSTERS),'bosses':len(BOSSES)}
