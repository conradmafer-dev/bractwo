"""UI20 geography: natural biomes, broad deserts and shore-to-shore travel.

Apply after the legacy generators so their persistent identifiers remain intact.
The old starting valley and underground coordinates are deliberately retained.
Call finalize after additional adventures and environment configuration.
"""
import math
from copy import deepcopy

try:
    from .living_world import SurfaceMap, BIOME_SURFACE, curve, segment_distance
    from .vertical_world import WaterMap, segment
except ImportError:
    from living_world import SurfaceMap, BIOME_SURFACE, curve, segment_distance
    from vertical_world import WaterMap, segment


# Coastlines are real collision polygons, also sent unchanged to both clients.
# Bays, long peninsulas and chains of small islands interrupt the old grid.
LANDMASSES = [
    dict(id='mainland', name='Kontynent Pogranicza', group='mainland', label_x=38400,label_y=43000, points=[
        [0,0],[1800,0],[14800,350],[20500,1400],[29400,400],[36200,1850],
        [44700,450],[53200,1800],[59000,900],[64700,3100],[71500,700],[78100,2500],
        [84700,1000],[91000,2300],[94900,6400],[92500,10400],[94500,14800],
        [91700,18300],[87600,20200],[89500,23500],[94700,26200],[96700,32200],
        [93800,34700],[96100,39600],[91800,43400],[86000,42600],[83700,46500],
        [79100,48600],[77500,52300],[79200,55900],[74100,58700],[72400,61900],
        [66700,64200],[61900,61700],[56100,63900],[52400,63100],[48000,68400],
        [48700,73800],[46300,77800],[49700,84600],[47700,88500],[42300,90100],
        [38500,91800],[31600,88200],[26300,89700],[21000,86000],[16800,87200],
        [12800,82100],[8900,79800],[6300,74700],[7600,69100],[3700,65800],
        [1200,59100],[3400,53000],[250,47400],[1900,41900],[170,36000],
        [1900,28900],[80,22200],[1500,15600],[100,9000]]),
    dict(id='sun_island', name='Wyspy Słonecznych Wydm', group='sun', label_x=115500,label_y=8800, points=[
        [100900,6900],[103200,2900],[110500,850],[116200,2300],[121000,650],
        [125600,3900],[127800,8600],[125400,11800],[127400,15800],[124900,20100],
        [120500,21900],[115800,20500],[112800,22500],[108700,21300],[105200,17800],
        [101400,17000],[103500,13200],[100700,10800]]),
    dict(id='ember_island', name='Wyspy Żaru', group='sun', label_x=116400,label_y=36500, points=[
        [106000,24400],[111300,26600],[116600,24200],[121100,25200],[124000,28100],
        [127500,30800],[125200,35100],[127000,39000],[123800,43800],[119100,44500],
        [115600,42000],[109000,45000],[105700,41400],[101300,39900],[100000,35000],
        [102300,31500],[103400,27600]]),
    # The northern islands form a narrow bent chain, not rectangular plates.
    dict(id='frost_island', name='Archipelag Lodowej Korony', group='frost', label_x=86600,label_y=55500, points=[
        [75800,49300],[80300,47800],[83200,51600],[86800,53500],[91000,50100],
        [94300,49800],[93700,53700],[91600,56500],[95600,60700],[96600,64900],
        [94000,66800],[91600,62900],[87600,59600],[83100,60100],[79500,56800],
        [78100,57900],[76000,54900],[77000,52200]]),
    dict(id='dragon_island', name='Smocze Wyspy', group='frost', label_x=116500,label_y=57300, points=[
        [118900,47100],[124600,48700],[125700,51600],[122100,54800],[120100,58500],
        [119100,61900],[114600,64600],[109000,63500],[106700,60700],[103600,59500],
        [103500,56200],[107100,53900],[111500,54100],[113200,55900],[116500,54600],
        [118200,52200],[117600,49500]]),
    dict(id='rift_island', name='Wyspy Rozdarcia', group='ash', label_x=63600,label_y=80300, points=[
        [55200,71000],[60200,73300],[65000,71100],[70000,70800],[73900,74800],
        [72400,77600],[76200,79900],[74500,83700],[71900,91900],[67700,89300],
        [62400,91800],[56600,90300],[54800,85600],[53100,80900],[55400,76400]]),
    dict(id='obsidian_island', name='Archipelag Obsydianu', group='ash', label_x=87800,label_y=81400, points=[
        [82000,75700],[85000,76700],[87900,73200],[92500,70900],[96700,72000],
        [95800,74600],[91900,75900],[90700,79500],[93500,81800],[95600,84900],
        [93200,88700],[89900,87000],[87700,84500],[83300,83900],[80700,81400],
        [77800,81200],[76900,78600],[79300,76800]]),
    dict(id='ash_island', name='Wyspy Morza Popiołu', group='ash', label_x=111100,label_y=81600, points=[
        [108300,70700],[113400,72800],[117800,70800],[122700,72400],[124400,75100],
        [119700,76700],[117500,80000],[119100,83800],[116600,85500],[118800,89000],
        [115200,91800],[111000,90300],[109300,86700],[106700,84600],[107100,81300],
        [103000,79900],[104500,76100],[106700,75000]]),
    dict(id='glass_key', name='Iglica Szklanego Lodu', group='frost', points=[
        [97600,47500],[99800,48000],[100600,50600],[99300,53200],[97500,51500],[98000,49100]]),
    dict(id='dragon_tooth', name='Smoczy Kieł', group='frost', points=[
        [123900,60200],[126600,61700],[126900,65300],[124100,67500],[122700,64900]]),
    dict(id='ember_tooth', name='Żużlowa Iglica', group='ash', points=[
        [123000,81800],[126500,83800],[126100,86600],[124000,89400],[122700,86300]]),
    dict(id='salt_key', name='Solne Ławice', group='sun', points=[
        [96600,20800],[98200,21400],[99800,20400],[101200,22700],[99100,24700],[98000,22900],[96600,23500]]),
    dict(id='frost_key', name='Wyspa Białej Latarni', group='frost', points=[
        [100800,41300],[102400,41900],[103300,40900],[104300,43300],[102100,44700],[100400,43200]]),
    dict(id='cinder_key', name='Czarne Ławice', group='ash', points=[
        [73300,65300],[74800,65800],[75600,64700],[77300,66600],[75800,68500],[73600,68000]]),
    dict(id='whisper_key', name='Wyspy Szeptu', group='sun', points=[
        [95600,7600],[97800,6400],[99300,7900],[98400,10500],[96700,10000]]),
    dict(id='seal_key', name='Focza Skała', group='frost', points=[
        [97600,67100],[99600,65800],[101100,67400],[100300,68900],[98200,68800]]),
    dict(id='black_sail_key', name='Wyspa Czarnego Żagla', group='ash', points=[
        [51000,66700],[52700,65900],[53800,68000],[52400,70000],[50800,69000]]),
]

# Shared jagged borders tessellate the land exactly: no equal square biomes and
# no overlaps where the simulation and atlas could disagree on biome identity.
REGION_NODES = [
    [(0,0),(23200,0),(49300,0),(71300,0),(99600,0),(128000,0)],
    [(0,22400),(26800,20700),(50500,23600),(69400,18500),(99100,22800),(128000,23200)],
    [(0,47400),(24500,43800),(51900,47400),(72400,48600),(101400,45000),(128000,46700)],
    [(0,69000),(27900,71900),(51400,67000),(77300,68600),(102100,69800),(128000,70000)],
    [(0,92160),(25600,92160),(51200,92160),(76800,92160),(102400,92160),(128000,92160)],
]
REGION_LABELS = [
    (12800,12300),(36900,11000),(59100,11400),(82600,10100),(115500,9400),
    (12800,32800),(37100,34000),(60200,33700),(81400,32400),(116000,34900),
    (13200,58200),(38100,55100),(63700,55400),(88400,56100),(116500,56600),
    (26300,79200),(41900,79700),(63200,81000),(87800,80100),(115500,82300),
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
    # Meadow: eastbound valley road, short southward farm branch.
    [[(.18,.21),(.34,.34),(.55,.40),(.76,.47),(.98,.50)],[(.55,.40),(.60,.61),(.52,.72)]],
    # Forest: river-parallel spine with fingers into wooded clearings.
    [[(.08,.08),(.22,.25),(.27,.46),(.43,.57),(.51,.78),(.67,.93)],[(.27,.46),(.48,.38),(.63,.23)],[(.51,.78),(.29,.81)]],
    # Orc upland: narrow diagonal military trail and one watchtower spur.
    [[(.02,.26),(.23,.31),(.36,.45),(.52,.51),(.67,.70),(.83,.77)],[(.36,.45),(.41,.24),(.51,.13)]],
    # Golden coast: inland-to-port route with a southbound coast fork.
    [[(.04,.40),(.15,.45),(.25,.50),(.41,.51),(.53,.63)],[(.25,.50),(.25,.71),(.18,.86)]],
    # Desert island: one caravan spine, short oasis and pyramid diversions.
    [[(.43,.12),(.46,.32),(.45,.50),(.50,.68),(.44,.84)],[(.45,.50),(.65,.47),(.76,.34)],[(.50,.68),(.29,.72)]],
    # Wetlands: sinuous north/south causeway with a single dry-bank spur.
    [[(.47,.04),(.42,.25),(.51,.43),(.44,.62),(.55,.82),(.62,.97)],[(.51,.43),(.68,.50),(.77,.63)]],
    # Birch valley: diagonal trail following seven streams, two short branches.
    [[(.10,.12),(.22,.29),(.31,.47),(.49,.58),(.62,.74),(.84,.88)],[(.31,.47),(.49,.37),(.57,.20)],[(.62,.74),(.43,.79)]],
    # Necropolis: staggered straight processional alleys, never a circular road.
    [[(.04,.33),(.30,.33),(.30,.53),(.57,.53),(.57,.72),(.83,.72)],[(.30,.53),(.15,.53),(.15,.72)],[(.57,.53),(.74,.53),(.74,.31)]],
    # Mainland desert: long north/south caravan road with an east oasis spur.
    [[(.20,.04),(.29,.23),(.30,.46),(.44,.61),(.43,.87)],[(.30,.46),(.48,.44),(.63,.55)]],
    # Volcano: a Y following three separate lava arms.
    [[(.22,.28),(.41,.42),(.55,.49),(.66,.65),(.66,.82)],[(.55,.49),(.68,.31),(.80,.21)]],
    # Minotaur grassland: grazing route across open plains, northward stock track.
    [[(.12,.70),(.30,.62),(.51,.58),(.69,.43),(.90,.39)],[(.51,.58),(.45,.38),(.52,.19)]],
    # Mountains: a single tight zigzag pass, one quarry dead end.
    [[(.05,.27),(.24,.36),(.33,.48),(.48,.53),(.56,.68),(.76,.78)],[(.48,.53),(.64,.42),(.75,.43)]],
    # Tundra: fragmented winding border patrol trail.
    [[(.06,.19),(.23,.25),(.34,.45),(.49,.56),(.64,.69)],[(.34,.45),(.17,.58),(.13,.76)]],
    # Frost chain: bent spine along the long, narrow island.
    [[(.11,.24),(.23,.38),(.41,.47),(.59,.42),(.66,.61),(.73,.78)],[(.41,.47),(.41,.64)]],
    # Dragon islands: the ridge climbs north-east, spur reaches the western cape.
    [[(.22,.66),(.43,.61),(.52,.43),(.66,.35),(.75,.17)],[(.52,.43),(.29,.41),(.11,.50)]],
    # Root ruins: two long cross-country legs meeting under the ancient tree.
    [[(.39,.05),(.46,.26),(.62,.42),(.65,.64),(.81,.79)],[(.62,.42),(.42,.48),(.23,.62)]],
    # Sunless kingdom: procession from north to south with an observatory spur.
    [[(.36,.07),(.40,.30),(.57,.43),(.52,.64),(.68,.79)],[(.57,.43),(.74,.30),(.81,.17)]],
    # Rift: an angular lava-fault spine and two short shelter branches.
    [[(.25,.17),(.43,.36),(.51,.55),(.42,.71),(.50,.88)],[(.51,.55),(.72,.57)],[(.43,.36),(.22,.43)]],
    # Obsidian hook: coast-following cape trail, archive branch at the bend.
    [[(.16,.47),(.34,.45),(.47,.60),(.60,.68),(.75,.61)],[(.47,.60),(.49,.38),(.64,.22)]],
    # Ash island: a long broken north/south road with a western harbour fork.
    [[(.67,.11),(.56,.29),(.44,.43),(.48,.64),(.52,.88)],[(.44,.43),(.28,.49),(.20,.42)]],
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
        if min(a[0],b[0])<=x<=max(a[0],b[0]) and min(a[1],b[1])<=y<=max(a[1],b[1]) and abs((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))<.001:return True
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def region_at(regions,x,y):
    """Use identical polygons for biome labels, movement and discovery difficulty."""
    return next((r for r in regions if r['x']<=x<=r['x']+r['w'] and r['y']<=y<=r['y']+r['h']
                 and (not r.get('points') or contains(r['points'],x,y))),None)


def _natural_regions(c,zones):
    horizontal={};vertical={}
    def edge(a,b,bend,phase):
        dx,dy=b[0]-a[0],b[1]-a[1];length=max(1,math.hypot(dx,dy))
        return [list(a)]+[[round(a[0]+dx*t-dy/length*offset),round(a[1]+dy*t+dx/length*offset)]
                         for t,offset in [(.22,bend),(.43,-bend*.72),(.68,bend*.5),(.84,-bend*.45)]]+[list(b)]
    for row in range(5):
        for col in range(5):
            horizontal[row,col]=edge(REGION_NODES[row][col],REGION_NODES[row][col+1],
                                      0 if row in (0,4) else (630+(row*571+col*313)%1150)*(-1 if col%2 else 1),0)
    for row in range(4):
        for col in range(6):
            vertical[row,col]=edge(REGION_NODES[row][col],REGION_NODES[row+1][col],
                                    0 if col in (0,5) else (550+(row*293+col*197)%1450)*(-1 if row%2 else 1),0)
    for i,r in enumerate(c.REGIONS):
        row,col=divmod(i,5)
        points=(horizontal[row,col][:-1]+vertical[row,col+1][:-1]+
                list(reversed(horizontal[row+1,col]))[:-1]+list(reversed(vertical[row,col]))[:-1])
        xs,ys=zip(*points);r['legacy_bounds']=[r['x'],r['y'],r['w'],r['h']]
        r.update(points=points,x=min(xs),y=min(ys),w=max(xs)-min(xs),h=max(ys)-min(ys),
                 label_x=REGION_LABELS[i][0],label_y=REGION_LABELS[i][1])
        zone=next((z for z in zones if z['id']==r['id']),None)
        if zone:zone.update(r)
    c.UI20_CRYPT_ANCHOR=(115500,15500,38)


class Geography:
    def __init__(self,lands):
        self.lands=list(lands);self.cache={}
        self.bounds={p['id']:(min(x for x,y in p['points']),min(y for x,y in p['points']),max(x for x,y in p['points']),max(y for x,y in p['points'])) for p in lands}

    def land(self,x,y,clearance=0):
        for item in self.lands:
            x0,y0,x1,y1=self.bounds[item['id']]
            if not x0<=x<=x1 or not y0<=y<=y1 or not contains(item['points'],x,y):continue
            if clearance and any(min(a[0],b[0])-clearance<x<max(a[0],b[0])+clearance and min(a[1],b[1])-clearance<y<max(a[1],b[1])+clearance and segment_distance(x,y,a,b)<clearance for a,b in zip(item['points'],item['points'][1:]+item['points'][:1])):continue
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
        if floor:return 'stone'
        if any(math.hypot(x-c['x'],y-c['y'])<c.get('paving_radius',205) for c in self.cities):return 'stone'
        candidates=self.cells.get((math.floor(x/512),math.floor(y/512)),())
        for entry in candidates:
            if entry[0]=='road' and segment_distance(x,y,entry[1],entry[2])<=33:return 'path'
        for entry in reversed(candidates):
            if entry[0]!='patch':continue
            p=entry[1]
            if p.get('points'):
                if contains(p['points'],x,y):return p['kind']
            elif ((x-p['x']-p['w']/2)/(p['w']/2))**2+((y-p['y']-p['h']/2)/(p['h']/2))**2<=1:return p['kind']
        if x<3200 and y<2304:
            if 1720<x<2220 and y>1370:return 'mud'
            if x>2250:return 'stone'
            if y<900 and x<1400:return 'forest'
            return 'grass'
        return BIOME_SURFACE.get((region_at(self.regions,x,y) or {}).get('biome'),'grass')


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



def _coastal_landing(c,land_id,x,y):
    """A dry arrival point and the nearest visible water edge on that island."""
    land=next(p for p in c.LANDMASSES if p['id']==land_id);candidates=[]
    for a,b in zip(land['points'],land['points'][1:]+land['points'][:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
        sx,sy=a[0]+dx*t,a[1]+dy*t
        length=max(1,math.hypot(x-sx,y-sy));px,py=sx+(x-sx)/length*170,sy+(y-sy)/length*170
        if c.GEOGRAPHY.land(px,py,70):candidates.append((math.hypot(px-x,py-y),px,py,sx,sy))
    _,px,py,sx,sy=min(candidates)
    return round(px,1),round(py,1),round(sx,1),round(sy,1)

def _ports(c,npcs,landmarks):
    c.PORTS=[];c.SEA_ROUTES=[];c.PORT_DECKS=[]
    for city in c.CITIES:
        npc=next(n for n in npcs if n.get('port_id')=='port_'+city['id'])
        docks={
            'przystan':(1400,1460,1510,1460),
            'brzezina':(32000,34940,32000,35140),
            'zloty_port':(83200,12290,83200,12520),
            'mrozna_przystan':(83200,57980,83200,58200),
            'popielny_port':(108800,81190,108800,81400),
            'solna_przystan':(113600,18750,113600,18950),
            'zarowe_nabrzeze':(111000,28630,111000,29200),
            'przelom_rzeki':(28000,43950,28000,44150),
            'przystan_cieni':(54940,77800,54600,77900),
            'bazaltowa_straznica':(77750,79500,77380,79500),
        }
        x,y,sx,sy=docks[city['id']]
        if city['id'] in ('przystan_cieni','bazaltowa_straznica'):
            x,y,sx,sy=_coastal_landing(c,city['landmass_id'],x,y)
        x,y=c.GEOGRAPHY.nearest(x,y,65,city['landmass_id'])
        npc.update(x=x,y=y,shore_x=sx,shore_y=sy)
        c.PORTS.append(dict(id=npc['port_id'],city_id=city['id'],name=city['name'],x=x,y=y,
                            shore_x=sx,shore_y=sy,floor=0,npc_id=npc['id'],landmass_id=city['landmass_id']))
        c.PORT_DECKS.append(segment([x,y],[sx,sy],150,'pier_'+city['id']))
        c.ROADS.extend(_route(c.GEOGRAPHY,[(city['x'],city['y']),(x,y)]))
    for ident,name,x,y,level in [('dragon_landing','Smocza Przeprawa',106200,57300,70),
                                 ('salt_key','Solne Ławice',98300,22400,30),
                                 ('white_lighthouse','Biała Latarnia',102400,42700,45),
                                 ('cinder_key','Czarne Ławice',75400,66600,65),
                                 ('whisper_key','Wyspy Szeptu',97600,8300,20),
                                 ('seal_key','Focza Skała',99300,67400,60),
                                 ('black_sail_key','Wyspa Czarnego Żagla',52200,68300,50),
                                 ('glass_key','Iglica Szklanego Lodu',99100,49900,65),
                                 ('dragon_tooth','Smoczy Kieł',125000,64000,80),
                                 ('ember_tooth','Żużlowa Iglica',124400,85600,110)]:
        port_id='port_'+ident;npc_id='boat_'+ident
        land=c.GEOGRAPHY.land(x,y)
        if ident=='dragon_landing':x,y=104000,57500
        x,y,sx,sy=_coastal_landing(c,land['id'],x,y)
        c.PORTS.append(dict(id=port_id,city_id='',name=name,x=x,y=y,shore_x=sx,shore_y=sy,floor=0,npc_id=npc_id,landmass_id=land['id']))
        npcs.append(dict(id=npc_id,name='Przewoźnik · '+name,role='Lokalne przeprawy',x=x,y=y,shore_x=sx,shore_y=sy,floor=0,radius=125,service='boat',port_id=port_id))
        c.PORT_DECKS.append(segment([x,y],[sx,sy],150,'pier_'+ident))
        if ident!='dragon_landing':
            bounds=c.GEOGRAPHY.bounds[land['id']];candidates=[]
            for gx in range(int(bounds[0])+180,int(bounds[2])-100,330):
                for gy in range(int(bounds[1])+180,int(bounds[3])-100,330):
                    if not contains(land['points'],gx,gy) or not c.GEOGRAPHY.land(gx,gy,130):continue
                    length=math.hypot(gx-x,gy-y)
                    if length<1000:continue
                    steps=max(2,math.ceil(length/100))
                    if all(c.GEOGRAPHY.land(x+(gx-x)*i/steps,y+(gy-y)*i/steps,65) for i in range(steps+1)):
                        candidates.append((length,gx,gy))
            if candidates:
                _,gx,gy=max(candidates)
                c.ROADS.append([[x,y],[gx,gy]])

        landmarks.append(dict(id='landing_'+ident,name=name,x=x,y=y,floor=0,radius=120,biome='coast',recommended_level=level,
                              description='Mała przystań. Przewoźnik kursuje do sąsiednich wysp.',reward=dict(xp=30+level*2,gold=10)))
    routes=[('przystan','brzezina',45,8),('brzezina','przelom_rzeki',25,8),('przystan','zloty_port',90,8),
            ('zloty_port','solna_przystan',55,15),('solna_przystan','zarowe_nabrzeze',45,20),
            ('zarowe_nabrzeze','mrozna_przystan',65,25),('mrozna_przystan','bazaltowa_straznica',75,30),
            ('przelom_rzeki','przystan_cieni',70,25),('przystan_cieni','bazaltowa_straznica',45,30),
            ('bazaltowa_straznica','popielny_port',55,35),('mrozna_przystan','zloty_port',80,20),
            ('mrozna_przystan','dragon_landing',35,30),('solna_przystan','salt_key',18,15),
            ('zarowe_nabrzeze','white_lighthouse',25,20),('white_lighthouse','mrozna_przystan',25,20),
            ('przelom_rzeki','cinder_key',35,25),('cinder_key','przystan_cieni',25,25),
            ('zloty_port','whisper_key',18,20),('whisper_key','solna_przystan',25,20),
            ('mrozna_przystan','seal_key',18,60),('seal_key','dragon_landing',22,65),
            ('przelom_rzeki','black_sail_key',30,50),('black_sail_key','przystan_cieni',24,50),
            ('white_lighthouse','glass_key',20,65),('glass_key','dragon_landing',22,70),
            ('dragon_landing','dragon_tooth',25,80),('popielny_port','ember_tooth',22,110)]
    for a,b,cost,level in routes:
        for origin,target in [(a,b),(b,a)]:
            c.SEA_ROUTES.append(dict(id='boat_'+origin+'_'+target,from_id='port_'+origin,to_id='port_'+target,cost=cost,min_level=1,recommended_level=level))
    for npc in npcs:
        if npc.get('service')=='boat':npc['routes']=[r['id'] for r in c.SEA_ROUTES if r['from_id']==npc['port_id']]
    for ident,x,y,kinds in [
        ('salt_key',98400,22400,['scorpion','scarab','mummy']),
        ('frost_key',102000,42900,['frost_wolf','ice_elemental']),
        ('cinder_key',75100,67000,['fire_elemental','nightmare']),
        ('whisper_key',97700,8500,['bandit_archer','elf','bandit']),
        ('seal_key',99400,67700,['frost_wolf','frost_giant']),
        ('black_sail_key',52300,68000,['vampire','necromancer']),
        ('glass_key',98800,50000,['ice_elemental','frost_giant']),
        ('dragon_tooth',125000,64200,['dragon','dragon_lord']),
        ('ember_tooth',124500,85300,['demon','ancient_guardian']),
    ]:
        ground=dict(id='island_hunt_'+ident,name=next(p['name'] for p in c.LANDMASSES if p['id']==ident)+' · dzikie ostępy',
                    x=x,y=y,floor=0,kind=kinds[0],members=kinds,decoration='bones',
                    region_id=(region_at(c.REGIONS,x,y) or c.REGIONS[0])['id'])
        c.HUNTING_GROUNDS.append(ground)
        for i,kind in enumerate(kinds):
            c.SPAWNS.append((kind,x+math.cos(i*2.399963)*210,y+math.sin(i*2.399963)*210,0))



def _regional_terrain(c):
    for ri,region in enumerate(c.REGIONS):
        name,base,accent=REGIONAL_CHARACTER[ri];region.update(landscape=name,route_style=name)
        x,y,w,h=region['x'],region['y'],region['w'],region['h']
        attached=set()
        for pi,source_path in enumerate(REGIONAL_ROUTES[ri]):
            path=list(source_path)
            # Branches can leave a trunk but do not rejoin it into template rings.
            if len(path)>2 and (path[-1]==path[0] or path[-1] in attached):path=path[:-1]
            attached.update(path)
            points=[(x+px*w,y+py*h) for px,py in path]
            c.ROADS.extend(_route(c.GEOGRAPHY,points))
            # Irregular broad terrain follows each region's own structural routes.
            for j,(px,py) in enumerate(points[1:-1]):
                if not c.GEOGRAPHY.land(px,py,500):continue
                rx=1250+((ri*317+pi*263+j*139)%1700);ry=650+((ri*191+j*257)%1200)
                c.TERRAIN.append(dict(x=px-rx,y=py-ry,w=rx*2,h=ry*2,kind=accent if j%2 else base,region_id=region['id']))



def _authored_landscapes(c,obstacles,landmarks):
    """Large named landforms replace repeated circular decorations on the atlas."""
    forms=[
        ('old_forest','Puszcza Starych Dębów','forest',[(28100,3400),(34200,1800),(43100,4600),(47000,9500),(44300,13200),(46100,17900),(39800,21000),(34600,18400),(29800,20800),(27900,13700),(25100,9900)]),
        ('birch_woods','Lasy Siedmiu Strumieni','forest',[(27200,25200),(32600,23200),(37500,27400),(43600,26100),(47400,31200),(43500,35000),(46600,40700),(39300,43200),(35400,39700),(30000,41500),(27900,35900),(24800,30300)]),
        ('reed_marsh','Rozlewiska Trzcin','mud',[(8500,25400),(13700,23100),(19000,26500),(22000,31600),(20100,37100),(22400,41800),(16700,44600),(13000,39400),(7700,37100),(9900,31600)]),
        ('northern_pass','Przełęcz Złamanych Turni','stone',[(29800,46300),(34500,44900),(38700,48100),(42600,47600),(46900,51300),(44500,55300),(48100,59000),(44200,62500),(39500,58800),(35700,56800),(31100,51600)]),
        ('red_canyon','Kanion Czerwonych Ścian','stone',[(71500,22700),(75300,24000),(77300,28500),(75900,33400),(80100,36800),(83200,41300),(80200,44500),(76200,40900),(72700,37400),(72800,31600),(69400,27500)]),
        ('dune_sea','Wielkie Morze Wydm','sand',[(105300,4700),(110900,3500),(115100,5800),(120800,4200),(124600,7500),(122700,10500),(125100,15500),(121300,19200),(115600,18000),(111100,20200),(107000,16400),(109700,12100),(104800,9200)]),
        ('palm_oasis','Oaza Białych Palm','grass',[(113100,14900),(114600,14200),(116000,14800),(116800,16200),(115100,16900),(113300,16100)]),
        ('stone_steps','Schody Olbrzymów','stone',[(106000,52600),(109100,51400),(113400,53100),(114600,56500),(118300,58400),(117000,61700),(112200,60700),(109100,58000),(105800,56800)]),
        ('rootwood','Puszcza Zatopionych Ruin','forest',[(11200,72000),(18000,68900),(22300,72000),(27100,71400),(30500,76300),(27900,81900),(29100,86300),(22600,85200),(17900,82600),(15300,77500)]),
        ('deadwood','Martwy Bór','forest',[(32700,70800),(37200,71800),(40500,75400),(45100,76800),(44000,81800),(47100,84900),(42600,86800),(37500,83800),(35400,78900),(30700,75900)]),
    ]
    for ident,name,kind,points in forms:
        xs,ys=zip(*points)
        c.TERRAIN.append(dict(id=ident,name=name,kind=kind,points=[list(p) for p in points],
                              x=min(xs),y=min(ys),w=max(xs)-min(xs),h=max(ys)-min(ys)))
        if kind=='forest':
            # Real varied tree groups, with gaps; final road and site clearance
            # removes any group intersecting a travel corridor or service.
            for i in range(90):
                x=min(xs)+(max(xs)-min(xs))*((i*.61803398875)%1)
                y=min(ys)+(max(ys)-min(ys))*((i*.41421356237+.17)%1)
                if not contains(points,x,y) or not c.GEOGRAPHY.land(x,y,230):continue
                radius=55+(i*47)%135
                obstacles.append(dict(x=round(x-radius),y=round(y-radius*.72),w=round(radius*2),h=round(radius*1.44),
                                      floor=0,type='grove',landscape=ident))
    # Broad asymmetric paths trace landforms rather than repeating a ring.
    routes=[
        [(27600,5700),(31000,8200),(32500,11700),(36700,15100),(40300,16000),(44900,18600)],
        [(31100,28000),(32900,30400),(31800,33700),(34700,36500),(39000,39400),(43300,37900)],
        [(30400,47200),(34100,48800),(35500,52200),(39400,53400),(41900,56600),(45900,59000)],
        [(70700,23600),(74100,26600),(75000,30400),(74400,34100),(77800,36900),(81000,41700)],
        [(106100,6300),(110200,9000),(114000,11500),(112200,14200),(115500,15500),(117700,18400),(120000,19300)],
        [(108600,53700),(111000,55700),(111500,58800),(115000,59500),(118700,62100)],
    ]
    for points in routes:c.ROADS.extend(_route(c.GEOGRAPHY,points))
    # Two distinct long traversable mountain passes, bounded by real cliffs.
    for ident,name,points in [
        ('red_canyon_ui20','Kanion Czerwonych Ścian',routes[3]),
        ('northern_pass_ui20','Przełęcz Złamanych Turni',routes[2]),
    ]:
        path=curve(points);c.CANYONS.append(dict(id=ident,name=name,points=path,width=620))
        for j in range(0,len(path)-1,3):
            a,b=path[j],path[min(j+3,len(path)-1)]
            dx,dy=b[0]-a[0],b[1]-a[1];length=max(1,math.hypot(dx,dy))
            for side in (-1,1):
                x,y=a[0]-dy/length*450*side,a[1]+dx/length*450*side
                if c.GEOGRAPHY.land(x,y,230):
                    obstacles.append(dict(x=round(x-145),y=round(y-145),w=290,h=290,floor=0,type='canyon',landscape=ident))
        x,y=path[len(path)//2]
        landmarks.append(dict(id=ident,name=name,x=x,y=y,floor=0,radius=110,biome='mountain',
                              description='Długi, kręty szlak wśród skalnych ścian. Otwarte wyloty przełęczy łączą sąsiednie krainy.',
                              reward=dict(xp=100,gold=15),recommended_level=35))

def _connect(c,point):
    """Connect to a nearby road on the same landmass, preserving open sea."""
    x,y=point;land=c.GEOGRAPHY.land(x,y)
    if not land:return
    candidates=[q for path in c.ROADS
                if any(math.dist(point,end)>1200 for end in (path[0],path[-1]))
                for q in path[::8]]
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
        old_region=int(y//23040)*5+int(x//25600)
        home={4:'sun_island',9:'ember_island',13:'frost_island',14:'dragon_island',17:'rift_island',18:'obsidian_island',19:'ash_island'}.get(old_region)
        nx,ny=c.GEOGRAPHY.nearest(x,y,230,home)
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
    c.WORLD_REVISION=20
    c.LANDMASSES=deepcopy(LANDMASSES);c.GEOGRAPHY=Geography(c.LANDMASSES)
    c.ADVENTURE_ANCHORS={key:dict(value,id=key,floor=0,reserve_radius=900) for key,value in ADVENTURE_ANCHORS.items()}
    c._continent_obstacles=obstacles;c._continent_npcs=npcs;c._continent_landmarks=landmarks;c._continent_quests=quests
    _protect_legacy_sites(c)
    # Retain the starting valley's authored roads and the rock-bounded passes.
    original=list(c.ROADS)
    c.ROADS[:]=[path for path in original if all(x<7000 and y<6600 for x,y in path)]
    # The old generator left thousands of dirt/grass patches along its two
    # identical loop roads in every biome. Keeping those patches alone still
    # painted phantom rings in the atlas even after replacing every old road.
    # Preserve authored starting habitats; continental soil now follows landforms.
    c.TERRAIN[:]=[p for p in c.TERRAIN if p['x']+p['w']<7000 and p['y']+p['h']<6600]
    c.ROADS.extend(path['points'] for path in c.CANYONS)
    _regional_terrain(c)
    for points in [
        [[97400,21500],[98600,22000],[99400,23200],[98600,23800]],
        [[101400,41800],[102400,42300],[103300,43200],[102100,43900]],
        [[74300,65900],[75400,66300],[76700,66750],[75500,67650]],
    ]:c.ROADS.extend(_route(c.GEOGRAPHY,points))
    _link_regions(c)
    _natural_regions(c,zones)
    _authored_landscapes(c,obstacles,landmarks)
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
    # Port decks created at the actual river or coast by _ports remain indexed.
    c.PORT_DECKS.append(segment([111000,28680],[111000,28950],150,'ember_old_deck'))
    finalize(c,obstacles)


def finalize(c,obstacles=None):
    """Rebuild indexes after adventure additions; never bridge across the sea."""
    obstacles=obstacles if obstacles is not None else c._continent_obstacles
    clipped=[]
    for path in c.ROADS:
        part=[]
        for a,b in zip(path,path[1:]):
            steps=max(1,math.ceil(math.dist(a,b)/150))
            for i in range(steps):
                point=[a[0]+(b[0]-a[0])*i/steps,a[1]+(b[1]-a[1])*i/steps]
                if c.GEOGRAPHY.land(*point,50):part.append(point)
                else:
                    if len(part)>1:clipped.append(part)
                    part=[]
        if path and c.GEOGRAPHY.land(*path[-1],50):part.append(path[-1])
        if len(part)>1:clipped.append(part)
    c.ROADS[:]=clipped
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
        if o.get('floor',0) or o.get('type')=='terrace' or o['x']<3200 and o['y']<2304:return False
        x,y=o['x']+o['w']/2,o['y']+o['h']/2;r=math.hypot(o['w'],o['h'])/2+50
        for gx in range(math.floor((x-r)/512),math.floor((x+r)/512)+1):
            for gy in range(math.floor((y-r)/512),math.floor((y+r)/512)+1):
                if any(e[0]=='road' and segment_distance(x,y,e[1],e[2])<r for e in c.SURFACE_MAP.cells.get((gx,gy),())):return True
        return False
    obstacles[:]=[o for o in obstacles if not clear_road(o)]
    _repair_access(c,obstacles)
    refresh_shops(c)


def refresh_shops(c):
    # The economy module owns curated shops and rare monster-only equipment.
    try:
        from . import loot_economy
    except ImportError:
        import loot_economy
    loot_economy.refresh_shops(c)


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
        if enemy and any(math.hypot(x-city['x'],y-city['y'])<city['radius']+100 for city in getattr(c,'SAFE_ZONES',c.CITIES)):return False
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
