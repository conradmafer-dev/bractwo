"""UI19 geography pass: authored coasts, regional routes and working settlements.

Apply after the legacy generators so their persistent identifiers remain intact.
The old starting valley and underground coordinates are deliberately retained.
Call finalize after additional adventures and environment configuration.
"""
import math
from copy import deepcopy

try:
    from .living_world import SurfaceMap, curve, segment_distance
    from .vertical_world import WaterMap, segment
except ImportError:
    from living_world import SurfaceMap, curve, segment_distance
    from vertical_world import WaterMap, segment


LANDMASSES = [
    dict(id='mainland', name='Kontynent Pogranicza', group='mainland', points=[
        [0,0],[91000,0],[95600,6500],[93700,17500],[86000,22000],[93800,30000],
        [89500,40200],[76500,42500],[75200,57500],[64500,64300],[52200,62900],
        [47500,69900],[50200,87200],[38100,92160],[18000,88200],[6500,75000],[0,56000]]),
    dict(id='sun_island', name='Wyspy Słonecznych Wydm', group='sun', points=[
        [102500,1300],[121000,800],[127800,9000],[125600,20300],[113000,22100],[101400,16200]]),
    dict(id='ember_island', name='Wyspy Żaru', group='sun', points=[
        [106000,24500],[121000,24000],[127500,31000],[124000,44000],[109000,45000],[100000,35000]]),
    dict(id='frost_island', name='Archipelag Lodowej Korony', group='frost', points=[
        [77500,48000],[96300,46200],[101300,54500],[99400,64800],[86300,67900],[77100,61100]]),
    dict(id='dragon_island', name='Smocze Wyspy', group='frost', points=[
        [105500,46800],[122500,48000],[127000,54800],[124300,67700],[108600,66300],[103000,57900]]),
    dict(id='rift_island', name='Wyspy Rozdarcia', group='ash', points=[
        [55200,71000],[70000,70800],[76200,79900],[71900,91900],[56600,90300],[53100,80900]]),
    dict(id='obsidian_island', name='Archipelag Obsydianu', group='ash', points=[
        [80600,71400],[96800,69700],[101000,80500],[94600,91300],[79200,88400],[77100,78900]]),
    dict(id='ash_island', name='Wyspy Morza Popiołu', group='ash', points=[
        [105100,71900],[120300,70400],[127400,78200],[124000,90700],[110000,91800],[102800,83800]]),
    dict(id='salt_key', name='Solne Ławice', group='sun', points=[
        [96600,20800],[99800,20400],[101200,22700],[99100,24700],[96600,23500]]),
    dict(id='frost_key', name='Wyspa Białej Latarni', group='frost', points=[
        [100800,41300],[103300,40900],[104300,43300],[102100,44700],[100400,43200]]),
    dict(id='cinder_key', name='Czarne Ławice', group='ash', points=[
        [73300,65300],[75600,64700],[77300,66600],[75800,68500],[73600,68000]]),
]

ADVENTURE_ANCHORS = {
    'starter_ruins': dict(x=8400,y=5600,region_id='region_0',level=8,biome='meadow'),
    'forest_shrine': dict(x=34300,y=33500,region_id='region_6',level=18,biome='forest'),
    'royal_catacombs': dict(x=60200,y=35400,region_id='region_7',level=32,biome='ruins'),
    'dune_observatory': dict(x=114000,y=11500,region_id='region_4',level=42,biome='desert'),
    'volcanic_fissure': dict(x=116000,y=33800,region_id='region_9',level=60,biome='lava'),
    'frost_hollow': dict(x=88400,y=56100,region_id='region_13',level=75,biome='snow'),
    'dragon_watch': dict(x=116500,y=56600,region_id='region_14',level=90,biome='mountain'),
    'obsidian_archive': dict(x=87800,y=80100,region_id='region_18',level=110,biome='obsidian'),
}

# Each region has its own route graph; numbers are fractions of its old bounds.
# No four-spoke/two-loop template is repeated across the continent.
REGIONAL_ROUTES = [
    [[(.18,.21),(.38,.37),(.58,.42),(.78,.50),(.98,.50)],[(.38,.37),(.28,.62),(.46,.83),(.65,.97)]],
    [[(.02,.50),(.23,.32),(.42,.46),(.67,.28),(.98,.41)],[(.23,.32),(.20,.72),(.52,.80),(.67,.28)],[(.42,.46),(.72,.68),(.88,.94)]],
    [[(.02,.41),(.33,.35),(.56,.53),(.83,.49),(.98,.50)],[(.56,.53),(.43,.74),(.55,.94)],[(.33,.35),(.36,.14),(.71,.17),(.83,.49)]],
    [[(.02,.50),(.25,.40),(.42,.51),(.58,.42),(.66,.64)],[(.25,.40),(.16,.17),(.38,.10),(.55,.21)],[(.42,.51),(.22,.74),(.12,.96)]],
    [[(.18,.76),(.31,.59),(.53,.50),(.66,.26),(.79,.15)],[(.31,.59),(.38,.29),(.55,.18)],[(.53,.50),(.76,.62),(.82,.81)]],
    [[(.23,.08),(.39,.29),(.24,.47),(.43,.63),(.40,.93)],[(.39,.29),(.61,.20),(.78,.35),(.72,.61),(.43,.63)],[(.72,.61),(.92,.80)]],
    [[(.03,.80),(.24,.50),(.41,.44),(.64,.30),(.97,.48)],[(.24,.50),(.29,.23),(.53,.13),(.64,.30)],[(.41,.44),(.54,.72),(.76,.80),(.91,.93)]],
    [[(.02,.48),(.25,.49),(.38,.60),(.64,.58),(.80,.47),(.98,.47)],[(.25,.49),(.25,.22),(.51,.22),(.64,.58)],[(.38,.60),(.25,.84),(.64,.83),(.80,.47)]],
    [[(.02,.47),(.23,.30),(.45,.37),(.60,.21)],[(.23,.30),(.26,.66),(.45,.69),(.57,.58)],[(.45,.37),(.55,.51),(.45,.69)]],
    [[(.34,.24),(.45,.36),(.61,.47),(.58,.68),(.38,.83)],[(.45,.36),(.68,.21),(.82,.36),(.78,.68),(.58,.68)]],
    [[(.39,.02),(.46,.25),(.68,.40),(.71,.65),(.90,.83)],[(.46,.25),(.25,.41),(.33,.67),(.62,.80),(.71,.65)],[(.68,.40),(.90,.23)]],
    [[(.02,.83),(.23,.66),(.39,.74),(.52,.52),(.66,.59),(.82,.39),(.97,.44)],[(.52,.52),(.37,.27),(.48,.11)],[(.82,.39),(.83,.16)]],
    [[(.02,.44),(.25,.39),(.44,.29),(.65,.23)],[(.25,.39),(.44,.57),(.47,.72)],[(.44,.29),(.41,.12),(.68,.08)]],
    [[(.21,.49),(.37,.32),(.60,.36),(.72,.52),(.67,.75)],[(.21,.49),(.26,.74),(.46,.86),(.67,.75)],[(.60,.36),(.67,.17),(.83,.32)]],
    [[(.21,.54),(.35,.33),(.53,.42),(.67,.25),(.80,.37)],[(.21,.54),(.35,.75),(.56,.63),(.69,.81)],[(.53,.42),(.56,.63)]],
    [[(.28,.08),(.48,.23),(.55,.44),(.73,.64),(.88,.79)],[(.48,.23),(.74,.20),(.89,.39),(.73,.64)]],
    [[(.03,.79),(.25,.66),(.38,.46),(.59,.55),(.79,.39)],[(.38,.46),(.25,.24),(.41,.09),(.67,.21),(.59,.55)]],
    [[(.20,.36),(.36,.25),(.61,.32),(.70,.49),(.58,.72),(.34,.79)],[(.36,.25),(.37,.53),(.58,.72)],[(.70,.49),(.85,.60)]],
    [[(.20,.45),(.43,.31),(.64,.23),(.77,.43),(.62,.68),(.38,.78),(.20,.45)],[(.43,.31),(.48,.53),(.62,.68)]],
    [[(.25,.50),(.43,.33),(.66,.23),(.80,.44),(.70,.72),(.48,.82)],[(.25,.50),(.46,.59),(.70,.72)]],
]

REGIONAL_CHARACTER = [
    ('Doliny i pola','grass','forest'),('Leśne ostępy','forest','grass'),('Warowne trakty','grass','stone'),
    ('Nadmorskie trakty','sand','grass'),('Wydmy i oazy','sand','stone'),('Rozlewiska i groble','mud','grass'),
    ('Polany i leśne osady','forest','grass'),('Cmentarne aleje','stone','forest'),('Szlak grobowców','sand','stone'),
    ('Pierścień wulkanu','ash','stone'),('Pastwiska minotaurów','grass','stone'),('Przełęcze kamieniołomów','stone','snow'),
    ('Pogranicze tundry','snow','grass'),('Fiordy i lodowe jeziora','snow','stone'),('Smocze granie','stone','ash'),
    ('Ruiny pod korzeniami','forest','stone'),('Martwe knieje','stone','forest'),('Pęknięcia ziemi','ash','stone'),
    ('Obsydianowe tarasy','ash','stone'),('Pola popiołu','ash','sand'),
]

LANDMARK_NAMES = [
    ('Drogowskaz Doliny','Wzgórze Jaskółek'),('Dąb Szeptów','Krąg Zielonych Płomieni'),
    ('Brama Czerwonego Kła','Wieża Trzech Bębnów'),('Latarnia Złotego Brzegu','Zatoka Kupieckich Żagli'),
    ('Oaza Białych Kości','Obelisk Zaginionego Słońca'),('Pomost Trzcinowej Wiedźmy','Zatopiona Dzwonnica'),
    ('Polana Siedmiu Brzóz','Kamień Leśnego Przymierza'),('Aleja Zapomnianych Królów','Mauzoleum Bez Imienia'),
    ('Wrota Piaskowych Grobowców','Studnia Bez Echa'),('Kuźnia Wygasłego Krateru','Czerwony Komin'),
    ('Kamień Rogatego Wodza','Pola Połamanych Wozów'),('Brama Żelaznego Serca','Plac Starych Wind'),
    ('Ostatnia Sosna','Kamienie Zamarzniętej Granicy'),('Latarnia Lodowego Fiordu','Tron Śnieżnej Ciszy'),
    ('Smoczy Przesmyk','Gniazdo Nad Chmurami'),('Plac Zaplątanych Korzeni','Fontanna Zielonego Snu'),
    ('Brama Wiecznej Nocy','Obserwatorium Bez Gwiazd'),('Pęknięty Ołtarz','Most Nad Rozdarciem'),
    ('Brama Obsydianowego Bastionu','Dziedziniec Czarnych Luster'),('Latarnia Ostatniego Brzegu','Kamień Popielnego Przypływu'),
]

CITY_PLANS = {
    'przystan': dict(radius=260,layout='village',role='Wioska wyprawowa',trade='Podstawowy ekwipunek i zapasy',houses=0),
    'brzezina': dict(radius=440,layout='woodland',role='Osada łowców i zielarzy',trade='Łuki, skóry i druidyczne laski',houses=9),
    'zloty_port': dict(radius=760,layout='harbour',role='Duże miasto kupieckie',trade='Pancerze, broń i zamorski handel',houses=22),
    'mrozna_przystan': dict(radius=350,layout='crescent',role='Port wypraw polarnych',trade='Wyposażenie wypraw i ciężka broń',houses=7),
    'popielny_port': dict(radius=510,layout='bastion',role='Warowna przystań',trade='Uzbrojenie na najdalsze wyprawy',houses=13),
    'solna_przystan': dict(radius=210,layout='quay',role='Rybacka osada',trade='Lekkie uzbrojenie i zapasy',houses=4),
    'zarowe_nabrzeze': dict(radius=230,layout='forge',role='Osada górników',trade='Broń i pancerze z kuźni',houses=5),
    'przelom_rzeki': dict(radius=180,layout='riverside',role='Przystanek rzeczny',trade='Zapasy i narzędzia podróżne',houses=3),
    'przystan_cieni': dict(radius=200,layout='ruined',role='Osada badaczy ruin',trade='Fokusy i zapasy badaczy',houses=4),
    'bazaltowa_straznica': dict(radius=280,layout='fort',role='Strażnica na wyspie',trade='Tarcze i ciężkie uzbrojenie',houses=6),
}

NEW_CITIES = [
    ('solna_przystan','Solna Przystań',113600,18500,4),
    ('zarowe_nabrzeze','Żarowe Nabrzeże',111000,28700,9),
    ('przelom_rzeki','Przełom Rzeki',28000,43800,6),
    ('przystan_cieni','Przystań Cieni',56500,78000,17),
    ('bazaltowa_straznica','Bazaltowa Strażnica',80500,79600,18),
]

SHOP_STOCK = {
    'przystan':['health_potion','cloth','knight_weapon_1','ranger_weapon_1','mage_weapon_1','druid_weapon_1','druid_leather','wooden_shield'],
    'brzezina':['health_potion','health_potion_2','leather','hide_armor','wooden_shield','ranger_weapon_2','druid_weapon_2'],
    'zloty_port':['health_potion_2','scale','armor_4','knight_weapon_3','ranger_weapon_3','copper_ring','hunter_ring'],
    'mrozna_przystan':['health_potion_2','health_potion_3','armor_5','knight_weapon_5','ranger_weapon_5','ring_5'],
    'popielny_port':['health_potion_3','health_potion_4','armor_7','knight_weapon_7','ranger_weapon_7','ring_7'],
    'solna_przystan':['health_potion','health_potion_2','leather','ranger_weapon_3','druid_weapon_3'],
    'zarowe_nabrzeze':['health_potion_2','scale','armor_5','knight_weapon_4','knight_weapon_5'],
    'przelom_rzeki':['health_potion','cloth','leather','ranger_weapon_1','druid_weapon_1'],
    'przystan_cieni':['health_potion_3','mage_weapon_5','druid_weapon_5','ring_5'],
    'bazaltowa_straznica':['health_potion_3','armor_6','armor_7','knight_weapon_6','wooden_shield'],
}


def contains(points,x,y):
    inside=False
    for a,b in zip(points,points[1:]+points[:1]):
        if segment_distance(x,y,a,b)<.001:return True
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


class Geography:
    def __init__(self,lands):
        self.lands=list(lands);self.cache={}
        self.bounds={p['id']:(min(x for x,y in p['points']),min(y for x,y in p['points']),max(x for x,y in p['points']),max(y for x,y in p['points'])) for p in lands}

    def land(self,x,y,clearance=0):
        for item in self.lands:
            x0,y0,x1,y1=self.bounds[item['id']]
            if not x0<=x<=x1 or not y0<=y<=y1 or not contains(item['points'],x,y):continue
            if clearance and any(segment_distance(x,y,a,b)<clearance for a,b in zip(item['points'],item['points'][1:]+item['points'][:1])):continue
            return item
        return None

    def nearest(self,x,y,clearance=100,land_id=None):
        key=(round(x,1),round(y,1),clearance,land_id)
        if key in self.cache:return self.cache[key]
        own=self.land(x,y,clearance)
        if own and (not land_id or own['id']==land_id):return x,y
        candidates=[]
        for land in self.lands:
            if land_id and land['id']!=land_id:continue
            points=land['points'];cx=sum(p[0] for p in points)/len(points);cy=sum(p[1] for p in points)/len(points)
            candidates.append((cx,cy))
            for a,b in zip(points,points[1:]+points[:1]):
                dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
                qx,qy=a[0]+dx*t,a[1]+dy*t
                for i in range(8):
                    angle=i*math.tau/8;candidates.append((qx+math.cos(angle)*(clearance*1.6+2),qy+math.sin(angle)*(clearance*1.6+2)))
        for px,py in sorted(candidates,key=lambda p:math.hypot(p[0]-x,p[1]-y)):
            land=self.land(px,py,clearance)
            if land and (not land_id or land['id']==land_id):
                result=round(px,1),round(py,1);self.cache[key]=result;return result
        raise ValueError('No dry land near '+str((x,y)))


class OceanWaterMap:
    def __init__(self,geography,waterways,bridges):
        self.geography=geography;self.rivers=WaterMap(waterways,bridges);self.cells=self.rivers.cells

    def is_ocean(self,x,y):return self.geography.land(x,y) is None

    def blocked(self,x,y,radius=18):
        return self.geography.land(x,y,max(0,radius)) is None or self.rivers.blocked(x,y,radius)


class ContinentSurfaceMap(SurfaceMap):
    def at(self,x,y,floor=0):
        if not floor and any(math.hypot(x-c['x'],y-c['y'])<c.get('paving_radius',205) for c in self.cities):return 'stone'
        return super().at(x,y,floor)


def _route(geography,points):
    """Clip cosmetic road samples at coasts: ships, never bridges, cross seas."""
    paths=[];part=[]
    for point in curve(points):
        if geography.land(*point,70):part.append(point)
        else:
            if len(part)>1:paths.append(part)
            part=[]
    if len(part)>1:paths.append(part)
    return paths


def _settlements(c,obstacles,landmarks,zones,npcs):
    for ident,name,x,y,ri in NEW_CITIES:
        c.CITIES.append(dict(id=ident,name=name,x=x,y=y,floor=0,region_id=f'region_{ri}'))
    for city in c.CITIES:
        ident=city['id'];plan=CITY_PLANS[ident];city.update(plan,type=plan['layout'],theme=c.REGIONS[int(city['region_id'].split('_')[1])]['biome'],paving_radius=round(plan['radius']*.83))
        x,y,r=city['x'],city['y'],city['radius'];city['w']=r*2;city['h']=r*1.7
        city['landmass_id']=c.GEOGRAPHY.land(x,y)['id']
        old_zone=next((z for z in zones if z['id']=='town_'+ident),None)
        zone=dict(id='town_'+ident,name=city['name'],x=x-r,y=y-r*.85,w=r*2,h=r*1.7,floor=0,color='#b0ad87',biome='town')
        if old_zone:old_zone.update(zone)
        elif ident!='przystan':zones.append(zone)
        marker=next((p for p in landmarks if p['id']=='city_'+ident),None)
        detail=f"{plan['role']}. {plan['trade']}. Lokalne rejsy sprawdzisz u przewoźnika."
        if marker:marker.update(description=detail)
        else:landmarks.append(dict(id='city_'+ident,name=city['name'],x=x,y=y,floor=0,radius=120,biome='town',description=detail,reward=dict(xp=30,gold=10)))
        if ident!='przystan':
            obstacles[:]=[o for o in obstacles if o.get('floor',0) or math.hypot(o['x']+o['w']/2-x,o['y']+o['h']/2-y)>r+200]
            for i in range(plan['houses']):
                if plan['layout']=='harbour':
                    row,col=divmod(i,6);dx=(col-2.5)*190;dy=(row-1.5)*180
                    if abs(dx)<140:dx+=150 if dx>=0 else -150
                elif plan['layout'] in ('bastion','fort'):
                    angle=i*math.tau/plan['houses'];dx=math.cos(angle)*r*.68;dy=math.sin(angle)*r*.65
                elif plan['layout'] in ('woodland','crescent'):
                    angle=-2.6+i*4.7/max(1,plan['houses']-1);dx=math.cos(angle)*r*.68;dy=math.sin(angle)*r*.62
                else:dx=(-1 if i%2 else 1)*(110+(i//4)*90);dy=(i//2-1)*130
                obstacles.append(dict(x=round(x+dx-45),y=round(y+dy-35),w=90+(i%3)*12,h=68+(i%2)*14,floor=0,type='house',settlement=ident,role=plan['role']))
            c.TERRAIN.append(dict(x=x-r,y=y-r*.85,w=r*2,h=r*1.7,kind='stone'))
        for service,dx,dy in [('bank',-65,50),('master',65,-75),('merchant',120,50),('captain',0,r-55)]:
            if ident=='przystan' and service=='merchant':continue
            npc=next((n for n in npcs if n['id']==service+'_'+ident),None)
            if npc:
                if ident!='przystan':npc.update(x=x+dx,y=y+dy)
            elif service in ('merchant','captain'):
                npc=dict(id=service+'_'+ident,name=('Przewoźnik' if service=='captain' else 'Kupiec')+' · '+city['name'],x=x+dx,y=y+dy,floor=0,city_id=ident,radius=125,service=service)
                npcs.append(npc)
            if npc and service=='merchant':
                npc.update(stock=list(SHOP_STOCK[ident]),role=plan['trade'])
            if npc and service=='captain':
                npc.update(service='boat',role='Lokalne przeprawy',port_id='port_'+ident)
        if ident in ('brzezina','zloty_port','mrozna_przystan','popielny_port'):
            stock=([f'{cls}_weapon_{tier}' for cls in ('mage','druid') for tier in ([2,3] if ident=='brzezina' else [4,5] if ident=='zloty_port' else [5,6] if ident=='mrozna_przystan' else [7,8])])
            npcs.append(dict(id='focus_trader_'+ident,name='Opiekun reliktów · '+city['name'],role='Fokusy i magiczne laski',service='merchant',stock=stock,x=x-115,y=y-75,floor=0,radius=125,city_id=ident))
    c.STARTER_MERCHANT_STOCK=list(SHOP_STOCK['przystan'])


def _ports(c,npcs,landmarks):
    c.PORTS=[];c.SEA_ROUTES=[]
    for city in c.CITIES:
        npc=next(n for n in npcs if n.get('port_id')=='port_'+city['id'])
        c.PORTS.append(dict(id=npc['port_id'],city_id=city['id'],name=city['name'],x=city['x'],y=city['y'],floor=0,npc_id=npc['id'],landmass_id=city['landmass_id']))
    for ident,name,x,y,level in [('dragon_landing','Smocza Przeprawa',107500,56000,70),
                                 ('salt_key','Solne Ławice',98300,22400,30),
                                 ('white_lighthouse','Biała Latarnia',102400,42700,45),
                                 ('cinder_key','Czarne Ławice',75400,66600,65)]:
        port_id='port_'+ident;npc_id='boat_'+ident
        c.PORTS.append(dict(id=port_id,city_id='',name=name,x=x,y=y,floor=0,npc_id=npc_id,landmass_id=c.GEOGRAPHY.land(x,y)['id']))
        npcs.append(dict(id=npc_id,name='Przewoźnik · '+name,role='Lokalne przeprawy',x=x,y=y+60,floor=0,radius=125,service='boat',port_id=port_id))
        landmarks.append(dict(id='landing_'+ident,name=name,x=x,y=y,floor=0,radius=120,biome='coast',recommended_level=level,
                              description='Mała przystań. Przewoźnik kursuje do sąsiednich wysp.',reward=dict(xp=30+level*2,gold=10)))
    routes=[('przystan','brzezina',45,8),('brzezina','przelom_rzeki',25,8),('przystan','zloty_port',90,8),
            ('zloty_port','solna_przystan',55,15),('solna_przystan','zarowe_nabrzeze',45,20),
            ('zarowe_nabrzeze','mrozna_przystan',65,25),('mrozna_przystan','bazaltowa_straznica',75,30),
            ('przelom_rzeki','przystan_cieni',70,25),('przystan_cieni','bazaltowa_straznica',45,30),
            ('bazaltowa_straznica','popielny_port',55,35),('mrozna_przystan','zloty_port',80,20),
            ('mrozna_przystan','dragon_landing',35,30),('solna_przystan','salt_key',18,15),
            ('zarowe_nabrzeze','white_lighthouse',25,20),('white_lighthouse','mrozna_przystan',25,20),
            ('przelom_rzeki','cinder_key',35,25),('cinder_key','przystan_cieni',25,25)]
    for a,b,cost,level in routes:
        for origin,target in [(a,b),(b,a)]:
            c.SEA_ROUTES.append(dict(id='boat_'+origin+'_'+target,from_id='port_'+origin,to_id='port_'+target,cost=cost,min_level=level))
    for npc in npcs:
        if npc.get('service')=='boat':npc['routes']=[r['id'] for r in c.SEA_ROUTES if r['from_id']==npc['port_id']]


def _regional_terrain(c):
    for ri,region in enumerate(c.REGIONS):
        name,base,accent=REGIONAL_CHARACTER[ri];region.update(landscape=name,route_style=name)
        x,y,w,h=region['x'],region['y'],region['w'],region['h']
        for pi,path in enumerate(REGIONAL_ROUTES[ri]):
            points=[(x+px*w,y+py*h) for px,py in path]
            c.ROADS.extend(_route(c.GEOGRAPHY,points))
            # Irregular broad terrain follows each region's own structural routes.
            for j,(px,py) in enumerate(points[1:-1]):
                if not c.GEOGRAPHY.land(px,py,500):continue
                rx=1250+((ri*317+pi*263+j*139)%1700);ry=650+((ri*191+j*257)%1200)
                c.TERRAIN.append(dict(x=px-rx,y=py-ry,w=rx*2,h=ry*2,kind=accent if j%2 else base,region_id=region['id']))


def _connect(c,point):
    """Connect to a nearby road on the same landmass, preserving open sea."""
    x,y=point;land=c.GEOGRAPHY.land(x,y)
    if not land:return
    candidates=[q for path in c.ROADS for q in path[::8]]
    for q in sorted(candidates,key=lambda p:math.dist(point,p))[:160]:
        n=max(2,math.ceil(math.dist(point,q)/250))
        if all(c.GEOGRAPHY.land(x+(q[0]-x)*i/n,y+(q[1]-y)*i/n,50) for i in range(n+1)):
            c.ROADS.append(curve([point,q]));return


def _link_regions(c):
    mainland={0,1,2,3,5,6,7,8,10,11,12,15,16}
    samples={ri:[] for ri in mainland}
    for path in c.ROADS:
        for point in path[::12]:
            ri=int(point[1]//23040)*5+int(point[0]//25600)
            if ri in samples:samples[ri].append(point)
    for ri in sorted(mainland):
        for neighbour in (ri+1,ri+5):
            if neighbour not in mainland or neighbour==ri+1 and ri//5!=neighbour//5:continue
            vertical=neighbour==ri+5;boundary=(ri//5+1)*23040 if vertical else (ri%5+1)*25600
            axis=1 if vertical else 0
            left=sorted(samples[ri],key=lambda p:abs(p[axis]-boundary))[:35]
            right=sorted(samples[neighbour],key=lambda p:abs(p[axis]-boundary))[:35]
            for a,b in sorted(((a,b) for a in left for b in right),key=lambda pair:math.dist(*pair)):
                n=max(2,math.ceil(math.dist(a,b)/200))
                if all(c.GEOGRAPHY.land(a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n,75) for j in range(n+1)):
                    c.ROADS.append(curve([a,b]));break


def _relocate(c,obstacles,landmarks,quests):
    """Keep every discovery/quest ID; move only positions erased by the coastline."""
    for point in landmarks+c.HUNTING_GROUNDS:
        if point.get('floor',0) or point['x']<3200 and point['y']<2304:continue
        point['x'],point['y']=c.GEOGRAPHY.nearest(point['x'],point['y'],180)
        parts=point['id'].split('_')
        if len(parts)==3 and parts[0]=='land' and parts[1].isdigit() and parts[2] in ('0','1'):
            ri=int(parts[1]);point['name']=LANDMARK_NAMES[ri][int(parts[2])]
            point['description']=REGIONAL_CHARACTER[ri][0]+'. Charakterystyczny punkt na miejscowym szlaku; pobliscy przeciwnicy odpowiadają poziomowi krainy.'
    # Entrances/terraces are retained as small natural promontories when needed.
    for index,(kind,x,y,floor) in enumerate(c.SPAWNS):
        if floor or c.GEOGRAPHY.land(x,y,80):continue
        nx,ny=c.GEOGRAPHY.nearest(x,y,230)
        angle=index*2.399963
        px,py=nx+math.cos(angle)*100,ny+math.sin(angle)*100
        c.SPAWNS[index]=(kind,round(px,1),round(py,1),floor)
    obstacles[:]=[o for o in obstacles if o.get('floor',0) or o.get('type')=='terrace' or c.GEOGRAPHY.land(o['x']+o['w']/2,o['y']+o['h']/2,30)]
    by_id={p['id']:p for p in landmarks}
    for quest in quests:
        for objective in quest['objectives']:
            if objective['type']=='discover' and objective['target'] in by_id:
                p=by_id[objective['target']];objective.update(x=p['x'],y=p['y'],floor=p.get('floor',0))
                if quest['id'].startswith('hunt_'):objective['label']='Odkryj: '+p['name']
            elif objective.get('floor',0)==0 and 'x' in objective:
                objective['x'],objective['y']=c.GEOGRAPHY.nearest(objective['x'],objective['y'],100)


def _protect_legacy_sites(c):
    """Small coastal outcrops retain all old stairs and positive-floor supports."""
    points=[s for s in c.STAIRS if s.get('floor',0)==0]
    points += [dict(x=o['x']+o['w']/2,y=o['y']+o['h']/2) for o in c._continent_obstacles if o.get('type')=='terrace' and o.get('floor',0)==0]
    for i,p in enumerate(points):
        if c.GEOGRAPHY.land(p['x'],p['y'],900):continue
        x,y=c.GEOGRAPHY.nearest(p['x'],p['y'],300)
        points2=[[p['x']+math.cos(j*math.tau/12)*1200,p['y']+math.sin(j*math.tau/12)*1200] for j in range(12)]
        points2 += [[x+math.cos(j*math.tau/8)*650,y+math.sin(j*math.tau/8)*650] for j in range(8)]
        points2=_hull(points2)
        # A promontory is a real polygon in both collision and rendering.
        c.LANDMASSES.append(dict(id=f'legacy_headland_{i}',name='Przylądek dawnych ruin',group='headlands',points=points2))
    c.GEOGRAPHY=Geography(c.LANDMASSES)


def _hull(points):
    values=sorted(set(map(tuple,points)))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in values:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(values):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1]+upper[:-1]]


def configure(c,obstacles,landmarks,zones,npcs,quests,enemies=None):
    c.WORLD_REVISION=19
    c.LANDMASSES=deepcopy(LANDMASSES);c.GEOGRAPHY=Geography(c.LANDMASSES)
    c.ADVENTURE_ANCHORS={key:dict(value,id=key,floor=0,reserve_radius=900) for key,value in ADVENTURE_ANCHORS.items()}
    c._continent_obstacles=obstacles;c._continent_npcs=npcs;c._continent_landmarks=landmarks;c._continent_quests=quests
    _protect_legacy_sites(c)
    # Retain the starting valley's authored roads and the rock-bounded passes.
    original=list(c.ROADS)
    c.ROADS[:]=[path for path in original if all(x<7000 and y<6600 for x,y in path)]
    c.ROADS.extend(path['points'] for path in c.CANYONS)
    _regional_terrain(c)
    for points in [
        [[97400,21500],[98600,22000],[99400,23200],[98600,23800]],
        [[101400,41800],[102400,42300],[103300,43200],[102100,43900]],
        [[74300,65900],[75400,66300],[76700,66750],[75500,67650]],
    ]:c.ROADS.extend(_route(c.GEOGRAPHY,points))
    _link_regions(c)
    _settlements(c,obstacles,landmarks,zones,npcs)
    _ports(c,npcs,landmarks)
    c.SHOP_REQUESTS={n['id']:list(n['stock']) for n in npcs if n.get('service')=='merchant' and 'stock' in n}
    _relocate(c,obstacles,landmarks,quests)
    for city in c.CITIES:_connect(c,(city['x'],city['y']))
    for stair in c.STAIRS:
        if stair.get('floor',0)==0:_connect(c,(stair['x'],stair['y']))
    for anchor in c.ADVENTURE_ANCHORS.values():_connect(c,(anchor['x'],anchor['y']))
    for port in c.PORTS:_connect(c,(port['x'],port['y']))
    # Protect the new authored content from unrelated wilderness clutter.
    def reserved(x,y):return any(math.hypot(x-a['x'],y-a['y'])<a['reserve_radius'] for a in c.ADVENTURE_ANCHORS.values())
    obstacles[:]=[o for o in obstacles if o.get('floor',0) or not reserved(o['x']+o['w']/2,o['y']+o['h']/2)]
    c.SPAWNS[:]=[s for s in c.SPAWNS if s[3] or not reserved(s[1],s[2])]
    # Short tributaries make the inland ports actual waterside places.
    for ident,points,width in [('brzezina_river',[[18800,40100],[24400,38300],[31300,35100],[32000,35150]],150),
                                ('przelom_river',[[21400,43300],[25900,44500],[28000,44150]],170),
                                ('gold_harbour',[[94500,15000],[89200,14300],[84600,13200],[83200,12520]],320),
                                ('frost_fjord',[[77500,58400],[80500,58800],[83200,58200]],240),
                                ('ash_inlet',[[103000,82600],[106000,82200],[108800,81400]],260),
                                ('salt_inlet',[[113600,22400],[114200,21100],[113600,18950]],180),
                                ('ember_inlet',[[107000,24500],[110000,26900],[111000,29200]],180)]:
        path=curve(points)
        c.WATERWAYS.extend(segment(a,b,width,f'{ident}_{i}') for i,(a,b) in enumerate(zip(path,path[1:])))
    # These captains stand beside tributaries: solid, rendered decks connect
    # their original service positions to the town bank.
    c.PORT_DECKS=[segment([32000,34740],[32000,35010],150,'pier_brzezina'),
                  segment([111000,28680],[111000,28950],150,'pier_zarowe_nabrzeze')]
    finalize(c,obstacles)


def finalize(c,obstacles=None):
    """Rebuild indexes after adventure additions; never bridge across the sea."""
    obstacles=obstacles if obstacles is not None else c._continent_obstacles
    c.SURFACE_MAP=ContinentSurfaceMap(c.ROADS,c.TERRAIN,c.CITIES,c.REGIONS)
    rivers=WaterMap(c.WATERWAYS,[])
    c.BRIDGES[:]=[]
    for i,path in enumerate(c.ROADS):
        for j,(a,b) in enumerate(zip(path,path[1:])):
            if not c.GEOGRAPHY.land(*a,50) or not c.GEOGRAPHY.land(*b,50):continue
            if any(rivers.blocked(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,100) for t in (0,.5,1)):
                c.BRIDGES.append(segment(a,b,140,f'coast_bridge_{i}_{j}'))
    c.BRIDGES.extend(getattr(c,'PORT_DECKS',()))
    c.WATER_MAP=OceanWaterMap(c.GEOGRAPHY,c.WATERWAYS,c.BRIDGES)
    def clear_road(o):
        if o.get('floor',0) or o.get('type') in ('terrace','canyon') or o['x']<3200 and o['y']<2304:return False
        x,y=o['x']+o['w']/2,o['y']+o['h']/2;r=math.hypot(o['w'],o['h'])/2+50
        for gx in range(math.floor((x-r)/512),math.floor((x+r)/512)+1):
            for gy in range(math.floor((y-r)/512),math.floor((y+r)/512)+1):
                if any(e[0]=='road' and segment_distance(x,y,e[1],e[2])<r for e in c.SURFACE_MAP.cells.get((gx,gy),())):return True
        return False
    obstacles[:]=[o for o in obstacles if not clear_road(o)]
    _repair_access(c,obstacles)
    refresh_shops(c)


def refresh_shops(c):
    # Applied on every refresh: initial world setup precedes the magic catalog.
    # SHOP_REQUESTS remains the source of each merchant's ordinary assortment.
    magic_stock={
        'merchant_brzezina':['magic_longbow_1','magic_quarterstaff_1','ring_resistance_poison','ring_free_action'],
        'merchant_zloty_port':['magic_longsword_1','magic_shield_1','magic_chain_mail_1','ring_protection'],
        'merchant_solna_przystan':['ring_swimming','ring_resistance_lightning'],
        'merchant_mrozna_przystan':['ring_warmth','ring_resistance_cold','mithral_chain_mail'],
        'merchant_zarowe_nabrzeze':['ring_resistance_fire','adamantine_chain_mail'],
        'merchant_przelom_rzeki':['ring_swimming','magic_quarterstaff_1'],
        'merchant_przystan_cieni':['ring_resistance_necrotic','ring_resistance_poison','ring_free_action'],
        'merchant_bazaltowa_straznica':['adamantine_chain_mail','mithral_chain_mail','magic_chain_mail_1','magic_shield_1'],
        'merchant_popielny_port':['ring_resistance_fire','ring_protection'],
    }
    for npc in c._continent_npcs:
        if npc['id'] in c.SHOP_REQUESTS:
            requested=c.SHOP_REQUESTS[npc['id']]+magic_stock.get(npc['id'],[])
            npc['stock']=[key for key in dict.fromkeys(requested) if key in c.ITEMS]
    c.STARTER_MERCHANT_STOCK[:]=[key for key in SHOP_STOCK['przystan'] if key in c.ITEMS]


def _repair_access(c,obstacles):
    """Make unchanged identifiers usable after new water and city construction."""
    interactions=[p for p in c._continent_npcs+c.STAIRS+c.PORTS if p.get('floor',0)==0]
    # Houses and roadside rocks cannot cover a service or a stair landing.
    obstacles[:]=[o for o in obstacles if o.get('floor',0) or o.get('type') in ('terrace','canyon') or
                  not any(o['x']-55<p['x']<o['x']+o['w']+55 and o['y']-55<p['y']<o['y']+o['h']+55 for p in interactions)]
    cells={}
    for o in obstacles:
        if o.get('floor',0):continue
        for gx in range(math.floor((o['x']-25)/512),math.floor((o['x']+o['w']+25)/512)+1):
            for gy in range(math.floor((o['y']-25)/512),math.floor((o['y']+o['h']+25)/512)+1):cells.setdefault((gx,gy),[]).append(o)
    def clear(x,y,enemy=False):
        if not 25<x<c.WIDTH-25 or not 25<y<c.HEIGHT-25 or c.WATER_MAP.blocked(x,y,22):return False
        if x+22>1500 and x-22<1680 and y-22<2304 and (y-22<1080 or y+22>1230):return False
        if enemy and any(math.hypot(x-city['x'],y-city['y'])<city['radius']+100 for city in c.CITIES):return False
        return not any(o['x']-22<x<o['x']+o['w']+22 and o['y']-22<y<o['y']+o['h']+22 for o in cells.get((int(x//512),int(y//512)),()))
    def place(x,y,enemy=False):
        if clear(x,y,enemy):return x,y
        x,y=c.GEOGRAPHY.nearest(x,y,100)
        for i in range(800):
            angle=i*2.399963;radius=90+6*i
            nx,ny=x+math.cos(angle)*radius,y+math.sin(angle)*radius
            if clear(nx,ny,enemy):return round(nx,1),round(ny,1)
        raise ValueError('No accessible position near '+str((x,y)))
    for i,(kind,x,y,floor) in enumerate(c.SPAWNS):
        if floor:continue
        nx,ny=place(x,y,True);c.SPAWNS[i]=(kind,nx,ny,floor)
    # An active site is tied to its stairs/terrace; clear its approach, never move it.
    for point in c._continent_landmarks+c.HUNTING_GROUNDS:
        if point.get('floor',0) or point.get('action') or point['id'].startswith(('trail_','city_')):continue
        point['x'],point['y']=place(point['x'],point['y'])
    by_id={p['id']:p for p in c._continent_landmarks}
    for quest in c._continent_quests:
        for objective in quest['objectives']:
            if objective['type']=='discover' and objective['target'] in by_id:
                p=by_id[objective['target']];objective.update(x=p['x'],y=p['y'],floor=p.get('floor',0))
            elif objective['type']=='kill' and objective.get('floor',0)==0 and 'x' in objective:
                residents=[s for s in c.SPAWNS if s[0]==objective['target'] and s[3]==0]
                if residents:
                    target=min(residents,key=lambda s:math.hypot(s[1]-objective['x'],s[2]-objective['y']))
                    objective['x'],objective['y']=target[1:3]
