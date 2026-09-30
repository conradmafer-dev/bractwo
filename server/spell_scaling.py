"""Authoritative SRD 5.2.1 spell growth, delayed to Bractwo's level gates.

Cantrips grow with character level. Levelled spells grow ONLY where their SRD
entry permits upcasting and pay the chosen circle's mana cost. Auto chooses the
highest *useful* circle; a persisted per-spell choice can keep a cheaper version.
No catalogue dictionaries are mutated. Fields/repeated concentration attacks
retain their paid-for casting profile, even across a level or preference change.
"""
import copy
from math import ceil
try:
    from . import combat_rules as rules, dnd_content as dnd
except ImportError:
    import combat_rules as rules, dnd_content as dnd

# Pure mechanics from the SRD; see LICENSE-SRD.txt and docs/SPELL_SCALING_0.8.7.md.
UPCAST = {
    'magic_missile': {'shots': 1},
    'burning_hands': {'dice': 1},
    'ensnaring_strike': {'dice': 1},
    'cure_wounds': {'dice': 2},
    'healing_word': {'dice': 2},
    'longstrider': {'ally_targets': 1},
    'scorching_ray': {'shots': 1},
    'moonbeam': {'dice': 1},
    'fireball': {'dice': 1},
    'lightning_bolt': {'dice': 1},
    'call_lightning': {'dice': 1},
    'blight': {'dice': 1},
    'freedom_of_movement': {'ally_targets': 1},
    'ice_storm': {'dice': 1},  # only the bludgeoning d10s, NEVER the cold d6s
    'cone_of_cold': {'dice': 1},
    'mass_cure_wounds': {'dice': 1},
    'chain_lightning': {'max_targets': 1},
    'heal': {'flat_heal': 10},
    'hunters_mark': {'duration_tiers': ((1, 600), (3, 4800), (5, 14400))},
}

# No spell gains a fictitious caster-level bonus. This conversion also supports
# future rules saying +N per two/three caster levels: +N per 10/15 game levels.
def caster_steps(level, every=1, start=1):
    if type(every) is not int or every < 1 or type(start) is not int or start < 1:
        raise ValueError('Positive integer caster-level intervals are required')
    effective = min(20, max(1, 1 + int(level)//5))
    return max(0, (effective-start)//every)


def circle_options(p, key):
    s = dnd.SPELLS.get(key)
    if not s or key not in UPCAST or not dnd.spell_allowed(p, key):
        return []
    highest = max(s['circle'], dnd.circle_for(p.class_id, p.level))
    if key == 'hunters_mark':
        return [c for c, _ in UPCAST[key]['duration_tiers'] if c <= highest]
    return list(range(s['circle'], highest+1))


def sanitize_choices(p):
    raw = getattr(p, 'spell_circle_choices', {})
    p.spell_circle_choices = {key: rank for key, rank in raw.items()
        if isinstance(key, str) and type(rank) is int and rank in circle_options(p, key)} if isinstance(raw, dict) else {}
    p._spell_profiles_cache = None


def choose_circle(p, key, rank):
    """False means malformed, locked, wrong-class or ineffectual rank. Zero = Auto."""
    if not isinstance(key, str) or type(rank) is not int:
        return False
    options = circle_options(p, key)
    if not options or rank != 0 and rank not in options:
        return False
    if rank == 0:
        p.spell_circle_choices.pop(key, None)
    else:
        p.spell_circle_choices[key] = rank
    p._spell_profiles_cache = None
    return True


def resolve(p, key, *, automatic=False, active=True):
    """Return independent complete casting data. All use-sites share this path.

    automatic=True is a permanent-progression projection, NOT live Auto casting:
    compare the highest useful paid circle, ignoring preferences, remaining free
    uses and armed discounts. Otherwise a Wisdom increase that restores a free
    base-rank Guiding Bolt can falsely appear as a damage loss on level-up.
    """
    s = copy.deepcopy(dnd.SPELLS[key])
    if key=='wizard_phantasm' and not automatic and not getattr(p,'wizard_school_state',{}).get('phantasm_spent',0):s['mana']=0
    options = circle_options(p, key)
    selected = getattr(p, 'spell_circle_choices', {}).get(key, 0)
    rank = (selected if not automatic and selected in options else options[-1]) if options else s['circle']
    try:from . import druid_circles as dc
    except ImportError:import druid_circles as dc
    free_base=(key=='guiding_bolt' and dc.circle(p)=='stars' and dc.feature_remaining(p,'guiding_bolt') and dc.state(p).get('map_equipped',True)
        or dc.circle(p)=='land' and p.level>=25 and dc.state(p).get('natural_free_armed') and not dc.spent(p,'natural_free') and key in dc.bonus_spells(p) and s.get('circle',0)>0)
    if not automatic and free_base and not selected:rank=s['circle']
    s.update(cast_circle=rank, power_choice=0 if automatic or selected not in options else selected,
             power_options=options, resolved=True)
    if options:
        s['mana'] = 0 if s.get('free_cast') else dnd.MANA_COSTS[rank]
        increase = rank-s['circle']
        for field, value in UPCAST[key].items():
            if field == 'dice':
                s['dice'][0] += value*increase
            elif field == 'duration_tiers':
                rounds = next(n for c, n in reversed(value) if c <= rank)
                s['duration_rounds'] = rounds
                s['duration'] = rounds*dnd.GAME_ROUND_SECONDS
            else:
                s[field] = s.get(field, 1 if field == 'ally_targets' else 0)+value*increase
    if s.get('scales'):
        s['dice'][0] = rules.cantrip_count(p)
    if key == 'second_wind':
        s['dice'][2] += rules.effective_level(p)
    elif s.get('add_ability'):
        s['dice'][2] += rules.ability_modifier(p, rules.spell_ability(p))
    if key == 'shillelagh':
        q = copy.copy(p)
        q.buffs = {**p.buffs, 'shillelagh': {'until': getattr(p, 'current_wall_time', 0)+1}}
        q.form = ''
        if rules.gear.shillelagh_applies(q):
            s['weapon_dice'] = list(rules.weapon_dice(q))
        else:
            count=rules.cantrip_count(p)
            s['weapon_dice']=[2 if count>=4 else 1,6 if count>=4 else (8,10,12)[count-1],rules.ability_modifier(p,rules.spell_ability(p))]
    if key=='arcane_recovery':s['restore_mana']=rules.caster.recovery_amount(p)
    if s.get('kind')=='shape':
        f=rules.caster.FORMS[s['form']]
        s.update(duration=rules.caster.form_duration(p),temporary_hp=dc.form_temp_hp(p),form_ac=max(f['ac'],13+dc.wisdom(p) if dc.circle(p)=='moon' else 0),form_attacks=f['attacks'])
    if s.get('duration'):
        s['duration_rounds'] = ceil(s['duration']/dnd.GAME_ROUND_SECONDS)
    # Repeated actions use the original paid profile; changing a preference or
    # gaining a circle must never improve an existing spell for zero mana.
    locked = getattr(p, 'concentration_profile', {})
    if (active and not automatic and s.get('recast') and p.concentration == key
            and p.concentration_until > getattr(p, 'current_wall_time', 0)
            and locked.get('id') == key):
        saved = copy.deepcopy(locked)
        saved.update(power_choice=s['power_choice'], power_options=options, recast_active=True)
        s = saved
    s['visual'] = {**s['visual'], 'shots': s.get('shots', 1)}
    s['power_summary'] = summary(s)
    return s


def dice_text(dice):
    return rules.dice_text(tuple(dice))


def summary(s):
    if s.get('kind')=='martial_feature':
        role='Reakcja' if s.get('martial_maneuver') in ('riposte','parry') else 'Przygotowanie następnego ataku'
        return role+' · 1 kość przewagi przy wykonaniu · przygotowanie bez kosztu'
    parts = []
    if s['circle']:
        parts.append(f'Rzucanie: krąg {s["cast_circle"]}')
    if s.get('weapon_dice'):
        parts.append('Laska: '+dice_text(s['weapon_dice']))
    elif s.get('dice'):
        damage = dice_text(s['dice'])
        if s.get('extra_dice'):
            damage += ' + '+dice_text(s['extra_dice'])
        if s.get('shots', 1) > 1:
            parts.append(f'{s["shots"]} × {damage}')
        else:
            parts.append(('Leczenie: ' if s['kind']=='heal' else 'Obrażenia: ')+damage)
    elif s.get('flat_heal'):
        parts.append(f'Leczenie: {s["flat_heal"]} HP')
    if s.get('restore_mana'):parts.append(f'+{s["restore_mana"]} many')
    if s.get('temporary_hp'):parts.append(f'+{s["temporary_hp"]} tymczasowych HP · KP {s["form_ac"]}')
    if s.get('form_attacks'):parts.append(' + '.join(dice_text(d) for d in s['form_attacks']))
    if s.get('max_targets'):
        parts.append(f'Cele: do {s["max_targets"]}')
    if s.get('ally_targets'):
        parts.append(f'Sojusznicy: do {s["ally_targets"]}')
    if s.get('duration_rounds'):
        n = s['duration_rounds']
        unit = 'runda' if n == 1 else 'rundy' if n%10 in (2,3,4) and n%100 not in (12,13,14) else 'rund'
        parts.append(f'{n} {unit}')
    if s.get('id')=='ensnaring_strike':parts.append('Obrażenia co rundę · po trafieniu bronią')
    if s.get('free_cast') or s.get('feature') and not s.get('mana'):parts.append(f'Bez many · odnowienie {s.get("cooldown",0):g} s')
    if s.get('recast_active'):
        parts.append('Utrzymywany czar · powtórzenie bez many')
    return ' · '.join(parts)


def _changes(a, b):
    """Individual truthful deltas. Never infer average dice as an extra die."""
    result=[]
    def add(metric, amount, unit=''):
        if amount:
            result.append(dict(metric=metric, amount=amount, unit=unit))
    healing = b['kind']=='heal'
    for field in ('dice','extra_dice'):
        if field not in a or field not in b:
            continue
        x, y = a[field], b[field]
        if x[1] == y[1]:
            if y[0] != x[0]:
                result.append(dict(metric='healing_dice' if healing else 'damage_dice',
                    amount=f'{y[0]-x[0]:+d}k{y[1]}', unit='do leczenia' if healing else 'do obrażeń'))
            add('healing_flat' if healing else 'damage_flat', y[2]-x[2], 'do leczenia' if healing else 'do obrażeń')
    add('healing_fixed', b.get('flat_heal',0)-a.get('flat_heal',0), 'do leczenia')
    add('shots', b.get('shots',1)-a.get('shots',1), 'promień' if b['id']=='scorching_ray' else 'pocisk')
    add('targets', b.get('max_targets',0)-a.get('max_targets',0), 'cel')
    add('allies', b.get('ally_targets',1)-a.get('ally_targets',1), 'cel')
    add('duration', b.get('duration_rounds',0)-a.get('duration_rounds',0), 'tur trwania efektu')
    add('mana', b['mana']-a['mana'], 'do kosztu many')
    add('restore_mana',b.get('restore_mana',0)-a.get('restore_mana',0),'many')
    return result


def level_gains(before, after, key):
    if not dnd.spell_allowed(before,key) or not dnd.spell_allowed(after,key):
        return []
    return _changes(resolve(before,key,automatic=True,active=False), resolve(after,key,automatic=True,active=False))


def next_upgrade(p, key):
    candidates=(range(2,96) if key=='arcane_recovery' and getattr(p,'mana_rules_version',dnd.MANA_RULES_VERSION)>=dnd.MANA_RULES_VERSION
                else sorted(set(range(5,100,5)) | set(dnd.RANGER_CIRCLE_LEVELS)))
    now = resolve(p,key,automatic=True,active=False)
    for level in candidates:
        if level <= p.level:
            continue
        q=copy.copy(p);q.level=level
        changes = [c for c in _changes(now,resolve(q,key,automatic=True,active=False)) if c['metric'] != 'mana']
        if key == 'shillelagh':
            future=resolve(q,key,automatic=True,active=False)
            x,y=now['weapon_dice'],future['weapon_dice']
            delta=(y[0]*(y[1]+1)/2+y[2])-(x[0]*(x[1]+1)/2+x[2])
            if delta:
                changes=[dict(metric='weapon_average', amount=delta, unit='do średnich obrażeń laski')]
        if changes:
            items=[]
            for c in changes:
                amount = c['amount'] if isinstance(c['amount'],str) else f'{c["amount"]:+g}'.replace('.',',')
                unit=c['unit']
                if c['metric']=='duration' and c['amount']==1:unit='tura trwania efektu'
                items.append(f'{amount} {unit}')
            return f'Poziom {level}: '+', '.join(items)
    return ''


def client_profiles(p):
    """Small private overrides, cached; the shared base catalogue stays immutable."""
    locked=getattr(p,'concentration_profile',{})
    active=bool(p.concentration_until>getattr(p,'current_wall_time',0))
    signature=(p.class_id,p.level,getattr(p,'mana_rules_version',dnd.MANA_RULES_VERSION),p.primal_order,p.weapon_grip,tuple(sorted(p.training_feats.items())),rules.gear.weapon(p).get('weapon_type',''),tuple(sorted(getattr(p,'spell_circle_choices',{}).items())),
        rules.ability_modifier(p,rules.spell_ability(p)),p.gear_bonus('attack'),p.mastery.get('power',0),
        p.concentration if active else '',locked.get('cast_circle',0) if active else 0)
    try:
        from . import druid_circles as dc, rest_rules, martial_rules as martial
    except ImportError:
        import druid_circles as dc, rest_rules, martial_rules as martial
    wizard_live=getattr(p,'wizard_school_runtime',{})
    signature+=(getattr(p,'promoted',False),getattr(p,'wizard_school',''),repr(getattr(p,'wizard_school_state',{})),
        wizard_live.get('decoy_until',0)>getattr(p,'current_wall_time',0),
        wizard_live.get('shelter',{}).get('until',0)>getattr(p,'current_wall_time',0),
        tuple(sorted(k for k,v in p.buffs.items() if k.startswith('wizard_') and v.get('until',0)>getattr(p,'current_wall_time',0))),
        p.form,dc.circle(p),dc.land(p),dc.starry_form(p),dc.feature_allowed(p,'circle_wrath_strike'),repr(getattr(p,'druid_circle_state',{})),repr(getattr(p,'rest_resources',{})),martial.path(p),repr(martial.state(p)))
    cache=getattr(p,'_spell_profiles_cache',None)
    if cache and cache[0]==signature:
        return cache[1]
    result={}
    fields=('cast_circle','power_choice','power_options','mana','dice','extra_dice','weapon_dice','flat_heal',
            'shots','max_targets','ally_targets','duration','duration_rounds','power_summary','recast_active','restore_mana','temporary_hp','form_ac','form_attacks')
    for key in dnd.SPELLS:
        if not dnd.spell_allowed(p,key):
            result[key]={'available':False}
            continue
        spec=resolve(p,key)
        result[key]={f:spec[f] for f in fields if f in spec}
        result[key]['next_upgrade']=next_upgrade(p,key)
        result[key]['available']=True
        gate=dnd.spell_level(spec,p.class_id)
        if key in dc.bonus_spells(p):
            gate=min(gate,dc.bonus_spells(p)[key]) if p.class_id in spec['class_ids'] else dc.bonus_spells(p)[key]
        if spec.get('kind')=='shape' and dc.circle(p)=='moon':
            from fractions import Fraction
            form=rules.caster.FORMS[spec['form']]
            gate=min(gate,max(10,5*(3*int(Fraction(str(form.get('cr','0'))))-1)))
            if form.get('fly'):gate=max(35,gate)
        result[key]['required_level']=gate
        if spec.get('cast_circle',spec.get('circle'))==spec.get('circle'):
            if key=='guiding_bolt' and dc.circle(p)=='stars' and dc.feature_remaining(p,'guiding_bolt') and dc.state(p).get('map_equipped',True):result[key]['mana']=0
            if dc.circle(p)=='land' and p.level>=25 and dc.state(p).get('natural_free_armed') and not dc.spent(p,'natural_free') and key in dc.bonus_spells(p) and spec.get('circle',0)>0:result[key]['mana']=0
        result[key]['cast_in_form']=dc.circle(p)=='moon' and key in dc.bonus_spells(p)
        if spec.get('kind')=='martial_feature':
            maneuver=spec['martial_maneuver']
            role=martial.MANEUVERS[maneuver]['kind']
            result[key].update(uses_remaining=martial.remaining(p),uses_maximum=martial.maximum(p),
                resource_cost=1,resource_name='Kości przewagi',martial_role=role,
                armed=martial.state(p).get(role)==maneuver)
        if key.startswith('wizard_'):
            try: from . import wizard_schools as ws
            except ImportError: import wizard_schools as ws
            state=ws.state(p)
            if key=='wizard_phantasm':result[key]['mana']=0 if not state.get('phantasm_spent',0) else 30
            uses={'wizard_decoy':('decoy_spent',2,'Sobowtór'), 'wizard_shelter':('shelter_spent',1,'Urzeczywistniona osłona'), 'wizard_third_eye':('third_eye_used',1,'Trzecie oko')}
            if key in uses:
                field,maximum,name=uses[key]
                result[key].update(uses_remaining=max(0,maximum-state.get(field,0)),uses_maximum=maximum,resource_cost=1,resource_name=name)
            if key=='wizard_ward_recharge':result[key]['already_active']=not state.get('ward_created') or state.get('ward_hp',0)>=ws.ward_max(p)
            if key=='wizard_self_restore':result[key]['already_active']=not state.get('self_spent',0)
            if key=='wizard_decoy':result[key]['already_active']=ws.runtime(p).get('decoy_until',0)>getattr(p,'current_wall_time',0)
            if key=='wizard_shelter':result[key]['already_active']=ws.runtime(p).get('shelter',{}).get('until',0)>getattr(p,'current_wall_time',0)
        if key in rest_rules.NAMES:
            result[key]['uses_remaining']=rest_rules.remaining(p,key)
            result[key]['uses_maximum']=rest_rules.maximum(p,key)
        if key in dc.SPELL_FEATURES:
            current = dc.starry_form(p)
            is_form = key in ('circle_star_archer', 'circle_star_chalice', 'circle_star_dragon')
            free = key in ('circle_star_arrow', 'circle_move_sanctuary', 'circle_wrath_strike')
            free = free or (is_form and bool(current) and p.level >= 45)
            free = free or (key == 'circle_wrath_of_sea' and dc.active(p, 'wrath_of_sea'))
            if key == 'circle_moonlight_step':
                result[key].update(uses_remaining=dc.feature_remaining(p,'moonlight_step'),
                    uses_maximum=max(1,dc.wisdom(p)),resource_cost=1,resource_name='Księżycowy krok')
            else:
                result[key].update(resource_cost=0 if free else 2 if key=='circle_oceanic_gift_shared' else 1,
                    resource_name='Dziki kształt')
                if not free:
                    result[key].update(uses_remaining=dc.shape_remaining(p),uses_maximum=dc.shape_max(p))
            if is_form: result[key]['already_active'] = key == 'circle_star_'+current
            amount = (2 if p.level >= 45 else 1)
            wisdom = dc.wisdom(p)
            dice = str(amount)+'k8'+('+' if wisdom>=0 else '')+str(wisdom)
            if key in ('circle_star_archer','circle_star_arrow'):
                result[key]['power_summary'] = dice+' obrażeń promienistych · akcja dodatkowa. Strzały nie zużywają użyć przemiany.'
            elif key == 'circle_star_chalice':
                result[key]['power_summary'] = '+'+dice+' leczenia po czarze leczącym opłaconym maną. Bez pasywnej regeneracji.'
            elif key == 'circle_star_dragon':
                result[key]['power_summary'] = 'Minimum 10 na k20: koncentracja, testy INT i MĄD.'+(' Lot 20 stóp.' if p.level>=45 else '')
        if key.startswith('wild_shape_') or key=='wild_companion':
            result[key]['resource_cost']=0 if key.startswith('wild_shape_') and p.form else 1
            result[key]['resource_name']='Dziki kształt'
            result[key]['uses_remaining']=dc.shape_remaining(p)
            result[key]['uses_maximum']=dc.shape_max(p)
    p._spell_profiles_cache=(signature,result)
    return result
