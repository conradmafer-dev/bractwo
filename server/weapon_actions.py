"""Light, Thrown and Unarmed rules shared by actual attacks and UI previews.

Thrown weapons leave the bag as exact instances. Their private ground ledger is
saved with the owner, so a restart neither duplicates nor destroys the weapon.
No function here starts a turn: main actions establish the existing turn token.
"""
from contextlib import contextmanager
from copy import deepcopy
import math
from types import SimpleNamespace

try:
    from . import equipment_rules as gear, inventory_rules, fighter_rules, environment_rules
except ImportError:
    import equipment_rules as gear, inventory_rules, fighter_rules, environment_rules

PIXELS_PER_FOOT=6.4
THROWN_LIMIT=40
MODES=('weapon','throw','unarmed')


def _rules():return gear._rules()
def _items():return gear._content().ITEMS


def held_item(p,slot='weapon'):
    uid=getattr(p,'equipment',{}).get(slot,'')
    instance=next((i for i in getattr(p,'inventory',[]) if i.get('uid')==uid),None)
    return dict(_items().get(instance.get('template'),instance),uid=uid,template=instance.get('template')) if instance else {}


def mode(p):
    if getattr(p,'form','') or environment_rules.polymorph(p):return 'weapon'
    context=getattr(p,'_weapon_action_mode',None)
    return context if context in MODES else getattr(p,'weapon_attack_mode','weapon') if getattr(p,'weapon_attack_mode','weapon') in MODES else 'weapon'


def current_weapon(p):
    """Canonical attack weapon; an offhand context changes only this attack."""
    context=getattr(p,'_weapon_action_item',None)
    if context is not None:return context
    return {} if mode(p)=='unarmed' else held_item(p)


def is_offhand(p):return bool(getattr(p,'_weapon_action_offhand',False))
def is_thrown(p):return mode(p)=='throw' and bool(current_weapon(p).get('thrown'))


@contextmanager
def attack_context(p,item,*,offhand=False,attack_mode=None):
    fields=('_weapon_action_item','_weapon_action_offhand','_weapon_action_mode')
    missing=object();previous={key:getattr(p,key,missing) for key in fields}
    p._weapon_action_item=item;p._weapon_action_offhand=bool(offhand)
    p._weapon_action_mode=attack_mode or mode(p)
    try:yield
    finally:
        for key,value in previous.items():
            if value is missing:delattr(p,key)
            else:setattr(p,key,value)


def mode_error(p,value):
    if value not in MODES:return 'Wybierz atak bronią, rzut bronią albo atak bez broni.'
    if getattr(p,'form','') or environment_rules.polymorph(p):return 'Zakończ przemianę przed zmianą sposobu ataku.'
    if not getattr(p,'alive',True):return 'Najpierw wróć do życia.'
    if value=='throw' and not held_item(p).get('thrown'):return 'Założona broń nie ma właściwości Rzucana.'
    if value=='throw' and len(getattr(p,'thrown_weapons',[]))>=THROWN_LIMIT:return 'Podnieś rzuconą broń przed kolejnym rzutem.'
    return ''


def set_mode(p,value):
    error=mode_error(p,value)
    if error:return error
    p.weapon_attack_mode=value
    return ''


def ranges(p):
    """Normal/long reach in world pixels, or None for unchanged legacy attacks."""
    if mode(p)=='unarmed' or getattr(p,'fighting_style','')=='unarmed' and not current_weapon(p):return 32,32
    if not is_thrown(p):return None
    normal,long=current_weapon(p).get('thrown_range',[20,60])
    return normal*PIXELS_PER_FOOT,long*PIXELS_PER_FOOT


def long_range_disadvantage(p,target):
    reach=ranges(p)
    return bool(is_thrown(p) and reach and math.hypot(target.x-p.x,target.y-p.y)>reach[0])


def damage_ability_modifier(p,ability_modifier):
    """The Light attack excludes positive ability damage without its style."""
    styled=getattr(p,'fighting_style','')=='two_weapon' and fighter_rules.style_active(p,'two_weapon')
    return ability_modifier if not is_offhand(p) or styled else min(0,ability_modifier)


def unarmed_dice(p):
    strength=_rules().ability_modifier(p,'strength')
    if getattr(p,'fighting_style','')=='unarmed' and fighter_rules.style_active(p,'unarmed'):
        held=any(held_item(p,slot) for slot in ('weapon','offhand','shield'))
        return 1,6 if held else 8,strength
    return 0,1,max(0,1+strength)


def record_light_attack(p,item,now,*,main_action=True):
    """Called for an attempted main Attack, including a miss, never a reaction."""
    until=getattr(p,'_feat_turn_until',0)
    if not main_action or getattr(p,'_off_turn_attack',False) or is_offhand(p) or not item.get('light') or not item.get('uid') or now>=until:return False
    p._light_attack_until=until
    p._light_attack_uid=item['uid']
    return True


def offhand_error(p,now):
    if getattr(p,'form','') or environment_rules.polymorph(p):return 'W tej postaci nie można atakować drugą bronią.'
    other=held_item(p,'offhand')
    if not other or not other.get('light') or other.get('two_handed'):return 'Załóż lekką broń w drugiej ręce.'
    if p.equipment.get('shield') or getattr(p,'weapon_grip','one')=='two':return 'Druga ręka jest zajęta.'
    if (now>=getattr(p,'_light_attack_until',0) or getattr(p,'_light_attack_until',0)!=getattr(p,'_feat_turn_until',0)
            or other.get('uid')==getattr(p,'_light_attack_uid','')):
        return 'Najpierw w tej turze zaatakuj inną lekką bronią.'
    if getattr(p,'bonus_cooldown_until',0)>now or getattr(p,'_light_extra_used_until',0)==getattr(p,'_feat_turn_until',0):
        return 'Akcja dodatkowa tej tury jest już wykorzystana.'
    return ''


def spend_offhand(p,now):
    error=offhand_error(p,now)
    if error:return error
    p._light_extra_used_until=p._feat_turn_until
    # Share exactly the same Bonus Action gate as spells; do not reset any turn.
    p.bonus_cooldown_until=max(now+_rules().ROUND_SECONDS,p._feat_turn_until)
    return ''


def free_hand(p):
    main=held_item(p)
    if main.get('two_handed') or main.get('versatile_dice') and getattr(p,'weapon_grip','one')=='two':return False
    return sum(bool(held_item(p,slot)) for slot in ('weapon','offhand','shield'))+getattr(p,'_weapon_grapple_hands',0)<2


def grapple_dc(p):return 8+_rules().proficiency(p)+_rules().ability_modifier(p,'strength')


def owned_grapple(p,target,now):
    grip=environment_rules.conditions(target).get('grappled',{})
    return bool(grip.get('owner')==p.id and grip.get('until',0)>now)


def throw_error(p,item=None):
    item=current_weapon(p) if item is None else item
    if not item.get('thrown') or not item.get('uid'):return 'Potrzebujesz trzymanej broni z właściwością Rzucana.'
    if not any(i.get('uid')==item['uid'] for i in p.inventory):return 'Ta broń nie jest już w twoim plecaku.'
    if len(getattr(p,'thrown_weapons',[]))>=THROWN_LIMIT:return 'Podnieś rzuconą broń przed kolejnym rzutem.'
    return ''


def throw_weapon(p,target,item=None,*,slot='weapon'):
    """Release after the resolved attack and draw the next identical template."""
    item=current_weapon(p) if item is None else item
    if throw_error(p,item):return None
    uid=item['uid'];template=item.get('template')
    # Snapshot before removing it: never manufacture a fresh canonical identity.
    instance=inventory_rules.remove_instance(p,uid)
    if instance is None:return None
    entry=dict(item=deepcopy(instance),x=target.x,y=target.y,floor=target.floor)
    if not isinstance(getattr(p,'thrown_weapons',None),list):p.thrown_weapons=[]
    p.thrown_weapons.append(entry)
    equipped=set(p.equipment.values())
    next_item=next((i for i in p.inventory if i.get('template')==template and i.get('uid') not in equipped
        and p.level>=_items().get(template,{}).get('min_level',1) and gear.proficient(p,_items().get(template,{}))),None)
    if next_item:p.equipment[slot]=next_item['uid']
    return entry


def recover_thrown(p,uid,capacity,*,line_clear=None):
    """Owner-only recovery near the landing point, atomic even for a full bag."""
    if not isinstance(uid,str):return 'Wybierz rzuconą broń.'
    entry=next((e for e in getattr(p,'thrown_weapons',[]) if isinstance(e,dict) and e.get('item',{}).get('uid')==uid),None)
    if not entry:return 'Nie ma tu twojej rzuconej broni.'
    target=SimpleNamespace(x=entry['x'],y=entry['y'],floor=entry['floor'])
    if not getattr(p,'alive',True) or target.floor!=p.floor or math.hypot(target.x-p.x,target.y-p.y)>64:
        return 'Podejdź do swojej rzuconej broni.'
    if line_clear is not None and not line_clear(p,target):return 'Broń leży za przeszkodą.'
    if not inventory_rules.restore_instance(p,deepcopy(entry['item']),capacity):return 'Brak miejsca w plecaku albo broń została już podniesiona.'
    p.thrown_weapons.remove(entry)
    return ''


def sanitize(p):
    """Repair optional old fields while keeping every valid owned identity."""
    if getattr(p,'weapon_attack_mode','weapon') not in MODES:p.weapon_attack_mode='weapon'
    p.equipment.setdefault('offhand','')
    other=held_item(p,'offhand');main=held_item(p)
    if p.equipment['offhand'] and (not other.get('light') or (main and not main.get('light'))
            or other.get('uid')==main.get('uid') or p.equipment.get('shield') or getattr(p,'weapon_grip','one')=='two'):
        p.equipment['offhand']=''
    owned={i.get('uid') for i in p.inventory+getattr(p,'depot',[]) if isinstance(i,dict)}
    raw=getattr(p,'thrown_weapons',[]);valid=[]
    if isinstance(raw,list):
        for entry in raw:
            if not isinstance(entry,dict) or not isinstance(entry.get('item'),dict):continue
            item=entry['item'];uid=item.get('uid');template=item.get('template')
            if not isinstance(template,str):continue
            spec=_items().get(template,{})
            if not isinstance(uid,str) or not uid or uid in owned or spec.get('slot')!='weapon' or not spec.get('thrown'):continue
            if type(entry.get('floor')) is not int:continue
            if any(type(entry.get(key)) not in (int,float) or not math.isfinite(entry[key]) for key in ('x','y')):continue
            owned.add(uid)
            valid.append(dict(item=dict(spec,uid=uid,template=template),x=entry['x'],y=entry['y'],floor=entry['floor']))
            if len(valid)==THROWN_LIMIT:break
    p.thrown_weapons=valid
    return p


def sheet(p,now):
    held=held_item(p)
    return dict(mode=mode(p),modes=[dict(id=value,enabled=not mode_error(p,value)) for value in MODES],
        offhand=held_item(p,'offhand'),offhand_enabled=not offhand_error(p,now),offhand_reason=offhand_error(p,now),
        can_equip_offhand=bool(held.get('light') and not p.equipment.get('shield')),
        can_grapple=free_hand(p),grapple_dc=grapple_dc(p),unarmed_dice=_rules().dice_text(unarmed_dice(p)),
        thrown_weapons=deepcopy(getattr(p,'thrown_weapons',[])))
