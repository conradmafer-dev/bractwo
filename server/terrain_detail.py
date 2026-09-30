"""Small scenic landforms beside the final continental routes.

The compact starting valley is kept verbatim. These deterministic additions
compose the rest of the map at walking scale: broken ridges, wooded clearings,
gullies and dry hummocks. They add no gameplay entities, rewards or water.
Every blocker is checked against the existing travel and interaction geometry.
"""
import math
import random
from collections import Counter

try:
    from .continent_world import ContinentSurfaceMap, region_at
    from .living_world import BIOME_SURFACE
    from . import skill_content
except ImportError:
    from continent_world import ContinentSurfaceMap, region_at
    from living_world import BIOME_SURFACE
    import skill_content


SOURCE = 'terrain_detail_v1'
CELL = 512
PROFILES = {
    'meadow': ('wooded_valley', 'broken_ridge', 'field_copse'),
    'forest': ('wooded_valley', 'forest_clearing', 'root_ridge'),
    'orc': ('broken_ridge', 'rock_pass', 'field_copse'),
    'swamp': ('marsh_hummocks', 'reed_banks', 'wooded_valley'),
    'desert': ('desert_gully', 'dune_basin', 'broken_ridge'),
    'mountain': ('rock_pass', 'broken_ridge', 'stone_shelf'),
    'snow': ('snow_hollow', 'rock_pass', 'frost_ridge'),
    'ruins': ('ruin_terraces', 'root_ridge', 'broken_ridge'),
    'lava': ('ash_rift', 'stone_shelf', 'broken_ridge'),
    'obsidian': ('ash_rift', 'rock_pass', 'stone_shelf'),
}
COLORS = {
    'meadow': '#78856a', 'forest': '#62775a', 'orc': '#9b906a',
    'swamp': '#758579', 'desert': '#b29a70', 'mountain': '#929c96',
    'snow': '#afc4c8', 'ruins': '#86918b', 'lava': '#8c7168',
    'obsidian': '#787184',
}


def _starter(bounds):
    # Any overlap, rather than only an object's centre, protects the valley.
    return bounds[0] < 7000 and bounds[1] < 6600


def _intersects_segment(bounds, a, b):
    """Liang-Barsky intersection, including touching a rectangle boundary."""
    left, top, right, bottom = bounds
    dx, dy = b[0]-a[0], b[1]-a[1]
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, a[0]-left), (dx, right-a[0]),
                 (-dy, a[1]-top), (dy, bottom-a[1])):
        if abs(p) < 1e-9:
            if q < 0:return False
            continue
        t = q/p
        if p < 0:lo = max(lo, t)
        else:hi = min(hi, t)
        if lo > hi:return False
    return True


class _Protection:
    """Generation-only index; no additional work is added to simulation ticks."""
    def __init__(self):
        self.cells = {}

    def add(self, bounds, entry):
        for x in range(math.floor(bounds[0]/CELL), math.floor(bounds[2]/CELL)+1):
            for y in range(math.floor(bounds[1]/CELL), math.floor(bounds[3]/CELL)+1):
                self.cells.setdefault((x,y), []).append(entry)

    def circle(self, x, y, radius):
        self.add((x-radius,y-radius,x+radius,y+radius), ('circle',x,y,radius))

    def rectangle(self, o, margin=45):
        b = (o['x']-margin,o['y']-margin,o['x']+o['w']+margin,o['y']+o['h']+margin)
        self.add(b, ('rect',b))

    def segment(self, a, b, clearance):
        bounds = (min(a[0],b[0])-clearance,min(a[1],b[1])-clearance,
                  max(a[0],b[0])+clearance,max(a[1],b[1])+clearance)
        self.add(bounds, ('segment',a,b,clearance))

    def clear(self, bounds):
        left,top,right,bottom = bounds
        seen = set()
        for x in range(math.floor(left/CELL),math.floor(right/CELL)+1):
            for y in range(math.floor(top/CELL),math.floor(bottom/CELL)+1):
                for row in self.cells.get((x,y), ()):
                    ident = id(row)
                    if ident in seen:continue
                    seen.add(ident)
                    if row[0] == 'circle':
                        _,cx,cy,r = row
                        nx,ny = max(left,min(right,cx)),max(top,min(bottom,cy))
                        if math.hypot(nx-cx,ny-cy) <= r:return False
                    elif row[0] == 'rect':
                        l,t,r,b = row[1]
                        if right >= l and left <= r and bottom >= t and top <= b:return False
                    elif _intersects_segment((left-row[3],top-row[3],right+row[3],bottom+row[3]),row[1],row[2]):
                        return False
        return True


def _protection(c, obstacles, landmarks):
    index = _Protection()
    for path in c.ROADS:
        for a,b in zip(path,path[1:]):index.segment(a,b,112)
    for water in c.WATERWAYS:
        index.segment(water['a'],water['b'],water['width']/2+55)
    for o in obstacles:
        if not o.get('floor',0):index.rectangle(o,65)
    for city in c.CITIES:index.circle(city['x'],city['y'],city.get('radius',260)+300)
    npcs = getattr(c,'NPCS',())
    for p in list(npcs)+list(c.STAIRS)+list(getattr(c,'PORTS',()))+list(landmarks):
        if not p.get('floor',0):index.circle(p['x'],p['y'],max(200,p.get('radius',0)+80))
    for p in getattr(c,'ADVENTURE_ANCHORS',{}).values():
        index.circle(p['x'],p['y'],p.get('reserve_radius',900)+100)
    for p in c.HUNTING_GROUNDS:
        if not p.get('floor',0):index.circle(p['x'],p['y'],230)
    for _,x,y,floor in c.SPAWNS:
        if not floor:index.circle(x,y,225)
    anchors = {p['id']:p for p in list(landmarks)+list(npcs)}
    for row in skill_content.CHALLENGES:
        anchor = anchors.get(row['anchor'])
        if not anchor or anchor.get('floor',0):continue
        for offset in (row['offset'],row.get('route',row['offset'])):
            index.circle(anchor['x']+offset[0],anchor['y']+offset[1],190)
    return index


def _polygon(cx,cy,rx,ry,angle,rng):
    """An asymmetric contour, with both a broad lobe and a shallow indentation."""
    ca,sa = math.cos(angle),math.sin(angle)
    points = []
    for j in range(11):
        a = math.tau*j/11
        radius = rng.uniform(.76,1.04)*(1.10 if j in (1,2,3) else .83 if j in (6,7) else 1)
        px,py = math.cos(a)*rx*radius,math.sin(a)*ry*radius
        points.append([round(cx+px*ca-py*sa),round(cy+px*sa+py*ca)])
    return points


def _patch(c, ident, theme, kind, points, layer, biome):
    xs,ys = zip(*points)
    bounds = (min(xs),min(ys),max(xs),max(ys))
    if _starter(bounds):return None
    # Keep small authored landforms entirely inland; water retains its shape.
    if not all(c.GEOGRAPHY.land(x,y,65) for x,y in points):return None
    p = dict(x=bounds[0],y=bounds[1],w=bounds[2]-bounds[0],h=bounds[3]-bounds[1],
             kind=kind,points=points,relief_id=ident,relief_theme=theme,
             relief_layer=layer,relief_biome=biome,relief_color=COLORS.get(biome,COLORS['meadow']),
             relief_source=SOURCE)
    c.TERRAIN.append(p)
    return p


def _candidate_groups(c, landmarks):
    by_region = {r['id']:[] for r in c.REGIONS}
    # Use final routes, not the superseded uniform hunting grid.
    for path in c.ROADS:
        along = 0
        for a,b in zip(path,path[1:]):
            distance = math.dist(a,b)
            along += distance
            if along < 720 or distance < 1:continue
            along = 0
            angle = math.atan2(b[1]-a[1],b[0]-a[0])
            for side,offset in ((1,420),(-1,530),(1,760),(-1,850)):
                x = (a[0]+b[0])/2-math.sin(angle)*offset*side
                y = (a[1]+b[1])/2+math.cos(angle)*offset*side
                region = region_at(c.REGIONS,x,y)
                if region:by_region[region['id']].append((x,y,angle,'road'))
    # A smaller share of compositions frames an already existing discovery.
    for p in list(landmarks)+list(c.HUNTING_GROUNDS):
        if p.get('floor',0):continue
        for j in (0,1,2):
            angle = (p['x']*.00019+p['y']*.00013+j*2.13) % math.tau
            x,y = p['x']+math.cos(angle)*610,p['y']+math.sin(angle)*610
            region = region_at(c.REGIONS,x,y)
            if region:by_region[region['id']].append((x,y,angle+math.pi/2,'site'))
    return by_region


def _compose(c, obstacles, index, ident, theme, biome, x,y,angle,rng):
    """Open-sided layouts keep a usable central notch and several exits."""
    size = rng.choice((.78,.94,1.08,1.22))
    rx,ry = rng.randint(420,650)*size,rng.randint(230,380)*size
    base = BIOME_SURFACE.get(biome,'grass')
    wooded = theme in ('wooded_valley','forest_clearing','field_copse','root_ridge')
    wet = theme in ('marsh_hummocks','reed_banks')
    desert = theme in ('desert_gully','dune_basin')
    body = 'forest' if wooded else 'mud' if wet else 'sand' if desert else 'stone'
    edge = _patch(c,ident,theme,base,_polygon(x,y,rx*1.14,ry*1.18,angle,rng),'edge',biome)
    main = _patch(c,ident,theme,body,_polygon(x,y,rx,ry,angle,rng),'body',biome)
    if main is None:
        if edge is not None:c.TERRAIN.remove(edge)
        return None
    patches = int(edge is not None)+1
    ca,sa = math.cos(angle),math.sin(angle)
    def point(dx,dy):return x+dx*ca-dy*sa,y+dx*sa+dy*ca
    # Off-centre clearings and banks avoid concentric decoration templates.
    accents = [(-rx*.28,ry*.12,rx*.46,ry*.48),(rx*.38,-ry*.20,rx*.31,ry*.34)]
    for dx,dy,ax,ay in accents:
        px,py = point(dx,dy)
        kind = 'grass' if wooded or wet else 'ash' if biome in ('lava','obsidian') else 'snow' if biome=='snow' else base
        if _patch(c,ident,theme,kind,_polygon(px,py,ax,ay,angle+.18,rng),'accent',biome):patches += 1
    # Two broken, uneven banks; no closed wall or repeated circular enclosure.
    layouts = [(-.85,-.48),(-.43,-.80),(.18,-.76),(.73,-.49),(-.66,.63),(.46,.75)]
    if wooded:layouts = [(-.82,-.44),(-.52,-.78),(.18,-.83),(.72,-.35),(.55,.68)]
    elif wet:layouts = [(-.83,-.32),(-.28,-.78),(.71,-.45),(.60,.71)]
    elif theme in ('rock_pass','desert_gully','ash_rift'):
        layouts = [(-.84,-.57),(-.36,-.85),(.48,-.63),(.87,-.35),(-.76,.67),(.34,.83)]
    made = []
    for j,(dx,dy) in enumerate(layouts):
        px,py = point(dx*rx,dy*ry)
        px += rng.uniform(-34,34);py += rng.uniform(-28,28)
        w = rng.randint(95,175)*size
        h = rng.randint(65,112)*size
        o = dict(x=round(px-w/2),y=round(py-h/2),w=round(w),h=round(h),floor=0,
                 type='grove' if wooded else 'rock' if wet or theme=='dune_basin' else
                      'canyon' if theme in ('desert_gully','ash_rift') else 'mountain' if j%3==0 else 'rock',
                 relief_id=ident,relief_theme=theme,relief_biome=biome,relief_height=rng.randint(17,40) if wooded or wet else rng.randint(24,62),
                 relief_color=COLORS.get(biome,COLORS['meadow']),relief_source=SOURCE)
        bounds = (o['x'],o['y'],o['x']+o['w'],o['y']+o['h'])
        if _starter(bounds) or not index.clear(bounds):continue
        samples = ((bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[0],bounds[3]),(bounds[2],bounds[3]),(px,py))
        if not all(c.GEOGRAPHY.land(sx,sy,65) for sx,sy in samples):continue
        obstacles.append(o);index.rectangle(o,40);made.append(o)
    if not made:
        c.TERRAIN[:] = [p for p in c.TERRAIN if p.get('relief_id') != ident]
        return None
    return dict(id=ident,x=round(x),y=round(y),theme=theme,biome=biome,
                bounds=[main['x'],main['y'],main['w'],main['h']],patches=patches,obstacles=len(made))


def configure(c, obstacles, landmarks):
    """Apply once after gameplay/environment generation and final route layout."""
    # Re-entry during development is deterministic and cannot duplicate scenery.
    c.TERRAIN[:] = [p for p in c.TERRAIN if p.get('relief_source') != SOURCE]
    obstacles[:] = [o for o in obstacles if o.get('relief_source') != SOURCE]
    index = _protection(c,obstacles,landmarks)
    candidates = _candidate_groups(c,landmarks)
    pockets = []
    for ri,region in enumerate(c.REGIONS):
        rng = random.Random(290930+ri*7919)
        choices = candidates[region['id']]
        road = [p for p in choices if p[3]=='road'];site = [p for p in choices if p[3]=='site']
        rng.shuffle(road);rng.shuffle(site)
        # Mix discovery surroundings with roadside places without repeating
        # one spatial template throughout a whole biome.
        ordered = []
        while road or site:
            for _ in range(3):
                if road:ordered.append(road.pop())
            if site:ordered.append(site.pop())
        accepted = []
        target = 8+(ri%3==1)
        biome = region['biome'];themes = PROFILES.get(biome,PROFILES['meadow'])
        for x,y,angle,origin in ordered:
            if len(accepted)>=target:break
            if _starter((x-900,y-900,x+900,y+900)):continue
            if not c.GEOGRAPHY.land(x,y,800):continue
            if c.WATER_MAP.blocked(x,y,40) or not index.clear((x-55,y-55,x+55,y+55)):continue
            if any(math.hypot(x-p['x'],y-p['y'])<1750 for p in accepted):continue
            ident = f'relief_{region["id"]}_{len(accepted)}'
            theme = themes[(len(accepted)+ri)%len(themes)]
            pocket = _compose(c,obstacles,index,ident,theme,biome,x,y,angle,rng)
            if pocket:
                pocket.update(region_id=region['id'],origin=origin)
                accepted.append(pocket);pockets.append(pocket)
    c.TERRAIN_DETAIL = dict(version=1,protected_starter=[0,0,7000,6600],pockets=pockets,
        counts=dict(pockets=len(pockets),patches=sum(p['patches'] for p in pockets),
                    obstacles=sum(p['obstacles'] for p in pockets),
                    regions=dict(Counter(p['region_id'] for p in pockets)),
                    themes=dict(Counter(p['theme'] for p in pockets))))
    c.SURFACE_MAP = ContinentSurfaceMap(c.ROADS,c.TERRAIN,c.CITIES,c.REGIONS)
    return c.TERRAIN_DETAIL
