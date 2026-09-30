"""Deterministic walking-scale encounters composed from existing surface mobs.

Only spawn coordinates change. Species, indices, floors and stat blocks keep
their identities, as do the starter, named hunts and authored quest encounters.
Navigation and spatial indexes below exist only while constructing the world.
"""
import heapq
import math
from collections import Counter, defaultdict
from copy import deepcopy

try:
    from .continent_world import region_at
    from .living_world import segment_distance
except ImportError:
    from continent_world import region_at
    from living_world import segment_distance


CELL = 256
STEP = 64
FAMILIES = {
    'wolves': ('den', 'Wilcze ostępy', ('wolf','boar','bear')),
    'spiders': ('web', 'Pajęcze zagłębienie', ('spider','spitting_spider')),
    'bandits': ('camp', 'Rozbójniczy trakt', ('bandit','bandit_archer','bandit_veteran')),
    'elves': ('ruin', 'Leśna strażnica', ('elf','thorn_shaman')),
    'trolls': ('den', 'Ostęp trolli', ('troll','wolf')),
    'goblins': ('camp', 'Obóz Zielonego Kła', ('goblin','troll')),
    'orcs': ('camp', 'Orcza warownia', ('orc','orc_shaman','troll','thorn_shaman')),
    'bog': ('reeds', 'Ostępy nad rozlewiskiem', ('crocodile','spider','wisp','spitting_spider')),
    'desert': ('bones', 'Wydmowe łowisko', ('scarab','scorpion','minotaur')),
    'undead': ('crypt', 'Zarośnięta nekropolia', ('skeleton','skeleton_archer','mummy','ghoul','vampire','necromancer','lich','skeleton_sentinel','grave_acolyte','crypt_guard')),
    'dwarves': ('quarry', 'Straż kamieniołomu', ('dwarf','golem','minotaur')),
    'harpies': ('bones', 'Gniazda na skalnych półkach', ('harpy','ogre')),
    'frost_wolves': ('den', 'Legowisko śnieżnych wilków', ('frost_wolf',)),
    'ice': ('crystals', 'Lodowe zagłębienie', ('ice_elemental','frost_giant','golem')),
    'frost_guard': ('camp', 'Obozowisko Zimowej Straży', ('frost_ranger',)),
    'dragons': ('bones', 'Smocze ostępy', ('dragon','dragon_lord')),
    'rift': ('rift', 'Pęknięcie spopielonej ziemi', ('demon','fire_elemental','nightmare')),
    'abyss': ('rift', 'Ostępy obsydianowej straży', ('abyss_walker','ancient_guardian','demon','obsidian_knight')),
}
REGIONAL_FAMILIES = (
    ('wolves','spiders','bandits','goblins','undead','bog','harpies'),
    ('wolves','spiders','bandits','elves','trolls'), ('orcs','goblins'),
    ('desert','bandits'), ('desert','undead'), ('bog','spiders'),
    ('elves','bandits','orcs'), ('undead',), ('undead','dwarves'),
    ('dragons','rift'), ('orcs','bandits','dwarves'), ('dwarves','harpies','ice'),
    ('frost_wolves','dwarves','ice','frost_guard'), ('frost_wolves','ice','frost_guard'),
    ('dragons','ice'), ('elves','undead'), ('undead','rift'),
    ('rift','dragons'), ('abyss','rift'), ('abyss','rift'),
)
RANGED = {'bandit_archer','elf','orc_shaman','thorn_shaman','skeleton_archer',
          'necromancer','lich','grave_acolyte','frost_ranger'}


def ranged(c,kind):
    spec=c.ENEMIES[kind]
    return kind in RANGED or bool(spec.get('projectile')) or (
        spec.get('combat_role') in ('ranged','hybrid') and spec.get('range',0)>200)


def _group_layout(family,number):
    """Tangent/away-from-road offsets and size; ecology determines composition."""
    if family in ('wolves','trolls','frost_wolves'):
        rows=[(-650,40,4),(480,320,4),(60,700,1)]
    elif family in ('dragons','harpies'):
        rows=[(-620,120,2),(620,430,2),(80,740,1)]
    elif family=='spiders':
        rows=[(-630,100,4),(450,550,4)]
    elif family in ('bandits','orcs','elves','frost_guard','goblins'):
        rows=[(-360,0,2),(260,480,3),(-780,310,2+number%2)]
    elif family=='undead':
        rows=[(-420,70,4),(200,550,3),(730,20,2)]
    elif family=='bog':
        rows=[(-590,120,3),(440,610,4),(-110,850,1)]
    elif family=='desert':
        rows=[(-610,20,4),(520,500,3),(30,870,2)]
    elif family=='dwarves':
        rows=[(-460,80,3),(280,540,4),(-820,420,2)]
    else:
        rows=[(-670,0,3),(480,430,3),(-60,800,2)]
    # Mirror alternate habitats; group count and shapes remain family-specific.
    return [((t if number%2==0 else -t),depth,size) for t,depth,size in rows]


class Residents:
    def __init__(self, rows):
        self.cells = defaultdict(set);self.positions = {}
        for i,(kind,x,y,floor) in enumerate(rows):
            if not floor:self.put(i,x,y)

    def put(self, i,x,y):
        if i in self.positions:
            px,py = self.positions[i];self.cells[(int(px//CELL),int(py//CELL))].discard(i)
        self.positions[i] = (x,y);self.cells[(int(x//CELL),int(y//CELL))].add(i)

    def near(self,x,y,radius,ignore=None):
        for cx in range(math.floor((x-radius)/CELL),math.floor((x+radius)/CELL)+1):
            for cy in range(math.floor((y-radius)/CELL),math.floor((y+radius)/CELL)+1):
                for i in self.cells.get((cx,cy),()):
                    if i==ignore:continue
                    px,py=self.positions[i]
                    if math.hypot(x-px,y-py)<radius:yield i


class Geometry:
    def __init__(self,c,obstacles):
        self.c=c;self.obstacles=defaultdict(list);self.free_cache={};self.edge_cache={};self.open_cells={}
        for o in obstacles:
            if o.get('floor',0):continue
            for cx in range(math.floor((o['x']-22)/CELL),math.floor((o['x']+o['w']+22)/CELL)+1):
                for cy in range(math.floor((o['y']-22)/CELL),math.floor((o['y']+o['h']+22)/CELL)+1):
                    self.obstacles[(cx,cy)].append(o)
        self.roads=defaultdict(list)
        for path in c.ROADS:
            for a,b in zip(path,path[1:]):
                for cx in range(math.floor(min(a[0],b[0])/512),math.floor(max(a[0],b[0])/512)+1):
                    for cy in range(math.floor(min(a[1],b[1])/512),math.floor(max(a[1],b[1])/512)+1):
                        self.roads[(cx,cy)].append((a,b))

    def free(self,x,y):
        if not 22<x<self.c.WIDTH-22 or not 22<y<self.c.HEIGHT-22:return False
        cell=(int(x//CELL),int(y//CELL))
        if cell not in self.open_cells:
            cx,cy=(cell[0]+.5)*CELL,(cell[1]+.5)*CELL
            radius=math.hypot(CELL/2,CELL/2)+22
            rivers=getattr(self.c.WATER_MAP,'rivers',self.c.WATER_MAP)
            self.open_cells[cell]=(not self.obstacles.get(cell) and
                self.c.GEOGRAPHY.land(cx,cy,radius) is not None and not rivers.blocked(cx,cy,radius))
        if self.open_cells[cell]:return True
        if self.c.WATER_MAP.blocked(x,y,22):return False
        return not any(o['x']-22<x<o['x']+o['w']+22 and o['y']-22<y<o['y']+o['h']+22
                       for o in self.obstacles.get((int(x//CELL),int(y//CELL)),()))

    def line(self,a,b):
        # 22px generation clearance and <=8px sampling cover the18px actor
        # continuously, including narrow diagonal corners between colliders.
        n=max(1,math.ceil(math.dist(a,b)/8))
        return all(self.free(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n+1))

    def nearest_roads(self,x,y,radius=2200):
        seen=set();out=[]
        for cx in range(math.floor((x-radius)/512),math.floor((x+radius)/512)+1):
            for cy in range(math.floor((y-radius)/512),math.floor((y+radius)/512)+1):
                for a,b in self.roads.get((cx,cy),()):
                    key=(tuple(a),tuple(b))
                    if key in seen:continue
                    seen.add(key);dx,dy=b[0]-a[0],b[1]-a[1]
                    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
                    p=(a[0]+dx*t,a[1]+dy*t);distance=math.hypot(x-p[0],y-p[1])
                    if distance<=radius:out.append((distance,p))
        return sorted(out,key=lambda row:row[0])

    def road_distance(self,x,y,limit):
        rows=self.nearest_roads(x,y,limit)
        return rows[0][0] if rows else float('inf')

    def path(self,start,goal,max_nodes=450):
        if self.line(start,goal):return [list(start),list(goal)]
        # Global lattice coordinates allow nearby groups to reuse collision
        # work. Every edge still uses the actual world collision geometry.
        def point(node):return node[0]*STEP,node[1]*STEP
        def free(node):
            p=point(node);key=(round(p[0],1),round(p[1],1))
            if key not in self.free_cache:self.free_cache[key]=self.free(*p)
            return self.free_cache[key]
        base=(round(start[0]/STEP),round(start[1]/STEP))
        starts=sorted(((base[0]+dx,base[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1)),key=lambda n:math.dist(start,point(n)))
        first=next((n for n in starts if free(n) and self.line(start,point(n))),None)
        if first is None:return None
        queue=[(math.dist(point(first),goal),0,first)];cost={first:0};parent={};visited=0
        while queue and visited<max_nodes:
            _,g,node=heapq.heappop(queue)
            if g!=cost.get(node):continue
            visited+=1;p=point(node)
            if math.dist(p,goal)<=STEP*1.5 and self.line(p,goal):
                nodes=[node]
                while nodes[-1] in parent:nodes.append(parent[nodes[-1]])
                nodes.reverse();raw=[list(start)]+[list(point(n)) for n in nodes]+[list(goal)]
                # Collapse collinear steps without replacing turns by shortcuts.
                result=[raw[0]]
                for i in range(1,len(raw)-1):
                    a,b,d=raw[i-1],raw[i],raw[i+1]
                    if abs((b[0]-a[0])*(d[1]-b[1])-(b[1]-a[1])*(d[0]-b[0]))>.001:result.append(b)
                result.append(raw[-1]);return result
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                nxt=(node[0]+dx,node[1]+dy);np=point(nxt)
                ng=g+math.hypot(dx,dy)*STEP
                if ng>=cost.get(nxt,float('inf')) or ng>4200 or not free(nxt):continue
                edge=(tuple(p),tuple(np))
                if edge not in self.edge_cache:self.edge_cache[edge]=self.line(p,np)
                if not self.edge_cache[edge]:continue
                cost[nxt]=ng;parent[nxt]=node
                heapq.heappush(queue,(ng+math.dist(np,goal),ng,nxt))
        return None

    def connect_route(self,point,route):
        candidates=[]
        for j,(a,b) in enumerate(zip(route,route[1:])):
            dx,dy=b[0]-a[0],b[1]-a[1]
            t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/max(1,dx*dx+dy*dy)))
            q=(a[0]+dx*t,a[1]+dy*t)
            candidates.append((math.dist(point,q),j,q))
        for _,j,q in sorted(candidates)[:3]:
            if self.line(point,q):return [list(point),list(q)]+route[j+1:]
        return None


def _protected(c,rows,landmarks):
    protected={};residents=Residents(rows)
    for i,(kind,x,y,floor) in enumerate(rows):
        if floor:protected[i]='other_floor'
        elif x<7000 and y<6600:protected[i]='starter'
        elif c.ENEMIES[kind].get('boss') or kind=='boss':protected[i]='boss'
        elif kind.startswith(('adv_','exp_')):protected[i]='authored_kind'
    pins=[(g['x'],g['y'],'named_habitat') for g in c.HUNTING_GROUNDS if g.get('name') and not g.get('floor',0)]
    pins.extend((x,y,'boss_neighbors') for kind,x,y,floor in rows
                if not floor and (c.ENEMIES[kind].get('boss') or kind=='boss'))
    pins.extend((g['x'],g['y'],'loot_hunt') for g in c.LOOT_HUNTS if not g.get('floor',0))
    pins.extend((p['x'],p['y'],'final_loot_pin') for p in landmarks
                if p['id'].startswith('loot_hunt_') and not p.get('floor',0))
    for x,y,reason in pins:
        for i in residents.near(x,y,700.01):protected.setdefault(i,reason)
    for anchor in c.ADVENTURE_ANCHORS.values():
        for i in residents.near(anchor['x'],anchor['y'],900.01):protected.setdefault(i,'adventure_approach')
    for q in c.QUESTS_REF:
        for objective in q['objectives']:
            if objective['type']!='kill' or objective.get('floor',0) or 'x' not in objective:continue
            matches=[(math.hypot(x-objective['x'],y-objective['y']),i)
                     for i,(kind,x,y,floor) in enumerate(rows) if not floor and kind==objective['target']]
            if matches:protected.setdefault(min(matches)[1],'quest_target')
    return protected


def _anchors(c,geo):
    anchors=[]
    for p in c.TERRAIN_DETAIL['pockets']:
        anchors.append(dict(x=p['x'],y=p['y'],region_id=p['region_id'],relief_id=p['id'],
                            origin='relief',theme=p['theme']))
    # Small encampments frame existing approaches, well beyond safe settlements.
    for city in c.CITIES:
        segments=[]
        for path in c.ROADS:
            for p in path[::12]:
                distance=math.hypot(p[0]-city['x'],p[1]-city['y'])
                if city['radius']+1200<distance<city['radius']+2800:segments.append((distance,p))
        selected=[]
        for _,p in sorted(segments,key=lambda row:row[0]):
            if any(math.dist(p,q)<1300 for q in selected):continue
            region=region_at(c.REGIONS,*p)
            if not region:continue
            selected.append(p)
            anchors.append(dict(x=p[0],y=p[1],region_id=region['id'],relief_id='',
                                origin='city',theme='approach',city_id=city['id']))
            if len(selected)>=2:break
    return anchors


def _choose_family(ri,number,theme,pools,used,identities,landmass_id):
    choices=list(REGIONAL_FAMILIES[ri])
    if theme in ('wooded_valley','forest_clearing','field_copse','root_ridge'):
        choices.sort(key=lambda family:family not in ('wolves','spiders','elves','trolls'))
    elif theme in ('marsh_hummocks','reed_banks'):choices.sort(key=lambda family:family!='bog')
    elif theme in ('rock_pass','broken_ridge','stone_shelf'):choices.sort(key=lambda family:family not in ('dwarves','harpies','orcs','ice'))
    elif theme in ('desert_gully','dune_basin'):choices.sort(key=lambda family:family!='desert')
    elif theme=='ash_rift':choices.sort(key=lambda family:family not in ('rift','abyss'))
    offset=number%len(choices)
    for family in choices[offset:]+choices[:offset]:
        if sum(i not in used and identities[i][1]==landmass_id
               for kind in FAMILIES[family][2] for i in pools.get(kind,()))>=7:return family
    return None


def _destination(c,geo,residents,kind,point,source_index,region_id,landmass_id,interactions):
    x,y=point;spec=c.ENEMIES[kind];wander=spec.get('wander',175)
    # Idle AI may overshoot wander by45; the additional75 covers road width.
    clearance=spec.get('base_aggro',spec['aggro'])+wander+120
    # The buffer also prevents ordinary wandering into the preserved starter.
    if x<7800 and y<7400:return None
    region=region_at(c.REGIONS,x,y)
    if not region or region['id']!=region_id:return None
    land=c.GEOGRAPHY.land(x,y,25)
    if not land or land['id']!=landmass_id or not geo.free(x,y):return None
    if geo.road_distance(x,y,clearance+1)<clearance:return None
    for p in interactions:
        if math.hypot(x-p['x'],y-p['y'])<clearance+p.get('radius',0):return None
    if next(residents.near(x,y,160,source_index),None) is not None:return None
    neighbors=list(residents.near(x,y,240,source_index))
    if len(neighbors)>=4:return None
    for neighbor in neighbors:
        if sum(1 for _ in residents.near(*residents.positions[neighbor],240,source_index))>=4:return None
    # A reachable fan gives the AI several genuine wander destinations, rather
    # than placing its home in an isolated free tile between colliders.
    open_directions=0
    for j in range(8):
        a=j*math.pi/4;end=(x+math.cos(a)*wander*.85,y+math.sin(a)*wander*.85)
        if geo.line(point,end):open_directions+=1
    if open_directions<5:return None
    return dict(wander=wander,road_clearance=clearance,open_wander_directions=open_directions)


def configure(c,obstacles,landmarks):
    """Compose the final world once, after UI29 geometry has been finalized."""
    if not hasattr(c,'_encounter_original_spawns'):
        c._encounter_original_spawns=list(c.SPAWNS)
        c._encounter_original_grounds=deepcopy(c.HUNTING_GROUNDS)
    c.SPAWNS[:]=c._encounter_original_spawns
    c.HUNTING_GROUNDS[:]=deepcopy(c._encounter_original_grounds)
    original=c._encounter_original_spawns;protected=_protected(c,original,landmarks)
    geo=Geometry(c,obstacles);residents=Residents(original)
    pools=defaultdict(lambda:defaultdict(list));identities={};crowd={}
    for i,(kind,x,y,floor) in enumerate(original):
        if i in protected:continue
        region=region_at(c.REGIONS,x,y);land=c.GEOGRAPHY.land(x,y)
        if not region or not land:continue
        identities[i]=(region['id'],land['id']);pools[region['id']][kind].append(i)
        crowd[i]=sum(1 for _ in residents.near(x,y,220,i))
    interactions=list(getattr(c,'SAFE_ZONES',c.CITIES))+list(c.PORTS)
    interactions.extend(p for p in c.NPCS if not p.get('floor',0))
    sites=[];moves=[];used=set();region_numbers=Counter();skipped=Counter()
    for anchor in _anchors(c,geo):
        region_id=anchor['region_id'];ri=int(region_id.split('_')[-1]);number=region_numbers[region_id]
        anchor_land=c.GEOGRAPHY.land(anchor['x'],anchor['y'])
        if not anchor_land:skipped['anchor_water']+=1;continue
        family=_choose_family(ri,number,anchor['theme'],pools[region_id],used,identities,anchor_land['id'])
        if not family:skipped['no_family']+=1;continue
        nearest=geo.nearest_roads(anchor['x'],anchor['y'],2400)
        if not nearest:skipped['no_road']+=1;continue
        # The outward direction keeps the approach visible while maintaining
        # the species-specific unprovoked aggression margin around the road.
        road=nearest[0][1];dx,dy=anchor['x']-road[0],anchor['y']-road[1];length=math.hypot(dx,dy)
        if length<80:
            other=nearest[min(12,len(nearest)-1)][1]
            dx,dy=-(other[1]-road[1]),other[0]-road[0];length=max(1,math.hypot(dx,dy))
        nx,ny=dx/max(1,length),dy/max(1,length);tx,ty=-ny,nx
        desired=max(950,min(1500,length+450))
        center=(road[0]+nx*desired,road[1]+ny*desired)
        # Different anchor origins select asymmetry, not a common circular camp.
        group_centers=[((center[0]+tx*t+nx*depth,center[1]+ty*t+ny*depth),size)
                       for t,depth,size in _group_layout(family,number)]
        decoration,label,kinds=FAMILIES[family]
        site_id='encounter_'+anchor.get('relief_id','') if anchor.get('relief_id') else f'encounter_city_{anchor.get("city_id","road")}_{len(sites)}'
        site=dict(id=site_id,x=round(center[0],1),y=round(center[1],1),region_id=region_id,
                  origin=anchor['origin'],relief_id=anchor.get('relief_id',''),theme=anchor['theme'],
                  family=family,encounter_label=label,decoration=decoration,groups=[],indices=[])
        for group_number,(gcenter,wanted) in enumerate(group_centers):
            group_id=f'{site_id}_group_{group_number}'
            available=[i for kind in kinds for i in pools[region_id].get(kind,())
                       if i not in used and identities[i][1]==anchor_land['id']]
            available.sort(key=lambda i:(-min(crowd[i],12),math.dist(original[i][1:3],gcenter),i))
            group=dict(id=group_id,x=round(gcenter[0],1),y=round(gcenter[1],1),indices=[])
            group_route=None
            for shift in (0,160,-160):
                hub=(gcenter[0]+nx*shift,gcenter[1]+ny*shift)
                if not geo.free(*hub):continue
                destinations=geo.nearest_roads(*hub,2200)
                if not destinations:continue
                group_route=geo.path(hub,destinations[0][1])
                if group_route:break
            if group_route is None:continue
            group['approach']=group_route
            while len(group['indices'])<wanted:
                slot=len(group['indices']);placed=False;failed_kinds=set()
                # Explicit role slots ensure archers/shamans are represented.
                prefer_ranged=slot==wanted-1 and any(ranged(c,original[i][0]) and i not in used for i in available)
                ordered=sorted((i for i in available if i not in used),key=lambda i:ranged(c,original[i][0])!=prefer_ranged)
                for i in ordered:
                    kind,sx,sy,floor=original[i];landmass_id=identities[i][1]
                    if kind in failed_kinds:continue
                    for attempt in range(18):
                        depth=(80 if ranged(c,kind) else -85)+((attempt//6)-1)*110
                        if family in ('wolves','trolls','frost_wolves','dragons','harpies'):
                            depth+=(-55,70,-20,115)[slot%4]
                        side=(-175,35,245,-335)[slot%4]+((attempt%6)-2.5)*95
                        point=(round(gcenter[0]+tx*side+nx*depth,1),round(gcenter[1]+ty*side+ny*depth,1))
                        details=_destination(c,geo,residents,kind,point,i,region_id,landmass_id,interactions)
                        if details is None:continue
                        route=geo.connect_route(point,group_route)
                        if route is None:continue
                        c.SPAWNS[i]=(kind,point[0],point[1],floor);residents.put(i,*point);used.add(i)
                        group['indices'].append(i);site['indices'].append(i)
                        moves.append(dict(index=i,kind=kind,floor=floor,region_id=region_id,landmass_id=landmass_id,
                            source=[sx,sy],destination=list(point),site_id=site_id,group_id=group_id,
                            access_path=route,**details))
                        placed=True;break
                    if placed:break
                    failed_kinds.add(kind)
                if not placed:break
            if group['indices']:site['groups'].append(group)
        if not site['indices']:skipped['no_usable_positions']+=1;continue
        sites.append(site);region_numbers[region_id]+=1
        for group in site['groups']:
            rows=[c.SPAWNS[i] for i in group['indices']]
            gx=sum(p[1] for p in rows)/len(rows);gy=sum(p[2] for p in rows)/len(rows)
            if not geo.free(gx,gy):
                nearby=None
                for radius in range(16,161,16):
                    for j in range(16):
                        angle=math.tau*j/16
                        point=(round(gx+math.cos(angle)*radius,1),round(gy+math.sin(angle)*radius,1))
                        if (geo.free(*point) and
                                all(math.hypot(row[1]-point[0],row[2]-point[1])<=700 for row in rows)):
                            nearby=point;break
                    if nearby:break
                if nearby:gx,gy=nearby
                else:
                    point=min(rows,key=lambda row:math.hypot(row[1]-gx,row[2]-gy));gx,gy=point[1:3]
            group.update(x=round(gx,1),y=round(gy,1))
            c.HUNTING_GROUNDS.append(dict(id=group['id'],name='',encounter_label=label,
                encounter_site=site_id,x=round(gx,1),y=round(gy,1),floor=0,region_id=region_id,
                kind=rows[0][0],members=[row[0] for row in rows],decoration=decoration,
                spawn_indices=list(group['indices']),encounter_layout_version=1))
        if not geo.free(site['x'],site['y']):site.update(x=site['groups'][0]['x'],y=site['groups'][0]['y'])
    # Retain named ground identity and every field. Anonymous decorations only
    # survive when they still describe actual local residents after relocation.
    coherent=[]
    for ground in c.HUNTING_GROUNDS:
        if (ground.get('name') or ground.get('encounter_layout_version') or
                ground['x']<7000 and ground['y']<6600):
            coherent.append(ground);continue
        nearby=list(residents.near(ground['x'],ground['y'],450))
        if not nearby:continue
        members=[c.SPAWNS[i][0] for i in nearby]
        original_members=set(ground.get('members',()))
        relevant=[kind for kind in members if kind in original_members]
        if not relevant:continue
        ground['members']=relevant;ground['kind']=relevant[0];coherent.append(ground)
    c.HUNTING_GROUNDS[:]=coherent
    c.ENCOUNTER_LAYOUT=dict(version=1,protected_starter=[0,0,7000,6600],starter_buffer=800,
        sites=sites,moves=moves,protected_indices=sorted(protected),
        counts=dict(sites=len(sites),groups=sum(len(site['groups']) for site in sites),moved=len(moves),
            original_surface=sum(not row[3] for row in original),background_surface=sum(not row[3] for row in original)-len(moves),
            protected=len(protected),protected_reasons=dict(Counter(protected.values())),
            regions=dict(Counter(move['region_id'] for move in moves)),
            families=dict(Counter(site['family'] for site in sites)),skipped=dict(skipped)))
    return c.ENCOUNTER_LAYOUT
