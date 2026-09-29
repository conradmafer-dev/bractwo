"""0.8.8 original monster variants, animated sprite metadata and authored habitats.
Append-only spawns preserve IDs of earlier quest monsters and deterministic world layout.
"""
try:
    from .continent_world import region_at
except ImportError:
    from continent_world import region_at

import math
from copy import deepcopy
try:
    from .loot_content import DROPS
except ImportError:
    from loot_content import DROPS

# id, source, name, level, HP, AC, attack bonus, dice, speed, role, projectile, size
DEFINITIONS=[
 ('bandit_veteran','bandit','Bandyta weteran',16,39,14,5,[2,6,2],132,'melee',None,1.10),
 ('bandit_captain','orc_king','Herszt Czarnego Traktu',24,110,16,6,[1,10,3],145,'hybrid','arrow',1.38),
 ('skeleton_sentinel','skeleton','Szkielet pancerny',18,39,16,5,[1,8,3],92,'melee',None,1.12),
 ('grave_acolyte','necromancer','Grobowy akolita',22,45,12,5,[1,8,2],112,'ranged','shadow',1.05),
 ('thorn_shaman','orc_shaman','Szaman Ciernistego Kręgu',18,39,13,5,[1,8,2],115,'ranged','venom',1.08),
 ('crypt_guard','skeleton','Strażnik zapieczętowanej krypty',38,91,17,7,[2,8,3],102,'melee',None,1.27),
 ('mummy_hierophant','lich_king','Mumia Hierofanta',48,220,16,8,[2,8,4],112,'hybrid','shadow',1.50),
 ('frost_ranger','elf','Łucznik Zimowej Straży',52,117,15,7,[2,8,3],161,'ranged','arrow',1.10),
 ('obsidian_knight','ancient_guardian','Obsydianowy rycerz',90,221,19,10,[3,8,5],140,'hybrid','shadow',1.38),
]
NEW_KINDS=[s[0] for s in DEFINITIONS]
BOSSES={'bandit_captain','mummy_hierophant'}
PALETTES={
 'bandit_veteran':('#735746','#c2b495','#d27b47'), 'bandit_captain':('#583e53','#d3b384','#ee6f49'),
 'skeleton_sentinel':('#647585','#eadbc3','#8be2e7'), 'grave_acolyte':('#574875','#c8bd9e','#b39bef'),
 'thorn_shaman':('#3b765a','#bdb080','#b5e787'), 'crypt_guard':('#496e78','#d4c79f','#5fdfc5'),
 'mummy_hierophant':('#9c803f','#ebd7a8','#6be3d2'), 'frost_ranger':('#668da8','#d0e4ef','#8bdef2'),
 'obsidian_knight':('#403b56','#a69bc5','#ed9258')}


def configure(enemies):
    # Public levels for the older starter creatures; combat values are unchanged.
    for k,level in {'rat':1,'boar':2,'wolf':3,'goblin':3,'spider':5,'skeleton':8,'wisp':6,'guardian':8,'boss':8}.items():
        enemies[k].setdefault('level',level)
    for key,source,name,level,hp,ac,atk,dice,speed,role,projectile,size in DEFINITIONS:
        s=deepcopy(enemies[source]);boss=key in BOSSES
        s.update(name=name,level=level,hp=hp,hp_dice=[max(1,round(hp/6.5)),8,0],armor_class=ac,
            damage_dice=dice[:],melee_dice=dice[:],special_dice=[dice[0]+(2 if boss else 1),dice[1],dice[2]],
            attack_bonus=atk,damage=dice[0]*(dice[1]+1)/2+dice[2],melee_damage=dice[0]*(dice[1]+1)/2+dice[2],
            speed=speed,size=size,boss=boss,combat_role=role,range=420 if projectile else 68,
            melee_range=72 if boss else 56,attack_interval=3.4 if key=='crypt_guard' else 3.0,
            ranged_interval=4.8 if boss else 3.8 if role=='hybrid' else 3.2,
            windup=.7 if boss else .55,aggro=550 if boss else 430 if projectile else 360,
            base_aggro=550 if boss else 430 if projectile else 360,leash=1100 if boss else 850,
            wander=95 if boss else 135,respawn=150 if boss else 35+level//2,
            xp=level*32 if boss else 25+level*5,gold=level*4 if boss else 5+level,
            save_bonus=min(8,1+level//16),save_dc=11+level//18+(2 if boss else 0),
            creature_type='undead' if key in ('skeleton_sentinel','grave_acolyte','crypt_guard','mummy_hierophant') else 'humanoid',
            sprite=f'assets/monsters/{key}.png',sprite_frame_width=80,sprite_frame_height=80,sprite_frames=4,
            appearance='skeleton' if key in ('skeleton_sentinel','crypt_guard','mummy_hierophant') else 'goblin',
            color=PALETTES[key][0],content_version='0.8.8')
        s['saves']={a:s['save_bonus'] for a in ('strength','dexterity','constitution','intelligence','wisdom','charisma')}
        if projectile:s['projectile']=projectile
        else:s.pop('projectile',None)
        if boss:s['special_range']=610
        else:s.pop('special_range',None)
        # No invented HP dice: show the actual fixed regional stat block.
        s['hp_dice']=[hp,1,0]
        enemies[key]=s
    # The two requested loot carriers now also look the part, instead of a generic axeman.
    for key in ('mummy','skeleton_archer'):
        enemies[key].update(sprite=f'assets/monsters/{key}.png',sprite_frame_width=80,
                            sprite_frame_height=80,sprite_frames=4)


def place(c, obstacles, landmarks):
    """Select existing safe, reachable habitats; add finite, reproducible spawns.
    Every new spawn connects to a pre-existing walkable point in the same ground.
    No original spawn or quest is removed, moved or re-numbered.
    """
    def clear(x,y):
        r=20
        if not (r<x<c.WIDTH-r and r<y<c.HEIGHT-r):return False
        if any(math.hypot(x-z['x'],y-z['y'])<850 for z in c.CITIES):return False
        if c.WATER_MAP.blocked(x,y,r):return False
        if x+r>1500 and x-r<1680 and y-r<2304 and (y-r<1080 or y+r>1230):return False
        return not any(o.get('floor',0)==0 and x+r>o['x'] and x-r<o['x']+o['w']
                       and y+r>o['y'] and y-r<o['y']+o['h'] for o in obstacles)
    def connected(x,y,a,b):
        n=max(1,math.ceil(math.hypot(x-a,y-b)/18))
        return all(clear(a+(x-a)*i/n,b+(y-b)*i/n) for i in range(n+1))
    originals=list(c.SPAWNS)
    # Spatial index keeps world generation bounded on a large continent.
    cells={}
    for kind,x,y,floor in originals:
        if floor==0:cells.setdefault((int(x//600),int(y//600)),[]).append((kind,x,y))
    def attach(kind,g,index):
        x,y=g['x'],g['y'];cx,cy=int(x//600),int(y//600)
        near=[s for dx in (-1,0,1) for dy in (-1,0,1) for s in cells.get((cx+dx,cy+dy),[]) if math.hypot(s[1]-x,s[2]-y)<450]
        for _,ax,ay in sorted(near,key=lambda s:math.hypot(s[1]-x,s[2]-y)):
            if not clear(ax,ay):continue
            for distance in (110,160,210):
                for j in range(12):
                    angle=(j+index%12)*math.pi/6
                    px,py=round(ax+math.cos(angle)*distance),round(ay+math.sin(angle)*distance)
                    if not connected(px,py,ax,ay):continue
                    if any(math.hypot(px-s[1],py-s[2])<55 for s in near):continue
                    if any(z==0 and math.hypot(px-bx,py-by)<55 for _,bx,by,z in c.SPAWNS[len(originals):]):continue
                    c.SPAWNS.append((kind,px,py,0))
                    if kind not in g['members']:g['members'].append(kind)
                    return px,py
        return None
    rules=[
       ('bandit_veteran',{'bandit','bandit_archer'},{'region_0','region_1','region_6','region_10'},18),
       ('skeleton_sentinel',{'skeleton','skeleton_archer'},{'region_0','region_7','region_8'},18),
       ('grave_acolyte',{'skeleton','ghoul','necromancer'},{'region_0','region_7','region_8'},16),
       ('thorn_shaman',{'elf','orc_shaman'},{'region_1','region_2','region_6','region_15'},16),
       ('crypt_guard',{'mummy','necromancer'},{'region_4','region_8','region_15'},18),
       ('frost_ranger',{'frost_wolf','ice_elemental'},{'region_12','region_13'},20),
       ('obsidian_knight',{'demon','ancient_guardian'},{'region_18','region_19'},18),
    ]
    # Evenly distributed, not solely clustered at the beginning of each region.
    added=[]
    for kind,members,regions,limit in rules:
        pool=[g for g in c.HUNTING_GROUNDS if g.get('floor',0)==0 and g.get('region_id') in regions
              and set(g.get('members',[]))&members and math.hypot(g['x']-560,g['y']-1180)>1800]
        # A nearby first location makes the additions discoverable without crossing the continent.
        pool.sort(key=lambda g:(g['x']*g['y']%104729,g['id']))
        count=0
        for i,g in enumerate(pool):
            pos=attach(kind,g,i)
            if pos:
                added.append((kind,*pos));count+=1
                if count>=limit:break
        if not count:raise ValueError('Nie znaleziono miejsca dla '+kind)
    for kind,members,region in [('bandit_captain',{'bandit','bandit_archer'},'region_1'),
                                ('mummy_hierophant',{'mummy','necromancer'},'region_4')]:
        pool=[g for g in c.HUNTING_GROUNDS if g.get('floor',0)==0 and g.get('region_id')==region and set(g.get('members',[]))&members]
        # Place a single boss near a habitat connected to a road.
        pool.sort(key=lambda g: min(math.hypot(g['x']-p[0],g['y']-p[1]) for path in c.ROADS for p in path))
        for i,g in enumerate(pool):
            pos=attach(kind,g,i)
            if pos:
                added.append((kind,*pos));g['name']=c.ENEMIES[kind]['name']+' · siedziba'
                break
        else:raise ValueError('Nie znaleziono siedziby bossa '+kind)
    c.LOOT_HUNTS=[]
    for kind in NEW_KINDS:
        spots=[(x,y) for k,x,y in added if k==kind]
        # Nearest to the starter town is listed in the player-facing atlas and release guide.
        x,y=min(spots,key=lambda p:math.hypot(p[0]-560,p[1]-1180))
        region=region_at(c.REGIONS,x,y) or min(c.REGIONS,key=lambda r:math.hypot(x-r.get('label_x',r['x']+r['w']/2),y-r.get('label_y',r['y']+r['h']/2)))
        s=c.ENEMIES[kind]
        entry=dict(id='loot_hunt_'+kind,name=s['name'],kind=kind,x=x,y=y,floor=0,
                   region=region['name'],level=s['level'],count=len(spots))
        c.LOOT_HUNTS.append(entry)
        landmarks.append(dict(id=entry['id'],name=s['name']+' · łowisko',x=x,y=y,floor=0,radius=105,
            biome=region['biome'],recommended_level=s['level'],
            description=f"{region['name']}. Przeciwnik poziomu {s['level']}. "+'Możliwe łupy: '+', '.join(c.ITEMS[k]['name'] for k,p in DROPS[kind]),reward={'xp':0,'gold':0}))
    return added
