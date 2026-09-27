"""Inventory stacks, equipped quick potions, and character-owned loot discoveries.

Canonical item stats never carry another character's discoveries. The legacy
`potions` dictionary is an output mirror for older clients, not a second bag.
"""
from copy import deepcopy

VERSION = 1
STACK_LIMIT = 99


def configure(items, potions):
    labels = ('mała', 'większa', 'potężna', 'najwyższa')
    for key, spec in potions.items():
        tier = int(key.rsplit('_', 1)[1]) if key[-1].isdigit() else 1
        spec.update(name='Mikstura zdrowia · '+labels[tier-1],
                    icon=f'assets/equipment/{key}.svg', potion_kind='health')
        dice = spec.get('dice')
        effect = f"{dice[0]}k{dice[1]}+{dice[2]} HP" if dice else f"{spec['restore']} HP"
        items[key] = dict(spec, slot='potion', class_ids=['knight','ranger','mage','druid'],
                          min_level=spec.get('min_level',1), value=max(1,spec['price']//3),
                          rarity=('common','uncommon','rare','epic')[tier-1], stack_limit=STACK_LIMIT,
                          attack=0, attack_bonus=0, armor=0, ac_bonus=0, effect_summary=effect,
                          description='Odnawia '+effect+'. Wspólne odnowienie mikstur: 3 sekundy.')
    # The first quest reward used to become identical to starter gear when the
    # rarity-to-enchantment conversion rounded both common/uncommon down to zero.
    for cls in ('knight','ranger','mage','druid'):
        for tier, bonus in ((2,1),(3,2)):
            spec=items[f'{cls}_weapon_{tier}']
            spec.update(attack_bonus=bonus, attack=0 if cls=='mage' else bonus,
                        enchantment=bonus, rarity='uncommon' if tier==2 else 'rare')
            spec['description']=('Fokus strażnika' if tier==2 else 'Fokus pogranicza')+f': +{bonus} do trafienia i ST czarów. Iskra pozostaje 1k4, bez skalowania.' if cls=='mage' else f'+{bonus} do trafienia i obrażeń broni.'


def count(p, template):
    return sum(int(i.get('quantity',1)) for i in p.inventory if i.get('template')==template and i.get('slot')=='potion')


def sync(p, potions):
    """Refresh compatibility counts after *every* inventory transfer."""
    p.potions={key:count(p,key) for key in potions}


def retired_potion(template):
    return isinstance(template,str) and (template=='mana_potion' or template.startswith('mana_potion_'))


def ensure(p, items, potions, make_item):
    """Migrate surviving supplies without dropping gear from a full old bag.

    A migrated overfull bag is temporarily allowed. New stacks cannot enter it
    until space is made. The version prevents duplication on subsequent logins.
    """
    # Retired mana stacks disappear from both bags, including already migrated saves.
    # Keep the original migration version so stale compatibility counts are not reimported.
    for bag in (p.inventory,p.depot):
        bag[:]=[item for item in bag if not retired_potion(item.get('template'))]
    if p.inventory_rules_version < VERSION:
        legacy=dict(p.potions)
        for key, amount in legacy.items():
            if key not in potions or type(amount) is not int or amount<=0:
                continue
            existing=count(p,key)
            if existing < amount:
                left=amount-existing
                for stack in p.inventory:
                    if stack.get('template')==key:
                        add=min(left,STACK_LIMIT-int(stack.get('quantity',1)))
                        stack['quantity']=int(stack.get('quantity',1))+add;left-=add
                while left>0:
                    item=make_item(key);item['quantity']=min(STACK_LIMIT,left)
                    p.inventory.append(item);left-=item['quantity']
        p.inventory_rules_version=VERSION
    q=p.potion_slots.get('q','health_potion') if isinstance(p.potion_slots,dict) else 'health_potion'
    if not isinstance(q,str) or (q not in potions and q!=''):q='health_potion'
    p.potion_slots={'q':q}
    if not isinstance(p.loot_discoveries,dict):p.loot_discoveries={}
    p.loot_discoveries={key:value for key,value in p.loot_discoveries.items() if not retired_potion(key)}
    sync(p,potions)


def slots_needed(p, rewards, cap=STACK_LIMIT):
    """Additional inventory cells needed for a complete, atomic reward."""
    needed=0
    for key,amount in rewards.items():
        free=sum(max(0,cap-int(i.get('quantity',1))) for i in p.inventory if i.get('template')==key and i.get('slot')=='potion')
        needed += (max(0,amount-free)+cap-1)//cap
    return needed


def add(p, template, quantity, make_item, capacity):
    if retired_potion(template) or type(quantity) is not int or quantity<1:return False
    extra=slots_needed(p,{template:quantity})
    if extra and len(p.inventory)+extra>capacity:return False
    left=quantity
    for item in p.inventory:
        if item.get('template')==template and item.get('slot')=='potion':
            n=min(left,max(0,STACK_LIMIT-int(item.get('quantity',1))))
            item['quantity']=int(item.get('quantity',1))+n;left-=n
            if not left:return True
    while left:
        item=make_item(template);item['quantity']=min(STACK_LIMIT,left)
        p.inventory.append(item);left-=item['quantity']
    return True


def consume(p, template, quantity=1):
    if count(p,template)<quantity:return False
    for item in list(p.inventory):
        if item.get('template')==template and item.get('slot')=='potion':
            n=min(quantity,int(item.get('quantity',1)))
            item['quantity']=int(item.get('quantity',1))-n;quantity-=n
            if item['quantity']==0:p.inventory.remove(item)
            if quantity==0:return True
    return False


def discover(p, template, kind, enemies):
    # Only an actual, successfully delivered monster drop may call this.
    if kind not in enemies:return
    if not any(e['template']==template for e in enemies[kind]['loot'].get('entries',[])):return
    found=p.loot_discoveries.setdefault(template,[])
    if kind not in found:found.append(kind)


def sources(p, template, enemies):
    rows=[]
    for kind in p.loot_discoveries.get(template,[]):
        enemy=enemies.get(kind)
        if enemy is None:continue
        entry=next((e for e in enemy['loot'].get('entries',[]) if e['template']==template),None)
        if entry:rows.append(dict(kind=kind,name=enemy['name'],chance=entry['chance']))
    return rows


def public_item(p, item, enemies):
    result=dict(item)
    result['sources']=sources(p,item.get('template',''),enemies)
    try: from . import equipment_rules
    except ImportError: import equipment_rules
    result['preview']=equipment_rules.cached_preview(p,item)
    return result


def known_loot(p, enemies):
    result={}
    for template in p.loot_discoveries:
        for src in sources(p,template,enemies):
            result.setdefault(src['kind'],[]).append(dict(template=template,chance=src['chance'],kind='potion' if template.startswith('health_potion') else 'item'))
    return result


def metadata_items(items):
    return {key:{k:v for k,v in item.items() if k!='sources'} for key,item in items.items()}


def metadata_enemies(enemies):
    result=deepcopy(enemies)
    for kind, spec in result.items():
        spec['kind']=kind
        spec['loot']={'discovered_only':True,'independent':True}
    return result
