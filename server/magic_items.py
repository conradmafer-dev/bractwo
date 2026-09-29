"""SRD 5.2.1 magic equipment; canonical effects and instance-bound attunement.

Sources: https://www.dndbeyond.com/sources/dnd/br-2024/magic-items-a-z
https://www.dndbeyond.com/sources/dnd/br-2024/equipment#Attunement
Distances and durations retain Bractwo's 6.4 units/foot and 3-second rounds.
"""
import math
from copy import deepcopy

VERSION = 1
DAY_SECONDS = 43200
ALL_CLASSES = ['knight', 'ranger', 'mage', 'druid']
SOURCE = 'SRD 5.2.1 (2024)'
CATALOG = {}
ALIASES = {}


def _item(key, name, slot, rarity, description, *, attune=False, base_cost=0, **extra):
    value = {'uncommon': 400, 'rare': 4000}[rarity] + base_cost
    CATALOG[key] = dict(name=name, slot=slot, rarity=rarity, min_level=1,
        class_ids=ALL_CLASSES[:], value=math.floor(value), price=math.ceil(value), srd_value_gp=value, attack=0, attack_bonus=0,
        ac_bonus=0, armor=0, magic_id=key, magic_source=SOURCE,
        requires_attunement=attune, description=description,
        icon='assets/equipment/'+key+'.svg', **extra)


_item('ring_protection', 'Pierścień ochrony', 'ring', 'rare',
      '+1 do KP i wszystkich rzutów obronnych. Wymaga zestrojenia.', attune=True,
      magic_effects={'protection': 1})
_item('ring_swimming', 'Pierścień pływania', 'ring', 'uncommon',
      'Szybkość pływania 40 stóp. Nie zapewnia oddychania pod wodą.',
      magic_effects={'swim': 40})
_item('ring_free_action', 'Pierścień swobody', 'ring', 'rare',
      'Trudny teren nie kosztuje dodatkowego ruchu. Magia nie obniża szybkości ani nie wywołuje paraliżu lub spętania. Wymaga zestrojenia.',
      attune=True, magic_effects={'free_action': True})
_item('ring_warmth', 'Pierścień ciepła', 'ring', 'uncommon',
      'Każde otrzymane obrażenia od zimna zmniejsza o 2k8. Chroni noszącego i jego ekwipunek przed temperaturą 0°F (ok. −18°C) i niższą. Wymaga zestrojenia.',
      attune=True, magic_effects={'warmth': True})
for _kind, _name in [('fire', 'ognia'), ('cold', 'zimna'), ('poison', 'trucizny'),
                     ('lightning', 'błyskawic'), ('necrotic', 'energii nekrotycznej')]:
    _item('ring_resistance_'+_kind, 'Pierścień odporności na '+_name, 'ring', 'rare',
          'Odporność na obrażenia typu '+_name+' (połowa obrażeń). Nie wymaga zestrojenia.',
          magic_effects={'resistance': _kind})
for _kind, _name, _cost, _dice, _damage, _category, _appearance in [
        ('longsword', 'Długi miecz +1', 15, [1, 8], 'slashing', 'martial', 'sword'),
        ('longbow', 'Długi łuk +1', 50, [1, 8], 'piercing', 'martial', 'bow'),
        ('quarterstaff', 'Kostur +1', .2, [1, 6], 'bludgeoning', 'simple', 'staff')]:
    _item('magic_'+_kind+'_1', _name, 'weapon', 'uncommon',
          '+1 do rzutów ataku i obrażeń wykonywanych tą bronią.', base_cost=_cost,
          weapon_type=_kind, weapon_name=_name, weapon_category=_category,
          weapon=_appearance, weapon_dice=_dice, damage_dice=f'{_dice[0]}k{_dice[1]}',
          damage_type=_damage, two_handed=_kind=='longbow', ranged=_kind=='longbow',
          heavy=_kind=='longbow', finesse=False, spell_bonus=0,
          magic_effects={'weapon_bonus': 1})
    CATALOG['magic_'+_kind+'_1'].update(attack=1, attack_bonus=1)
    if _kind!='longbow': CATALOG['magic_'+_kind+'_1']['versatile_dice']=[1, 10 if _kind=='longsword' else 8]
_item('magic_shield_1', 'Tarcza +1', 'shield', 'uncommon',
      '+1 do KP oprócz zwykłej premii tarczy +2 (łącznie +3 KP).', base_cost=10,
      shield_ac=3, armor_summary='Tarcza · +3 KP', magic_effects={'shield_bonus': 1})
for _key, _name, _rarity, _description, _effect in [
        ('magic_chain_mail_1', 'Kolczuga +1', 'rare', '+1 do KP kolczugi (KP 17).', {'armor_bonus': 1}),
        ('adamantine_chain_mail', 'Adamantynowa kolczuga', 'uncommon', 'Każde trafienie krytyczne przeciw noszącemu staje się zwykłym trafieniem.', {'adamantine': True}),
        ('mithral_chain_mail', 'Mithralowa kolczuga', 'uncommon', 'Nie wymaga Siły 13 i nie utrudnia testów Zręczności (Skradanie). Można nosić pod zwykłym ubraniem.', {'mithral': True})]:
    _item(_key, _name, 'armor', _rarity, _description, base_cost=75,
          armor_kind='heavy', base_ac=16, strength_required=0 if 'mithral' in _effect else 13,
          stealth_disadvantage='mithral' not in _effect,
          armor_summary='Ciężka · KP '+('17' if 'armor_bonus' in _effect else '16'), magic_effects=_effect)
    if 'armor_bonus' in _effect: CATALOG[_key].update(ac_bonus=1, armor=1)


def configure(items):
    """Run last: the old rarity converter must not overwrite SRD properties."""
    for key, old in list(items.items()):
        if old.get('slot')!='ring' or key in CATALOG: continue
        resistance=next(iter(old.get('resistances',())), '')
        replacement=old.get('magic_id') or ('ring_resistance_'+resistance if 'ring_resistance_'+resistance in CATALOG else (
            'ring_swimming' if key=='copper_ring' else 'ring_protection'))
        if replacement not in CATALOG:replacement='ring_protection'
        ALIASES[key]=replacement
        items[key]=deepcopy(CATALOG[replacement])
        items[key]['legacy_template']=key
    items.update(deepcopy(CATALOG))


def _catalog():
    try: from . import world_content
    except ImportError: import world_content
    return world_content.ITEMS


def _possessions(p):
    return [i for i in getattr(p,'inventory',()) if isinstance(i,dict)]


def _records(p):
    values=getattr(p,'magic_attunements',())
    return values if isinstance(values,list) else []


def _transformed(p):
    buff=getattr(p,'buffs',{}).get('polymorph',{})
    return bool(getattr(p,'form','') or buff.get('until',0)>getattr(p,'current_wall_time',0))


def active_items(p):
    if _transformed(p): return []
    equipped=set(getattr(p,'equipment',{}).values()); items=_catalog()
    attuned={r.get('uid') for r in _records(p) if isinstance(r,dict)}
    result=[]; seen=set()
    for item in _possessions(p):
        spec=items.get(item.get('template'),{})
        if item.get('uid') not in equipped or not spec.get('magic_id'): continue
        key=spec['magic_id']
        if key in seen or spec.get('requires_attunement') and item.get('uid') not in attuned: continue
        seen.add(key);result.append(spec)
    return result


def effect(p,key):
    return next((s['magic_effects'][key] for s in active_items(p) if key in s.get('magic_effects',{})),0)


def resistance(p,kind):
    return any(s.get('magic_effects',{}).get('resistance')==kind for s in active_items(p))


def reduces_magic_condition(p,key,value):
    if key not in ('paralyzed','restrained','web_restrained','elemental_restrained','slow','growth','headwind'): return False
    if not effect(p,'free_action'): return False
    # A weapon mastery, grapple or mundane net is not a spell.
    return bool(value.get('spell_id') or value.get('magical') is True)


def reduce_damage(p,amount,kind,rng):
    amount=max(0,int(amount))
    if amount and kind=='cold' and effect(p,'warmth'):
        return max(0,amount-rng.randint(1,8)-rng.randint(1,8))
    return amount


def prevent_critical(p,result):
    """Keep the hit (including natural 20), remove only the extra critical dice."""
    if not result.get('critical') or not effect(p,'adamantine'): return False
    rolls=result.get('damage_rolls',[])
    if rolls:
        rolls=rolls[:len(rolls)//2]
        result.update(damage_rolls=rolls,damage=max(0,sum(rolls)+result.get('damage_modifier',0)))
    result.update(critical=False,critical_prevented=True)
    return True


def _position(p):
    return dict(x=float(getattr(p,'x',0)),y=float(getattr(p,'y',0)),floor=int(getattr(p,'floor',0)))


def maintain(p,now=None):
    """Keep bonds on unequipped items; separated items lose them only after 24h."""
    now=float(getattr(p,'current_wall_time',0) if now is None else now)
    items=_catalog(); owned={i.get('uid'):i for i in _possessions(p)}
    pending=getattr(p,'rest_state',{}).get('magic_item',{})
    if pending and pending.get('uid') not in owned:pending['interrupted']=True
    kept=[];seen=set();uids=set()
    for raw in _records(p):
        if not isinstance(raw,dict) or not isinstance(raw.get('uid'),str): continue
        record=dict(raw);uid=record['uid'];item=owned.get(uid)
        template=item.get('template') if item else record.get('template')
        if not isinstance(template,str): continue
        spec=items.get(template,{})
        key=spec.get('magic_id')
        if not key or not spec.get('requires_attunement') or key in seen or uid in uids: continue
        record['template']=template
        if item:
            record['away_since']=None;record['last_position']=_position(p)
        else:
            pos=record.get('last_position') or _position(p)
            try: far=(int(pos['floor'])!=getattr(p,'floor',0) or math.hypot(float(pos['x'])-getattr(p,'x',0),float(pos['y'])-getattr(p,'y',0))>640)
            except (ValueError,KeyError,TypeError): far=True
            since=record.get('away_since')
            if not isinstance(since,(int,float)) or not math.isfinite(since) or since>now: since=None
            record['away_since']=(now if since is None else since) if far else None
            if far and now-record['away_since']>=DAY_SECONDS: continue
        kept.append(record);seen.add(key);uids.add(uid)
        if len(kept)>=3: break
    p.magic_attunements=kept
    buffs=getattr(p,'buffs',{})
    for key,value in tuple(buffs.items()):
        if reduces_magic_condition(p,key,value):buffs.pop(key,None)
    return kept


def migrate(p,items=None):
    items=items or _catalog()
    for container in (getattr(p,'inventory',[]),getattr(p,'depot',[])):
        if not isinstance(container,list): continue
        for item in container:
            if not isinstance(item,dict): continue
            spec=items.get(item.get('template'),{})
            if not spec.get('magic_id'): continue
            uid=item.get('uid');template=item.get('template');quantity=item.get('quantity')
            item.clear();item.update(deepcopy(spec),uid=uid,template=template)
            if quantity is not None:item['quantity']=quantity
    maintain(p)
    p.magic_items_version=VERSION


def attunement_error(p,uid,action):
    if action not in ('attune','unattune'): return 'Nieznana czynność zestrojenia.'
    if not isinstance(uid,str): return 'Wybierz posiadany przedmiot.'
    item=next((i for i in _possessions(p) if i.get('uid')==uid),None)
    if not item:return 'Przedmiot musi znajdować się w plecaku przez cały odpoczynek.'
    spec=_catalog().get(item.get('template'),{})
    if not spec.get('requires_attunement'):return 'Ten przedmiot nie wymaga zestrojenia.'
    records=maintain(p);attuned=any(r['uid']==uid for r in records)
    if action=='unattune':return '' if attuned else 'Nie jesteś zestrojony z tym przedmiotem.'
    if attuned:return 'Ten przedmiot jest już zestrojony.'
    if len(records)>=3:return 'Możesz być zestrojony najwyżej z trzema przedmiotami.'
    if any(_catalog().get(r['template'],{}).get('magic_id')==spec['magic_id'] for r in records):
        return 'Nie można zestroić dwóch egzemplarzy tego samego przedmiotu.'
    return ''


async def command(game,p,data):
    if not isinstance(data,dict):return
    p.current_wall_time=game.now()
    if not p.alive or _transformed(p):return await game.notice(p,'Zestrojenie wymaga żywej postaci bez przemiany.')
    action=data.get('action');uid=data.get('uid')
    error=attunement_error(p,uid,action)
    if error:return await game.notice(p,error)
    if p.rest_state:return await game.notice(p,'Najpierw zakończ bieżący odpoczynek.')
    await game.start_rest(p,'short',recover=False)
    if p.rest_state:
        p.rest_state['magic_item']=dict(action=action,uid=uid)
        await game.notice(p,'Skupienie na przedmiocie trwa przez cały krótki odpoczynek.')


def finish_rest(p,rest):
    request=rest.get('magic_item')
    if not isinstance(request,dict) or rest.get('kind')!='short':return ''
    if request.get('interrupted'):return 'Przerwano kontakt z przedmiotem. Rozpocznij zestrojenie od nowa.'
    uid=request.get('uid');action=request.get('action')
    error=attunement_error(p,uid,action)
    if error:return error
    if action=='unattune':
        p.magic_attunements=[r for r in _records(p) if r['uid']!=uid]
        return 'Zestrojenie zakończone.'
    item=next(i for i in _possessions(p) if i.get('uid')==uid)
    p.magic_attunements.append(dict(uid=uid,template=item['template'],away_since=None,last_position=_position(p)))
    return 'Zestrojenie ukończone: '+_catalog()[item['template']]['name']+'.'


def on_death(p):
    p.magic_attunements=[]


def sheet(p):
    records=maintain(p);active_ids={s['magic_id'] for s in active_items(p)}
    pending=getattr(p,'rest_state',{}).get('magic_item',{})
    rows=[]
    for item in _possessions(p):
        spec=_catalog().get(item.get('template'),{})
        if not spec.get('magic_id'):continue
        uid=item.get('uid');attuned=any(r['uid']==uid for r in records)
        rows.append(dict(uid=uid,template=item['template'],name=spec['name'],
            requires_attunement=spec.get('requires_attunement',False),attuned=attuned,
            equipped=uid in getattr(p,'equipment',{}).values(),active=spec['magic_id'] in active_ids and uid in getattr(p,'equipment',{}).values(),
            action='unattune' if attuned else 'attune',
            attunement_error=attunement_error(p,uid,'unattune' if attuned else 'attune') if spec.get('requires_attunement') else '',
            pending=pending.get('uid')==uid,description=spec['description']))
    return dict(limit=3,used=len(records),items=rows,pending=pending,
        cold_reduction='2k8' if effect(p,'warmth') else '',free_action=bool(effect(p,'free_action')),
        swim_speed=effect(p,'swim'),critical_immunity=bool(effect(p,'adamantine')))


def metadata():
    return dict(source=SOURCE,attunement_limit=3,attunement_rest='short',
        ring_slots=1,ring_slot_rule='Jedno miejsce na pierścień jest zasadą ekwipunku Bractwa, nie limitem D&D.',
        items=[dict(id=k,**deepcopy(v)) for k,v in CATALOG.items()])
