"""Persistent, rest-based class resources. Game clocks are deliberately compressed."""
try:
    from . import caster_rules as caster
except ImportError:
    import caster_rules as caster

NAMES = {'hit_dice':'Kości zdrowia', 'arcane_recovery':'Odzyskanie mocy',
         'second_wind':'Drugi oddech', 'action_surge':'Zryw akcji',
         'animal_companion':'Przywołanie towarzysza', 'lucky':'Szczęściarz'}

def state(p):
    if not isinstance(getattr(p,'rest_resources',None),dict):p.rest_resources={}
    return p.rest_resources

def maximum(p,key):
    level=caster.effective_level(p)
    if key=='lucky':
        try:from . import equipment_rules as gear
        except ImportError:import equipment_rules as gear
        return 2+(level-1)//4 if gear.has_feat(p,'lucky') else 0
    if key=='hit_dice':return level
    if key=='arcane_recovery':return int(p.class_id=='mage')
    if key=='second_wind':return 2+int(level>=4)+int(level>=10) if p.class_id=='knight' else 0
    if key=='action_surge':return 1+int(level>=17) if p.class_id=='knight' and level>=2 else 0
    if key=='animal_companion':return int(p.class_id=='ranger' and p.level>=10)
    return 0

def spent(p,key):
    try:return max(0,int(state(p).get(key,0)))
    except (ValueError,TypeError,OverflowError):return 0

def remaining(p,key):return max(0,maximum(p,key)-spent(p,key))

def spend(p,key):
    if remaining(p,key)<1:return False
    state(p)[key]=spent(p,key)+1
    return True

def restore(p,key,count=None):
    state(p)[key]=0 if count is None else max(0,spent(p,key)-count)

def migrate(p,now):
    data=state(p)
    if data.get('version')!=1:
        # A live legacy timer means the ability was spent; login never refreshes it.
        for key in ('arcane_recovery','second_wind','action_surge','animal_companion'):
            if p.spell_cooldowns.get(key,0)>now:data[key]=max(spent(p,key),1)
        if any(until>now for key,until in p.spell_cooldowns.items() if key=='wild_shape_shared' or key=='wild_companion' or key.startswith('wild_shape_')):
            p.druid_circle_state['shape_spent']=max(1,p.druid_circle_state.get('shape_spent',0))
        data['version']=1
    for key in NAMES:data[key]=min(maximum(p,key),spent(p,key))
    for key in tuple(p.spell_cooldowns):
        if key in NAMES or key=='wild_shape_shared' or key=='wild_companion' or key.startswith('wild_shape_'):
            p.spell_cooldowns.pop(key,None)

def finish(p,kind,rng,recover=True):
    """Returns an auditable summary; mutate only after a completed rest."""
    hp0,mana0=p.hp,p.mana;used=0;draws=[]
    if kind=='long':
        p.hp,p.mana=p.max_hp,p.max_mana
        for key in NAMES:restore(p,key)
        p.temp_hp=0
        p.exhaustion=max(0,getattr(p,'exhaustion',0)-1)
    else:
        # Spend one die at a time and stop at full HP, preserving unused dice.
        try:
            from . import combat_rules as rules
        except ImportError:
            import combat_rules as rules
        con=(rules.own_attributes(p)['constitution']-10)//2
        while p.hp<p.max_hp and spend(p,'hit_dice'):
            used+=1
            draw={};value=rules.gear.feat_rules.rest_die(p,rng,draw)
            potential=max(0,value+con)
            draw.update(modifier=con,potential=potential)
            draws.append(draw);p.hp=min(p.max_hp,p.hp+potential)
        restore(p,'second_wind',1);restore(p,'action_surge')
        if recover and p.mana<p.max_mana and spend(p,'arcane_recovery'):
            p.mana=min(p.max_mana,p.mana+caster.recovery_amount(p))
    return dict(hp=round(p.hp-hp0,1),mana=round(p.mana-mana0,1),hit_dice=used,rolls=draws)

def sheet(p):
    rows = [dict(id=key,name=name,remaining=remaining(p,key),maximum=maximum(p,key),
        recovery='Krótki: wszystkie' if key=='action_surge' else 'Krótki: 1; długi: wszystkie' if key=='second_wind' else 'Długi odpoczynek')
        for key,name in NAMES.items() if maximum(p,key)]
    try: from . import martial_rules as martial
    except ImportError: import martial_rules as martial
    if martial.maximum(p):
        rows.append(dict(id='superiority_dice', name='Kości przewagi k'+str(martial.die_sides(p)),
            remaining=martial.remaining(p), maximum=martial.maximum(p), recovery='Krótki lub długi: wszystkie'))
    return rows

def configure(spells):
    descriptions={
        'arcane_recovery':'Po krótkim odpoczynku odzyskujesz część many. Jedno użycie na długi odpoczynek.',
        'second_wind':'Akcja dodatkowa: 1k10 + poziom D&D zdrowia. Krótki odpoczynek przywraca jedno użycie; długi wszystkie.',
        'action_surge':'Dodatkowa akcja ataku, raz w turze. Wszystkie użycia odnawia krótki lub długi odpoczynek.',
        'animal_companion':'Przywołuje wilczego towarzysza. Ponowne przywołanie po długim odpoczynku.'}
    for key,description in descriptions.items():
        if key in spells:spells[key].update(cooldown=0,description=description)
    for key,spec in spells.items():
        if key.startswith('wild_shape_') or key=='wild_companion':
            spec.update(cooldown=0,description=spec.get('description','').split('Wspólne odnowienie')[0]+'Zużywa Dziki kształt. Krótki odpoczynek: +1 użycie; długi: wszystkie.')
