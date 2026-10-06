"""Authoritative optional weapon modes, Light bonus attacks and grappling."""
import math

try:
    from . import combat_rules as rules, weapon_actions as weapons, environment_rules as environment, fighter_rules, skill_rules
    from .progression import same_floor, train
except ImportError:
    import combat_rules as rules, weapon_actions as weapons, environment_rules as environment, fighter_rules, skill_rules
    from progression import same_floor, train


def _distance(a,b):return math.hypot(a.x-b.x,a.y-b.y)
GRAPPLE_ID='weapon_grapple'


class StyleWeaponGame:
    async def choose_weapon_mode(self,p,value):
        p.current_wall_time=self.now()
        error=weapons.set_mode(p,value)
        if error:return await self.notice(p,error)
        self.cancel_channel(p,'')
        p._equipment_preview_cache=None
        with self.db:self.save_player(p)
        await self.notice(p,{'weapon':'Atak założoną bronią.','throw':'Rzut bronią; odzyskasz ją z miejsca trafienia.','unarmed':'Atak bez broni.'}[value])

    async def recover_weapon(self,p,uid):
        error=weapons.recover_thrown(p,uid,self._style_inventory_cap(),line_clear=self.line_clear)
        if error:return await self.notice(p,error)
        with self.db:self.save_player(p)
        await self.notice(p,'Podniesiono rzuconą broń.')

    def _style_inventory_cap(self):
        try:from .server import INVENTORY_CAP
        except ImportError:from server import INVENTORY_CAP
        return INVENTORY_CAP

    def _style_target(self,p,target_id,enemy_id,reach):
        if (target_id is not None and not isinstance(target_id,str) or enemy_id is not None and not isinstance(enemy_id,str)
                or target_id is not None and enemy_id is not None):return None,'Wskaż jeden cel.'
        if target_id is None and enemy_id is None:
            target_id=p.auto_target_id or None;enemy_id=p.auto_enemy_id or None
        target=self.players.get(target_id) if target_id else self.enemies.get(enemy_id) if enemy_id else None
        if target_id:
            error=self.pvp_error(p,target)
            if error:return None,error
        elif self.in_safe(p):return None,'W bezpiecznej strefie nie można atakować.'
        if target is None and not target_id and not enemy_id:
            candidates=[e for e in self.nearby_enemies(p,reach) if e.alive and e.hp>0 and same_floor(p,e)
                and _distance(p,e)<=reach and self.line_clear(p,e)]
            target=min(candidates,key=lambda e:_distance(p,e)) if candidates else None
        if target is None or not target.alive or target.hp<=0 or not same_floor(p,target) or _distance(p,target)>reach or not self.line_clear(p,target):
            return None,'Cel jest poza zasięgiem albo za przeszkodą.'
        return target,''

    async def offhand_attack(self,p,target_id=None,enemy_id=None):
        now=self.now();p.current_wall_time=now
        if not p.alive or environment.actions_blocked(p,now):return
        error=weapons.offhand_error(p,now)
        if error:return await self.notice(p,error)
        other=weapons.held_item(p,'offhand')
        attack_mode='throw' if weapons.mode(p)=='throw' and other.get('thrown') else 'weapon'
        with weapons.attack_context(p,other,offhand=True,attack_mode=attack_mode):
            if weapons.is_thrown(p):
                error=weapons.throw_error(p,other)
                if error:return await self.notice(p,error)
            target,error=self._style_target(p,target_id,enemy_id,rules.attack_range(p))
            if error:return await self.notice(p,error)
            error=weapons.spend_offhand(p,now)
            if error:return await self.notice(p,error)
            self.cancel_rest(p);self.cancel_channel(p,'')
            self.tag(p,self.is_player_target(target));p.attack_until=self.time+.3
            unjust=self.begin_pvp_hostility(p,target) if self.is_player_target(target) else False
            self.basic_effect(p,target)
            melee=rules.gear.melee(p) and not weapons.is_thrown(p)
            if self.is_player_target(target):result=self.hit_player(p,target,pvp=True,unjust=unjust,melee=melee,action='Dodatkowy atak lekką bronią')
            else:result=self.hit_enemy(p,target,melee=melee,action='Dodatkowy atak lekką bronią')
            train(p,'melee' if melee else 'distance')
            self.trigger_ensnaring_strike(p,target,result)
            self.fighter_on_weapon_hit(p,target,result)
            if weapons.is_thrown(p):weapons.throw_weapon(p,target,other,slot='offhand')
        if not self.is_player_target(target) and target.hp<=0:await self.defeat(target)
        with self.db:
            self.save_player(p)
            if self.is_player_target(target):self.save_player(target)
        return result

    def _style_grapples(self,p):
        refs=getattr(p,'condition_targets',())
        return [(ref,target) for ref in tuple(refs) if (target:=self.resolve_target_ref(ref)) is not None
            and weapons.owned_grapple(p,target,self.now()) and self.target_conditions(target)['grappled'].get('spell_id')==GRAPPLE_ID]

    async def grapple_attack(self,p,target_id=None,enemy_id=None):
        now=self.now();p.current_wall_time=now
        if not p.alive or environment.actions_blocked(p,now) or p.attack_cooldown_until>now:return
        if p.pending_spell:
            if p.pending_spell.get('until',0)>=now:return
            p.pending_spell={}
        if p.form or environment.polymorph(p):return await self.notice(p,'W przemianie używaj zdolności ataku swojej bestii.')
        held=sum(bool(weapons.held_item(p,slot)) for slot in ('weapon','offhand','shield'))
        if not weapons.free_hand(p) or held+len(self._style_grapples(p))>=2:return await self.notice(p,'Do chwytu potrzebujesz wolnej ręki.')
        target,error=self._style_target(p,target_id,enemy_id,32)
        if error:return await self.notice(p,error)
        if self._circle_target_size(target)>self._circle_target_size(p)+1:return await self.notice(p,'Ta istota jest za duża, aby ją chwycić.')
        if weapons.owned_grapple(p,target,now):return await self.notice(p,'Już trzymasz tę istotę.')
        self.cancel_channel(p,'');self.begin_action(p)
        self.tag(p,self.is_player_target(target))
        unjust=self.begin_pvp_hostility(p,target) if self.is_player_target(target) else False
        ability=max(('strength','dexterity'),key=lambda a:self.target_save_bonus(target,a))
        result=self.target_save(target,ability,weapons.grapple_dc(p),dict(damage=0,damage_dice='',damage_rolls=[]),False)
        result.update(damage_type='bludgeoning',grapple=True,ability=ability)
        if not result['saved']:
            self.target_conditions(target)['grappled']=dict(until=now+3600,owner=p.id,hostile=True,spell_id=GRAPPLE_ID,
                dc=weapons.grapple_dc(p),reach=32,concentration=False,escape_ready=now+rules.ROUND_SECONDS)
            ref=self.target_ref(target)
            if ref not in p.condition_targets:p.condition_targets.append(ref)
            if self.is_player_target(target):self.record_pvp_effect(p,target,unjust)
            else:self.provoke_enemy(target,p)
        self.report_roll(p,target,result,'Chwyt',p)
        train(p,'melee')
        # Grappling replaces one Unarmed Strike of the Attack action. Extra
        # Attack still grants the remaining strikes, with independent rolls.
        for index in range(1,rules.attacks_per_round(p)):
            if not p.alive or not target.alive or target.hp<=0:break
            with weapons.attack_context(p,{},attack_mode='unarmed'):
                self.basic_effect(p,target)
                if self.is_player_target(target):self.hit_player(p,target,pvp=True,unjust=unjust,melee=True,action=f'Atak bez broni {index+1}/{rules.attacks_per_round(p)}')
                else:self.hit_enemy(p,target,melee=True,action=f'Atak bez broni {index+1}/{rules.attacks_per_round(p)}')
        p._weapon_grapple_slow=any(self._circle_target_size(q)>self._circle_target_size(p)-2 for _,q in self._style_grapples(p))
        p._weapon_grapple_hands=len(self._style_grapples(p))
        if not self.is_player_target(target) and target.hp<=0:await self.defeat(target)
        with self.db:
            self.save_player(p)
            if self.is_player_target(target):self.save_player(target)
        return result

    async def escape_weapon_grapple(self,p):
        now=self.now();grip=self.target_conditions(p).get('grappled',{})
        if grip.get('spell_id')!=GRAPPLE_ID or grip.get('until',0)<=now or p.attack_cooldown_until>now:return
        if not p.alive or environment.actions_blocked(p,now):return
        self.begin_action(p)
        skill=max(('athletics','acrobatics'),key=lambda key:skill_rules.bonus(p,key))
        ability='strength' if skill=='athletics' else 'dexterity'
        result=self.environment_ability_check(p,ability,grip['dc'],skill,action_name='Wyrwanie z chwytu')
        if result['saved']:p.buffs.pop('grappled',None)
        self.style_weapon_update()
        with self.db:self.save_player(p)
        return result

    async def cast_spell(self,p,key,enemy_id=None,target_id=None,queue=True):
        if key=='escape_grapple' and self.target_conditions(p).get('grappled',{}).get('spell_id')==GRAPPLE_ID:
            return await self.escape_weapon_grapple(p)
        return await super().cast_spell(p,key,enemy_id,target_id,queue)

    def style_weapon_begin_turn(self,p):
        token=getattr(p,'_feat_turn_until',0)
        if (not p.alive or environment.incapacitated(p,self.now()) or getattr(p,'fighting_style','')!='unarmed'
                or not fighter_rules.style_active(p,'unarmed') or getattr(p,'_unarmed_grapple_turn_until',0)==token):return
        p._unarmed_grapple_turn_until=token
        held=self._style_grapples(p)
        hand_count=sum(bool(weapons.held_item(p,slot)) for slot in ('weapon','offhand','shield'))
        main=weapons.held_item(p)
        if main.get('two_handed') or main.get('versatile_dice') and getattr(p,'weapon_grip','one')=='two':return
        held=held[:max(0,2-hand_count)]
        if not held:return
        selected=p.auto_target_id or p.auto_enemy_id
        target=next((q for _,q in held if q.id==selected),held[0][1])
        if not target.alive or target.hp<=0 or not same_floor(p,target) or _distance(p,target)>32:return
        if self.is_player_target(target) and self.pvp_error(p,target):return
        rolled=rules.roll_damage(self.combat_rng,(1,4,0))
        result=dict(rolled,check='damage',hit=True,critical=False,damage_type='bludgeoning',unarmed_grapple=True)
        if self.is_player_target(target):
            unjust=self.begin_pvp_hostility(p,target);before=target.hp+target.temp_hp
            self.damage_player(target,result['damage'],killer=p,unjust=unjust,rolled=True,damage_type='bludgeoning',source=p)
            result['damage']=max(0,before-target.hp-target.temp_hp)
        else:
            result['damage']=self.environment_damage_enemy(target,result['damage'],p,'bludgeoning')
            self.remember_attacker(target,p)
        self.report_roll(p,target,result,'Walka bez broni · chwyt',p)
        return result

    def style_weapon_update(self):
        now=self.now()
        for owner in tuple(self.players.values()):
            pairs=self._style_grapples(owner)
            held=sum(bool(weapons.held_item(owner,slot)) for slot in ('weapon','offhand','shield'))
            hands=max(0,2-held)
            main=weapons.held_item(owner)
            if main.get('two_handed') or main.get('versatile_dice') and getattr(owner,'weapon_grip','one')=='two':hands=0
            for index,(ref,target) in enumerate(pairs):
                grip=self.target_conditions(target).get('grappled',{})
                valid=(index<hands and owner.alive and not environment.incapacitated(owner,now) and not owner.form
                    and not environment.polymorph(owner) and target.alive and target.hp>0 and same_floor(owner,target)
                    and _distance(owner,target)<=32 and self.line_clear(owner,target))
                if self.is_player_target(target):valid=valid and not self.pvp_error(owner,target)
                if not valid and grip.get('owner')==owner.id:
                    self.target_conditions(target).pop('grappled',None)
            owner._weapon_grapple_slow=any(self._circle_target_size(q)>self._circle_target_size(owner)-2 for _,q in self._style_grapples(owner))
            owner._weapon_grapple_hands=len(self._style_grapples(owner))
            if owner._weapon_grapple_hands and now>=getattr(owner,'_feat_turn_until',0):
                rules.begin_feat_turn(owner,now)
                self.style_weapon_begin_turn(owner)
            for _,target in self._style_grapples(owner):
                grip=self.target_conditions(target)['grappled']
                if (target.hp>0 and not self.is_player_target(target) and now>=grip.get('escape_ready',0)
                        and target.ready<=self.time and not environment.actions_blocked(target,now)):
                    grip['escape_ready']=now+rules.ROUND_SECONDS
                    ability=max(('strength','dexterity'),key=lambda a:self.target_save_bonus(target,a))
                    result=self.environment_ability_check(target,ability,grip['dc'],'athletics' if ability=='strength' else 'acrobatics',action_name='Wyrwanie z chwytu',target=owner)
                    target.ready=max(target.ready,self.time+rules.ROUND_SECONDS)
                    target.ranged_ready=max(target.ranged_ready,self.time+rules.ROUND_SECONDS)
                    if result['saved']:self.target_conditions(target).pop('grappled',None)
            owner._weapon_grapple_slow=any(self._circle_target_size(q)>self._circle_target_size(owner)-2 for _,q in self._style_grapples(owner))
            owner._weapon_grapple_hands=len(self._style_grapples(owner))
            # Independent grapples use normal condition tracking, never a second
            # per-frame scan over the entire world creature catalogue.

    def environment_attack_flags(self,source,target):
        dis,adv=super().environment_attack_flags(source,target)
        grip=self.target_conditions(source).get('grappled',{})
        if grip.get('until',0)>self.now() and grip.get('owner')!=getattr(target,'id',None):dis=True
        return dis,adv

    def circle_note_movement(self,p,old_x,old_y):
        super().circle_note_movement(p,old_x,old_y)
        if getattr(p,'form','') or not self.is_player_target(p) or getattr(self,'_style_dragging',False):return
        dx,dy=p.x-old_x,p.y-old_y
        if abs(dx)+abs(dy)<.001:return
        self._style_dragging=True
        try:
            for _,target in self._style_grapples(p):self.environment_forced_move(target,dx,dy)
        finally:self._style_dragging=False
