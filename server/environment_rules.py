"""Shared conditions, water, sight and terrain used by spells and normal combat."""
import math
from types import SimpleNamespace
try:
    from . import world_content as content, caster_rules as caster, druid_circles as circles, magic_items
    from .living_world import segment_distance
    from .progression import same_floor
except ImportError:
    import world_content as content, caster_rules as caster, druid_circles as circles, magic_items
    from living_world import segment_distance
    from progression import same_floor

def conditions(actor):return getattr(actor,'buffs',getattr(actor,'conditions',{}))
def active(actor,key,now=None):
    value=conditions(actor).get(key,{})
    return value.get('until',0)>(getattr(actor,'current_wall_time',0) if now is None else now) and not magic_items.reduces_magic_condition(actor,key,value)
def incapacitated(actor,now=None):return any(active(actor,k,now) for k in ('incapacitated','paralyzed','unconscious','stunned','sleep_pending'))
def actions_blocked(actor,now=None):return incapacitated(actor,now) or active(actor,'stinking_poison',now)
def immobile(actor,now=None):
    if any(active(actor,k,now) for k in ('paralyzed','unconscious','stunned','grappled')):return True
    return not active(actor,'freedom',now) and any(active(actor,k,now) for k in ('restrained','web_restrained','elemental_restrained'))
def polymorph(actor):return conditions(actor).get('polymorph',{}) if active(actor,'polymorph') else {}
def physical_form(actor):
    transformed=polymorph(actor)
    if transformed:return caster.FORMS.get(transformed.get('form',''),transformed)
    if getattr(actor,'class_id',''):return caster.form_spec(actor)
    spec=content.ENEMIES.get(getattr(actor,'kind',''),{})
    return dict(spec,speed=spec.get('walking_speed_ft',30))
def enemy_spec(actor):
    base=content.ENEMIES.get(getattr(actor,'kind',''),{})
    form=polymorph(actor)
    if not form:return base
    result=dict(base);attributes=form.get('attributes',{})
    beast=caster.FORMS.get(form.get('form',''),{})
    result.update(armor_class=form.get('ac',10),attack_bonus=form.get('attack_bonus',0),
        damage_dice=form.get('attacks',[[1,4,0]])[0],speed=form.get('speed',30)*100/30,
        combat_role='melee',boss=False,blindsight=beast.get('blindsight',0),
        resistances=beast.get('resistances',[]),immunities=beast.get('immunities',[]),
        saves={a:(int(v)-10)//2 for a,v in attributes.items()})
    return result

def water_info(point):
    if getattr(point,'floor',0):return dict(water=False,depth_ft=0,width_ft=0)
    x,y=point.x,point.y
    water=content.WATER_MAP.blocked(x,y,0) or 1500<x<1680 and 0<y<2304 and not 1080<y<1230
    depth=30 if water else 0;width=180 if water else 0
    if getattr(content.WATER_MAP,'is_ocean',lambda *_:False)(x,y):water=True;depth=80;width=1280
    for kind,segment in content.WATER_MAP.cells.get((math.floor(x/512),math.floor(y/512)),()):
        if kind=='water' and segment_distance(x,y,segment['a'],segment['b'])<segment['width']/2:
            depth=max(depth,segment.get('depth_ft',30));width=max(width,segment['width'])
    return dict(water=water,depth_ft=depth,width_ft=width/6.4)

def configure_world():
    # A widened, visible stretch of the existing river supports deep-water magic.
    try:from .vertical_world import WaterMap,segment
    except ImportError:from vertical_world import WaterMap,segment
    if not any(w['id']=='deep_river_pool' for w in content.WATERWAYS):
        pool=segment([5880,8050],[5880,8250],400,'deep_river_pool');pool['depth_ft']=40
        content.WATERWAYS.append(pool);content.WATER_MAP=WaterMap(content.WATERWAYS,content.BRIDGES)

def flying(actor):return bool(circles.flight_speed(actor) or physical_form(actor).get('fly',0)) and not immobile(actor)
def swimming(actor):return bool(circles.can_swim(actor) or physical_form(actor).get('swim',0) or active(actor,'freedom') or magic_items.effect(actor,'swim'))
def effective_water_info(actor):
    resolver=getattr(actor,'_environment_water_resolver',None)
    return resolver(actor) if callable(resolver) else water_info(actor)

def movement_speed(actor,speed,surface=1):
    if immobile(actor):return 0
    form=physical_form(actor)
    flight=circles.flight_speed(actor) or form.get('fly',0)
    if flight:
        if flight!='walking':speed=speed*float(flight)/max(1,form.get('speed',30))
        surface=1
    elif effective_water_info(actor)['water']:
        swim=float(form.get('swim',0))/max(1,float(form.get('speed',30)))
        swim=max(swim,float(magic_items.effect(actor,'swim'))/30)
        surface=max(swim,1 if circles.can_swim(actor) or active(actor,'freedom') else 0) or .5
    elif magic_items.effect(actor,'free_action'):surface=max(surface,1)
    if active(actor,'difficult_terrain') and not flight and not active(actor,'freedom') and not magic_items.effect(actor,'free_action'):surface*=.5
    wind=conditions(actor).get('headwind',{})
    if active(actor,'headwind'):
        wx,wy=wind.get('direction',(0,0))
        if getattr(actor,'dx',0)*wx+getattr(actor,'dy',0)*wy<0:surface*=.5
    if (getattr(actor,'druid_circle_runtime',None) or {}).get('grapple_slow'):surface*=.5
    # Tree Stride spends ten feet of this turn's movement budget.
    cost=conditions(actor).get('tree_movement_cost',{})
    movement_cost=float(cost.get('feet',0))*6.4/3 if active(actor,'tree_movement_cost') else 0
    if active(actor,'feat_slasher_slow') and not active(actor,'freedom') and not magic_items.effect(actor,'free_action'):movement_cost+=10*6.4/3
    return max(0,speed*surface-movement_cost)

def public(actor,private=False):
    now=getattr(actor,'current_wall_time',0);water=effective_water_info(actor)['water']
    result=dict(in_water=water,submerged=bool(getattr(actor,'submerged',False)),flight=flying(actor),
        breath_remaining=max(0,round(getattr(actor,'breath_until',now)-now,1)) if getattr(actor,'submerged',False) else 0)
    if private:
        resolver=getattr(actor,'_environment_hide_resolver',None)
        if callable(resolver):result['hide']=resolver(actor)
    return result

class EnvironmentGame:
    def environment_fields(self):return (*getattr(self,'spell_fields',()),*getattr(self,'circle_spell_fields',()))

    def environment_bind(self,actor):
        # Runtime only: positions and Control Water modes must be read live.
        actor._environment_water_resolver=self.environment_water_info
        actor._environment_hide_resolver=self.environment_hide_public

    def environment_reveal(self,p,reason=''):
        hidden=conditions(p).pop('hidden',None)
        if hidden and reason and hasattr(p,'class_id'):self.caster_message(p,reason)
        return bool(hidden)

    def environment_hide_cover(self,p):
        # Runtime adaptation: a solid obstacle within 40 units supplies a place
        # to crouch, but enemies must ALSO lack line of sight. Fog is heavy
        # obscurement. Blindness on the hider alone is never suitable cover.
        if self.environment_obscured(p,False):return True
        for cx in range(int((p.x-40)//256),int((p.x+40)//256)+1):
            for cy in range(int((p.y-40)//256),int((p.y+40)//256)+1):
                for o in self.obstacle_cells.get((p.floor,cx,cy),()):
                    if o.get('type') not in ('house','mill','wall','rock','mountain','grove','ruin','canyon','terrace'):continue
                    dx=max(o['x']-p.x,0,p.x-o['x']-o['w']);dy=max(o['y']-p.y,0,p.y-o['y']-o['h'])
                    if math.hypot(dx,dy)<=40:return True
        return False

    def environment_hide_observers(self,p):
        seen=set()
        for e in self.nearby_enemies(p,1450):
            if e.id in seen or not e.alive or e.hp<=0 or not same_floor(e,p):continue
            seen.add(e.id)
            if math.hypot(e.x-p.x,e.y-p.y)<=max(768,enemy_spec(e).get('aggro',0)):
                yield e

    def environment_hide_reason(self,p):
        if not p.alive:return 'Ukrywanie wymaga żywej postaci.'
        if actions_blocked(p,self.now()):return 'Obecny stan uniemożliwia ukrycie.'
        if p.pvp_combat_until>self.now():return 'Ukrywanie przed potworami jest niedostępne podczas walki PvP.'
        if p.attack_cooldown_until>self.now():return 'Zaczekaj na następną akcję.'
        if not self.environment_hide_cover(p):return 'Podejdź do osłony albo wejdź w gęstą mgłę.'
        if any(self.environment_raw_can_see(e,p) for e in self.environment_hide_observers(p)):
            return 'Potwór cię widzi. Najpierw zejdź z jego linii wzroku.'
        return ''

    def environment_hide_public(self,p):
        hidden=conditions(p).get('hidden',{})
        active_hidden=hidden.get('until',0)>self.now()
        reason='' if active_hidden else self.environment_hide_reason(p)
        return dict(active=active_hidden,available=active_hidden or not reason,reason=reason,
                    dc=hidden.get('dc') if active_hidden else 15,remaining=None,scope='pve')

    def environment_hide_tick(self,p):
        hidden=conditions(p).get('hidden',{})
        if hidden.get('until',0)<=self.now():return
        if not p.alive or actions_blocked(p,self.now()) or p.pvp_combat_until>self.now():
            self.environment_reveal(p,'Ukrycie zostało przerwane.');return
        if not self.environment_hide_cover(p):
            self.environment_reveal(p,'Wyjście zza osłony zdradza twoją pozycję.');return
        hidden['until']=self.now()+86400  # session condition; never saved
        for e in self.environment_hide_observers(p):
            if self.environment_raw_can_see(e,p):
                self.environment_reveal(p,'Potwór dostrzegł cię poza osłoną.');return
            distance=math.hypot(e.x-p.x,e.y-p.y)
            # Hearing reaches 30 feet, and does not pass solid walls. Nearby
            # pursuers Search once per turn, spending their attack action.
            if distance>192 or not self.line_clear(e,p) or active(e,'deafened',self.now()):continue
            spec=enemy_spec(e)
            bonus=spec.get('perception_bonus',spec.get('saves',{}).get('wisdom',0))
            passive=spec.get('passive_perception',10+bonus)
            if passive>=hidden['dc']:
                self.environment_reveal(p,'Potwór usłyszał cię i odnalazł kryjówkę.');return
            pursuing=e.chase_id==p.id or e.attacker_id==p.id
            if not pursuing or e.ready>self.time or getattr(e,'_hide_search_until',0)>self.now():continue
            if actions_blocked(e,self.now()):continue
            e._hide_search_until=self.now()+3;e.ready=max(e.ready,self.time+3)
            if self.combat_rng.randint(1,20)+bonus>=hidden['dc']:
                self.environment_reveal(p,'Poszukujący cię potwór odnalazł kryjówkę.');return

    def begin_action(self,p,bonus=False):
        if getattr(p,'_hide_casting',False):self.environment_reveal(p,'Rzucanie czaru zdradza kryjówkę.')
        return super().begin_action(p,bonus=bonus)

    def hit_enemy(self,p,*args,**kwargs):
        result=super().hit_enemy(p,*args,**kwargs)
        if result is not None:self.environment_reveal(p)
        return result

    def hit_player(self,source,*args,**kwargs):
        result=super().hit_player(source,*args,**kwargs)
        if result is not None and result.get('check')=='attack':self.environment_reveal(source)
        return result

    def environment_submerge(self,actor):
        self.environment_bind(actor)
        if getattr(actor,'submerged',False):return
        try:from . import combat_rules as rules
        except ImportError:import combat_rules as rules
        actor.submerged=True
        modifier=rules.ability_modifier(actor,'constitution') if self.is_player_target(actor) else enemy_spec(actor).get('saves',{}).get('constitution',0)
        seconds=max(15,(1+modifier)*30,float(caster.form_spec(actor).get('hold_breath',0))/2)
        actor.breath_until=self.now()+seconds

    def environment_water_info(self,point):
        result=water_info(point)
        for field in self.environment_fields():
            if field.get('key')!='control_water' or field.get('until',0)<=self.now() or field.get('floor',0)!=point.floor:continue
            if abs(point.x-field['x'])>320 or abs(point.y-field['y'])>320:continue
            variant=field.get('water_variant',field.get('profile',{}).get('water_variant','flood'))
            if variant=='part':return dict(water=False,depth_ft=0,width_ft=result['width_ft'])
            if variant=='flood':return dict(water=True,depth_ft=result['depth_ft']+20,width_ft=100)
        return result

    def environment_control_water(self,field,nearby,due):
        if not due:return
        profile=field['profile'];variant=profile.get('water_variant','flood')
        owner=self.players.get(field['owner'])
        if not owner:return
        for actor in nearby:
            self.environment_bind(actor)
            if flying(actor) or not self.environment_water_info(actor)['water']:continue
            if variant=='redirect':
                dx,dy=profile.get('flow',(0,1));length=math.hypot(dx,dy) or 1
                self.environment_forced_move(actor,dx/length*32,dy/length*32)
            elif variant=='whirlpool':
                dx,dy=field['x']-actor.x,field['y']-actor.y;length=math.hypot(dx,dy) or 1
                if length>50*6.4:continue
                self.environment_forced_move(actor,dx/length*min(length,64),dy/length*min(length,64))
            if self.is_player_target(actor) and variant in ('flood','whirlpool') and not self.pvp_error(owner,actor):
                self.environment_submerge(actor)

    def environment_stone_support(self,point):
        if self.environment_water_info(point)['water']:return False
        if content.SURFACE_MAP.at(point.x,point.y,point.floor)=='stone':return True
        obstacles=self.obstacle_cells.get((point.floor,int(point.x//256),int(point.y//256)),())
        return any(o.get('type') in ('rock','mountain') and o['x']-64<=point.x<=o['x']+o['w']+64 and o['y']-64<=point.y<=o['y']+o['h']+64 for o in obstacles)

    def environment_trees(self):
        # Match the authored groves that are actually drawn on the map.
        if hasattr(self,'_environment_trees'):return self._environment_trees
        seen=set();trees=[]
        for obstacles in self.obstacle_cells.values():
            for o in obstacles:
                key=(o['x'],o['y'],o.get('floor',0))
                if key in seen or o.get('type')!='grove':continue
                seen.add(key)
                trees.append(dict(id=f'tree_{key[0]}_{key[1]}',x=o['x']+o['w']/2,y=o['y']+o['h'],radius=20,
                    floor=o.get('floor',0),kind='oak',size='large',living=True))
        self._environment_trees=trees
        return trees

    def environment_wall_blocked(self,x,y,radius=2,floor=0):
        for field in self.environment_fields():
            if field.get('until',0)<=self.now() or field.get('floor',0)!=floor:continue
            for wall in field.get('segments',()):
                if wall.get('hp',1)>0 and x+radius>wall['x'] and x-radius<wall['x']+wall['w'] and y+radius>wall['y'] and y-radius<wall['y']+wall['h']:return True
        return False

    def blocked_for(self,actor,x,y,radius=18):
        self.environment_bind(actor)
        # Inland swimming, flight and Control Water intentionally bypass river
        # collision. The ocean is a separate map boundary: island journeys use
        # boats, and neither normal movement nor a forced push may cross it.
        if actor.floor==0 and content.WATER_MAP.ocean_blocked(x,y,radius):return True
        if not getattr(actor,'_environment_forced',False) and not flying(actor):
            trapped=conditions(actor).get('whirlpool',{});escape=conditions(actor).get('whirlpool_escape',{})
            if trapped.get('until',0)>self.now() and not (escape.get('until',0)>self.now() and escape.get('field_id')==trapped.get('field_id')):
                for field in self.environment_fields():
                    if field.get('id')==trapped.get('field_id') and field.get('until',0)>self.now():
                        if math.hypot(x-field['x'],y-field['y'])>math.hypot(actor.x-field['x'],actor.y-field['y'])+.001:return True
        return self.blocked(x,y,radius,floor=actor.floor,ignore_water=True,ignore_low=flying(actor))

    def environment_recover_shore(self,p):
        """Rescue a saved offshore position only after combat has ended.

        Choose nearby dry coast rather than granting a free trip to a bound
        city. The marker is runtime-only and is reconstructed on every login.
        """
        if not getattr(p,'_shore_recovery_pending',False) or not p.alive:return False
        if max(p.combat_until,p.pvp_combat_until)>self.now():return False
        if p.floor or not content.WATER_MAP.ocean_blocked(p.x,p.y,18):
            p._shore_recovery_pending=False
            return False
        origin=(p.x,p.y)
        x,y=content.GEOGRAPHY.nearest(*origin,clearance=32)
        candidates=[(x,y)]
        for radius in (32,64,128,256,512,1024,2048):
            for i in range(16):
                angle=i*math.tau/16
                candidates.append((x+math.cos(angle)*radius,y+math.sin(angle)*radius))
        destination=next((point for point in sorted(candidates,key=lambda q:math.dist(origin,q))
                          if not self.blocked(*point,floor=0)),None)
        if destination is None:
            # Authored ports are guaranteed dry and reachable. This fallback
            # also handles a coast whose nearest tile is hidden behind cliffs.
            destination=next(((port['x'],port['y']) for port in sorted(content.PORTS,
                              key=lambda port:math.hypot(port['x']-origin[0],port['y']-origin[1]))
                              if not self.blocked(port['x'],port['y'],floor=0)),None)
        if destination is None:return False
        p.x,p.y=destination
        p.dx=p.dy=0;p.input_time=-10;p.submerged=False
        p.world_revision=getattr(content,'WORLD_REVISION',20)
        p._shore_recovery_pending=False
        self.caster_message(p,'Przywrócono postać z morza na najbliższy dostępny brzeg. Między wyspami kursują łodzie.')
        return True

    def environment_obscured(self,actor,include_blind=True):
        if include_blind and active(actor,'blind',self.now()):return True
        for field in self.environment_fields():
            if field.get('until',0)<=self.now() or field.get('floor',0)!=actor.floor:continue
            spec=field.get('profile',{})
            if (spec.get('obscure') or field.get('key') in ('fog_cloud','sleet_storm','stinking_cloud')) and math.hypot(actor.x-field['x'],actor.y-field['y'])<=field.get('radius',128):return True
        return False

    def environment_raw_can_see(self,a,b):
        if not same_floor(a,b) or not self.line_clear(a,b):return False
        spec=enemy_spec(a) if not hasattr(a,'class_id') else caster.form_spec(a)
        reach=float(spec.get('blindsight',0))*6.4
        if reach and math.hypot(a.x-b.x,a.y-b.y)<=reach:return True
        # Blindness belongs to the observer; it does not hide that observer
        # from other creatures. Third Eye pierces magical cover, not blindness.
        if active(a,'blind',self.now()):return False
        if self.wizard_third_eye(a):return True
        if self.environment_obscured(a,False) or self.environment_obscured(b,False):return False
        for field in self.environment_fields():
            if field.get('until',0)<=self.now() or field.get('floor',0)!=a.floor:continue
            if field.get('profile',{}).get('obscure') or field.get('key') in ('fog_cloud','sleet_storm','stinking_cloud'):
                if segment_distance(field['x'],field['y'],(a.x,a.y),(b.x,b.y))<=field.get('radius',128):return False
        return True

    def environment_can_see(self,a,b):
        # PvE only: positions stay public to other players and hidden never
        # grants an advantage, protection or targeting immunity against them.
        if not hasattr(a,'class_id') and hasattr(b,'class_id') and active(b,'hidden',self.now()):
            spec=enemy_spec(a)
            reach=max(spec.get('blindsight',0),spec.get('truesight',0))*6.4
            if math.hypot(a.x-b.x,a.y-b.y)>reach or not self.line_clear(a,b):return False
        return self.environment_raw_can_see(a,b)

    def environment_attack_flags(self,source,target):
        now=self.now();see=self.environment_can_see(source,target);seen=self.environment_can_see(target,source)
        dis=not see or any(active(source,k,now) for k in ('poisoned','web_restrained','elemental_restrained','stinking_poison'))
        adv=not seen or any(active(target,k,now) for k in ('paralyzed','unconscious','web_restrained','elemental_restrained'))
        spec=enemy_spec(source) if not hasattr(source,'class_id') else caster.form_spec(source)
        if active(target,'blur',now) and not spec.get('blindsight') and not spec.get('truesight') and not self.wizard_third_eye(source):dis=True
        bolt=conditions(target).pop('guiding_bolt',{})
        adv=adv or bolt.get('until',0)>now or active(target,'feat_crusher_exposed',now)
        dis=dis or active(source,'feat_slasher_disadvantage',now)
        # Retain the already computed benefit for this roll, then reveal before
        # damage riders can trigger a second weapon attack (e.g. Horde Breaker).
        self.environment_reveal(source)
        return dis,adv

    def environment_adjust_damage(self,source,target,result,dice,melee=False):
        if not result.get('hit'):return
        try:
            from . import combat_rules as rules
        except ImportError:
            import combat_rules as rules
        if not result.get('critical') and math.hypot(source.x-target.x,source.y-target.y)<=32 and any(active(target,k,self.now()) for k in ('paralyzed','unconscious')):
            result.update(rules.roll_damage(self.combat_rng,dice,True,maximize=self.wizard_maximize_spell(source,getattr(source,'_wizard_damage_spec',None) or {})),critical=True)
        magic_items.prevent_critical(target,result)
    def environment_attack_riders(self,source,target,result,melee=False):
        if not result.get('hit'):return
        try:
            from . import combat_rules as rules
        except ImportError:
            import combat_rules as rules
        if melee and active(source,'fount_of_moonlight',self.now()):
            extra=rules.roll_damage(self.combat_rng,(2,6,0),result.get('critical',False))
            result.setdefault('damage_components',[dict(type=result.get('damage_type','bludgeoning'),damage=result['damage'])]).append(dict(type='radiant',damage=extra['damage']))
            result['damage']+=extra['damage'];result['damage_dice']+=' + 2k6 promienistych'
            rules.record_damage_roll(result, extra, 'Światło księżyca')

    def environment_damage_enemy(self,target,amount,source=None,damage_type='bludgeoning',components=None,critical=False):
        spec=enemy_spec(target)
        def resisted(value,kind):
            if kind in spec.get('immunities',()):return 0
            return int(max(0,value)*(.5 if kind in spec.get('resistances',()) else 1))
        amount=sum(resisted(c['damage'],c['type']) for c in components) if components is not None else resisted(amount,damage_type)
        before=amount
        if getattr(target,'temp_hp',0)>0:
            absorbed=min(target.temp_hp,amount);target.temp_hp-=absorbed;amount-=absorbed
        target.hp=max(0,target.hp-amount)
        if before>0 and hasattr(self,'circle_spell_damage_received'):self.circle_spell_damage_received(target,before,source)
        return before

    async def cast_spell(self,p,*args,**kwargs):
        if actions_blocked(p,self.now()):return await self.notice(p,'Ten stan uniemożliwia wykonywanie akcji.')
        prior=getattr(p,'_hide_casting',False);p._hide_casting=True
        try:return await super().cast_spell(p,*args,**kwargs)
        finally:p._hide_casting=prior

    async def cast_circle_spell(self,p,*args,**kwargs):
        prior=getattr(p,'_hide_casting',False);p._hide_casting=True
        try:return await super().cast_circle_spell(p,*args,**kwargs)
        finally:p._hide_casting=prior

    async def _cast_circle_spell(self,p,*args,**kwargs):
        # Queued circle spells execute this core entry directly, bypassing
        # both public cast methods when the next action becomes available.
        prior=getattr(p,'_hide_casting',False);p._hide_casting=True
        try:return await super()._cast_circle_spell(p,*args,**kwargs)
        finally:p._hide_casting=prior

    async def start_caster_channel(self,p,*args,**kwargs):
        before=getattr(p,'casting_channel',None)
        result=await super().start_caster_channel(p,*args,**kwargs)
        if p.casting_channel and p.casting_channel is not before:self.environment_reveal(p,'Rozpoczęcie rytuału zdradza kryjówkę.')
        return result

    async def dnd_attack(self,p,*args,**kwargs):
        if actions_blocked(p,self.now()):return
        return await super().dnd_attack(p,*args,**kwargs)

    def target_save(self,target,ability,dc,damage,half=False):
        try:
            from . import combat_rules as rules
        except ImportError:
            import combat_rules as rules
        if ability in ('strength','dexterity') and any(active(target,k,self.now()) for k in ('paralyzed','unconscious','stunned')):
            return dict(damage,check='save',saved=False,hit=True,critical=False,roll=0,rolls=[],total=0,bonus=0,defense=dc,automatic_failure=True,save_half=half)
        check_draws=[]
        bonus=self.target_save_bonus(target,ability)+self.circle_roll_adjustment(target,'save',ability=ability,receipt=check_draws)
        dis=ability=='dexterity' and any(active(target,k,self.now()) for k in ('restrained','web_restrained','elemental_restrained'))
        dis=dis or ability=='constitution' and getattr(target,'_shatter_save_disadvantage',False)
        if self.is_player_target(target) and ability in ('strength','dexterity'):dis=dis or rules.gear.armor_penalty(target)
        advantage=active(target,'foresight',self.now()) or ability=='strength' and active(target,'conjure_animals_strength',self.now())
        if getattr(self,'_wizard_spell_source',None) is not None:advantage=advantage or self.wizard_spell_save_advantage(target)
        result=rules.roll_save(self.combat_rng,bonus,dc,damage,half,advantage=advantage,disadvantage=dis,fixed_roll=self.wizard_save_portent(target))
        if check_draws:result['check_extra_rolls']=check_draws
        if rules.gear.feat_rules.lucky_save(target,result,self.combat_rng,damage):
            with self.db:self.save_player(target)
        return result

    def environment_ability_check(self,actor,ability,dc,skill='',*,action_name=None,target=None):
        try:
            from . import combat_rules as rules, skill_rules
        except ImportError:
            import combat_rules as rules, skill_rules
        now=self.now();dis=active(actor,'poisoned',now) or active(actor,'stinking_poison',now) or self.martial_frightened(actor)
        if hasattr(actor,'class_id') and ability in ('strength','dexterity'):
            dis=dis or rules.gear.armor_penalty(actor)
        if skill=='stealth' and hasattr(actor,'class_id') and not getattr(actor,'form',''):
            dis=dis or rules.equipped_item(actor,'armor').get('stealth_disadvantage',False)
        adv=active(actor,'foresight',now)
        bonus=rules.ability_modifier(actor,ability) if hasattr(actor,'class_id') else enemy_spec(actor).get('saves',{}).get(ability,0)
        if hasattr(actor,'class_id') and skill in skill_rules.SKILLS:
            bonus=skill_rules.bonus(actor,skill,ability=ability)
        elif skill in getattr(actor,'skill_proficiencies',()):bonus+=rules.proficiency(actor)
        bonus-=getattr(actor,'exhaustion',0)*2
        # Cosmic Omen is committed before the D20, not after seeing its result.
        check_draws=[]
        bonus+=self.circle_roll_adjustment(actor,'ability',ability=ability,receipt=check_draws)
        rolls=[self.combat_rng.randint(1,20) for _ in range(2 if adv!=dis else 1)]
        roll=max(max(rolls) if adv and not dis else min(rolls),circles.roll_floor(actor,ability,'ability'))
        guidance=conditions(actor).get('guidance',{})
        guidance_roll = None
        if guidance.get('until',0)>now and guidance.get('skill')==skill:
            guidance_roll = self.combat_rng.randint(1,4);bonus += guidance_roll
        result=dict(check='ability',roll=roll,rolls=rolls,bonus=bonus,total=roll+bonus,defense=dc,saved=roll+bonus>=dc,hit=False,damage=0,damage_dice='',ability=ability,skill=skill)
        if guidance_roll is not None:
            check_draws.append(dict(name='Wskazówki', sides=4, rolls=[guidance_roll], sign=1))
        if check_draws:result['check_extra_rolls']=check_draws
        self.report_roll(actor,target or actor,result,action_name or skill or ability,actor if self.is_player_target(actor) else None)
        return result

    def environment_forced_move(self,target,dx,dy):
        prior=getattr(target,'_environment_forced',False)
        target._environment_forced=True
        try:self.move(target,dx,dy)
        finally:target._environment_forced=prior

    async def environment_action(self,p,action,enabled=None,enemy_id=None,target_id=None):
        if action=='unhide':self.environment_reveal(p);return
        if not p.alive or actions_blocked(p,self.now()):return
        if action=='hide':
            if active(p,'hidden',self.now()):return
            reason=self.environment_hide_reason(p)
            if reason:return await self.notice(p,reason)
            self.cancel_rest(p);self.cancel_channel(p,'');self.stop_auto(p);self.begin_action(p)
            result=self.environment_ability_check(p,'dexterity',15,'stealth')
            if not result['saved']:return await self.notice(p,'Nie udało się ukryć. Możesz spróbować ponownie w następnej turze.')
            p.buffs['hidden']=dict(until=self.now()+86400,dc=result['total'],pve=True)
            self.environment_hide_tick(p)
            if active(p,'hidden',self.now()):await self.notice(p,f'Ukrycie przed potworami · ST wykrycia {result["total"]}. Inni gracze nadal cię widzą.')
            return
        if action in ('study','search'):
            if p.attack_cooldown_until>self.now():return
            if action=='study':
                if enemy_id is not None and not isinstance(enemy_id,str) or target_id is not None and not isinstance(target_id,str):return
                target=self.enemies.get(enemy_id or p.auto_enemy_id or '')
                if not target or not target.alive or not self.environment_can_see(p,target) or math.hypot(p.x-target.x,p.y-target.y)>120*6.4:
                    return await self.notice(p,'Wybierz widocznego przeciwnika, aby zbadać jego naturę.')
                spec=enemy_spec(target);kind=spec.get('creature_type','creature')
                skill=('arcana' if kind in ('aberration','construct','elemental','fey','monstrosity') else
                       'religion' if kind in ('celestial','fiend','undead') else
                       'history' if kind in ('giant','humanoid') else 'nature')
                self.cancel_rest(p);self.cancel_channel(p,'');self.stop_auto(p);self.begin_action(p)
                # The world's common creatures use an easy lore check; bosses are rare lore.
                result=self.environment_ability_check(p,'intelligence',15 if spec.get('boss') else 10,skill)
                if not result['saved']:return await self.notice(p,'Badanie: nie przypominasz sobie pewnych informacji o tym stworzeniu.')
                types={'fire':'ogień','cold':'zimno','lightning':'błyskawice','thunder':'grzmot','poison':'trucizna','radiant':'promieniste','necrotic':'nekrotyczne','bludgeoning':'obuchowe','piercing':'kłute','slashing':'cięte'}
                defenses=', '.join(types.get(k,k) for k in spec.get('resistances',())) or 'brak'
                immunities=', '.join(types.get(k,k) for k in spec.get('immunities',())) or 'brak'
                info=f"{spec.get('name',target.kind)}: KP {spec.get('armor_class',10)}, maks. HP {spec.get('hp',target.hp)}. Odporności: {defenses}. Niewrażliwości: {immunities}."
                knowledge=getattr(p,'_environment_knowledge',None)
                if not isinstance(knowledge,dict):p._environment_knowledge={}
                p._environment_knowledge[target.kind]=info
                return await self.notice(p,'Badanie: '+info)
            self.cancel_rest(p);self.cancel_channel(p,'');self.stop_auto(p);self.begin_action(p)
            result=self.environment_ability_check(p,'wisdom',10,'perception')
            if not result['saved']:return await self.notice(p,'Rozejrzenie: nie dostrzegasz dodatkowych śladów zagrożenia.')
            found=[]
            for target in self.enemies.values():
                if not target.alive or not same_floor(p,target):continue
                distance=math.hypot(p.x-target.x,p.y-target.y)
                if distance>120*6.4:continue
                # Perception includes hearing; fog does not conceal nearby sounds.
                threshold=10 if distance<=60*6.4 else 15
                stealth=conditions(target).get('hidden',{}).get('dc',threshold)
                if result['total']<max(threshold,stealth):continue
                horizontal='wschód' if target.x>p.x else 'zachód';vertical='południe' if target.y>p.y else 'północ'
                direction=vertical if abs(target.y-p.y)>abs(target.x-p.x)*2 else horizontal if abs(target.x-p.x)>abs(target.y-p.y)*2 else vertical+' / '+horizontal
                found.append((distance,target, direction))
            found.sort(key=lambda row:row[0])
            p._environment_detected={target.id:self.now() for _,target,_ in found}
            if not found:return await self.notice(p,'Rozejrzenie: nie wykrywasz zagrożeń w pobliżu.')
            text='; '.join(f"{enemy_spec(target).get('name',target.kind)} — {direction}, {round(distance/6.4)} stóp" for distance,target,direction in found[:6])
            return await self.notice(p,'Rozejrzenie: '+text+'.')
        if action!='dive':return
        if enabled is False:p.submerged=False;return
        if not self.environment_water_info(p)['water']:return await self.notice(p,'Zanurkuj po wejściu do wody.')
        self.environment_submerge(p)

    def tick_dnd(self,dt):
        for actor in (*self.players.values(),*self.enemies.values()):self.environment_bind(actor)
        for p in self.players.values():self.environment_recover_shore(p)
        super().tick_dnd(dt)
        now=self.now()
        for p in self.players.values():
            self.environment_hide_tick(p)
            if incapacitated(p,now):
                self.cancel_rest(p);self.cancel_channel(p);self.break_concentration(p);self.stop_auto(p)
            if not getattr(p,'submerged',False):continue
            if not self.environment_water_info(p)['water'] or flying(p):p.submerged=False;continue
            form=caster.form_spec(p)
            if active(p,'water_breathing',now) or form.get('water_breathing'):
                p.breath_until=now+30;continue
            if p.breath_until<=now and getattr(p,'_suffocate_ready',0)<=now:
                p._suffocate_ready=now+3
                # 2024 suffocation: one exhaustion level per round; six is death.
                p.exhaustion=min(6,getattr(p,'exhaustion',0)+1)
                if p.exhaustion>=6:self.damage_player(p,p.hp+p.temp_hp+10000,damage_type='suffocation')
                self.caster_message(p,f'Brak powietrza! Wyczerpanie {p.exhaustion}/6. Wynurz się.')
