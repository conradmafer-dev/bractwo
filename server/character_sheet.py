"""Owner-only character sheet; all bonuses use the actual combat calculations."""
try:
    from . import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter
except ImportError:
    import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter

DAMAGE_NAMES = {'acid':'Kwas','bludgeoning':'Obuchowe','cold':'Zimno','fire':'Ogień',
    'force':'Moc','lightning':'Błyskawice','necrotic':'Nekrotyczne','piercing':'Kłute',
    'poison':'Trucizna','psychic':'Psychiczne','radiant':'Promieniste','slashing':'Cięte','thunder':'Grzmot'}


def build(p):
    resistances=[]
    for key,name in DAMAGE_NAMES.items():
        resistances.append(dict(type=key,name=name,multiplier=rules.resistance_multiplier(p,key)))
    gear=rules.gear;caster=rules.caster
    return dict(training=gear.training_sheet(p),caster=caster.sheet(p),ability_modifiers={k:rules.ability_modifier(p,k) for k in rules.attributes(p)},
        saving_throws={k:rules.save_bonus(p,k) for k in rules.attributes(p)},
        proficient_saves=list(p.spec['saves']),spell_attack_bonus=rules.spell_bonus(p),
        attack_ability=rules.attack_ability(p),spell_ability=rules.spell_ability(p),
        damage_type=rules.damage_type(p),damage_name=DAMAGE_NAMES[rules.damage_type(p)],
        resistances=resistances,immunities=[],vulnerabilities=[],
        hit_die='1k'+str(p.spec['hit_die']),critical_threshold=20,
        movement_per_round=round(p.speed*rules.ROUND_SECONDS/dnd.UNITS_PER_FOOT,1),
        round_seconds=rules.ROUND_SECONDS,ward_reduction=12 if p.ward_until>p.current_wall_time else 0,
        fighter=fighter.class_sheet(p), feats=([dict(id=p.fighting_style,**fighter.STYLES[p.fighting_style])] if p.class_id=='knight' and getattr(p,'fighting_style','') in fighter.STYLES else []),favorite_spell=dnd.favorite_spell(p),spell_history_size=len(p.spell_history))
