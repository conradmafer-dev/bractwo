"""UI33: two small, server-owned starter expeditions and personal treasures.

Geometry is appended AFTER the continent generators. Existing IDs, spawns,
quests and saves are not regenerated. Level 10 is advice, never an entry gate.
"""
from copy import deepcopy
import math
from types import SimpleNamespace

CRYPT_BOSS = 'dawn_headless_skeleton'
TOWER_BOSS = 'old_tower_archer'
CRYPT_CHEST = 'dawn_crypt_treasure'
TOWER_CHEST = 'old_tower_treasure'
BOSSES = (CRYPT_BOSS, TOWER_BOSS)
CHEST_BOSSES = {CRYPT_CHEST: CRYPT_BOSS, TOWER_CHEST: TOWER_BOSS}
TOWER_REWARDS = ('old_tower_breastplate_1', 'ring_focused_will',
                 'old_tower_shield_1', 'echo_rapier')


def configure(c, obstacles, landmarks, zones, enemies):
    if getattr(c, 'STARTER_ADVENTURES', None):
        return
    c.STARTER_ADVENTURES = dict(version=33, recommended_level=10,
        crypt_entry=dict(x=2570, y=445, floor=0),
        tower_entry=dict(x=740, y=1750, floor=0),
        treasure_rule='Osobista nagroda raz na postać. Pokonaj strażnika; bez wymaganego poziomu.')

    def room(x, y, w, h):
        return dict(x=x, y=y, w=w, h=h)

    def area(key, name, floor, rooms, theme):
        x=min(r['x'] for r in rooms); y=min(r['y'] for r in rooms)
        a=dict(id=key, name=name, floor=floor, rooms=rooms, x=x, y=y,
            w=max(r['x']+r['w'] for r in rooms)-x,
            h=max(r['y']+r['h'] for r in rooms)-y, min_level=1,
            recommended_level=10, max_level=12, theme=theme, starter_adventure=True,
            color='#a7a090' if floor>0 else '#817b85')
        (c.DUNGEONS if floor<0 else c.ELEVATIONS).append(a)
        zones.append(deepcopy(a))

    def landmark(key, name, x, y, floor, description, **extra):
        l=dict(id=key, name=name, x=x, y=y, floor=floor, radius=68,
            min_level=1, recommended_level=10, hint=True,
            biome='dungeon' if floor<0 else 'ruins', starter_adventure=True,
            description=description, reward=dict(xp=12, gold=0), **extra)
        landmarks.append(l)
        return l

    def link(key, up_name, down_name, a, b):
        for suffix, name, origin, target in [('a',up_name,a,b),('b',down_name,b,a)]:
            ident='starter_'+key+'_'+suffix
            s=dict(id=ident,name=name,x=origin[0],y=origin[1],floor=origin[2],
                to_x=target[0],to_y=target[1],to_floor=target[2],radius=52,
                min_level=1,recommended_level=10,starter_adventure=True,
                discovery_id='discovery_'+ident)
            c.STAIRS.append(s)
            landmark(s['discovery_id'],name,*origin,
                'E: przejdź. Zalecany poziom walki: 10; wejście jest dostępne od początku.',
                source_kind='stair')

    def prop(kind, x,y,w,h,floor=0):
        obstacles.append(dict(type=kind,x=x,y=y,w=w,h=h,floor=floor,starter_adventure=True))

    # The mausoleum faces south, directly in the existing Dawn Courtyard.
    # Its collision does not replace any ruin or move the surface skeletons.
    prop('dawn_mausoleum',2505,365,130,48)
    link('dawn_entry','Krypty Świtu · wejście','Dziedziniec Świtu · wyjście',
         (2570,445,0),(2570,445,-1))
    # Three chambers connected by generous corridors. All are below the ruins;
    # no overlap with the old Mine Under the Mill, also on floor -1.
    rooms=[room(2410,330,340,310),room(2730,440,180,125),
           room(2870,310,340,330),room(3040,605,125,210),
           room(2860,775,490,400)]
    area('starter_dawn_crypt','Krypty Świtu',-1,rooms,'dawn_crypt')
    for x,y in [(2445,530),(2905,345),(3110,345),(2895,1045),(3245,1045)]:
        prop('dawn_sarcophagus',x,y,64,94,-1)
    for x,y in [(2450,370),(2690,370),(2910,580),(3300,820)]:
        prop('dawn_brazier',x,y,22,24,-1)
    c.SPAWNS.extend([('dawn_crypt_skeleton',2670,570,-1),
        ('dawn_crypt_skeleton',2945,550,-1),
        ('dawn_crypt_skeleton',3150,525,-1),
        (CRYPT_BOSS,3100,930,-1)])
    chest=landmark(CRYPT_CHEST,'Skrzynia Bezgłowego',3110,1110,-1,
        'Pokonaj Szkielet bez głowy. Osobista nagroda: 120 złota i 3 małe mikstury zdrowia. Bez wymaganego poziomu. Raz na postać.',
        action='starter_treasure',boss_kind=CRYPT_BOSS,treasure_gold=120,
        treasure_items=[],treasure_potions={'health_potion':3})
    c.POIS.append(chest)

    # A real, compact tower immediately south of the original field rats.
    # Its expanded interiors are separate floors; the old mine remains open.
    prop('old_starter_tower',630,1790,220,245)
    link('tower_entry','Stara wieża · parter','Stara wieża · wyjście',
         (740,1750,0),(740,1810,1))
    for f,name in [(1,'Parter'),(2,'Izba wartowników'),(3,'Szczyt')]:
        area('starter_tower_'+str(f),'Stara wieża · '+name,f,
             [room(500,1730,480,510)],'old_tower')
    link('tower_first','Stara wieża · na piętro','Stara wieża · na parter',
         (870,2150,1),(590,1830,2))
    link('tower_top','Stara wieża · na szczyt','Stara wieża · na piętro',
         (870,2150,2),(590,2150,3))
    for f in (1,2):
        prop('tower_crates',535,1940,65,65,f)
        prop('tower_crates',875,1810,65,65,f)
    # Pillars provide actual collision and cover against the aimed shot.
    prop('tower_cover',650,1970,50,58,3)
    prop('tower_cover',820,1980,50,58,3)
    c.SPAWNS.extend([('old_tower_lookout',770,2030,1),
        ('old_tower_lookout',780,1990,2),(TOWER_BOSS,755,1880,3)])
    chest=landmark(TOWER_CHEST,'Skarb starej wieży',870,1820,3,
        'Pokonaj Łucznika starej wieży. Cztery gwarantowane przedmioty: napierśnik +1, pierścień ST +1, tarcza +1 i Rapier Echa. Bez wymaganego poziomu. Raz na postać.',
        action='starter_treasure',boss_kind=TOWER_BOSS,treasure_gold=60,
        treasure_items=list(TOWER_REWARDS),treasure_potions={})
    c.POIS.append(chest)
    road=[[740,1610],[740,1750]]
    c.ROADS.append(road)
    # Keep the authoritative movement surface in sync, without rebuilding the
    # large continent's spatial index or regenerating any encounter positions.
    sm=c.SURFACE_MAP
    for a,b in zip(road,road[1:]):
        sm.insert(('road',a,b),min(a[0],b[0])-34,min(a[1],b[1])-34,
                  max(a[0],b[0])+34,max(a[1],b[1])+34)
    for l in landmarks:
        if l['id']=='dawn_ruins':
            l['description']+=' Kamienne schody na dziedzińcu prowadzą do małych Krypt Świtu (zalecany poziom 10).'
        if l['id']=='trail_board':
            l['description']='Południe: za szczurami Stara wieża (zalecany poziom 10), dalej bandyci. Za mostem na północ: Dziedziniec Świtu i małe krypty. N → Atlas → Okolica pokazuje kierunki.'

    def creature(key,name,hp,ac,attack,dice,**extra):
        s=dict(name=name,hp=hp,hp_dice=[hp,1,0],armor_class=ac,
            attack_bonus=attack,damage_dice=list(dice),melee_dice=list(dice),
            special_dice=[1,6,2],damage=dice[0]*(dice[1]+1)/2+dice[2],
            range=58,melee_range=58,melee_damage=dice[0]*(dice[1]+1)/2+dice[2],
            attack_interval=3.6,ranged_interval=3.8,windup=.7,speed=76,
            xp=35,gold=8,respawn=75,aggro=155,leash=550,wander=16,
            boss=False,level=6,save_bonus=1,save_dc=11,
            saves=dict(strength=1,dexterity=1,constitution=1,intelligence=0,wisdom=0,charisma=0),
            creature_type='humanoid',combat_role='melee',size=1,
            loot=dict(independent=True,entries=[dict(kind='potion',template='health_potion',chance=.12)]),
            starter_adventure=True,loot_origin='Strażnik małej wyprawy',**extra)
        enemies[key]=s
        return s
    creature('dawn_crypt_skeleton','Kruchy szkielet',8,11,2,[1,4,0],
             appearance='skeleton',starter_visual='crypt_skeleton',color='#d7d0b9')
    enemies['dawn_crypt_skeleton'].update(creature_type='undead',condition_immunities=['poisoned'])
    creature('old_tower_lookout','Wartownik starej wieży',9,11,2,[1,4,1],
             appearance='goblin',starter_visual='tower_lookout',color='#bd9877')
    s=creature(CRYPT_BOSS,'Szkielet bez głowy',36,12,3,[1,4,1],
        appearance='skeleton',starter_visual='headless',color='#ded5b5')
    s.update(boss=True,level=10,xp=150,gold=28,respawn=240,size=1.2,hp_dice=[8,8,0],
        creature_type='undead',condition_immunities=['poisoned'],aggro=260,
        special_range=160,special_pattern='blind_sweep',special_interval=9.0,
        special_dice=[1,6,2],special_windup=1.45,special_radius=110)
    s['loot']['entries']=[dict(kind='item',template='ring_headless_signet',chance=.15),
        dict(kind='item',template='trophy_undead',chance=1),
        dict(kind='potion',template='health_potion',chance=.25)]
    s=creature(TOWER_BOSS,'Łucznik starej wieży',32,12,3,[1,6,1],
        appearance='goblin',starter_visual='tower_archer',color='#beaa7a')
    s.update(boss=True,level=10,xp=150,gold=28,respawn=240,hp_dice=[5,8,10],
        projectile='arrow',combat_role='ranged',range=360,melee_range=58,
        melee_dice=[1,4,1],special_dice=[1,8,1],aggro=350,speed=72,
        retreat_distance=0,special_range=430,special_pattern='aimed_shot',
        special_interval=9.5,special_windup=1.65,special_width=22)
    s['loot']['entries']=[dict(kind='item',template='bandit_longbow',chance=.12),
        dict(kind='item',template='trophy_raider',chance=1),
        dict(kind='potion',template='health_potion',chance=.25)]


def record_victory(p,kind):
    if kind in BOSSES and kind not in p.starter_bosses:
        p.starter_bosses.append(kind)


def normalize(p):
    values=getattr(p,'starter_bosses',[])
    p.starter_bosses=[k for k in BOSSES if isinstance(values,list) and k in values]
    if not isinstance(p.chests,list):p.chests=[]


def player_state(p):
    return dict(defeated=[k for k in BOSSES if k in p.starter_bosses],
                claimed=[k for k in CHEST_BOSSES if k in p.chests])


def in_telegraph(h,p):
    if h['shape']=='circle':
        return math.hypot(p.x-h['x'],p.y-h['y'])<=h['radius']+12
    dx,dy=h['target_x']-h['x'],h['target_y']-h['y']
    length=max(1,math.hypot(dx,dy));ux,uy=dx/length,dy/length
    along=(p.x-h['x'])*ux+(p.y-h['y'])*uy
    across=abs((p.x-h['x'])*uy-(p.y-h['y'])*ux)
    return 0<=along<=length and across<=h['width']+12


class StarterAdventureGame:
    async def open_starter_treasure(self,p,site):
        """No await until all reward state and the receipt are committed."""
        try:
            from . import inventory_rules, world_content as c
            from .server import make_item, INVENTORY_CAP, POTIONS, PVP_RULES
        except ImportError:
            import inventory_rules, world_content as c
            from server import make_item, INVENTORY_CAP, POTIONS, PVP_RULES
        if (not p.alive or p.floor!=site['floor']
                or math.hypot(p.x-site['x'],p.y-site['y'])>site['radius']
                or not self.line_clear(p,SimpleNamespace(**site))):
            return await self.notice(p,'Podejdź do skrzyni.')
        if site['id'] in p.chests:
            return await self.notice(p,'Nagroda z tej skrzyni została już odebrana przez tę postać.')
        if site['boss_kind'] not in p.starter_bosses:
            return await self.notice(p,'Najpierw pokonaj strażnika tej skrzyni — samodzielnie lub z drużyną.')
        if any(e.kind==site['boss_kind'] and e.floor==site['floor'] and e.alive for e in self.enemies.values()):
            return await self.notice(p,'Strażnik znów pilnuje skarbu. Pokonaj go, aby otworzyć skrzynię.')
        now=self.now()
        # A short PvE pause, not the 20-second trade/logout block. PvP remains
        # unchanged. This reward is not usable as an in-combat heal or escape.
        if p.pvp_combat_until>now or p.combat_until-(PVP_RULES['combat_seconds']-3)>now:
            return await self.notice(p,'Zakończ walkę i odczekaj 3 sekundy przed otwarciem skrzyni.')
        items=site['treasure_items'];potions=site['treasure_potions']
        needed=len(items)+inventory_rules.slots_needed(p,potions)
        if len(p.inventory)+needed>INVENTORY_CAP:
            return await self.notice(p,f'Zwolnij {needed} miejsc w plecaku na całą nagrodę. Skrzynia pozostaje nieodebrana.')
        previous=deepcopy(p.inventory),p.gold,list(p.chests),dict(p.potions)
        try:
            with self.db:
                p.inventory.extend(make_item(k) for k in items)
                for key,n in potions.items():
                    if not inventory_rules.add(p,key,n,make_item,INVENTORY_CAP):
                        raise RuntimeError('Capacity changed during atomic treasure claim')
                p.gold+=site['treasure_gold']
                p.chests.append(site['id'])
                inventory_rules.sync(p,POTIONS)
                self.save_player(p)
        except Exception:
            p.inventory,p.gold,p.chests,p.potions=previous
            raise
        self.owner_cache.pop(p.id,None)
        self.combat_effect(p,'bulwark',radius=48,duration=.65)
        names=[c.ITEMS[k]['name'] for k in items]
        names.extend(f'{n} × {c.ITEMS[k]["name"]}' for k,n in potions.items())
        names.append(str(site['treasure_gold'])+' złota')
        return await self.notice(p,site['name']+': '+', '.join(names)+'.')

    def queue_enemy_attack(self,e,target,projectile=None,special=False):
        try:from . import environment_rules as env
        except ImportError:import environment_rules as env
        s=env.enemy_spec(e)
        pattern=s.get('special_pattern') if special else None
        if pattern not in ('blind_sweep','aimed_shot'):
            return super().queue_enemy_attack(e,target,projectile,special)
        if env.actions_blocked(e,self.now()):return
        delay=s['special_windup'];shape='circle' if pattern=='blind_sweep' else 'line'
        h=dict(starter=True,source_id=e.id,floor=e.floor,x=e.x,y=e.y,
            target_x=e.x,target_y=e.y,shape=shape,width=s.get('special_width',0),
            radius=s.get('special_radius',0),resolve=self.time+delay,
            dice=list(s['special_dice']),damage_type='slashing' if shape=='circle' else 'piercing',
            action='Ślepy zamach' if shape=='circle' else 'Strzał mierzony')
        if shape=='line':
            dx,dy=target.x-e.x,target.y-e.y;length=max(1,math.hypot(dx,dy))
            h['target_x']=e.x+dx/length*s['special_range']
            h['target_y']=e.y+dy/length*s['special_range']
        self.hazards.append(h)
        target_point=SimpleNamespace(id='',x=h['target_x'],y=h['target_y'],floor=e.floor)
        effect=self.combat_effect(e,'starter_warning',target_point,radius=h['radius'],duration=delay)
        effect.update(shape=shape,width=h['width'],label=h['action'])
        e.mobile_cast=False;e.cast_until=self.time+delay
        e.attack_until=self.time+delay;e.ready=max(e.ready,self.time+delay+.8)
        e.ranged_ready=max(e.ranged_ready,self.time+delay+.8)

    def resolve_hazards(self):
        try:from . import environment_rules as env
        except ImportError:import environment_rules as env
        own=[h for h in self.hazards if h.get('starter')]
        self.hazards=[h for h in self.hazards if not h.get('starter')]
        super().resolve_hazards()
        for h in own:
            e=self.enemies.get(h['source_id'])
            if (e is None or not e.alive or e.hp<=0 or e.floor!=h['floor']
                    or env.actions_blocked(e,self.now()) or env.polymorph(e)):
                continue
            if self.time<h['resolve']:
                self.hazards.append(h);continue
            origin=SimpleNamespace(id=e.id,x=h['x'],y=h['y'],floor=h['floor'])
            target=SimpleNamespace(id='',x=h['target_x'],y=h['target_y'],floor=h['floor'])
            fx=self.combat_effect(origin,'starter_strike',target,radius=h['radius'],duration=.3)
            fx.update(shape=h['shape'],width=h['width'])
            for p in (*self.players.values(),*self.companions.values(),*self.familiars.values()):
                if (p.alive and p.floor==h['floor'] and not self.in_safe(p)
                        and in_telegraph(h,p) and self.line_clear(origin,p)):
                    self.hit_player(e,p,dice=tuple(h['dice']),area=h['shape']=='circle',
                        melee=h['shape']=='circle',damage_kind=h['damage_type'],action=h['action'])
