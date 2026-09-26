"""Shared weapon/armor training, class grants and compact owner-specific previews.

2024 categories: simple / martial. Focus implements are NOT a third weapon
category. Class training is not the purchased General Feat and never grants its
ability increase. Sources are merged, so training cannot be acquired twice.
"""
import copy

ALL_CLASSES = ['knight', 'ranger', 'mage', 'druid']
TRAINING = {
    'simple_weapons': ('Broń prosta', 'simple'),
    'martial_weapons': ('Broń żołnierska', 'martial'),
    'light_armor': ('Lekkie pancerze', 'light'),
    'medium_armor': ('Średnie pancerze', 'medium'),
    'heavy_armor': ('Ciężkie pancerze', 'heavy'),
    'shields': ('Tarcze', 'shield'),
}
CLASS_TRAINING = {
    'knight': tuple(TRAINING),
    'ranger': ('simple_weapons','martial_weapons','light_armor','medium_armor','shields'),
    'mage': ('simple_weapons',),
    'druid': ('simple_weapons','light_armor','shields'),
}
WEAPON_TYPES = {
    'quarterstaff': dict(name='Laska', category='simple', dice=[1,6], versatile=[1,8], damage='bludgeoning', appearance='staff'),
    'club': dict(name='Maczuga', category='simple', dice=[1,4], damage='bludgeoning', appearance='staff'),
    'dagger': dict(name='Sztylet', category='simple', dice=[1,4], damage='piercing', finesse=True, appearance='sword'),
    'handaxe': dict(name='Toporek', category='simple', dice=[1,6], damage='slashing', appearance='sword'),
    'shortbow': dict(name='Krótki łuk', category='simple', dice=[1,6], damage='piercing', ranged=True, two=True, appearance='bow'),
    'longbow': dict(name='Długi łuk', category='martial', dice=[1,8], damage='piercing', ranged=True, two=True, heavy=True, appearance='bow'),
    'longsword': dict(name='Miecz długi', category='martial', dice=[1,8], versatile=[1,10], damage='slashing', appearance='sword'),
    'greatsword': dict(name='Miecz dwuręczny', category='martial', dice=[2,6], damage='slashing', two=True, heavy=True, appearance='sword'),
    'maul': dict(name='Młot dwuręczny', category='martial', dice=[2,6], damage='bludgeoning', two=True, heavy=True, appearance='sword'),
    'battleaxe': dict(name='Topór bojowy', category='martial', dice=[1,8], versatile=[1,10], damage='slashing', appearance='sword'),
    'greataxe': dict(name='Topór dwuręczny', category='martial', dice=[1,12], damage='slashing', two=True, heavy=True, appearance='sword'),
    'warhammer': dict(name='Młot bojowy', category='martial', dice=[1,8], versatile=[1,10], damage='bludgeoning', appearance='sword'),
    'rapier': dict(name='Rapier', category='martial', dice=[1,8], damage='piercing', finesse=True, appearance='sword'),
    'scimitar': dict(name='Sejmitar', category='martial', dice=[1,6], damage='slashing', finesse=True, appearance='sword'),
}
# These are genuine General Feats, separate from the class-granted training rows.
# Their +1 is awarded ONLY when the feat is selected, not for a class/path grant.
GENERAL_FEATS = {
    'lightly_armored': dict(name='Lekko opancerzony', grants=['light_armor','shields'], requires=[], abilities=['strength','dexterity'], description='Lekkie pancerze i tarcze. +1 Siła lub Zręczność.'),
    'moderately_armored': dict(name='Średnio opancerzony', grants=['medium_armor'], requires=['light_armor'], abilities=['strength','dexterity'], description='Średnie pancerze. +1 Siła lub Zręczność.'),
    'heavily_armored': dict(name='Ciężko opancerzony', grants=['heavy_armor'], requires=['medium_armor'], abilities=['strength','constitution'], description='Ciężkie pancerze. +1 Siła lub Kondycja.'),
    'martial_weapon_training': dict(name='Szkolenie w broni żołnierskiej', grants=['martial_weapons'], requires=[], abilities=['strength','dexterity'], description='Biegłość w broni żołnierskiej. +1 Siła lub Zręczność.'),
}
FEAT_LEVELS = (15,35,55,75)  # tabletop class 4/8/12/16; existing growth retained


def _rules():
    try: from . import combat_rules
    except ImportError: import combat_rules
    return combat_rules


def _content():
    try: from . import world_content
    except ImportError: import world_content
    return world_content


def _training(p):
    result={key:['Klasa'] for key in CLASS_TRAINING.get(p.class_id,())}
    if p.class_id=='druid' and getattr(p,'primal_order','')=='warden':
        for key in ('martial_weapons','medium_armor'):result.setdefault(key,[]).append('Strażnik')
    pending=set(getattr(p,'training_feats',{}));active=set()
    for _ in range(len(GENERAL_FEATS)):
        ready=[k for k in pending if k in GENERAL_FEATS and all(r in result for r in GENERAL_FEATS[k]['requires'])]
        if not ready:break
        for k in ready:
            active.add(k);pending.remove(k)
            for grant in GENERAL_FEATS[k]['grants']:result.setdefault(grant,[]).append(GENERAL_FEATS[k]['name'])
    return result,active


def training_sources(p):return _training(p)[0]
def active_feats(p):return _training(p)[1]


def has(p,key): return key in training_sources(p)


def weapon(p): return _rules().equipped_item(p,'weapon')


def is_focus(item): return item.get('implement')=='arcane'


def proficient(p,item=None):
    item=weapon(p) if item is None else item
    if not item: return True  # unarmed
    if is_focus(item):return p.class_id in item.get('class_ids',[])
    return has(p,'simple_weapons' if item.get('weapon_category')=='simple' else 'martial_weapons')


def shillelagh_applies(p):
    w=weapon(p)
    return not p.form and w.get('weapon_type') in ('quarterstaff','club') and _rules().active_buff(p,'shillelagh')


def armor_penalty(p):
    if p.form:return False
    kind=_rules().equipped_item(p,'armor').get('armor_kind','none')
    if kind=='medium' and p.class_id=='druid' and not getattr(p,'primal_order','') and getattr(p,'legacy_medium_grace',False):return False
    return kind in ('light','medium','heavy') and not has(p,kind+'_armor')


def shield_trained(p):return has(p,'shields')


def melee(p):return bool(p.form or not (is_focus(weapon(p)) or weapon(p).get('ranged')))


def weapon_disadvantage(p):
    w=weapon(p)
    if p.form:return False
    ability='dexterity' if w.get('ranged') else 'strength'
    return bool((armor_penalty(p) and _rules().attack_ability(p) in ('strength','dexterity')) or w.get('heavy') and _rules().attributes(p)[ability]<13)


def spell_equipment_bonus(p):
    if p.form:return 0
    w=weapon(p)
    if w.get('focus_classes') and p.class_id in w['focus_classes']:
        return min(3,max(0,int(w.get('spell_bonus',0))))
    return 0


def check_equip(p,item):
    if p.level<item.get('min_level',1):return 'Wymagany poziom: '+str(item['min_level'])
    if p.form:return 'Zmień wyposażenie po zakończeniu przemiany.'
    if item.get('slot')=='weapon' and is_focus(item) and p.class_id not in item.get('class_ids',[]):return 'To fokus czarodzieja.'
    return ''


def feat_points(p):return max(0,sum(p.level>=n for n in FEAT_LEVELS)-len(getattr(p,'training_feats',{})))


def feat_eligible(p,key):
    s=GENERAL_FEATS.get(key)
    if not s or key in getattr(p,'training_feats',{}):return False
    known=training_sources(p)
    return any(g not in known for g in s['grants']) and all(r in known for r in s['requires'])


def granted_rows(p):
    return [dict(id=k,name=TRAINING[k][0],sources=v,description=' / '.join(v),icon=f'assets/feats/{k}.svg') for k,v in training_sources(p).items()]


def training_sheet(p):
    scores=_rules().attributes(p)
    return dict(granted=granted_rows(p),points=feat_points(p),levels=list(FEAT_LEVELS),
        chosen=[dict(id=k,**GENERAL_FEATS[k],ability=v,active=k in active_feats(p),icon=f'assets/feats/{GENERAL_FEATS[k]["grants"][0]}.svg') for k,v in getattr(p,'training_feats',{}).items() if k in GENERAL_FEATS],
        options=[(dict(id=k,**s,icon=f'assets/feats/{s["grants"][0]}.svg',min_level=15)|dict(abilities=[a for a in s['abilities'] if scores[a]<20])) for k,s in GENERAL_FEATS.items() if feat_eligible(p,k)],
        armor_penalty=armor_penalty(p),weapon_proficient=proficient(p),
        grip=getattr(p,'weapon_grip','one'),can_change_grip=bool(weapon(p).get('versatile_dice')))


def configure(items):
    explicit={'goblin_cleaver':'handaxe','bandit_sabre':'rapier','orc_battleaxe':'battleaxe','orc_king_axe':'greataxe',
        'dwarf_hammer':'warhammer','crypt_blade':'longsword','captain_greatsword':'greatsword','abyss_blade':'greatsword',
        'skeleton_shortbow':'shortbow','training_maul':'maul'}
    for key,s in items.items():
        if s.get('slot')=='weapon':
            old=s.get('class_ids',['knight'])[0]
            s['spell_bonus']=0
            if old=='mage':
                s.update(implement='arcane',weapon_type='focus',weapon_name='Fokus magiczny',weapon_category='',
                    weapon='staff',weapon_dice=[1,4],damage_type='fire',damage_dice='1k4',two_handed=False,
                    attack=0,spell_bonus=s.get('attack_bonus',0),focus_classes=['mage'])
                s.pop('versatile_dice',None)
                continue
            kind=explicit.get(key) or s.get('weapon_type')
            if kind not in WEAPON_TYPES:
                kind='quarterstaff' if old=='druid' else 'shortbow' if s.get('weapon_dice')==[1,6] and old=='ranger' else 'longbow' if old=='ranger' else 'greatsword' if s.get('weapon_dice')==[2,6] else 'longsword'
            info=WEAPON_TYPES[kind]
            s.update(weapon_type=kind,weapon_name=info['name'],weapon_category=info['category'],weapon=info['appearance'],
                weapon_dice=list(info['dice']),damage_dice=f'{info["dice"][0]}k{info["dice"][1]}',damage_type=info['damage'],
                two_handed=bool(info.get('two')),ranged=bool(info.get('ranged')),finesse=bool(info.get('finesse')),heavy=bool(info.get('heavy')),class_ids=ALL_CLASSES[:])
            if info.get('versatile'):s['versatile_dice']=list(info['versatile'])
            else:s.pop('versatile_dice',None)
            if old=='druid':s.update(focus_classes=['druid','ranger'],spell_bonus=s.get('attack_bonus',0))
            try: from .fighter_rules import MASTERIES
            except ImportError: from fighter_rules import MASTERIES
            s.pop('mastery_name',None);s.pop('mastery_description',None)
            if kind in MASTERIES:
                s.update(mastery_name=MASTERIES[kind]['effect_name'],mastery_description=MASTERIES[kind]['description'])
        elif s.get('slot') in ('armor','shield'):
            s['class_ids']=ALL_CLASSES[:]
            if s.get('armor_kind')=='heavy':s['strength_required']=15 if s.get('base_ac',0)>=17 else 13 if s.get('base_ac',0)>=16 else 0
    common=dict(class_ids=ALL_CLASSES[:],min_level=1,rarity='common',attack=0,attack_bonus=0,armor=0,ac_bonus=0)
    items['druid_leather']=dict(common,name='Skórzany kaftan druida',slot='armor',armor_kind='light',base_ac=11,
        value=3,price=10,icon='assets/equipment/druid_leather.svg',armor_summary='Lekki · KP 11 + Zręczność')
    items['wooden_shield']=dict(common,name='Dębowa tarcza',slot='shield',shield_ac=2,value=3,price=10,
        icon='assets/equipment/wooden_shield.svg',armor_summary='Tarcza · +2 KP')
    # A purchasable ordinary medium armor: no automatic Warden equipment grant.
    items['hide_armor']=dict(common,name='Pancerz ze skór',slot='armor',armor_kind='medium',base_ac=12,
        value=3,price=10,icon='assets/equipment/hide_armor.svg',armor_summary='Średni · KP 12 + Zręczność (maks. +2)')


def preview(p,item):
    """Hypothetical equipped item, using the same functions as actual combat."""
    r=_rules(); q=copy.copy(p);q.equipment=dict(p.equipment);q.inventory=list(p.inventory)
    canonical=_content().ITEMS.get(item.get('template'),item)
    slot=canonical.get('slot');result={'equip_error':check_equip(p,canonical)}
    if slot not in ('weapon','armor','shield','ring'):return result
    uid='preview_'+str(item.get('template',item.get('uid','item')))
    candidate=dict(canonical,uid=uid,template=item.get('template',''))
    # Runtime item templates are canonical; catalog callers always provide key.
    if candidate['template'] not in _content().ITEMS:return result
    q.inventory.append(candidate);q.equipment[slot]=uid
    q.form=''  # clearly a gear preview, never the beast's attack
    if slot=='weapon':
        if canonical.get('two_handed'):q.equipment['shield']=''
        q.weapon_grip='one'
        result.update(spell_bonus=0,proficient=proficient(q,canonical),proficiency=r.proficiency(q),attack=r.attack_bonus(q),
            dice=r.dice_text(r.weapon_dice(q)),damage_type=r.damage_type(q),
            mastery_active=q.class_id=='knight' and canonical.get('weapon_type') in ('longsword','greatsword','maul'))
        if canonical.get('versatile_dice'):
            q.weapon_grip='two';q.equipment['shield']='';result['two_hand_dice']=r.dice_text(r.weapon_dice(q))
        if canonical.get('spell_bonus') and p.class_id in canonical.get('focus_classes',[]):
            result.update(spell_bonus=canonical['spell_bonus'])
        result['heavy_penalty']=bool(canonical.get('heavy') and r.attributes(q)['dexterity' if canonical.get('ranged') else 'strength']<13)
    if slot=='shield' and (weapon(q).get('two_handed') or getattr(q,'weapon_grip','one')=='two'):
        result['equip_error']='Wymaga wolnej ręki.'
    if slot in ('armor','shield','ring'):
        result['ac']=r.armor_class(q)
        result['armor_penalty']=armor_penalty(q)
        result['speed_penalty']=armor_speed_penalty(q)>0
        if slot=='shield':result['untrained_shield']=not shield_trained(q)
    return result


def public_item(p,item):
    return dict(item,preview=preview(p,item))


def _preview_signature(p):
    return (p.class_id,p.level,getattr(p,'primal_order',''),tuple(sorted(getattr(p,'training_feats',{}).items())),
        getattr(p,'weapon_grip','one'),getattr(p,'fighting_style',''),p.form,
        tuple(sorted(p.mastery.items())),tuple(sorted(p.equipment.items())),
        tuple((i.get('uid'),i.get('template')) for i in p.inventory if i.get('uid') in p.equipment.values()),
        tuple(sorted(k for k,v in p.buffs.items() if v.get('until',0)>p.current_wall_time)),
        bool(getattr(p,'legacy_medium_grace',False)))


def cached_preview(p,item):
    signature=_preview_signature(p);cache=getattr(p,'_equipment_preview_cache',None)
    if not cache or cache[0]!=signature:
        cache=(signature,{});p._equipment_preview_cache=cache
    key=item.get('template','')
    if key not in cache[1]:cache[1][key]=preview(p,item)
    return cache[1][key]


def shop_previews(p):
    return {k:cached_preview(p,dict(v,template=k)) for k,v in _content().ITEMS.items() if 'price' in v}


def armor_speed_penalty(p):
    if p.form:return 0
    armor=_rules().equipped_item(p,'armor')
    required=armor.get('strength_required',0)
    return 10*6.4/3 if required and _rules().attributes(p)['strength']<required else 0
