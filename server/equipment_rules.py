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
    'tough': dict(name='Twardy', grants=[], requires=[], abilities=[], category='origin', description='Maksymalne HP zwiększone o 2 za każdy poziom D&D (poziomy Bractwa przeliczone ×5).', icon='assets/feats/tough.svg'),
    'savage_attacker': dict(name='Zacięty atak', grants=[], requires=[], abilities=[], category='origin', description='Raz na turę, po trafieniu bronią, rzucasz jej kośćmi obrażeń dwa razy i wybierasz lepszy zestaw.', icon='assets/feats/savage_attacker.svg'),
    'skilled': dict(name='Wszechstronny', grants=[], requires=[], abilities=[], category='origin', repeatable=True, description='Wybierz biegłość w trzech kolejnych umiejętnościach. Atut można wybrać ponownie; nie zwiększa cech.', icon='assets/feats/skilled.svg'),
    'ability_score_improvement': dict(name='Rozwój cech', grants=[], requires=[], abilities=['strength','dexterity','constitution','intelligence','wisdom','charisma'], repeatable=True, ability_points=2, description='+2 do jednej cechy albo +1 do dwóch cech, maksymalnie 20.', icon='assets/feats/ability_score_improvement.svg'),
    'heavy_armor_master': dict(name='Mistrz ciężkiego pancerza', grants=[], requires=['heavy_armor'], abilities=['strength','constitution'], description='+1 Siła lub Kondycja, maksymalnie 20. W ciężkim pancerzu obrażenia obuchowe, kłute i cięte od trafiających ataków są zmniejszone o premię z biegłości.', icon='assets/feats/heavy_armor_master.svg'),
    'medium_armor_master': dict(name='Mistrz średniego pancerza', grants=[], requires=['medium_armor'], abilities=['strength','dexterity'], description='+1 Siła lub Zręczność, maksymalnie 20. Przy Zręczności co najmniej 16 średni pancerz uwzględnia do +3 do KP ze Zręczności zamiast +2.', icon='assets/feats/medium_armor_master.svg'),
}
FEAT_LEVELS = (15,35,55,75,90)  # D&D 2024 class 4/8/12/16/19.
FIGHTER_FEAT_LEVELS = (15,25,35,55,65,75,90)  # Fighter also gets 6 and 14.
FEAT_RULES_VERSION = 1
MAX_FEAT_CHOICES = len(FIGHTER_FEAT_LEVELS)
ORIGIN_FEATS = tuple(k for k,v in GENERAL_FEATS.items() if v.get('category')=='origin')


def feat_levels(p):
    return FIGHTER_FEAT_LEVELS if p.class_id=='knight' else FEAT_LEVELS


def feat_entitlement(p):
    return sum(p.level>=n for n in feat_levels(p))


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
    if getattr(p,'origin_feat','') in ORIGIN_FEATS:pending.add('origin_'+p.origin_feat)
    for _ in range(len(GENERAL_FEATS)):
        ready=[k for k in pending if feat_key(k) in GENERAL_FEATS and all(r in result for r in GENERAL_FEATS[feat_key(k)]['requires'])]
        if not ready:break
        for k in ready:
            active.add(k);pending.remove(k)
            for grant in GENERAL_FEATS[feat_key(k)]['grants']:result.setdefault(grant,[]).append(GENERAL_FEATS[feat_key(k)]['name'])
    return result,active


def training_sources(p):return _training(p)[0]
def active_feats(p):return _training(p)[1]


def feat_key(instance):
    """Repeatable choices retain string keys and values in existing save files."""
    if not isinstance(instance,str):return ''
    if instance in GENERAL_FEATS:return instance
    if instance.startswith('origin_') and instance[7:] in ORIGIN_FEATS:return instance[7:]
    for key,spec in GENERAL_FEATS.items():
        if not spec.get('repeatable'):continue
        prefix=key+'_'
        suffix=instance[len(prefix):] if instance.startswith(prefix) else ''
        if suffix in {str(n) for n in range(2,MAX_FEAT_CHOICES+1)}:return key
    return ''


def feat_allocations(key,value):
    spec=GENERAL_FEATS.get(feat_key(key))
    if not spec or not isinstance(value,str):return None
    if not spec['abilities']:return {} if value=='' else None
    choices=value.split('+')
    if len(choices)!=spec.get('ability_points',1) or any(a not in spec['abilities'] for a in choices):return None
    return {a:choices.count(a) for a in choices}


def sanitize_feats(p):
    raw=getattr(p,'training_feats',{})
    p.training_feats={k:v for k,v in raw.items() if isinstance(k,str) and not k.startswith('origin_') and feat_allocations(k,v) is not None} if isinstance(raw,dict) else {}
    if getattr(p,'origin_feat','') not in ORIGIN_FEATS:p.origin_feat=''
    return p.training_feats


def migrate_advancement(p):
    """Keep earned choices and archive surplus legacy data, never grant free ASIs.

    Old primary-score increases were derived from level rather than persisted.
    Their removal is disclosed; existing manually selected feats keep their slots.
    Archiving records a choice for the owner without leaving its bonus active.
    """
    version=getattr(p,'feat_rules_version',0)
    if type(version) is int and version>=FEAT_RULES_VERSION:
        sanitize_feats(p)
        return False
    raw=getattr(p,'training_feats',{})
    raw=raw if isinstance(raw,dict) else {}
    p.training_feats=raw
    sanitize_feats(p)
    previous_hp=max(1,_rules().max_hp(p))
    fraction=max(0,min(1,getattr(p,'hp',previous_hp)/previous_hp))
    kept={};archive={}
    for key,value in raw.items():
        valid=isinstance(key,str) and not key.startswith('origin_') and feat_allocations(key,value) is not None
        if valid and len(kept)<feat_entitlement(p):kept[key]=value
        else:
            archive[str(key)[:100]]=dict(value=value if isinstance(value,str) else '',
                reason='Wybór ponad limit poziomu.' if valid else 'Nieprawidłowy dawny wybór.')
    p.training_feats=kept
    p.feat_legacy_choices=archive
    notes=[]
    if p.level>=20:
        notes.append('Usunięto dawny automatyczny wzrost głównej cechy na poziomach 20 i 40. Rozwój cech i atuty korzystają teraz ze wspólnej puli wyborów D&D; zachowano wcześniej wybrane atuty.')
    if archive:
        notes.append('Dawne wybory ponad limit lub nieprawidłowe zapisano poniżej bez aktywnych premii. Prawidłowy atut możesz wybrać ponownie, gdy zdobędziesz wolny wybór.')
    p.feat_migration_notice=' '.join(notes)
    p.feat_rules_version=FEAT_RULES_VERSION
    if hasattr(p,'hp'):p.hp=_rules().max_hp(p)*fraction
    p._level_up_cache=None
    return True


def feat_ability_bonuses(p):
    bonuses={}
    active=active_feats(p)
    for key,value in getattr(p,'training_feats',{}).items():
        if key not in active:continue
        for ability,amount in (feat_allocations(key,value) or {}).items():bonuses[ability]=bonuses.get(ability,0)+amount
    return bonuses


def has_feat(p,key):return any(feat_key(k)==key for k in active_feats(p))


def heavy_armor_reduction(p,kind,is_attack=False):
    if (not is_attack or kind not in ('bludgeoning','piercing','slashing') or getattr(p,'form','')
            or not has_feat(p,'heavy_armor_master') or _rules().equipped_item(p,'armor').get('armor_kind')!='heavy'):
        return 0
    return _rules().proficiency(p)


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


def feat_points(p):return max(0,feat_entitlement(p)-len(getattr(p,'training_feats',{})))


def feat_eligible(p,key):
    s=GENERAL_FEATS.get(key)
    if not s or not s.get('repeatable') and (key in getattr(p,'training_feats',{}) or getattr(p,'origin_feat','')==key):return False
    if key=='skilled':
        try:from . import skill_rules
        except ImportError:import skill_rules
        if not skill_rules.can_add_skilled(p):return False
    if s['abilities']:
        scores=_rules().own_attributes(p)
        if sum(max(0,20-scores[a]) for a in s['abilities'])<s.get('ability_points',1):return False
    known=training_sources(p)
    return (not s['grants'] or any(g not in known for g in s['grants'])) and all(r in known for r in s['requires'])


def select_origin_feat(p,key):
    """The initial Origin feat is its own one-time grant, never an ASI point."""
    if not isinstance(key,str) or key not in ORIGIN_FEATS:return 'Wybierz atut pochodzenia.'
    if getattr(p,'origin_feat',''):return 'Atut pochodzenia został już wybrany.'
    if not GENERAL_FEATS[key].get('repeatable') and key in getattr(p,'training_feats',{}):return 'Masz już ten atut. Wybierz inny atut pochodzenia.'
    if key=='skilled' and not feat_eligible(p,key):return 'Za mało nowych umiejętności na trzy biegłości tego atutu.'
    if getattr(p,'form',''):return 'Zakończ przemianę przed wyborem atutu.'
    p.origin_feat=key
    return ''


def select_feat(p,key,ability='',abilities=None,expected_spent=None):
    """Validate the whole allocation before spending a point; return error or ''."""
    if not isinstance(key,str) or key not in GENERAL_FEATS:return 'Nieznany atut.'
    if expected_spent is not None and (type(expected_spent) is not int or expected_spent!=len(getattr(p,'training_feats',{}))):
        return 'Ten wybór został już rozliczony. Sprawdź aktualną pulę rozwoju.'
    if feat_points(p)<1 or not feat_eligible(p,key):return 'Ten atut jest już posiadany, zbędny albo niedostępny.'
    if getattr(p,'form',''):return 'Zakończ przemianę przed wyborem atutu.'
    spec=GENERAL_FEATS[key]
    if abilities is not None:
        if not isinstance(abilities,(list,tuple)) or not all(isinstance(a,str) for a in abilities):return 'Wybierz właściwe cechy.'
        ability='+'.join(abilities)
    # A single ASI ability is a convenient request for +2 to that ability.
    if abilities is None and spec.get('ability_points')==2 and isinstance(ability,str) and ability in spec['abilities']:ability=ability+'+'+ability
    allocation=feat_allocations(key,ability)
    if allocation is None:return 'Wybierz właściwe cechy dla tego atutu.'
    scores=_rules().own_attributes(p)
    if any(scores[a]+n>20 for a,n in allocation.items()):return 'Atut nie może zwiększyć cechy powyżej 20.'
    instance=key
    if spec.get('repeatable'):
        for n in range(1,MAX_FEAT_CHOICES+1):
            instance=key if n==1 else key+'_'+str(n)
            if instance not in p.training_feats:break
        else:return 'Nie masz wolnego wyboru tego atutu.'
    p.training_feats[instance]=ability
    # Archive is a history ledger, not a second pool of usable points.
    for old_key,old in list(getattr(p,'feat_legacy_choices',{}).items()):
        if feat_key(old_key)==key and isinstance(old,dict) and old.get('value')==ability:
            del p.feat_legacy_choices[old_key]
            break
    return ''


def granted_rows(p):
    return [dict(id=k,name=TRAINING[k][0],sources=v,description=' / '.join(v),icon=f'assets/feats/{k}.svg') for k,v in training_sources(p).items()]


def training_sheet(p):
    scores=_rules().own_attributes(p)
    def row(key,value=None):
        base=feat_key(key);spec=GENERAL_FEATS[base]
        data=dict(spec,id=key,feat_id=base,icon=spec.get('icon') or f"assets/feats/{spec['grants'][0]}.svg",min_level=15)
        data['abilities']=[a for a in spec['abilities'] if scores[a]<20]
        if value is not None:data.update(ability=value,allocation=feat_allocations(key,value) or {},active=key in active_feats(p))
        return data
    archived=[dict(id=k,name=GENERAL_FEATS.get(feat_key(k),{}).get('name',k),reason=v.get('reason','Dawny wybór.'))
              for k,v in getattr(p,'feat_legacy_choices',{}).items() if isinstance(v,dict)]
    origin=getattr(p,'origin_feat','')
    origin_chosen=row('origin_'+origin,'') if origin in ORIGIN_FEATS else None
    if origin_chosen:origin_chosen['min_level']=1
    origin_options=[] if origin_chosen else [row(k) for k in ORIGIN_FEATS if feat_eligible(p,k)]
    for option in origin_options:option['min_level']=1
    return dict(granted=granted_rows(p),points=feat_points(p),levels=list(feat_levels(p)),
        dnd_levels=[1+n//5 for n in feat_levels(p)],earned=feat_entitlement(p),spent=len(getattr(p,'training_feats',{})),score_cap=20,
        migration_notice=getattr(p,'feat_migration_notice',''),archived=archived,
        origin=dict(chosen=origin_chosen,options=origin_options,points=0 if origin_chosen else 1),
        advancement_note='Rozwój cech (+2 albo +1/+1) i atut zużywają ten sam wybór. Na poziomie 90 można wybrać atut z dostępnego katalogu; epickie dary nie są jeszcze dostępne.',
        chosen=[row(k,v) for k,v in getattr(p,'training_feats',{}).items() if feat_key(k)],
        options=[row(k) for k in GENERAL_FEATS if feat_eligible(p,k)],
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
    if canonical.get('requires_attunement'):
        # Explicitly show the potential after a completed attunement, never grant it.
        q.magic_attunements=[dict(uid=uid,template=candidate['template'])]
        result['requires_attunement']=True
        result['attuned']=any(v.get('uid')==item.get('uid') for v in getattr(p,'magic_attunements',[]) if isinstance(v,dict))
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
    return (p.class_id,p.level,getattr(p,'promoted',False),getattr(p,'wizard_school',''),getattr(p,'primal_order',''),tuple(sorted(getattr(p,'training_feats',{}).items())),
        getattr(p,'origin_feat',''),
        tuple(sorted(_rules().base_attributes(p).items())),
        getattr(p,'weapon_grip','one'),getattr(p,'fighting_style',''),p.form,
        tuple(sorted(p.mastery.items())),tuple(sorted(p.equipment.items())),tuple(v.get('uid','') for v in getattr(p,'magic_attunements',[]) if isinstance(v,dict)),
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
