"""Runtime traits of the six UI_19 SRD creatures; first Game mixin.

Critical damage callers pass ``critical=`` to environment_damage_enemy. This
keeps Undead Fortitude on the same resistance/temporary-HP path as other damage.
Grick victims use the existing, class-independent ``escape_grapple`` action.
"""
import math

try:
    from . import environment_rules as environment
except ImportError:
    import environment_rules as environment


def _immune(target,key):
    aliases={'stinking_poison':'poisoned','blind':'blinded','web_restrained':'restrained',
             'elemental_restrained':'restrained','sleep_pending':'incapacitated'}
    spec=environment.physical_form(target) if environment.polymorph(target) else environment.enemy_spec(target)
    return aliases.get(key,key) in spec.get('condition_immunities',())


class AdventureGame:
    def apply_status(self,p,target,key,duration,spec,hostile=True):
        if not self.is_player_target(target) and _immune(target,key):return False
        return super().apply_status(p,target,key,duration,spec,hostile)

    def tick_target_conditions(self,target):
        if not self.is_player_target(target):
            conditions=environment.conditions(target)
            for key in tuple(conditions):
                if _immune(target,key):conditions.pop(key,None)
        return super().tick_target_conditions(target)

    def environment_damage_enemy(self,target,amount,source=None,damage_type='bludgeoning',components=None,critical=False):
        before=target.hp
        is_zombie=environment.enemy_spec(target).get('undead_fortitude') and not environment.polymorph(target)
        radiant=any(c.get('type')=='radiant' and c.get('damage',0)>0 for c in components) if components is not None else damage_type=='radiant' and amount>0
        taken=super().environment_damage_enemy(target,amount,source,damage_type,components)
        if is_zombie and before>0 and target.hp<=0 and taken>0 and not critical and not radiant:
            # The saving throw is based on damage taken, including overkill, not
            # the HP lost. It is a Constitution save, not a fixed probability.
            result=self.target_save(target,'constitution',5+taken,dict(damage=0,damage_dice='',damage_rolls=[]),False)
            if result.get('saved'):target.hp=1
            result['undead_fortitude']=True
            owner=source if source is not None and self.is_player_target(source) else None
            self.report_roll(target,target,result,'Nieumarła wytrwałość',owner)
        return taken

    def hit_player(self,source,target,power=0,*,pvp=False,unjust=False,area=False,dice=None,damage_kind=None,spell=False,melee=None,action=None):
        spec=environment.enemy_spec(source)
        # Regional UI_20 creatures use normal AI/hazards, while their contact
        # attacks retain the weapon's actual type (arrows pass theirs explicitly).
        if not pvp and damage_kind is None and spec.get('content_version')=='UI_20':
            damage_kind=spec.get('melee_damage_type','bludgeoning')
        attacks=spec.get('adventure_attacks')
        if pvp or area or spell or dice is not None or not attacks or environment.polymorph(source):
            return super().hit_player(source,target,power,pvp=pvp,unjust=unjust,area=area,dice=dice,
                damage_kind=damage_kind,spell=spell,melee=melee,action=action)
        result=None
        for attack in attacks:
            if not target.alive or target.hp<=0 or not source.alive or source.hp<=0:break
            result=super().hit_player(source,target,power,dice=tuple(attack['dice']),damage_kind=attack['type'],
                melee=True,action=spec['name']+' · '+attack['name'])
            if result and result.get('hit') and target.alive and target.hp>0 and attack.get('grapple_dc'):
                self._adventure_grapple(source,target,attack['grapple_dc'])
        return result

    def _adventure_grapple(self,source,target,dc):
        # A grick needs all four tentacles: it can hold only one creature. Large
        # Wild Shapes/Polymorph forms are too big for this Medium-or-smaller grab.
        size=self._circle_target_size(target)
        if size>2 or _immune(target,'grappled'):return
        now=self.now();conditions=environment.conditions(target)
        ref=self.target_ref(target)
        grips=getattr(self,'_adventure_grapples',None)
        if grips is None:grips=self._adventure_grapples={}
        for other_ref,owner_id in tuple(grips.items()):
            if owner_id!=source.id or other_ref==ref:continue
            other=self.resolve_target_ref(other_ref)
            if other is not None:
                old=environment.conditions(other).get('grappled',{})
                if old.get('owner_enemy')==source.id:environment.conditions(other).pop('grappled',None)
            grips.pop(other_ref,None)
        # `hostile` in generic status expiry means an ongoing player-owned PvP
        # effect. NPC effects use a distinct owner and explicit lifetime checks.
        conditions['grappled']=dict(until=now+86400,owner=source.id,owner_enemy=source.id,dc=dc,
            reach=32,hostile=False,npc_hostile=True,spell_id='adv_grick_grapple',concentration=False)
        grips[ref]=source.id
        if hasattr(self,'clear_caster_caches') and self.is_player_target(target):self.clear_caster_caches(target)

    def tick_dnd(self,dt):
        grips=getattr(self,'_adventure_grapples',{})
        for ref,owner_id in tuple(grips.items()):
            target=self.resolve_target_ref(ref);owner=self.enemies.get(owner_id)
            grip=environment.conditions(target).get('grappled',{}) if target is not None else {}
            valid=(target is not None and target.alive and target.hp>0 and owner is not None and owner.alive and owner.hp>0
                and not environment.incapacitated(owner,self.now()) and not environment.polymorph(owner)
                and target.floor==owner.floor and math.hypot(target.x-owner.x,target.y-owner.y)<=grip.get('reach',32)
                and grip.get('owner_enemy')==owner_id and self._circle_target_size(target)<=2)
            if valid:grip['until']=self.now()+86400
            else:
                if grip.get('owner_enemy')==owner_id:environment.conditions(target).pop('grappled',None)
                grips.pop(ref,None)
        return super().tick_dnd(dt)
