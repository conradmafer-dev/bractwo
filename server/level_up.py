"""Persistent, owner-only advancement receipts. Values describe gains, never totals.

Ranges keep a very large XP award constant-size. At most 32 outstanding receipts
are materialized per snapshot; closing them reveals older ones without losing any.
Permanent growth is calculated with the gear/mastery held at the time of the award,
without transient spells, forms, terrain or later equipment changes.
"""
import copy
import uuid
try:
    from . import combat_rules as rules, dnd_content as dnd, spell_scaling
except ImportError:
    import combat_rules as rules, dnd_content as dnd, spell_scaling

VISIBLE_LIMIT = 32
ATTRIBUTES = {'strength':'Siła','dexterity':'Zręczność','constitution':'Kondycja',
              'intelligence':'Inteligencja','wisdom':'Mądrość','charisma':'Charyzma'}


def mastery_points(p):
    return max(0, (p.level-50)//5+1-sum(p.mastery.values())) if p.promoted and p.level >= 50 else 0


def record(p, first, last):
    if last < first:
        return
    worn = set(p.equipment.values())
    context = copy.deepcopy(dict(class_id=p.class_id, promoted=p.promoted,
        primal_order=p.primal_order,training_feats=p.training_feats,caster_rules_version=p.caster_rules_version,
        druid_circle=p.druid_circle,druid_circle_state=p.druid_circle_state,
        wizard_school=p.wizard_school,wizard_school_state=p.wizard_school_state,
        martial_archetype=getattr(p,'martial_archetype',''),
        martial_state={k:v for k,v in getattr(p,'martial_state',{}).items() if k in ('maneuvers','hunter_choice')},
        mana_rules_version=p.mana_rules_version,hp_rules_version=p.hp_rules_version,
        mastery=p.mastery, fighting_style=p.fighting_style, weapon_grip=p.weapon_grip, equipment=p.equipment,
        inventory=[i for i in p.inventory if i.get('uid') in worn]))
    # Coalesce ordinary repeated awards only when their permanent profile agrees.
    previous = p.level_up_batches[-1] if p.level_up_batches else None
    if previous and previous.get('spell_scaling_version') == 1 and previous['context'] == context and previous['ranges'][-1][1] == first-1:
        previous['ranges'][-1][1] = last
    else:
        p.level_up_batches.append(dict(id=uuid.uuid4().hex, ranges=[[first,last]], context=context, spell_scaling_version=1))
    p._level_up_cache = None


def number(value):
    if isinstance(value, str):
        return value
    if (round(value) != 0 or value == 0) and abs(value-round(value)) < 1e-8:
        return f'{int(round(value)):+d}'
    # Do not hide a small real movement increase behind a displayed +0.
    for digits in (2,3,4,6,10):
        if round(value,digits):
            return (f'{value:+.{digits}f}'.rstrip('0').rstrip('.')).replace('.',',')
    return '+<0,0000000001' if value > 0 else '−<0,0000000001'


def permanent(p, level, context):
    q = copy.copy(p)
    q.fighting_style="";q.weapon_grip="one";q.primal_order='';q.training_feats={}
    q.druid_circle='';q.druid_circle_state={};q.druid_circle_runtime={}
    q.wizard_school='';q.wizard_school_state={};q.wizard_school_runtime={}
    q.martial_archetype='';q.martial_state={}
    # Pre-0.8.16 receipts have no mana-version stamp: preserve their earned gains.
    q.mana_rules_version=2
    q.hp_rules_version=0  # Preserve HP deltas in receipts earned before UI_12.
    for key,value in context.items():
        setattr(q,key,value)
    q.level=level
    q.form='';q.buffs={};q.current_wall_time=0
    return q


def receipt(p, batch, level):
    before=permanent(p,level-1,batch['context'])
    after=permanent(p,level,batch['context'])
    rows=[];actions=[]
    def add(key,label,delta,unit='',icon=''):
        if isinstance(delta,(int,float)) and abs(delta)<1e-12:
            return
        entry=dict(id=key,label=label,gain=number(delta))
        if unit:entry['unit']=unit
        if icon:entry['icon']=icon
        rows.append(entry)
    try: from . import wizard_schools
    except ImportError: import wizard_schools
    selected=wizard_schools.school(after)
    for feature_id, gate, name, description in wizard_schools.FEATURES.get(selected,()):
        if gate==level:add('school_'+feature_id,'Zdolność szkoły','+ '+name,icon=f'assets/feats/wizard_{selected}.svg')
    try: from . import martial_rules as martial
    except ImportError: import martial_rules as martial
    if level==martial.PROMOTION_LEVEL and after.class_id in ('knight','ranger'):
        add('martial_unlock','Specjalizacja po promocji','+ możliwość wyboru',icon='assets/feats/martial_'+('battle_master' if after.class_id=='knight' else 'hunter')+'.svg')
        actions.append(dict(kind='martial',label='Wybierz specjalizację',tab='feats'))
    if martial.path(after)=='battle_master':
        add('superiority_dice','Kości przewagi',martial.maximum(after)-martial.maximum(before))
        if martial.die_sides(after)!=martial.die_sides(before):add('superiority_die','Kość przewagi',f'k{martial.die_sides(before)} → k{martial.die_sides(after)}')
    if martial.path(after)=='champion' and martial.critical_threshold(after)<martial.critical_threshold(before):
        add('champion_critical','Krytyk bronią',f'{martial.critical_threshold(after)}–20')
    add('hp','HP',after.max_hp-before.max_hp)
    add('mana','Mana',after.max_mana-before.max_mana)
    for key in ATTRIBUTES:
        add('attribute_'+key,ATTRIBUTES[key],rules.attributes(after)[key]-rules.attributes(before)[key])
        add('modifier_'+key,'Modyfikator: '+ATTRIBUTES[key],rules.ability_modifier(after,key)-rules.ability_modifier(before,key))
    add('ac','Klasa Pancerza',rules.armor_class(after)-rules.armor_class(before))
    add('attack','Atak bronią',rules.attack_bonus(after)-rules.attack_bonus(before))
    ad,bd=rules.weapon_dice(after),rules.weapon_dice(before)
    add('weapon_damage','Obrażenia broni',ad[2]-bd[2])
    add('attacks','Ataki na rundę',rules.attacks_per_round(after)-rules.attacks_per_round(before))
    add('spell_attack','Atak czarem',rules.spell_bonus(after)-rules.spell_bonus(before))
    add('spell_dc','ST czarów',rules.spell_dc(after)-rules.spell_dc(before))
    add('proficiency','Biegłość',rules.proficiency(after)-rules.proficiency(before))
    for key,label in ATTRIBUTES.items():
        add('save_'+key,'Rzut obronny: '+label,rules.save_bonus(after,key)-rules.save_bonus(before,key))
    add('circle','Krąg czarów',dnd.circle_for(after.class_id,level)-dnd.circle_for(before.class_id,level-1))
    # Stable base movement, not the road/mud and short-lived spell multipliers.
    add('movement','Ruch', (after.base_speed-before.base_speed)*rules.ROUND_SECONDS/dnd.UNITS_PER_FOOT,'stopy / rundę')
    count_delta=rules.cantrip_count(after)-rules.cantrip_count(before)
    for key,s in dnd.SPELLS.items():
        if not dnd.spell_allowed(after,key):
            continue
        was=dnd.spell_allowed(before,key)
        if not was:
            add('unlock_'+key,'Nowa zdolność' if s.get('feature') else 'Nowy czar','+ '+s['name'],icon=s.get('icon',''))
            continue
        if batch.get('spell_scaling_version') == 1:
            for change in spell_scaling.level_gains(before,after,key):
                unit=change['unit']
                amount=change['amount']
                if change['metric']=='duration' and amount==1:unit='tura trwania efektu'
                if change['metric']=='shots' and isinstance(amount,int) and amount!=1:
                    unit='promienie' if key=='scorching_ray' else 'pociski'
                row_id='spell_'+change['metric']+'_'+key
                if s.get('scales') and change['metric']=='damage_dice':row_id='spell_damage_'+key
                if s.get('add_ability') and change['metric']=='healing_flat':row_id='healing_'+key
                if key=='second_wind' and change['metric']=='healing_flat':row_id='second_wind'
                add(row_id,s['name'],amount,unit,icon=s.get('icon',''))
        else:
            if s.get('scales') and count_delta:
                add('spell_damage_'+key,s['name']+' · obrażenia',f'+{count_delta}k{s["dice"][1]}',icon=s.get('icon',''))
            if s.get('add_ability'):
                gain=rules.ability_modifier(after,rules.spell_ability(after))-rules.ability_modifier(before,rules.spell_ability(before))
                add('healing_'+key,s['name']+' · leczenie',gain,icon=s.get('icon',''))
            if key=='second_wind':
                add('second_wind','Drugi oddech · leczenie',rules.effective_level(after)-rules.effective_level(before),icon=s.get('icon',''))
        if s.get('kind')=='shape':
            factor=1
            add('shape_hp_'+key,s['name']+' · tymczasowe HP',factor*(rules.effective_level(after)-rules.effective_level(before)),icon=s.get('icon',''))
            add('shape_attack_'+key,s['name']+' · atak',rules.proficiency(after)-rules.proficiency(before),icon=s.get('icon',''))
            # Form AC is the beast's AC, not a fabricated level bonus.
        if key=='animal_companion':
            add('pet_hp','Przywołany wilk · HP',5*(rules.effective_level(after)-rules.effective_level(before)))
            add('pet_attack','Przywołany wilk · atak',(rules.proficiency(after)+rules.ability_modifier(after,'wisdom'))-(rules.proficiency(before)+rules.ability_modifier(before,'wisdom')))
            add('pet_ac','Przywołany wilk · KP',rules.proficiency(after)-rules.proficiency(before))
            add('pet_damage','Przywołany wilk · obrażenia',rules.proficiency(after)-rules.proficiency(before))
        if key=='shillelagh':
            before.buffs={'shillelagh':{'until':1}};after.buffs={'shillelagh':{'until':1}}
            a,b=rules.weapon_dice(after),rules.weapon_dice(before)
            before.buffs={};after.buffs={}
            # A die replacement has no single exact extra die. Label the change
            # in expected damage explicitly; never repeat either old or new die.
            average_gain=(a[0]*(a[1]+1)/2+a[2])-(b[0]*(b[1]+1)/2+b[2])
            add('shillelagh_average','Shillelagh · średnie obrażenia',average_gain,icon=s.get('icon',''))
    gained=mastery_points(after)-mastery_points(before)
    if gained>0:
        add('mastery','Punkt mistrzostwa',gained)
        actions.append(dict(kind='mastery',label='Przydziel punkt',tab='stats'))
    if level in rules.gear.FEAT_LEVELS:
        add('training_feat','Wybór atutu wyszkolenia',1)
        actions.append(dict(kind='training_feat',label='Wybierz atut',tab='feats'))
    return dict(id=f'{batch["id"]}:{level}',level=level,rows=rows,actions=actions)


def pending(p):
    if p._level_up_cache is None:
        total=sum(hi-lo+1 for b in p.level_up_batches for lo,hi in b['ranges'])
        found=[]
        for batch in reversed(p.level_up_batches):
            for lo,hi in reversed(batch['ranges']):
                for level in range(hi,max(lo-1,hi-(VISIBLE_LIMIT-len(found))),-1):
                    found.append(receipt(p,batch,level))
                if len(found)>=VISIBLE_LIMIT:break
            if len(found)>=VISIBLE_LIMIT:break
        p._level_up_cache={'pending_level_ups':list(reversed(found)),'level_up_pending_count':total}
    return p._level_up_cache


def dismiss(p, receipt_id):
    if not isinstance(receipt_id,str) or not 1<len(receipt_id)<=64 or ':' not in receipt_id:
        return False
    batch_id,raw=receipt_id.rsplit(':',1)
    if not raw.isascii() or not raw.isdecimal():return False
    level=int(raw)
    for i,batch in enumerate(p.level_up_batches):
        if batch['id']!=batch_id:continue
        for j,(lo,hi) in enumerate(batch['ranges']):
            if lo<=level<=hi:
                parts=([[lo,level-1]] if lo<level else [])+([[level+1,hi]] if level<hi else [])
                batch['ranges'][j:j+1]=parts
                if not batch['ranges']:p.level_up_batches.pop(i)
                p._level_up_cache=None
                return True
    return False
