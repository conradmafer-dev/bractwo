"""Authored local adventures and deterministic, spatially indexed wilderness.

Road/terrain coordinates are shared by the simulation and both renderers. The
continent stays huge; density follows routes, with irregular habitats off them.
"""
import math
import random

SURFACES = {
    'grass': {'name': 'Trawa', 'speed': 1.0, 'color': '#7dab4f'},
    'path': {'name': 'Ścieżka', 'speed': 1.18, 'color': '#bda769'},
    'stone': {'name': 'Kamień', 'speed': 1.25, 'color': '#9e9f91'},
    'mud': {'name': 'Błoto', 'speed': .72, 'color': '#87745a'},
    'sand': {'name': 'Piasek', 'speed': .86, 'color': '#d4bb7b'},
    'snow': {'name': 'Śnieg', 'speed': .88, 'color': '#c6dadd'},
    'forest': {'name': 'Ściółka', 'speed': .94, 'color': '#598449'},
    'ash': {'name': 'Popiół', 'speed': .90, 'color': '#786777'},
}
BIOME_SURFACE = {'forest': 'forest', 'swamp': 'mud', 'desert': 'sand',
                 'snow': 'snow', 'lava': 'ash', 'obsidian': 'ash', 'mountain': 'stone', 'ruins': 'stone'}
PREMIUM = {'mode': 'simulation', 'price_pln': 10, 'period_days': 30, 'speed_multiplier': 1.2,
           'name': 'Premium · szybki marsz', 'description': '10 zł / miesiąc · +20% szybkości. Teraz bezpłatna symulacja, bez płatności i automatycznego odnowienia.'}


def segment_distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    q = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/max(1, dx*dx+dy*dy)))
    return math.hypot(x-a[0]-q*dx, y-a[1]-q*dy)


class SurfaceMap:
    """Point lookup visits only a 512px cell, never the entire road network."""
    def __init__(self, roads, patches, cities, regions):
        self.cells, self.cities, self.regions = {}, cities, regions
        for path in roads:
            for a, b in zip(path, path[1:]):
                self.insert(('road', a, b), min(a[0], b[0])-34, min(a[1], b[1])-34,
                            max(a[0], b[0])+34, max(a[1], b[1])+34)
        for p in patches:
            self.insert(('patch', p), p['x'], p['y'], p['x']+p['w'], p['y']+p['h'])

    def insert(self, data, x0, y0, x1, y1):
        for x in range(math.floor(x0/512), math.floor(x1/512)+1):
            for y in range(math.floor(y0/512), math.floor(y1/512)+1):
                self.cells.setdefault((x, y), []).append(data)

    def at(self, x, y, floor=0):
        if floor: return 'stone'
        if any(math.hypot(x-c['x'], y-c['y']) < 205 for c in self.cities): return 'stone'
        candidates = self.cells.get((math.floor(x/512), math.floor(y/512)), ())
        for entry in candidates:
            if entry[0] == 'road' and segment_distance(x, y, entry[1], entry[2]) <= 33:
                return 'path'
        for entry in reversed(candidates):
            if entry[0] == 'patch':
                p = entry[1]
                if ((x-p['x']-p['w']/2)/(p['w']/2))**2 + ((y-p['y']-p['h']/2)/(p['h']/2))**2 <= 1:
                    return p['kind']
        # Retain the original small biomes around Przystań.
        if x < 3200 and y < 2304:
            if 1720 < x < 2220 and y > 1370: return 'mud'
            if x > 2250: return 'stone'
            if y < 900 and x < 1400: return 'forest'
            return 'grass'
        r = next((r for r in self.regions if r['x'] <= x < r['x']+r['w'] and r['y'] <= y < r['y']+r['h']), {})
        return BIOME_SURFACE.get(r.get('biome'), 'grass')


def curve(points):
    """Catmull-Rom samples with bounded excursions and <=100px segments."""
    if len(points) < 3: return [list(p) for p in points]
    result = []
    for i in range(len(points)-1):
        p0, p1, p2, p3 = points[max(0, i-1)], points[i], points[i+1], points[min(len(points)-1, i+2)]
        n = max(3, math.ceil(math.dist(p1, p2)/95))
        for j in range(n):
            t = j/n
            xy = [.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t*t+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t*t*t) for k in (0, 1)]
            result.append([round(max(40, min(127960 if k == 0 else 92120, xy[k])), 1) for k in (0, 1)])
    result.append(list(points[-1]))
    return result


def configure(c, obstacles, landmarks, quests, enemies):
    c.VERSION = '0.5.0'
    c.TERRAIN = []
    c.SURFACES, c.PREMIUM = SURFACES, PREMIUM
    # Distinct roles: heavy does not automatically mean fast.
    for key, source, name, level, appearance, color in [
        ('bandit_archer', 'bandit', 'Bandyta łucznik', 11, 'goblin', '#c09368'),
        ('skeleton_archer', 'skeleton', 'Szkielet łucznik', 9, 'skeleton', '#d9d1b6'),
        ('spitting_spider', 'spider', 'Plujący pająk', 8, 'spider', '#99ba61'),
        ('cyclops', 'minotaur', 'Cyklop skalny', 24, 'cyclops', '#b9987b'),
        ('bear', 'boar', 'Niedźwiedź brunatny', 12, 'bear', '#997253'),
        ('harpy', 'elf', 'Harpia skalna', 22, 'harpy', '#b6a5a0'),
        ('ghoul', 'skeleton', 'Ghul cmentarny', 14, 'ghoul', '#97a279'),
        ('ogre', 'troll', 'Ogr maczugowy', 31, 'cyclops', '#88926c'),
        ('scorpion', 'spider', 'Skorpion piaskowy', 18, 'scorpion', '#d2a76a'),
    ]:
        enemies[key] = {**enemies[source], 'name': name, 'level': level, 'appearance': appearance,
                        'color': color, 'hp': 120+level*10, 'damage': 8+level, 'xp': 25+level*5}
    speeds = {'rat': 64, 'boar': 108, 'wolf': 130, 'goblin': 105, 'spider': 116,
              'skeleton': 92, 'guardian': 76, 'wisp': 102, 'troll': 112, 'bandit': 124,
              'orc': 128, 'orc_shaman': 104, 'crocodile': 110, 'elf': 152, 'minotaur': 142,
              'scarab': 128, 'mummy': 85, 'vampire': 188, 'necromancer': 110, 'dwarf': 118,
              'golem': 86, 'frost_wolf': 192, 'ice_elemental': 142, 'fire_elemental': 165,
              'dragon': 164, 'frost_giant': 132, 'lich': 124, 'nightmare': 221,
              'dragon_lord': 195, 'demon': 202, 'ancient_guardian': 123, 'abyss_walker': 222,
              'bear': 118, 'harpy': 181, 'ghoul': 131, 'ogre': 112, 'scorpion': 128,
              'bandit_archer': 116, 'skeleton_archer': 94, 'spitting_spider': 109, 'cyclops': 119}
    ranged = {'harpy': 'feather', 'ogre': 'stone', 'goblin': 'stone', 'bandit_archer': 'arrow', 'skeleton_archer': 'arrow',
              'spitting_spider': 'venom', 'cyclops': 'stone', 'wisp': 'arcane',
              'orc_shaman': 'arcane', 'elf': 'arrow', 'necromancer': 'shadow', 'lich': 'shadow',
              'ice_elemental': 'ice', 'fire_elemental': 'fire', 'dragon': 'fire',
              'dragon_lord': 'fire', 'demon': 'fire', 'abyss_walker': 'shadow'}
    sizes = {'bear':1.4, 'harpy':1.25, 'ogre':1.85, 'scorpion':1.1, 'ghoul':1.1, 'rat': .85, 'spider': 1.15, 'boar': 1.12, 'troll': 1.25, 'minotaur': 1.45,
             'golem': 1.5, 'cyclops': 1.7, 'dragon': 1.85, 'dragon_lord': 2.15, 'demon': 1.8,
             'frost_giant': 1.95, 'ancient_guardian': 1.65, 'abyss_walker': 1.7}
    for key, s in enemies.items():
        boss = key == 'boss' or s.get('boss', False)
        s.update(speed=speeds.get(key, 145+(s.get('level', 20)*.35)),
                 aggro=620 if boss else 470 if key in ranged else 380,
                 leash=1100 if boss else 850, size=sizes.get(key, 2.2 if boss else 1),
                 wander=115 if boss else 175, boss=boss,
                 attack_interval=1.8 if key in ranged else 1.35)
        if key in ranged:
            s.update(projectile=ranged[key], range=410 if key not in ('goblin', 'spitting_spider') else 350,
                     windup=.7 if key in ('cyclops', 'dragon', 'dragon_lord') else .38)
        if boss:
            s.update(projectile='fire' if 'dragon' in key else 'ice' if key == 'ice_queen' else 'shadow' if key in ('lich_king', 'abyss_lord') else 'stone',
                     range=440, windup=.7, attack_interval=2.1, special_range=610)
    hybrids = {'goblin', 'spitting_spider', 'cyclops', 'ogre', 'harpy', 'dragon', 'dragon_lord', 'demon', 'abyss_walker'}
    for key, s in enemies.items():
        s['combat_role'] = 'hybrid' if s.get('boss') or key in hybrids else 'ranged' if s.get('projectile') else 'melee'
        s['melee_range'] = 85 if s.get('boss') else 68 if s.get('size', 1) > 1.4 else 48
        s['melee_damage'] = s['damage'] * (1.15 if s['combat_role'] == 'hybrid' else .55)
        s['ranged_interval'] = 4.8 if s.get('boss') else 4.0 if s['combat_role'] == 'hybrid' else s['attack_interval']
    # Replace uniform surface rings; underground rooms and legacy quest targets stay.
    c.SPAWNS[:] = [s for s in c.SPAWNS if s[3] != 0]
    c.HUNTING_GROUNDS.clear()
    c.ROADS.clear()
    # Curving starter network, with the river crossed only at its bridge.
    starter = [
        [(560,1180),(610,905),(650,650),(900,580),(1250,610),(1310,320)],
        [(560,1180),(940,1200),(1320,1150),(1500,1150),(1680,1150),(1950,1150),(2170,1040),(2160,810),(2390,690),(2530,640),(2590,500),(2590,370)],
        [(560,1180),(630,1380),(820,1510),(980,1810),(1000,2010),(780,2290),(1150,2610),(1470,2910),(1260,3340)],
        [(560,1180),(570,1420),(500,1470),(390,1500),(340,1650),(390,2020),(520,2450),(750,2970),(1260,3340)],
        [(2050,1150),(2030,1450),(1870,1730),(1880,2230),(2290,2550),(2550,3050),(3100,3370)],
        [(2070,1150),(2470,1320),(2530,1550),(2530,1930)],
        [(1260,3340),(1910,3420),(2460,3600),(3100,3370),(3550,3870),(4350,4280),(4820,4910)],
        [(2590,370),(3030,330),(3410,800),(3730,1200)],
        [(2590,370),(3030,330),(3350,1670),(3440,2420),(3100,3370)],
    ]
    for points in starter: c.ROADS.append(curve(points))
    rng = random.Random(5052026)
    # Looping regional networks, stitched at identical boundary endpoints.
    for ri, r in enumerate(c.REGIONS):
        x, y, w, h = r['x'], r['y'], r['w'], r['h']
        center = (x+12800, y+11520)
        for end in [(x+40,y+11520),(x+w-40,y+11520),(x+12800,y+40),(x+12800,y+h-40)]:
            dx, dy = end[0]-center[0], end[1]-center[1]
            length = math.hypot(dx, dy)
            points = [center]
            for t in (.25, .5, .75):
                bend = rng.choice((-1,1))*rng.randint(400,850)
                points.append((center[0]+dx*t-dy/length*bend, center[1]+dy*t+dx/length*bend))
            points.append(end)
            c.ROADS.append(curve(points))
        # Two non-rectangular loops: journeys have choices and short diversions.
        for sign in (-1, 1):
            c.ROADS.append(curve([center, (x+6400,y+11520+sign*2100), (x+5900,y+11520+sign*6500),
                                 (x+12000,y+11520+sign*8300), (x+19000,y+11520+sign*6000),
                                 (x+20700,y+11520+sign*1800), center]))
    for city in c.CITIES:
        r = next(r for r in c.REGIONS if r['id'] == city['region_id'])
        start = (4820,4910) if city['id'] == 'przystan' else (city['x'], city['y'])
        end = (r['x']+5900,r['y']+5020)
        if math.dist(start, end)>100:
            points = [start] if city['id']=='przystan' else [start, (start[0],start[1]-380),(start[0]+180,start[1]-900)]
            c.ROADS.append(curve(points+[ ((start[0]+end[0])/2+300,(start[1]+end[1])/2-200), end]))
    # Avoid connections crossing old walls. Starter mine is already on its trail.
    for stair in c.STAIRS:
        if stair['floor'] != 0 or stair['id'] == 'down_0': continue
        p = (stair['x'], stair['y'])
        end = min((pt for path in c.ROADS for pt in path), key=lambda q: math.dist(p,q))
        c.ROADS.append(curve([p,((p[0]+end[0])/2+190,(p[1]+end[1])/2), end]))
    # Habitat templates, not arbitrary mixtures. Fires belong only to sentient camps.
    habitats = {
        'wolves': ('den', 'forest', ['wolf','wolf','boar']),
        'trolls': ('den', 'forest', ['troll','troll','wolf']),
        'lich_court': ('crypt', 'stone', ['lich','vampire','skeleton_archer','ghoul']),
        'bears': ('den', 'forest', ['bear','boar']),
        'harpies': ('bones', 'stone', ['harpy','harpy','ogre']),
        'spiders': ('web', 'forest', ['spider','spitting_spider','spider']),
        'bandits': ('camp', 'grass', ['bandit','bandit_archer','bandit']),
        'goblins': ('camp', 'grass', ['goblin','goblin','troll']),
        'undead': ('crypt', 'stone', ['skeleton','skeleton_archer','ghoul','mummy']),
        'haunted': ('crypt', 'stone', ['skeleton_archer','vampire','skeleton','necromancer']),
        'bog': ('reeds', 'mud', ['crocodile','spider','wisp']),
        'orcs': ('camp', 'grass', ['orc','orc','orc_shaman','troll']),
        'elves': ('ruin', 'forest', ['elf','elf','wolf']),
        'desert': ('bones', 'sand', ['scarab','scorpion','minotaur']),
        'tomb': ('crypt', 'sand', ['mummy','skeleton_archer','necromancer']),
        'mine': ('quarry', 'stone', ['dwarf','golem','dwarf','minotaur']),
        'ice': ('crystals', 'snow', ['frost_wolf','ice_elemental','frost_wolf']),
        'giants': ('quarry', 'stone', ['frost_giant','ice_elemental','golem']),
        'dragons': ('bones', 'stone', ['dragon','dragon_lord']),
        'hell': ('rift', 'ash', ['demon','fire_elemental','nightmare']),
        'abyss': ('rift', 'ash', ['abyss_walker','ancient_guardian','demon']),
    }
    pools = [['wolves','spiders','bandits','goblins','undead','bog','bears','harpies'],['wolves','bandits','spiders','elves','bears','trolls'],['orcs','goblins'],
             ['desert','bandits'],['desert','tomb'],['bog','spiders'],['elves','bandits','orcs'],['undead','haunted'],
             ['tomb','haunted','mine'],['dragons','hell'],['orcs','mine','bandits'],['mine','giants','harpies'],['ice','mine'],
             ['ice','giants'],['dragons','giants'],['haunted','elves'],['haunted','hell','lich_court'],['hell','dragons'],['hell','abyss'],['abyss','hell']]
    ground_cells = {}
    def add_ground(x, y, ri, habitat, named=None, members=None):
        if not (140 < x < c.WIDTH-140 and 140 < y < c.HEIGHT-140): return
        if any(math.hypot(x-city['x'],y-city['y'])<850 for city in c.CITIES): return
        key = (int(x//600),int(y//600))
        if any(math.hypot(x-a,y-b)<620 for dx in (-1,0,1) for dy in (-1,0,1) for a,b in ground_cells.get((key[0]+dx,key[1]+dy),[])) and not named: return
        ground_cells.setdefault(key,[]).append((x,y))
        deco, terrain, kinds = habitats[habitat]
        kinds = list(members or kinds)
        if not named and rng.random()<.3: kinds=kinds[:rng.choice([1,2])]
        g = {'id': f'habitat_{len(c.HUNTING_GROUNDS)}', 'x':round(x), 'y':round(y), 'floor':0,
             'kind':kinds[0], 'members':kinds, 'decoration':deco, 'region_id':f'region_{ri}', 'name':named or ''}
        c.HUNTING_GROUNDS.append(g)
        rx, ry = rng.randint(290,510), rng.randint(220,440)
        c.TERRAIN.append({'x':round(x-rx),'y':round(y-ry),'w':rx*2,'h':ry*2,'kind':terrain})
        for kind in kinds:
            # Independent positions and different home radii. No circles/formations.
            c.SPAWNS.append((kind,round(x+rng.uniform(-185,210)),round(y+rng.uniform(-155,170)),0))
        return g
    local = [
        (750,2740,'bandits','Chłodny Trakt · rozbity wóz',['bandit','bandit_archer']),
        (2160,2760,'spiders','Pajęczy Zagajnik',None),
        (3690,1520,'undead','Cmentarz Trzech Dzwonów',['skeleton','skeleton_archer','mummy']),
        (3670,3220,'mine','Cyklopie Wzgórze',['cyclops']),
        (4450,670,'harpies','Gniazda Szarej Grani',['harpy','harpy']),
        (490,3950,'bears','Miodowa Barć',['bear','boar']),
        (2270,4300,'bog','Rozlewisko Szeptów',None),
        (4850,3370,'haunted','Kaplica bez Świtu',['skeleton','skeleton_archer','vampire']),
        (4890,5600,'orcs','Zasadzka Czerwonego Kła',None),
        (5600,1900,'dragons','Spękana Skała · smocza jama',['dragon']),
    ]
    for x,y,h,name,members in local:
        g=add_ground(x,y,0,h,name,members)
        level=max(enemies[k].get('level', 5) for k in g['members'])
        landmarks.append({'id':g['id'], 'name':name,'x':x,'y':y,'floor':0,'radius':115,'biome':h,
                          'decoration':g['decoration'],'recommended_level':level,'hint':True,
                          'description':('Zagrożenie opcjonalne. Omiń boczną odnogę, jeśli nie jesteś gotów. ' if level>20 else 'Boczny szlak w pobliżu Przystani. ')+', '.join(enemies[k]['name'] for k in g['members'])+'.',
                          'reward':{'xp':20+level*2,'gold':10}})
    # Nearby hints, without revealing every distant surprise.
    landmarks.append({'id':'trail_board','name':'Drogowskaz Przystani','x':730,'y':1390,'floor':0,'radius':110,'biome':'town',
                      'decoration':'sign','hint':True,'recommended_level':1,
                      'description':'Południe: rozbity wóz i bandyci. Za mostem: pajęczy zagajnik. Wschód: cmentarz, cyklopie wzgórze i smocza jama. K → Atlas → Okolica pokazuje kierunki.',
                      'reward':{'xp':5,'gold':0}})
    # More local loops: variety is reachable within the first few minutes.
    for end in [(item[0],item[1]) for item in local]:
        p=min((pt for path in c.ROADS for pt in path),key=lambda q:math.dist(q,end))
        c.ROADS.append(curve([p,((p[0]+end[0])/2+80,(p[1]+end[1])/2-70),end]))
    # Frequent roadside sightings throughout the entire continent.
    for path in list(c.ROADS):
        along=0
        for a,b in zip(path,path[1:]):
            along+=math.dist(a,b)
            if along<rng.randint(650,1100):continue
            along=0;x,y=b
            if x<3500 and y<2450:continue
            dx,dy=b[0]-a[0],b[1]-a[1];d=max(1,math.hypot(dx,dy))
            side=rng.choice([-1,1])*rng.randint(230,460)
            x-=dy/d*side;y+=dx/d*side
            ri=max(0,min(19,int(y//23040)*5+int(x//25600)))
            add_ground(x,y,ri,rng.choice(pools[ri]))
    # Off-road terrain and encounters, including rare solitary stronger residents.
    for ri,r in enumerate(c.REGIONS):
        step=1150 if ri==0 else 2700
        for y in range(r['y']+600,r['y']+r['h']-200,step):
            for x in range(r['x']+600,r['x']+r['w']-200,step):
                px,py=x+rng.randint(-180,180),y+rng.randint(-180,180)
                if px<6500 and py<6500:continue
                h=rng.choice(pools[ri])
                if ri==0 and rng.random()<.1:
                    add_ground(px,py,ri,'mine',members=['cyclops'])
                elif ri==0 and rng.random()<.035:
                    add_ground(px,py,ri,'dragons',members=['dragon'])
                else:add_ground(px,py,ri,h)
    # Use a grid for generation too; refuse new obstacles on trails or entrances.
    surface=SurfaceMap(c.ROADS,c.TERRAIN,c.CITIES,c.REGIONS)
    def touches_road(ox,oy,w,h):
        px,py=ox+w/2,oy+h/2
        radius=math.hypot(w,h)/2+55
        for gx in range(math.floor((px-radius)/512),math.floor((px+radius)/512)+1):
            for gy in range(math.floor((py-radius)/512),math.floor((py+radius)/512)+1):
                if any(entry[0]=='road' and segment_distance(px,py,entry[1],entry[2])<radius for entry in surface.cells.get((gx,gy),())):
                    return True
        return False
    obstacles[:]=[o for o in obstacles if o['x']<3200 and o['y']<2304 or o.get('type')=='house' or not touches_road(o['x'],o['y'],o['w'],o['h'])]
    for i,g in enumerate(c.HUNTING_GROUNDS):
        if g['x']<3400 and g['y']<2400:continue
        count=3 if g['decoration'] in ('quarry','bones','rift') else 2
        for j in range(count):
            ox=g['x']+rng.choice((-1,1))*rng.randint(230,390)
            oy=g['y']+rng.randint(-330,330)
            w,h=rng.randint(85,190),rng.randint(70,130)
            if touches_road(ox,oy,w,h):continue
            if any(math.hypot(ox-s['x'],oy-s['y'])<350 for s in c.STAIRS if s['floor']==0):continue
            if any(math.hypot(ox-l['x'],oy-l['y'])<240 for l in landmarks):continue
            obstacles.append({'x':round(ox),'y':round(oy),'w':w,'h':h,'floor':0,
                              'type':'mountain' if g['decoration'] in ('quarry','bones','rift') else 'grove' if g['decoration'] in ('web','den') else 'rock'})
    # An actual nearby dragon cave with two connected floors; optional, signed.
    x,y=5600,1900
    for floor in (-1,-2):
        d={'id':f'dungeon_20_{floor}','name':'Smocza Jama Spękanej Skały','floor':floor,'x':x-130,'y':y-180,'w':890,'h':440,'color':'#898170',
           'rooms':[{'x':x-130,'y':y-150,'w':380,'h':360},{'x':x+240,'y':y-50,'w':160,'h':120},{'x':x+360,'y':y-180,'w':400,'h':440}]}
        c.DUNGEONS.append(d)
    for sid,sx,sy,floor,tx,ty,to_floor in [('down_20',x,y,0,x,y,-1),('up_20',x,y,-1,x,y+85,0),('deep_20',x+680,y+190,-1,x+10,y,-2),('return_20',x,y,-2,x+660,y+95,-1)]:
        c.STAIRS.append({'id':sid,'name':'Smocza Jama · '+('zejście' if to_floor<floor else 'wyjście'),'x':sx,'y':sy,'floor':floor,'to_x':tx,'to_y':ty,'to_floor':to_floor,'radius':80,'min_level':1})
    c.SPAWNS[:]=[s for s in c.SPAWNS if not(s[0]=='dragon' and s[3]==0 and math.hypot(s[1]-x,s[2]-y)<400)]
    c.SPAWNS.extend([('spider',x+170,y+90,-1),('dragon',x+560,y+90,-1),('dragon',x+500,y+100,-2),('fire_elemental',x+640,y-70,-2)])
    # Filter collisions once, not on every tick. Relocate irregularly if necessary.
    grid={}
    for o in obstacles:
        for gx in range(int(o['x']//256),int((o['x']+o['w'])//256)+1):
            for gy in range(int(o['y']//256),int((o['y']+o['h'])//256)+1):grid.setdefault((gx,gy),[]).append(o)
    def blocked(x,y):
        if not(25<x<c.WIDTH-25 and 25<y<c.HEIGHT-25):return True
        if y<2324 and 1480<x<1700 and not 1100<y<1210:return True
        return any(x+22>o['x'] and x-22<o['x']+o['w'] and y+22>o['y'] and y-22<o['y']+o['h'] for gx in range(int((x-22)//256),int((x+22)//256)+1) for gy in range(int((y-22)//256),int((y+22)//256)+1) for o in grid.get((gx,gy),[]))
    fixed=[]
    for kind,x,y,floor in c.SPAWNS:
        if floor==0 and blocked(x,y):
            for _ in range(80):
                nx,ny=x+rng.randint(-240,240),y+rng.randint(-240,240)
                if not blocked(nx,ny):x,y=nx,ny;break
            else:continue
        fixed.append((kind,x,y,floor))
    c.SPAWNS[:]=fixed
    # Hunt hints follow actual residents after the habitat redistribution.
    for quest in quests:
        if not quest['id'].startswith('hunt_'):continue
        ri=int(quest['id'].split('_')[1]);r=c.REGIONS[ri]
        for objective in quest['objectives']:
            if objective['type']!='kill':continue
            residents=[(x,y) for kind,x,y,floor in c.SPAWNS if kind==objective['target'] and floor==0 and r['x']<=x<r['x']+r['w'] and r['y']<=y<r['y']+r['h']]
            if residents:
                objective['x'],objective['y']=min(residents,key=lambda point:math.dist(point,(objective['x'],objective['y'])))
    for region in c.REGIONS:
        region['kinds']=sorted(set(region['kinds'])|{kind for ground in c.HUNTING_GROUNDS if ground['region_id']==region['id'] for kind in ground['members']})
    c.SURFACE_MAP=surface
