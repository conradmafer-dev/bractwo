"""Authoritative d20, explicit damage dice and bounded 5E-style statistics.
Mana, 3-second rounds and delayed progression are documented Bractwo adaptations.
"""
import math
try:
    from . import world_content as content
    from . import fighter_rules as fighter
    from . import equipment_rules as gear, caster_rules as caster, druid_circles as circles, environment_rules as environment
    from .dnd_content import circle_for
    from .progression import same_floor
except ImportError:
    import world_content as content
    import fighter_rules as fighter
    import equipment_rules as gear, caster_rules as caster, druid_circles as circles, environment_rules as environment
    from dnd_content import circle_for
    from progression import same_floor

ROUND_SECONDS=3.0
HP_RULES_VERSION=1
RULES={'round_seconds':3.0,'attack_die':20,'critical':20,'automatic_miss':1,
       'manual_attacks':True,'auto_selected_target':True,'focus_auto_attack':False,'target_required':False,
       'shared_actions':['attack','cast_action'], 'bonus_action_seconds':3.0,
       'close_ranged_distance':72,'area_save':'spell_specific','save_damage':.5,
       'circles_every_levels':10,'full_caster_circle_levels':[1,10,20,30,40,50,60,70,80],
       'mana_budget':'per_level','mana_regen_in_combat':False,'hotbar_page_size':24,'hotbar_row_size':12,
       'longstrider_rounds':600,'tabletop_round_seconds':6,'units_per_foot':6.4,'ranger_circles_every_levels':20,'ranger_circle_levels':[1,20,40,60,80],'cantrip_levels':[20,50,80],
       'mage_basic_dice':[1,4,0],'monster_returns_home':True,'monster_return_delay_seconds':24,'monster_chase_anchor':'current_position',
       'pvp_spells':True,'pvp_fields':True,'pvp_companions':True,'pvp_support':True,
       'rules_source':'SRD 5.2.1 + zasady własne Bractwa'}


def weapon_autoattack(p):
    """Weapon-driven, not class-driven: wands are manual; bows, blades and forms autoattack.

    Selecting a hostile creature still supplies a target to spells and companions.
    The weak focus spark remains a normal shared action when explicitly requested.
    """
    return bool(p.form) or not gear.is_focus(gear.weapon(p))


def effective_level(p): return min(20,max(1,1+int(p.level)//5))
def proficiency(p): return 2+(effective_level(p)-1)//4

def attributes(p):
    scores=dict(p.spec['attributes'])
    scores[p.spec['primary']]=min(20,scores[p.spec['primary']]+2*(p.level>=20)+2*(p.level>=40))
    for ability,amount in gear.feat_ability_bonuses(p).items():
        scores[ability]=min(20,scores[ability]+amount)
    scores.update(caster.form_spec(p).get('attributes',{}))
    scores.update(environment.polymorph(p).get('attributes',{}))
    return scores

def ability_modifier(p, ability): return (attributes(p)[ability]-10)//2

def spell_ability(p): return 'intelligence' if p.class_id=='mage' else 'wisdom'
def spell_bonus(p): return proficiency(p)+ability_modifier(p,spell_ability(p))+gear.spell_equipment_bonus(p)+caster.spell_path_bonus(p)
def spell_dc(p): return 8+spell_bonus(p)

def active_buff(p,key): return p.buffs.get(key,{}).get('until',0)>p.current_wall_time

def attack_ability(p):
    w=equipped_item(p,'weapon')
    if p.form:return 'dexterity' if p.form=='cat' else 'strength'
    if gear.is_focus(w):return 'intelligence'
    if gear.shillelagh_applies(p):return 'wisdom'
    if w.get('ranged'):return 'dexterity'
    if w.get('finesse') and ability_modifier(p,'dexterity')>ability_modifier(p,'strength'):return 'dexterity'
    return 'strength'

def attack_bonus(p):
    if getattr(p,'is_companion',False):return p.attack_bonus
    if environment.polymorph(p):return int(environment.polymorph(p).get('attack_bonus',0))
    if p.form:return caster.form_spec(p).get('attack_bonus',2)+max(0,proficiency(p)-caster.form_spec(p).get('beast_proficiency',2))
    w=equipped_item(p,'weapon')
    pb=proficiency(p) if gear.proficient(p,w) else 0
    return pb+ability_modifier(p,attack_ability(p))+min(3,p.gear_bonus('attack_bonus'))

def armor_class(p):
    if getattr(p,'is_companion',False):return p.armor_class
    if environment.polymorph(p):return int(environment.polymorph(p).get('ac',10))
    dex=ability_modifier(p,'dexterity')
    equipped=set(p.equipment.values())
    armor=next((content.ITEMS[i['template']] for i in p.inventory if i['uid'] in equipped and content.ITEMS[i['template']]['slot']=='armor'),{})
    base=armor.get('base_ac',10)
    if armor.get('armor_kind')=='heavy':dex=0
    elif armor.get('armor_kind')=='medium':dex=min(3 if gear.has_feat(p,'medium_armor_master') and dex>=3 else 2,dex)
    ac=base+dex+min(3,p.gear_bonus('ac_bonus'))
    if p.form:ac=max(caster.form_spec(p).get('ac',10),circles.armor_class_floor(p))
    if active_buff(p,'mage_armor') and (p.form or armor.get('armor_kind','none')=='none'):ac=max(ac,13+ability_modifier(p,'dexterity')+min(3,p.gear_bonus('ac_bonus')))
    if active_buff(p,'barkskin'):ac=max(ac,17)
    if active_buff(p,'shield'):ac+=5
    if not p.form:
        ac += fighter.shield_bonus(p)
        if getattr(p,'fighting_style','')=='defense' and fighter.style_active(p):ac+=1
    return ac+(2 if active_buff(p,'nature_sanctuary') else 0)

def save_bonus(p,ability='dexterity'):
    if getattr(p,'is_companion',False):return max(2,p.attack_bonus) if ability in ('strength','dexterity') else 1
    if environment.polymorph(p):return caster.form_spec(p).get('saves',{}).get(ability,ability_modifier(p,ability))
    base=ability_modifier(p,ability)+(proficiency(p) if ability in p.spec['saves'] else 0)
    if p.form:base=max(base,caster.form_spec(p).get('saves',{}).get(ability,base))
    return base+circles.save_bonus(p,ability)+(2 if ability=='dexterity' and active_buff(p,'nature_sanctuary') else 0)-getattr(p,'exhaustion',0)*2

def legacy_max_hp(p):
    """Pre-UI_12 totals, retained for save migration and historical receipts."""
    # Wild Shape retains the druid's own maximum HP, even with a beast's CON.
    con=(min(20,p.spec['attributes']['constitution']+gear.feat_ability_bonuses(p).get('constitution',0))-10)//2
    return (p.spec['hit_die']+con+((p.level-1)*(p.spec['hit_die']//2+1+con))//5+p.mastery.get('vitality',0)*2
            +(2*effective_level(p) if gear.has_feat(p,'tough') else 0))


def max_hp(p):
    if getattr(p,'hp_rules_version',HP_RULES_VERSION)<HP_RULES_VERSION:
        return legacy_max_hp(p)
    # The first interval is 1 -> 5 (four advances), then 5 -> 10 -> ... -> 95.
    # Round the accumulated gain once; individual level gains never lose fractions.
    level=max(1,min(95,int(p.level)))
    con=(min(20,p.spec['attributes']['constitution']+gear.feat_ability_bonuses(p).get('constitution',0))-10)//2
    die=p.spec['hit_die'];gain=max(1,die//2+1+con)
    numerator,denominator=(level-1,4) if level<5 else (level,5)
    return max(1,die+con)+numerator*gain//denominator+(2*effective_level(p) if gear.has_feat(p,'tough') else 0)


def migrate_hp(p):
    """Refund retired Vitality and change the maximum without changing HP fraction."""
    upgrading=getattr(p,'hp_rules_version',0)<HP_RULES_VERSION
    previous=max(1,max_hp(p)) if upgrading else 1
    refunded=p.mastery.pop('vitality',0)
    if upgrading:
        fraction=max(0,min(1,p.hp/previous))
        p.hp_rules_version=HP_RULES_VERSION
        p.hp=p.max_hp*fraction
    p._level_up_cache=None
    return refunded

def cantrip_count(p):return 1+sum(p.level>=n for n in (20,50,80))

def equipped_item(p, slot):
    uid=p.equipment.get(slot, '')
    return next((content.ITEMS.get(i['template'], {}) for i in p.inventory if i['uid']==uid), {})


def weapon_dice(p):
    if p.form:
        f=caster.form_spec(p);attacks=f.get('attacks',[[1,4,0]])
        return tuple(attacks[min(len(attacks)-1,int(getattr(p,'form_attack_index',0)))])
    weapon=equipped_item(p,'weapon')
    if gear.is_focus(weapon):return 1,4,0
    mod=ability_modifier(p,attack_ability(p))+min(3,p.gear_bonus('attack'))+min(2,p.mastery.get('power',0)//10)
    if not weapon:return 0,1,max(0,1+ability_modifier(p,'strength'))
    if gear.shillelagh_applies(p):
        count=cantrip_count(p)
        return (2,6,mod) if count==4 else (1,(8,10,12)[count-1],mod)
    n,s=weapon.get('versatile_dice',weapon.get('weapon_dice',(1,6))) if fighter.two_handed(p) else weapon.get('weapon_dice',(1,6))
    if getattr(p,'fighting_style','')=='dueling' and fighter.style_active(p):mod+=2
    return n,s,mod

def attack_range(p):
    w=equipped_item(p,'weapon')
    return 108 if gear.melee(p) else 360 if gear.is_focus(w) else 310

def attacks_per_round(p):
    if p.form:return len(caster.form_spec(p).get('attacks',[1]))
    if p.class_id=='knight':return 1+sum(p.level>=n for n in (20,50,95))
    if p.class_id=='ranger':return 1+(p.level>=20)
    return 1

def damage_type(p):
    if p.form:
        if circles.lunar_damage_type(p):return circles.lunar_damage_type(p)
        f=caster.form_spec(p);types=f.get('attack_types',[f.get('damage','bludgeoning')])
        return types[min(len(types)-1,int(getattr(p,'form_attack_index',0)))]
    if gear.shillelagh_applies(p):return 'force'
    return equipped_item(p,'weapon').get('damage_type','bludgeoning')

def resistance_multiplier(p, kind):
    physical=kind in ('bludgeoning','piercing','slashing')
    gear_resist=not getattr(p,'form','') and any(kind in equipped_item(p,slot).get('resistances',[]) for slot in ('armor','ring'))
    return .5 if (circles.resists(p,kind) or kind in caster.form_spec(p).get('resistances',[]) or kind=='radiant' and active_buff(p,'fount_of_moonlight') or gear_resist or physical and active_buff(p,'stoneskin') or kind=='fire' and active_buff(p,'resist_fire')) else 1.0


def damage_dice(power,sides=6):
    """Compatibility helper for external tools only; normal combat uses explicit dice."""
    if isinstance(power,(tuple,list)):return tuple(power)
    count=max(1,min(24,round(power/(sides+1))))
    return count,sides,max(0,round(power-count*(sides+1)/2))

def dice_text(dice):
    n,s,m=dice
    return str(m) if n==0 else f'{n}k{s}'+(f'{m:+d}' if m else '')

def roll_damage(rng,dice,critical=False):
    n,s,m=dice
    rolls=[rng.randint(1,s) for _ in range(n*(2 if critical else 1))]
    return {'damage':max(0,sum(rolls)+m),'damage_dice':dice_text(dice),'damage_rolls':rolls,'damage_modifier':m}


def begin_feat_turn(p,now):
    """Main/bonus actions and Action Surge share the same three-second turn."""
    if now>=getattr(p,'_feat_turn_until',0):
        p._feat_turn_until=now+ROUND_SECONDS
        p._savage_attack_used=False


def savage_attacker_damage(p,result,rng,now):
    """Choose complete weapon dice sets before styles and damage riders apply."""
    if (not result.get('hit') or not gear.has_feat(p,'savage_attacker') or p.form
            or not gear.weapon(p) or gear.is_focus(gear.weapon(p))):return
    begin_feat_turn(p,now)
    if getattr(p,'_savage_attack_used',False):return
    first=list(result.get('damage_rolls',[]))
    if not first:return
    n,sides,modifier=weapon_dice(p)
    second=[rng.randint(1,sides) for _ in first]
    great_weapon=getattr(p,'fighting_style','')=='great_weapon' and fighter.style_active(p)
    score=lambda rolls:sum(max(3,r) if great_weapon else r for r in rolls)
    selected=1 if score(second)>score(first) else 0
    chosen=second if selected else first
    result.update(savage_attacker=True,savage_damage_rolls=[first,second],savage_chosen=selected,
                  damage_rolls=chosen,damage=max(0,sum(chosen)+result.get('damage_modifier',modifier)))
    p._savage_attack_used=True

def roll_attack(rng,bonus,ac,dice,disadvantage=False,advantage=False):
    disadvantage,advantage=bool(disadvantage and not advantage),bool(advantage and not disadvantage)
    rolls=[rng.randint(1,20) for _ in range(2 if disadvantage or advantage else 1)]
    roll=min(rolls) if disadvantage else max(rolls)
    crit=roll==20;hit=crit or (roll!=1 and roll+bonus>=ac)
    result={'check':'attack','rolls':rolls,'roll':roll,'bonus':bonus,'total':roll+bonus,'defense':ac,'hit':hit,'critical':crit,
        'disadvantage':disadvantage,'advantage':advantage,'damage':0,'damage_dice':dice_text(dice),'damage_rolls':[],'damage_modifier':dice[2]}
    if hit:result.update(roll_damage(rng,dice,crit))
    return result

def roll_save(rng,bonus,dc,damage,half=True,advantage=False,disadvantage=False):
    advantage,disadvantage=bool(advantage and not disadvantage),bool(disadvantage and not advantage)
    rolls=[rng.randint(1,20) for _ in range(2 if advantage or disadvantage else 1)]
    roll=min(rolls) if disadvantage else max(rolls);saved=roll+bonus>=dc
    return {'check':'save','rolls':rolls,'roll':roll,'bonus':bonus,'total':roll+bonus,'defense':dc,'saved':saved,
            'save_half':half,'hit':True,'critical':False,'advantage':advantage,'disadvantage':disadvantage,**damage,
            'damage':damage['damage']//2 if saved and half else 0 if saved else damage['damage']}

def configure(items,enemies):
    for item in items.values():
        slot=item.get('slot');rarity=item.get('rarity','common')
        enchant={'common':0,'uncommon':0,'rare':1,'epic':2,'legendary':3,'heirloom':2}.get(rarity,0)
        item['attack']=enchant if slot=='weapon' else (1 if slot=='ring' and rarity in ('epic','legendary') else 0)
        item['attack_bonus']=item['attack']
        item['ac_bonus']=enchant if slot=='armor' else (1 if slot=='ring' and rarity in ('rare','epic','legendary') else 0)
        item['armor']=item['ac_bonus']
        if slot=='weapon':
            cls=item.get('class_ids',['knight'])[0]
            item['damage_dice']='1k8' if cls in ('knight','ranger') else '1k6' if cls=='druid' else '1k4 (Iskra różdżki)'
            if cls == 'mage':
                item['attack'] = 0  # a focus improves accuracy, not spark damage
                item['description'] = (item.get('description', '') + ' Iskra: 1k4 ognia, bez skalowania. '
                    'Trafienie z tego przedmiotu wzmacnia także rzuty ataku sztuczek i czarów.').strip()
        if slot=='armor':
            level=item.get('min_level',1)
            if level<=1:item.update(base_ac=10,armor_kind='none')
            elif level<8:item.update(base_ac=11,armor_kind='light')
            else:item.update(base_ac=14,armor_kind='medium')
        if slot=='ring' and not item['attack'] and not item['ac_bonus']:item['description']='Ozdoba; bez premii bojowych.'
    # Early encounters use recognisable low-HP stat blocks. Regional variants stay custom.
    explicit={
        'rat':(4,[1,6,1],[1,4,0],10,2), 'boar':(11,[2,8,2],[1,6,1],11,3),
        'wolf':(11,[2,8,2],[2,4,2],13,4),'goblin':(7,[2,6,0],[1,6,2],13,4),
        'spider':(16,[3,8,3],[1,6,2],13,4),'skeleton':(13,[2,8,4],[1,6,2],13,4),
        'bandit':(11,[2,8,2],[1,6,1],12,3),'bandit_archer':(11,[2,8,2],[1,8,1],12,3),
        'skeleton_archer':(13,[2,8,4],[1,6,2],13,4),'wisp':(18,[4,6,4],[1,8,2],13,4),
        'guardian':(45,[6,8,18],[2,6,3],16,5),'boss':(90,[12,8,36],[2,6,3],16,5),
        'bear':(34,[4,10,12],[2,6,4],11,5),'ogre':(59,[7,10,21],[2,8,4],11,6),
        'ghoul':(22,[5,8,0],[2,4,2],12,4),
    }
    undead={'skeleton','skeleton_archer','ghoul','mummy','vampire','necromancer','lich','lich_king'}
    constructs={'guardian','golem','ancient_guardian'}
    for kind,s in enemies.items():
        level=max(1,int(s.get('level',8 if kind=='boss' else 1)))
        boss=s.get('boss',False) or kind=='boss'
        n=max(2,math.ceil((8+level*2.2)*(2.3 if boss else 1)/6.5))
        hp=math.floor(n*6.5);hpd=[n,8,n*2]
        dmg=[min(6,1+level//30),8,min(10,1+level//15)+(2 if boss else 0)]
        ac=min(22,11+level//18+(2 if kind in constructs or boss else 0))
        atk=min(14,3+level//14+(1 if boss else 0))
        if kind in explicit:hp,hpd,dmg,ac,atk=explicit[kind]
        s.update(hp=hp,hp_dice=hpd,damage_dice=dmg,melee_dice=dmg[:],special_dice=[dmg[0]+(2 if boss else 1),dmg[1],dmg[2]],
                 armor_class=ac,attack_bonus=atk,save_bonus=min(9,level//16+1),save_dc=10+min(9,level//18)+(2 if boss else 0),
                 creature_type='undead' if kind in undead else 'construct' if kind in constructs else 'creature')
        s['base_aggro']=s.get('base_aggro',s['aggro'])
        s['aggro']=round(s['base_aggro']*(.75 if not boss and hp<=18 else .88 if not boss and hp<=34 else 1))
        s['damage']=dmg[0]*(dmg[1]+1)/2+dmg[2]
        s['melee_damage']=s['damage']
        s['saves']={a:s['save_bonus'] for a in ('strength','dexterity','constitution','intelligence','wisdom','charisma')}
        s['attack_interval']=2.7 if kind in ('wolf','frost_wolf','vampire','nightmare') else 3.4 if kind in ('golem','guardian','mummy','ogre') else 3.0
        s['ranged_interval']=max(3.0,s['ranged_interval'])


class CombatRounds:
    def begin_action(self,p,bonus=False):
        begin_feat_turn(p,self.now())
        if bonus:p.bonus_cooldown_until=self.now()+ROUND_SECONDS
        else:p.attack_cooldown_until=self.now()+ROUND_SECONDS
        p.attack_until=self.time+.3

    def close_threat(self, p, target=None, spell=False):
        if not spell and gear.melee(p):return False
        if target is not None and target.alive and same_floor(p,target) and math.hypot(p.x-target.x,p.y-target.y)<=72 and self.line_clear(p,target):return True
        if any(e.alive and e.hp>0 and same_floor(p,e) and math.hypot(p.x-e.x,p.y-e.y)<=72 and self.line_clear(p,e)
                for e in self.nearby_enemies(p,72)):return True
        now=self.now()
        return any(q is not p and q.alive and same_floor(p,q) and not (p.party_id and p.party_id==q.party_id)
            and math.hypot(p.x-q.x,p.y-q.y)<=72 and self.line_clear(p,q)
            and (p.aggressors.get(q.id,0)>now or q.aggressors.get(p.id,0)>now) for q in self.players.values())

    def add_hunters_mark(self, p, target, result):
        target_kind='player' if self.is_player_target(target) else 'enemy'
        if (result.get('hit') and p.class_id=='ranger' and p.mark_target==target.id
                and getattr(p,'mark_target_kind','enemy')==target_kind and p.concentration=='hunters_mark'
                and p.concentration_until>self.now()):
            mark=roll_damage(self.combat_rng,(1,6,0),result.get('critical',False))
            components=result.setdefault('damage_components',[{'type':result['damage_type'],'damage':result['damage']}])
            components.append({'type':'force','damage':mark['damage']})
            result['damage']+=mark['damage'];result['damage_dice']+=' + 1k6 (Znak)';result['mark_rolls']=mark['damage_rolls']

    def report_roll(self,source,target,result,action,owner=None):
        fx=self.combat_effect(source,'combat_roll',target,duration=1.4)
        spec=content.ENEMIES.get(getattr(target,'kind',''),{})
        fx.update(result,action=action,target_name=getattr(target,'name',spec.get('name','Cel')))
        if owner is not None:
            owner.last_roll={**fx,'expires_at':self.now()+8}
            owner.combat_log.append(dict(owner.last_roll))
            owner.combat_log=owner.combat_log[-8:]
        return fx

    def hit_enemy(self,p,enemy,multiplier=1,action='Atak',power=None,dice=None,spell=False,melee=False,damage_kind=None):
        spec=environment.enemy_spec(enemy)
        dice=tuple(dice or weapon_dice(p))
        disadvantage=(not melee and self.close_threat(p,spell=spell)) or active_buff(p,'blind') or active_buff(p,'restrained')
        advantage=active_buff(p,'foresight') or self.enemy_condition(enemy,'restrained') or self.enemy_condition(enemy,'blind')
        fdis,fadv=self.fighter_roll_flags(p,enemy)
        edis,eadv=self.environment_attack_flags(p,enemy)
        bonus=(spell_bonus(p) if spell else attack_bonus(p))+self.circle_roll_adjustment(p,'attack',target=enemy)-getattr(p,'exhaustion',0)*2
        result=roll_attack(self.combat_rng,bonus,spec['armor_class'],dice,disadvantage or fdis or edis or (not spell and gear.weapon_disadvantage(p)),advantage or fadv or eadv or self.caster_attack_advantage(p,enemy))
        result['damage_type']=damage_kind or damage_type(p)
        self.environment_adjust_damage(p,enemy,result,dice,melee)
        if not spell:
            savage_attacker_damage(p,result,self.combat_rng,self.now())
            self.fighter_adjust_damage(p,result)
        self.circle_adjust_damage(p,enemy,result,weapon=not spell)
        self.environment_attack_riders(p,enemy,result,melee)
        self.provoke_enemy(enemy,p)
        if result['hit'] or result.get('graze'):
            self.add_hunters_mark(p,enemy,result)
            result['damage']=self.environment_damage_enemy(enemy,result['damage'],p,result['damage_type'],result.get('damage_components'));self.remember_attacker(enemy,p)
        self.report_roll(p,enemy,result,action,p)
        return result

    def area_hit(self,p,enemies,power,action):
        # Kept only for compatibility with integrations; new spells pass explicit dice.
        dmg=roll_damage(self.combat_rng,damage_dice(power))
        for e in enemies:
            result=roll_save(self.combat_rng,content.ENEMIES[e.kind]['save_bonus'],spell_dc(p),dmg)
            e.hp=max(0,e.hp-result['damage']);self.remember_attacker(e,p);self.report_roll(p,e,result,action,p)

    def resolve_player_hit(self, source, target, result, action, owner=None, unjust=False):
        """One damage path for weapon hits, spells and pets: resistance, forms, death and crimes."""
        self.tag(target,owner is not None)
        if result.get('hit') or result.get('graze'):
            before=target.hp+getattr(target,'temp_hp',0)
            self.damage_player(target,result['damage'],killer=owner,unjust=unjust,rolled=True,
                damage_type=result.get('damage_type','bludgeoning'),damage_components=result.get('damage_components'),
                is_attack=result.get('check')=='attack' and bool(result.get('hit')),source=source)
            result['damage']=round(before-target.hp-getattr(target,'temp_hp',0),1)
        self.report_roll(source,target,result,action,owner)
        return result

    def hit_player(self,source,target,power=0,*,pvp=False,unjust=False,area=False,dice=None,damage_kind=None,spell=False,melee=None,action=None):
        if not target.alive:return None
        if pvp:
            if self.pvp_error(source,target) or not same_floor(source,target):return None
            source.current_wall_time=self.now()
            unjust=self.begin_pvp_hostility(source,target)
        target.current_wall_time=self.now()
        spec=environment.enemy_spec(source)
        chosen=tuple(dice or (weapon_dice(source) if pvp else spec['special_dice'] if area else spec['damage_dice']))
        kind=damage_kind or (damage_type(source) if pvp else 'fire' if area and spec.get('projectile')=='fire' else 'cold' if area and spec.get('projectile')=='ice' else 'bludgeoning')
        if area:
            result=self.target_save(target,'dexterity',spec['save_dc'],roll_damage(self.combat_rng,chosen),half=True)
        else:
            if pvp:
                is_melee=gear.melee(source) if melee is None else melee
                dis=(not is_melee and self.close_threat(source,target,spell=spell)) or active_buff(source,'blind') or active_buff(source,'restrained')
                adv=active_buff(source,'foresight') or active_buff(target,'restrained') or active_buff(target,'blind')
                bonus=spell_bonus(source) if spell else attack_bonus(source)
                dis=dis or (not spell and gear.weapon_disadvantage(source))
                adv=adv or self.caster_attack_advantage(source,target)
            else:
                dis=self.enemy_condition(source,'blind') or self.enemy_condition(source,'restrained')
                adv=active_buff(target,'restrained') or active_buff(target,'blind')
                bonus=spec['attack_bonus']
            fdis,fadv=self.fighter_roll_flags(source,target)
            edis,eadv=self.environment_attack_flags(source,target)
            bonus+=self.circle_roll_adjustment(source,'attack',target=target)-getattr(source,'exhaustion',0)*2
            result=roll_attack(self.combat_rng,bonus,armor_class(target),chosen,dis or edis or active_buff(target,'foresight') or fdis,adv or fadv or eadv)
            result['damage_type']=kind
            self.environment_adjust_damage(source,target,result,chosen,melee if melee is not None else (gear.melee(source) if pvp else not spec.get('projectile')))
            if not getattr(target,'is_companion',False):self.shield_reaction(target,result)
            if pvp and not spell:
                savage_attacker_damage(source,result,self.combat_rng,self.now())
                self.fighter_adjust_damage(source,result)
        result['damage_type']=kind
        if pvp:self.circle_adjust_damage(source,target,result,weapon=not spell)
        if not area:self.environment_attack_riders(source,target,result,melee if melee is not None else (gear.melee(source) if pvp else not spec.get('projectile')))
        if pvp:self.add_hunters_mark(source,target,result)
        return self.resolve_player_hit(source,target,result,action or ('Atak' if pvp else spec['name']),owner=source if pvp else None,unjust=unjust)
