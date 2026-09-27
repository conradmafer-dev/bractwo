"""0.8.8: authored, class-independent species drops. All probabilities are per kill.
Original Bractwo names/locations; weapon dice and armor bases use SRD 5.2.1.
Old template IDs remain valid for saves, chests and already-owned equipment.
"""
from copy import deepcopy

CLASSES = ['knight', 'ranger', 'mage', 'druid']
ARMOR_CLASSES = {'none': CLASSES, 'light': ['knight','ranger','druid'],
                 'medium': ['knight','ranger','druid'], 'heavy': ['knight']}
ARMOR_NAMES = {'none':'Szata', 'light':'Lekki pancerz', 'medium':'Średni pancerz', 'heavy':'Ciężki pancerz'}
DAMAGE_NAMES = {'cold':'zimno','fire':'ogień','necrotic':'obrażenia nekrotyczne','poison':'trucizna','lightning':'błyskawice'}
NEW_ITEMS = {}


def weapon(key, name, cls, level, dice, enchant, value, *, kind='sword', damage_type=None, rarity=None, description=''):
    focus=cls=='mage'
    NEW_ITEMS[key]=dict(name=name,slot='weapon',class_ids=[cls],min_level=level,value=value,
        rarity=rarity or ('common' if not enchant else 'rare' if enchant==1 else 'epic' if enchant==2 else 'legendary'),
        weapon='bow' if cls=='ranger' else 'staff' if cls in ('mage','druid') else 'sword',
        weapon_dice=list(dice),damage_dice=f'{dice[0]}k{dice[1]}',
        attack=0 if focus else enchant,attack_bonus=enchant,armor=0,ac_bonus=0,
        damage_type=damage_type or ('piercing' if cls=='ranger' else 'fire' if focus else 'bludgeoning' if cls=='druid' or kind=='hammer' else 'slashing'),
        art_kind=kind,icon=f'assets/equipment/{key}.svg',description=description,
        enchantment=enchant,content_version='0.8.8')
    if focus:
        NEW_ITEMS[key]['damage_dice']='1k4 (Iskra różdżki)'
        NEW_ITEMS[key]['description']=(description+' Zwiększa trafienie czarami i ST obrony przed nimi. Iskra: 1k4 bez skalowania; nie zastępuje sztuczek.').strip()


def armor(key,name,kind,ac,level,enchant,value,*,resistance=None,description='',classes=None):
    NEW_ITEMS[key]=dict(name=name,slot='armor',class_ids=list(classes or ARMOR_CLASSES[kind]),min_level=level,value=value,
        rarity='epic' if enchant>=2 else 'rare' if enchant or resistance else 'uncommon',
        base_ac=ac,armor_kind=kind,attack=0,attack_bonus=0,armor=enchant,ac_bonus=enchant,
        art_kind='robe' if kind=='none' else kind,icon=f'assets/equipment/{key}.svg',
        enchantment=enchant,content_version='0.8.8',description=description)
    if resistance:NEW_ITEMS[key]['resistances']=[resistance]


def ring(key,name,level,value,*,ac=0,resistance=None):
    NEW_ITEMS[key]=dict(name=name,slot='ring',class_ids=list(CLASSES),min_level=level,value=value,
        rarity='epic' if level>=60 else 'rare',attack=0,attack_bonus=0,armor=ac,ac_bonus=ac,
        art_kind='ring',icon=f'assets/equipment/{key}.svg',content_version='0.8.8',description='')
    if resistance:NEW_ITEMS[key]['resistances']=[resistance]

# Weapons: no hundreds-of-damage power creep, separate base dice and magic bonus.
weapon('goblin_cleaver','Tasak Zielonego Kła','knight',3,(1,6),0,12,kind='axe')
weapon('bandit_longsword','Miecz rozbójnika','knight',5,(1,8),0,22)
weapon('bandit_sabre','Szabla rabusia +1','knight',8,(1,8),1,85,kind='sabre')
weapon('veteran_greatsword','Dwuręczny miecz weterana','knight',12,(2,6),0,75,kind='greatsword',rarity='uncommon')
weapon('captain_greatsword','Rozkaz Herszta +1','knight',20,(2,6),1,220,kind='greatsword')
weapon('orc_battleaxe','Topór orczego wojownika','knight',12,(1,10),0,48,kind='axe')
weapon('orc_king_axe','Topór Króla Orków +1','knight',25,(1,12),1,270,kind='axe')
weapon('dwarf_hammer','Młot Żelaznego Serca +1','knight',25,(1,8),1,155,kind='hammer')
weapon('crypt_blade','Ostrze strażnika krypty +1','knight',30,(1,10),1,190,kind='greatsword')
weapon('obsidian_greatsword','Obsydianowy miecz +2','knight',80,(2,6),2,780,kind='greatsword')
weapon('abyss_blade','Ostrze Władcy Otchłani +3','knight',120,(2,6),3,1500,kind='greatsword')
weapon('skeleton_shortbow','Łuk kościanego wartownika','ranger',5,(1,6),0,22,kind='bow')
weapon('crypt_bow','Łuk z krypty +1','ranger',8,(1,8),1,95,kind='bow')
weapon('bandit_longbow','Długi łuk rozbójnika','ranger',5,(1,8),0,30,kind='bow')
weapon('captain_bow','Łuk Czarnego Traktu +1','ranger',20,(1,8),1,180,kind='bow')
weapon('elven_bow','Cisowy łuk elfów +1','ranger',15,(1,8),1,130,kind='bow')
weapon('frost_bow','Łuk Zimowej Straży +2','ranger',50,(1,8),2,480,kind='bow')
weapon('dragon_bow','Łuk Smoczego Skarbca +2','ranger',90,(1,8),2,760,kind='bow')
weapon('abyss_bow','Łuk Popielnej Korony +3','ranger',120,(1,8),3,1450,kind='bow')
weapon('acolyte_wand','Różdżka grobowego akolity +1','mage',15,(1,4),1,110,kind='wand')
weapon('mummy_wand','Różdżka mumii +1','mage',20,(1,4),1,170,kind='wand',description='Zabalsamowany fokus ozdobiony złotym skarabeuszem.')
weapon('hierophant_wand','Berło Hierofanty +2','mage',40,(1,4),2,450,kind='wand')
weapon('necromancer_wand','Różdżka nekromanty +1','mage',30,(1,4),1,195,kind='wand')
weapon('lich_wand','Różdżka wiecznej nocy +2','mage',60,(1,4),2,590,kind='wand')
weapon('abyss_wand','Różdżka Rozdarcia +3','mage',120,(1,4),3,1500,kind='wand')
weapon('thorn_staff','Kostur Ciernistego Kręgu +1','druid',12,(1,6),1,110,kind='nature_staff')
weapon('orc_shaman_staff','Kostur orczego szamana +1','druid',18,(1,6),1,140,kind='nature_staff')
weapon('root_staff','Kostur starych korzeni +2','druid',50,(1,6),2,500,kind='nature_staff')
weapon('winter_staff','Kostur Królowej Lodu +2','druid',80,(1,6),2,820,kind='nature_staff')
weapon('abyss_staff','Kostur Odrodzenia +3','druid',120,(1,6),3,1450,kind='nature_staff')
# Robes are not armor and work with Mage Armor. New body armor has real categories.
armor('bandit_leather','Skórzany kaftan rabusia','light',11,3,0,22)
armor('studded_raider','Ćwiekowana skóra rozbójnika','light',12,8,0,55)
armor('elven_leather','Skóra leśnego zwiadowcy +1','light',12,15,1,140)
armor('thorn_leather','Ciernista skóra +1','light',12,18,1,160)
armor('frost_leather','Skóra Zimowej Straży +1','light',12,45,1,340,resistance='cold')
armor('night_leather','Skóra wampirzego łowcy +2','light',12,60,2,650)
armor('raider_chainshirt','Koszulka kolcza najemnika','medium',13,8,0,60)
armor('orc_scale','Łuski orczego wojownika','medium',14,12,0,85)
armor('thorn_hide','Pancerz z kory i skór','medium',12,7,0,40)
armor('crypt_breastplate','Napierśnik krypty +1','medium',14,30,1,270)
armor('sand_halfplate','Półpłyta pustynnego strażnika +1','medium',15,35,1,330)
armor('dragon_scale','Smoczy pancerz łuskowy +1','medium',14,70,1,650,resistance='fire')
armor('root_breastplate','Napierśnik żywych korzeni +2','medium',14,65,2,650,resistance='poison')
armor('sentry_chainmail','Kolczuga szkieletowego strażnika','heavy',16,12,0,110)
armor('captain_splint','Zbroja paskowa herszta','heavy',17,20,0,210)
armor('dwarf_plate','Płytowa zbroja Żelaznego Serca','heavy',18,25,0,350)
armor('crypt_plate','Płyta grobowego strażnika +1','heavy',18,35,1,430)
armor('obsidian_plate','Obsydianowa płyta +2','heavy',18,80,2,1000)
armor('ancient_plate','Płyta pradawnych strażników +2','heavy',18,110,2,1350,resistance='fire')
armor('acolyte_robe','Szata grobowego akolity','none',10,8,1,70,classes=['mage','druid'])
armor('mummy_robe','Szata zapieczętowanego grobowca','none',10,20,1,130,classes=['mage','druid'])
armor('hierophant_robe','Szata Hierofanty','none',10,40,2,420,resistance='necrotic',classes=['mage','druid'])
armor('lich_robe','Szata wiecznej nocy','none',10,60,2,630,resistance='cold',classes=['mage','druid'])
ring('grave_ring','Pierścień ciszy grobowej',30,230,resistance='necrotic')
ring('venom_ring','Pierścień jadowej pieczęci',25,170,resistance='poison')
ring('winter_ring','Pierścień zimowego ogniska',50,380,resistance='cold')
ring('ember_ring','Pierścień smoczego żaru',70,580,resistance='fire')
ring('captain_ring','Pierścień herszta',20,175,ac=1)
ring('king_ring','Pieczęć Króla Nieumarłych',65,700,ac=1,resistance='necrotic')

# Fixed, unconditional percent for each named item. No class-dependent substitution.
DROPS = {
 'rat':[], 'boar':[], 'wolf':[], 'bear':[], 'frost_wolf':[], 'crocodile':[], 'nightmare':[],
 'spider':[], 'spitting_spider':[], 'scorpion':[], 'scarab':[],
 'goblin':[('goblin_cleaver',7),('bandit_leather',4)],
 'bandit':[('bandit_longsword',6),('bandit_sabre',3),('studded_raider',5)],
 'bandit_archer':[('bandit_longbow',7),('studded_raider',5)],
 'skeleton':[('bandit_longsword',5),('raider_chainshirt',3)],
 'skeleton_archer':[('skeleton_shortbow',7),('crypt_bow',1.5)],
 'bandit_veteran':[('veteran_greatsword',7),('bandit_sabre',4),('raider_chainshirt',6)],
 'bandit_captain':[('captain_greatsword',18),('captain_bow',10),('captain_splint',12),('captain_ring',4)],
 'skeleton_sentinel':[('sentry_chainmail',6),('bandit_longsword',5)],
 'grave_acolyte':[('acolyte_wand',4),('acolyte_robe',7)],
 'thorn_shaman':[('thorn_staff',5),('thorn_hide',7),('thorn_leather',2)],
 'crypt_guard':[('crypt_blade',5),('crypt_plate',2.5),('crypt_breastplate',4)],
 'mummy':[('mummy_wand',5),('mummy_robe',4),('grave_ring',.8)],
 'mummy_hierophant':[('hierophant_wand',15),('hierophant_robe',12),('sand_halfplate',10),('grave_ring',5)],
 'frost_ranger':[('frost_bow',3),('frost_leather',5),('winter_ring',1)],
 'obsidian_knight':[('obsidian_greatsword',3),('obsidian_plate',2)],
 'troll':[('goblin_cleaver',4),('thorn_hide',3)],
 'orc':[('orc_battleaxe',7),('orc_scale',6)],
 'orc_shaman':[('orc_shaman_staff',5),('thorn_hide',6)],
 'elf':[('elven_bow',4),('elven_leather',3)],
 'minotaur':[('veteran_greatsword',5),('orc_battleaxe',6)],
 'vampire':[('crypt_blade',4),('grave_ring',1)],
 'necromancer':[('necromancer_wand',5),('mummy_robe',6),('grave_ring',1.2)],
 'dwarf':[('dwarf_hammer',5),('dwarf_plate',2.5),('raider_chainshirt',6)],
 'golem':[], 'guardian':[], 'wisp':[], 'ice_elemental':[], 'fire_elemental':[],
 'frost_giant':[('dwarf_hammer',3),('winter_ring',1)],
 'lich':[('lich_wand',3),('lich_robe',3)],
 'dragon':[],
 'dragon_lord':[('dragon_bow',1.5),('dragon_scale',2),('ember_ring',.5)],
 'demon':[('obsidian_greatsword',2),('ember_ring',.6)],
 'ancient_guardian':[('ancient_plate',1.5)],
 'abyss_walker':[('abyss_wand',.6),('abyss_blade',.6)],
 'cyclops':[('orc_battleaxe',4)], 'ogre':[('veteran_greatsword',4)],
 'harpy':[], 'ghoul':[],
 'boss':[('bandit_sabre',18),('crypt_bow',12),('raider_chainshirt',15)],
 'orc_king':[('orc_king_axe',20),('dwarf_plate',10),('captain_ring',6)],
 'sand_queen':[('venom_ring',12),('sand_halfplate',10),('hierophant_wand',5)],
 'lich_king':[('lich_wand',16),('lich_robe',12),('king_ring',6),('root_staff',8),('root_breastplate',5),('night_leather',5)],
 'ice_queen':[('frost_bow',15),('winter_staff',12),('frost_leather',15),('winter_ring',8)],
 'ancient_dragon':[('dragon_bow',18),('dragon_scale',20),('ember_ring',8),('obsidian_greatsword',12)],
 'abyss_lord':[('abyss_blade',9),('abyss_bow',9),('abyss_wand',9),('abyss_staff',9),('ancient_plate',12)],
}
# Beasts drop body parts, elementals condensed essence, not wearable armor.
FAMILY_BY_KIND={
 'bandit_veteran':'raider','bandit_captain':'raider','skeleton_sentinel':'undead',
 'grave_acolyte':'undead','thorn_shaman':'raider','crypt_guard':'undead',
 'mummy_hierophant':'undead','frost_ranger':'frost','obsidian_knight':'abyss'}
NO_POTIONS={'rat','boar','wolf','bear','frost_wolf','crocodile','nightmare','spider','spitting_spider','scorpion','scarab',
 'golem','guardian','wisp','ice_elemental','fire_elemental','harpy','ghoul','dragon'}


def configure(items,enemies,tier_levels):
    items.update(deepcopy(NEW_ITEMS))
    # Generic stones, skins and essences remain trade goods. They are not crafting promises.
    trophy_specs={
      'rat':('Szczurzy ogon',1),'boar':('Szabla dzika',3),'wolf':('Wilcza skóra',4),
      'bear':('Niedźwiedzie futro',12),'frost_wolf':('Polarne futro',40),'crocodile':('Skóra krokodyla',14),
      'nightmare':('Grzywa koszmaru',65),'spider':('Pajęczy jedwab',6),'spitting_spider':('Worek pajęczego jadu',10),
      'scorpion':('Żądło skorpiona',15),'scarab':('Złoty pancerzyk',24),'harpy':('Pióro harpii',18),
      'ghoul':('Ghulowy pazur',10),'wisp':('Okruch błędnego światła',8),
      'guardian':('Odłamek ożywionego kamienia',20),'golem':('Rdzeń żelaznego golema',38),
      'ice_elemental':('Lodowa esencja',50),'fire_elemental':('Płomienna esencja',48),
      'dragon':('Smocza łuska',60),'dragon_lord':('Łuska smoczego władcy',90)}
    for kind,(name,value) in trophy_specs.items():
        key='loot_trophy_'+kind
        items[key]=dict(name=name,slot='trophy',class_ids=[],min_level=1,value=value,rarity='uncommon',
            art_kind='essence' if 'elemental' in kind or kind in ('wisp','golem','guardian') else 'trophy',
            icon=f'assets/equipment/{key}.svg',description='Trofeum na sprzedaż u kupca.',content_version='0.8.8')
    # Build transparent preview from exactly the same entries used by roll().
    for kind,spec in enemies.items():
        if kind not in DROPS:raise ValueError('Brak tabeli łupu: '+kind)
        old=spec.get('loot',{});family=FAMILY_BY_KIND.get(kind,old.get('family','stone'))
        level=spec.get('level',8 if kind in ('boss','guardian') else 1)
        tier=max(t for t,minimum in tier_levels.items() if minimum<=level)
        entries=[dict(kind='item',template=key,chance=percent/100) for key,percent in DROPS[kind]]
        boss=bool(spec.get('boss'))
        trophy='loot_trophy_'+kind if kind in trophy_specs else 'trophy_'+family
        entries.append(dict(kind='item',template=trophy,chance=1.0 if boss else .32))
        if kind not in NO_POTIONS:
            suffix='_3' if level>=70 else '_2' if level>=20 else ''
            entries.append(dict(kind='potion',template='health_potion'+suffix,chance=.15 if boss else .04))
        # Keep compatibility fields for tools; generated equipment and family uniques are disabled.
        spec['loot_origin']='Skarbiec i zdobycze' if kind in ('boss','sand_queen','dragon_lord','ancient_dragon','lich_king','abyss_lord','ice_queen') else 'Trofea' if kind in NO_POTIONS else 'Ekwipunek przeciwnika'
        spec['loot']=dict(family=family,tier=tier,equipment_chance=0,trophy_chance=0,potion_chance=0,
                          unique_chance=0,legendary_chance=0,entries=entries,independent=True)
    # Source lists on items use unconditional per-player kill probabilities, not nested rates.
    for item in items.values():item.pop('sources',None)
    for kind,spec in enemies.items():
        for e in spec['loot']['entries']:
            if e['kind']=='item':
                items[e['template']].setdefault('sources',[]).append(dict(kind=kind,name=spec['name'],chance=e['chance']))
    for item in items.values():
        if item.get('armor_kind') in ARMOR_NAMES:
            kind=item['armor_kind'];ac=item.get('base_ac',10)
            dex=' + Zręczność (maks. +2)' if kind=='medium' else ' + Zręczność' if kind in ('light','none') else ''
            bonus=item.get('ac_bonus',0)
            item['armor_summary']=f"{ARMOR_NAMES[kind]} · KP {ac}{dex}"+(f' +{bonus}' if bonus else '')
        if item.get('slot')=='ring' and item.get('ac_bonus'):
            item['description']=(item.get('description','')+f" Klasa Pancerza +{item['ac_bonus']}.").strip()
        if item.get('resistances'):
            extra='Połowa obrażeń: '+', '.join(DAMAGE_NAMES[x] for x in item['resistances'])+'.'
            item['description']=(item.get('description','')+' '+extra).strip()
    return items
