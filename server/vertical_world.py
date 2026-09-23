"""Authored heights, connected waterways and usable exploration sites.

All collision is shared as metadata; spatial grids keep per-step work local.
Positive floors are bounded terraces, not another full continent.
"""
import math
import random
try:
    from .living_world import SurfaceMap, curve, segment_distance
except ImportError:
    from living_world import SurfaceMap, curve, segment_distance


class WaterMap:
    def __init__(self, waterways, bridges):
        self.cells = {}
        for kind, entries in [('water', waterways), ('bridge', bridges)]:
            for item in entries:
                for x in range(math.floor((item['x']-40)/512), math.floor((item['x']+item['w']+40)/512)+1):
                    for y in range(math.floor((item['y']-40)/512), math.floor((item['y']+item['h']+40)/512)+1):
                        self.cells.setdefault((x, y), []).append((kind, item))

    def blocked(self, x, y, radius=18):
        entries = self.cells.get((math.floor(x/512), math.floor(y/512)), ())
        if radius > 40:
            entries = [item for cx in range(math.floor((x-radius)/512), math.floor((x+radius)/512)+1)
                       for cy in range(math.floor((y-radius)/512), math.floor((y+radius)/512)+1)
                       for item in self.cells.get((cx, cy), ())]
        if not any(k == 'water' and segment_distance(x, y, w['a'], w['b']) < w['width']/2+radius for k, w in entries):
            return False
        return not any(k == 'bridge' and segment_distance(x, y, w['a'], w['b']) <= w['width']/2-radius for k, w in entries)


def segment(a, b, width, ident):
    return {'id': ident, 'a': a, 'b': b, 'width': width, 'floor': 0,
            'x': min(a[0], b[0])-width/2, 'y': min(a[1], b[1])-width/2,
            'w': abs(a[0]-b[0])+width, 'h': abs(a[1]-b[1])+width}


def configure(c, obstacles, landmarks, zones, enemies):
    c.VERSION = '0.6.0'
    c.ELEVATIONS, c.WATERWAYS, c.BRIDGES, c.POIS, c.CANYONS = [], [], [], [], []
    # Continue the original river, without touching the original quest crossing.
    river = curve([[1590, 2304], [1720, 3250], [3100, 4050], [4040, 6250],
                   [5880, 8150], [6180, 10800], [8800, 14600], [12100, 18800],
                   [15000, 24000], [13000, 32000], [18800, 40100], [16500, 49000],
                   [24000, 57100], [21400, 64300], [30000, 74200], [34000, 82900], [31000, 92300]])
    c.WATERWAYS.extend(segment(a, b, 180, f'river_{i}') for i, (a, b) in enumerate(zip(river, river[1:])))
    # The first cap overlaps the old bank so there is no seam or invisible ford.
    water = WaterMap(c.WATERWAYS, [])

    def stairs(ident, name, a, b, level=1):
        for suffix, origin, target in [('up', a, b), ('down', b, a)]:
            c.STAIRS.append({'id': f'{ident}_{suffix}', 'name': name,
                'x': origin[0], 'y': origin[1], 'floor': origin[2],
                'to_x': target[0], 'to_y': target[1], 'to_floor': target[2], 'radius': 62, 'min_level': level})

    def poi(ident, name, x, y, floor, action, level, description):
        entry = {'id': ident, 'name': name, 'x': x, 'y': y, 'floor': floor, 'radius': 62,
                 'action': action, 'recommended_level': level, 'min_level': level, 'hint': True,
                 'biome': 'mountain' if floor > 0 else 'dungeon' if floor < 0 else 'ruins',
                 'description': description, 'reward': {'xp': 50+level*3, 'gold': 15+level}}
        c.POIS.append(entry)
        landmarks.append(entry)

    def clear_area(x, y, width, height):
        obstacles[:] = [o for o in obstacles if o.get('floor', 0) != 0 or
                         o['x']+o['w'] < x-width/2-160 or o['x'] > x+width/2+160 or
                         o['y']+o['h'] < y-height/2-160 or o['y'] > y+height/2+160]
        c.HUNTING_GROUNDS[:] = [h for h in c.HUNTING_GROUNDS if h.get('floor', 0) != 0 or
                               abs(h['x']-x) > width/2+130 or abs(h['y']-y) > height/2+130]

    def link_road(x, y, south=False):
        # Join an existing curve, never a straight road across the whole continent.
        candidates = (p for road in c.ROADS for p in road if not south or p[1] >= y+150)
        cliffs = [o for o in obstacles if o.get('type') == 'terrace' and o.get('floor', 0) == 0]
        for nearest in sorted(candidates, key=lambda p: math.hypot(p[0]-x, p[1]-y)):
            path = curve([nearest, [(nearest[0]+x)/2+80, (nearest[1]+y)/2], [x, y]])
            clear = True
            for a, b in zip(path, path[1:]):
                n = max(1, math.ceil(math.dist(a, b)/24))
                for i in range(n+1):
                    px, py = a[0]+(b[0]-a[0])*i/n, a[1]+(b[1]-a[1])*i/n
                    if any(o['x']-52 < px < o['x']+o['w']+52 and o['y']-52 < py < o['y']+o['h']+52 for o in cliffs):
                        clear = False; break
                if not clear: break
            if clear:
                c.ROADS.append(path); return
        raise ValueError(f'No accessible approach at {x},{y}')

    def place_height(ax, ay):
        for i in range(180):
            angle = i*2.399963
            distance = 0 if i == 0 else 600+60*i
            x, y = round(ax+math.cos(angle)*distance), round(ay+math.sin(angle)*distance)
            if not 3600 < x < c.WIDTH-1200 or not 700 < y < c.HEIGHT-1200:
                continue
            if any(math.hypot(x-s['x'], y-s['y']) < 1100 for s in c.STAIRS if s['floor'] == 0):
                continue
            if any(math.hypot(x-h['x'], y-h['y']) < 1600 for h in c.CITIES):
                continue
            if any(water.blocked(x+dx, y+dy, 650) for dx, dy in [(0, 0)]):
                continue
            entries = [v for cx in range((x-650)//512, (x+650)//512+1)
                       for cy in range((y-650)//512, (y+650)//512+1) for v in c.SURFACE_MAP.cells.get((cx, cy), ())]
            if any(v[0] == 'road' and segment_distance(x, y, v[1], v[2]) < 680 for v in entries):
                continue
            return x, y
        raise ValueError(f'No clear height near {ax},{ay}')

    sites = [
        ('watch', 'Strażnica nad Przełomem', 4200, 2550, 2, 10, ['bandit', 'bandit_archer']),
        ('cyclops', 'Tarasy Cyklopów', 5900, 4200, 2, 24, ['cyclops', 'ogre']),
        ('harpy', 'Trzy Iglice Harpii', 7000, 1100, 3, 22, ['harpy', 'harpy']),
        ('green', 'Korona Starego Lasu', 30800, 31400, 2, 30, ['elf', 'orc_shaman']),
        ('sun', 'Słoneczne Mesy', 76500, 17300, 3, 45, ['scarab', 'mummy']),
        ('dwarf', 'Tarasy Kamieniołomu', 42500, 49500, 2, 50, ['dwarf', 'golem']),
        ('ice', 'Lodowa Grań', 79600, 53600, 3, 70, ['frost_wolf', 'frost_giant']),
        ('dragon', 'Smocze Szczyty', 102500, 29600, 3, 85, ['dragon', 'dragon_lord']),
        ('ash', 'Iglica Popiołu', 107000, 77100, 3, 100, ['demon', 'abyss_walker']),
    ]
    dimensions = [(860, 780), (550, 470), (280, 200)]
    for ident, name, ax, ay, height, level, kinds in sites:
        x, y = place_height(ax, ay)
        clear_area(x, y, 1000, 1040)
        for floor in range(1, height+1):
            w, h = dimensions[floor-1]
            room = {'x': x-w/2, 'y': y-h/2, 'w': w, 'h': h}
            area = {**room, 'id': f'height_{ident}_{floor}', 'name': name, 'floor': floor,
                    'rooms': [room], 'color': '#b6afa0', 'min_level': level, 'max_level': level+15}
            c.ELEVATIONS.append(area); zones.append(area)
            obstacles.append({**room, 'floor': floor-1, 'type': 'terrace', 'height': floor, 'site': ident})
            offset = [0, 180, -70][floor-1]
            stairs(f'height_{ident}_{floor}', f'{name} · {floor-1:+d} ↔ {floor:+d}',
                   (x+offset, y+h/2+60, floor-1), (x+offset, y+h/2-65, floor))
            positions = [(-310, -220), (310, 90), (-300, 160)] if floor == 1 else [(-200, -140), (205, -100)] if floor == 2 else [(-60, -35)]
            for j, (dx, dy) in enumerate(positions):
                c.SPAWNS.append((kinds[j % len(kinds)], x+dx, y+dy, floor))
        link_road(x, y+450, south=True)
        poi(f'view_{ident}', f'{name} · kamień wiatru', x-300, y+290, 1, 'wind', level,
            'E: wiatr przyspiesza marsz o 15% przez 90 s. Odnowienie: 5 min. Tarasy i schody prowadzą wyżej.')
        poi(f'treasure_{ident}', f'{name} · skrytka na szczycie', x+70, y-20, height, 'cache', level,
            'E: skrytka z wyposażeniem, trofeum i szansą na rzadki przedmiot. Osobiste odnowienie: 30 min. Najpierw zakończ walkę.')
        landmarks.append({'id': f'trail_{ident}', 'name': name, 'x': x, 'y': y+515, 'floor': 0,
                          'radius': 85, 'hint': True, 'recommended_level': level, 'biome': 'mountain',
                          'description': f'Podejście na piętra +1 do +{height}. Na szczycie skrytka, na tarasach przeciwnicy.',
                          'reward': {'xp': 30+level, 'gold': 10}})

    # Winding passes bounded by continuous, overlapping rock walls.
    for index, (name, points, level, kind) in enumerate([
        ('Przełom Wilczej Rzeki', [[6800, 6700], [8200, 6350], [9400, 7700], [11100, 7150]], 25, 'cyclops'),
        ('Wąwóz Czerwonego Piasku', [[68500, 14500], [69700, 16100], [71700, 15800], [72600, 17700]], 45, 'scorpion'),
        ('Pęknięcie Lodowca', [[72500, 52000], [74000, 52700], [73600, 54600], [75600, 56000]], 70, 'ice_elemental'),
        ('Gardziel Popiołu', [[99000, 73000], [100100, 74800], [102000, 74200], [103400, 76000]], 95, 'demon'),
    ]):
        path = curve(points)
        link_road(*path[0]); link_road(*path[-1])
        c.ROADS.append(path)
        c.CANYONS.append({'id': f'canyon_{index}', 'name': name, 'points': path})
        for j in range(0, len(path)-1, 2):
            a, b = path[j], path[min(j+2, len(path)-1)]
            dx, dy = b[0]-a[0], b[1]-a[1]; length = max(1, math.hypot(dx, dy))
            for side in (-1, 1):
                x, y = a[0]-dy/length*360*side, a[1]+dx/length*360*side
                obstacles.append({'x': x-160, 'y': y-160, 'w': 320, 'h': 320, 'floor': 0, 'type': 'canyon'})
            if j % 12 == 0:
                c.SPAWNS.append((kind, a[0]+40, a[1]+40, 0))
        x, y = path[len(path)//2]
        poi(f'spring_{index}', f'{name} · źródło', x, y, 0, 'spring', level,
            'E: źródło odnawia całe zdrowie i manę poza walką. Odnowienie: 3 min. Przełęcz wyznacza drogę między skałami.')

    # Four additional, connected two-storey dungeons. Numeric IDs preserve old saves.
    for index, (x, y, name, weak, strong, level) in enumerate([
        (4220, 8700, 'Zalana Kopalnia', 'goblin', 'cyclops', 18),
        (9500, 8400, 'Krypty Przełomu', 'skeleton_archer', 'vampire', 30),
        (32600, 30100, 'Korzenie Starego Lasu', 'spitting_spider', 'necromancer', 35),
        (77500, 50700, 'Szczelina Mrozu', 'ice_elemental', 'frost_giant', 65),
    ], 21):
        clear_area(x, y, 160, 240); link_road(x, y)
        stairs(f'delve_{index}_entry', f'{name} · wejście / wyjście', (x, y, 0), (x, y, -1))
        for floor in (-1, -2):
            rooms = [{'x': x-130, 'y': y-150, 'w': 380, 'h': 360},
                     {'x': x+240, 'y': y-50, 'w': 160, 'h': 120},
                     {'x': x+360, 'y': y-180, 'w': 400, 'h': 440}]
            area = {'id': f'dungeon_{index}_{floor}', 'name': name, 'floor': floor, 'rooms': rooms,
                    'x': x-130, 'y': y-180, 'w': 890, 'h': 440, 'color': '#777889', 'min_level': level, 'max_level': level+20}
            c.DUNGEONS.append(area); zones.append(area)
            for j, (dx, dy) in enumerate([(110, 50), (460, -90), (630, 30), (510, 160)]):
                c.SPAWNS.append((strong if floor == -2 and j % 2 == 0 else weak, x+dx, y+dy, floor))
        # Explicit legacy-style labels also keep the atlas and route tests useful.
        stairs(f'delve_{index}_deep', f'{name} · -1 ↔ -2', (x+680, y+190, -1), (x, y, -2))
        c.STAIRS[-4]['id'] = f'down_{index}'; c.STAIRS[-3]['id'] = f'up_{index}'
        c.STAIRS[-2]['id'] = f'deep_{index}'; c.STAIRS[-1]['id'] = f'return_{index}'
        poi(f'delve_cache_{index}', f'{name} · zapieczętowana skrzynia', x+625, y+120, -2, 'cache', level,
            'E: osobista skrytka z wyposażeniem i trofeami. Odnowienie: 30 min. Wymaga zakończenia walki.')
        poi(f'delve_ward_{index}', f'{name} · kapliczka kamienia', x+145, y-80, -1, 'ward', level,
            'E: błogosławieństwo zmniejsza obrażenia od potworów o 12% przez 90 s. Odnowienie: 5 min.')

    c.SURFACE_MAP = SurfaceMap(c.ROADS, c.TERRAIN, c.CITIES, c.REGIONS)
    # Decks follow every road that actually crosses water. No invisible fords.
    for i, path in enumerate(c.ROADS):
        for j, (a, b) in enumerate(zip(path, path[1:])):
            if any(water.blocked(a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, 110) for t in (0, .5, 1)):
                c.BRIDGES.append(segment(a, b, 140, f'bridge_{i}_{j}'))
    c.WATER_MAP = WaterMap(c.WATERWAYS, c.BRIDGES)

    def on_road(o):
        x, y = o['x']+o['w']/2, o['y']+o['h']/2
        reach = math.hypot(o['w'], o['h'])/2+52
        for cx in range(math.floor((x-reach)/512), math.floor((x+reach)/512)+1):
            for cy in range(math.floor((y-reach)/512), math.floor((y+reach)/512)+1):
                for entry in c.SURFACE_MAP.cells.get((cx, cy), ()):
                    if entry[0] == 'road' and segment_distance(x, y, entry[1], entry[2]) < reach:
                        return True
        return False

    obstacles[:] = [o for o in obstacles if o.get('floor', 0) or o.get('type') == 'terrace' or
                    (o['x'] < 3200 and o['y'] < 2304) or not on_road(o)]
    # Clear small interaction approaches; physical cliffs always retain collision.
    for point in [s for s in c.STAIRS if s['floor'] == 0] + [p for p in c.POIS if p['floor'] == 0]:
        obstacles[:] = [o for o in obstacles if o.get('floor', 0) or o.get('type') == 'terrace' or
                       o['x']+o['w'] < point['x']-75 or o['x'] > point['x']+75 or
                       o['y']+o['h'] < point['y']-75 or o['y'] > point['y']+75]

    cells = {}
    for o in obstacles:
        if o.get('floor', 0): continue
        for cx in range(math.floor((o['x']-25)/512), math.floor((o['x']+o['w']+25)/512)+1):
            for cy in range(math.floor((o['y']-25)/512), math.floor((o['y']+o['h']+25)/512)+1):
                cells.setdefault((cx, cy), []).append(o)

    def blocked(x, y):
        if c.WATER_MAP.blocked(x, y): return True
        return any(o['x']-22 < x < o['x']+o['w']+22 and o['y']-22 < y < o['y']+o['h']+22
                   for o in cells.get((math.floor(x/512), math.floor(y/512)), ()))

    rng = random.Random(60606)
    for i, (kind, x, y, floor) in enumerate(c.SPAWNS):
        if floor or not blocked(x, y): continue
        for attempt in range(800):
            radius = 90+attempt*3
            angle = rng.random()*math.tau
            nx, ny = x+math.cos(angle)*radius, y+math.sin(angle)*radius
            if 30 < nx < c.WIDTH-30 and 30 < ny < c.HEIGHT-30 and not blocked(nx, ny):
                c.SPAWNS[i] = (kind, round(nx, 1), round(ny, 1), 0); break
        else: raise ValueError(f'Cannot relocate {kind} at {x},{y}')
    # Keep existing discovery IDs and decorative habitats off new water/cliffs.
    for point in landmarks + c.HUNTING_GROUNDS:
        if point.get('floor', 0) or not blocked(point['x'], point['y']): continue
        x, y = point['x'], point['y']
        for attempt in range(800):
            radius, angle = 90+attempt*3, attempt*2.399963
            nx, ny = x+math.cos(angle)*radius, y+math.sin(angle)*radius
            if not blocked(nx, ny):
                point['x'], point['y'] = round(nx, 1), round(ny, 1); break
        else: raise ValueError(f"Unreachable landmark {point['id']}")
    by_id = {p['id']: p for p in landmarks}
    for quest in c.QUESTS_REF:
        for objective in quest['objectives']:
            if objective['type'] == 'discover' and objective['target'] in by_id:
                point = by_id[objective['target']]
                objective.update(x=point['x'], y=point['y'], floor=point.get('floor', 0))
    # A quest pin always points at a real, reachable member of its species.
    for quest in c.QUESTS_REF:
        for objective in quest['objectives']:
            if objective['type'] == 'kill' and objective.get('floor', 0) == 0 and quest['id'].startswith('hunt_'):
                candidates = [s for s in c.SPAWNS if s[0] == objective['target'] and s[3] == 0]
                if candidates:
                    target = min(candidates, key=lambda s: math.hypot(s[1]-objective['x'], s[2]-objective['y']))
                    objective['x'], objective['y'] = target[1:3]
