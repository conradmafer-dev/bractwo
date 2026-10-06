"""Live SRD-inspired actions, persistent hotbars, pets and public leaderboard.
All costs, targets, ranges and cooldowns are checked on the authoritative server.
"""
from dataclasses import dataclass, field
from types import SimpleNamespace
try:
    from . import spell_geometry, spell_scaling, rest_rules, druid_circles, environment_rules, level_rules
    from .ranger_magic import RangerMagic
except ImportError:
    import spell_geometry, spell_scaling, rest_rules, druid_circles, environment_rules, level_rules
    from ranger_magic import RangerMagic
import math
import json
try:
    from . import combat_rules as rules, dnd_content as dnd, world_content as content
    from .progression import same_floor, train
except ImportError:
    import combat_rules as rules, dnd_content as dnd, world_content as content
    from progression import same_floor, train


def dist(a,b): return math.hypot(a.x-b.x,a.y-b.y)


@dataclass
class Companion:
    id: str
    owner_id: str
    name: str
    x: float
    y: float
    floor: int
    hp: float
    max_hp: int
    attack_bonus: int
    armor_class: int
    dice: tuple
    speed: float=140
    current_wall_time: float=0
    ready: float=0
    facing: list=field(default_factory=lambda:[0,1])
    attack_facing: list=field(default_factory=lambda:[0,1])
    buffs: dict=field(default_factory=dict)
    attack_until: float=0
    combat_until: float=0
    pvp_combat_until: float=0
    input_time: float=-10
    dx: float=0
    dy: float=0
    temp_hp: int=0
    is_companion: bool=True
    kind: str='wolf'
    form: str=''
    @property
    def alive(self): return self.hp>0
    def public(self):
        return dict(id=self.id,owner_id=self.owner_id,name=self.name,x=round(self.x,2),y=round(self.y,2),floor=self.floor,
                    hp=round(max(0,self.hp),1),max_hp=self.max_hp,alive=self.alive,kind='wolf',is_companion=True,
                    armor_class=self.armor_class,attack_bonus=self.attack_bonus,facing=self.facing,attack_until=self.attack_until,
                    wizard_phantasm=bool(getattr(self,'wizard_phantasm',False)))


class DNDGame(RangerMagic):
    def init_dnd(self):
        level_rules.migrate_database(self.db)
        self.companions={};self.spell_fields=[];self._ranking_cache=None;self._ranking_until=0
        self.db.execute('CREATE TABLE IF NOT EXISTS leaderboard(player_id INTEGER PRIMARY KEY,name TEXT NOT NULL,class_id TEXT NOT NULL,level INTEGER NOT NULL,xp INTEGER NOT NULL,kills INTEGER NOT NULL,boss_kills INTEGER NOT NULL)')
        self.db.execute('CREATE INDEX IF NOT EXISTS leaderboard_order ON leaderboard(level DESC,xp DESC,kills DESC,player_id ASC)')
        for pid,name,encoded in self.db.execute('SELECT id,name,data FROM accounts'):
            s=json.loads(encoded)
            self.db.execute('INSERT OR REPLACE INTO leaderboard VALUES(?,?,?,?,?,?,?)',(pid,name,'ranger' if s.get('class_id')=='paladin' else s.get('class_id','knight'),max(1,s.get('level',1)),max(0,s.get('xp',0)),max(0,s.get('kills',0)),max(0,s.get('boss_kills',0))))
        self.db.commit()

    def save_score(self,p):
        # SELECT prevents phantom accounts when tests/NPC helpers create transient Players.
        self.db.execute('INSERT INTO leaderboard SELECT id,?,?,?,?,?,? FROM accounts WHERE id=? ON CONFLICT(player_id) DO UPDATE SET name=excluded.name,class_id=excluded.class_id,level=excluded.level,xp=excluded.xp,kills=excluded.kills,boss_kills=excluded.boss_kills',
            (p.name,p.class_id,p.level,p.xp,p.kills,p.boss_kills,p.id))

    def ranking(self):
        now=self.now()
        if self._ranking_cache is None or now>=self._ranking_until:
            rows=self.db.execute('SELECT player_id,name,class_id,level,xp,kills,boss_kills FROM leaderboard ORDER BY level DESC,xp DESC,kills DESC,player_id ASC LIMIT 20').fetchall()
            self._ranking_cache=[dict(rank=i+1,name=r[1],class_id=r[2],level=r[3],kills=r[5],boss_kills=r[6],_pid=str(r[0])) for i,r in enumerate(rows)]
            self._ranking_until=now+5
        return {'type':'ranking','ranking':[{k:v for k,v in r.items() if k!='_pid'}|{'online':r['_pid'] in self.players and not self.players[r['_pid']].disconnected} for r in self._ranking_cache],
                'order':'level, xp, kills, creation','limit':20}

    def migrate_dnd(self,p,saved):
        old_class=p.class_id
        if p.class_id=='paladin':p.class_id='ranger'
        if p.class_id not in dnd.CLASS_SPECS:p.class_id='knight'
        for bag in (p.inventory,p.depot):
            for item in bag:
                if 'paladin' in item.get('template',''):item['template']=item['template'].replace('paladin','ranger')
        if saved.get('rules_version',0)<8:
            old={'knight':(150,18),'ranger':(115,13),'paladin':(115,13),'mage':(85,9),'druid':(100,11)}.get(old_class,(150,15))
            # Legacy values are recorded in the migration docs; preserve death and approximate health percentage.
            old_max=old[0]+(level_rules.growth_level(p)-1)*old[1]+p.mastery.get('vitality',0)*12
            p.hp=max(0,min(p.max_hp,p.max_hp*float(saved.get('hp',old_max))/max(1,old_max)))
            p.haste_until=p.bulwark_until=0;p.spell_cooldowns={};p.spell_ready=0
            # Removed Tibian runes are refunded once; no equipment UIDs or quest flags change.
            p.gold+=sum(max(0,int(n))*25 for n in p.runes.values());p.runes={}
            p.rules_version=8
        dnd.sync_hotbar(p)
        dnd.sanitize_spell_history(p)
        spell_scaling.sanitize_choices(p)
        old_mana_version = int(saved.get('mana_rules_version', 0))
        # Upgrade once directly from the saved version to the new absolute total.
        # Never fill an empty pool or rescale again on later logins. Keep spent
        # recovery/ability cooldowns, inventory, HP, XP and choices untouched.
        p.mana_rules_version = dnd.MANA_RULES_VERSION
        if old_mana_version < dnd.MANA_RULES_VERSION and 'mana' in saved:
            focus_bonus = max(0, min(20, int(p.mastery.get('focus', 0))))*4
            if old_mana_version < 1:
                old_base,old_growth={'mage':(55,2.5),'druid':(50,2),'ranger':(35,1.5),'knight':(30,1)}[p.class_id]
                old_max=int(old_base+(level_rules.growth_level(p)-1)*old_growth+p.mastery.get('focus',0)*4)
            elif old_mana_version == 1 and p.class_id == 'ranger':
                old_level=level_rules.growth_level(p)
                old_slots=dnd.FULL_CASTER_SLOTS[min(9,1+(old_level-20)//10)-1] if old_level>=20 else ()
                old_base=sum(n*dnd.MANA_COSTS[i+1] for i,n in enumerate(old_slots)) if old_slots else 35
                old_max=old_base+focus_bonus
            else:
                old_max=dnd.legacy_base_mana(p.class_id,level_rules.growth_level(p))+focus_bonus
            p.mana=max(0,min(1,float(saved['mana'])/max(1,old_max)))*p.max_mana
        p.ensnaring_armed=False
        # Forms/concentration need live world entities, so never resume orphaned effects after login/restart.
        p.form='';p.form_until=0;p.temp_hp=0;p.buffs={};p.concentration='';p.concentration_until=0;p.mark_target='';p.concentration_profile={}
        p.current_wall_time=self.now()

    async def bind_grouped_spell(self,p,slot,key):
        dnd.sync_hotbar(p)
        if not dnd.bind_grouped_hotbar(p,slot,key):
            return await self.notice(p,'Nieprawidłowy skrót lub niedostępna grupa zdolności.')
        with self.db:self.save_player(p)

    async def bind_spell(self,p,slot,key):
        if type(slot) is not int or not isinstance(key,str) or not 0<=slot<len(p.hotbar):
            return await self.notice(p,'Nieprawidłowy skrót czaru.')
        if key and not dnd.spell_allowed(p,key):
            return await self.notice(p,'Na pasek możesz przypisać tylko odblokowany czar swojej klasy.')
        if key and key in p.hotbar:
            other=p.hotbar.index(key)
            p.hotbar[other],p.hotbar[slot]=p.hotbar[slot],key
        else:p.hotbar[slot]=key
        dnd.sync_hotbar(p)
        with self.db:self.save_player(p)

    def spend_mana(self,p,amount):
        p.mana=max(0,p.mana-amount)
        if amount>0:p.mana_recovery_until=self.now()+dnd.MANA_RECOVERY_DELAY

    def stop_auto(self,p):
        p.auto_enemy_id='';p.auto_target_id='';p.auto_enabled=False;p.pending_spell={}

    async def select_combat_target(self,p,data):
        enemy_id,target_id=data.get('enemy_id',''),data.get('target_id','')
        if not isinstance(enemy_id,str) or not isinstance(target_id,str) or (enemy_id and target_id):return await self.notice(p,'Wybierz jeden cel.')
        if not enemy_id and not target_id:self.stop_auto(p);return
        target=self.enemies.get(enemy_id) if enemy_id else self.players.get(target_id)
        if not p.alive or target is None or not target.alive or not same_floor(p,target) or dist(p,target)>1800:
            self.stop_auto(p);return await self.notice(p,'Cel jest niedostępny.')
        # Friendly targeting remains usable for healing; it never silently disables PvP safety.
        changed=(p.auto_enemy_id,p.auto_target_id)!=(enemy_id,target_id)
        p.auto_enemy_id=enemy_id;p.auto_target_id=target_id
        p.auto_enabled=bool(enemy_id or not self.pvp_error(p,target))
        # Reselecting the same creature must not erase an accepted spell request.
        # A genuinely different target still cancels it: never transfer a queued
        # hostile spell silently to a new monster or player.
        if changed:p.pending_spell={}

    async def process_player_actions(self):
        for p in tuple(self.players.values()):
            p.current_wall_time=self.now()
            if not p.alive or p.disconnected:self.stop_auto(p);continue
            if p.pending_spell and p.pending_spell.get('until',0)<self.now():
                p.pending_spell={}
            if p.pending_spell and self.now()>=p.attack_cooldown_until:
                pending=p.pending_spell;p.pending_spell={}
                if pending.get('until',0)>=self.now():await self.cast_spell(p,pending['spell'],pending.get('enemy'),pending.get('target'),queue=False)
            if not p.auto_enabled or self.now()<p.attack_cooldown_until:continue
            target=self.enemies.get(p.auto_enemy_id) if p.auto_enemy_id else self.players.get(p.auto_target_id)
            if target is None or not target.alive or not same_floor(p,target) or dist(p,target)>1800:
                self.stop_auto(p);continue
            if p.auto_target_id and self.pvp_error(p,target):p.auto_enabled=False;continue
            if not rules.weapon_autoattack(p):continue
            if not self.in_safe(p) and dist(p,target)<=rules.attack_range(p) and self.line_clear(p,target):
                await self.dnd_attack(p,p.auto_target_id or None,p.auto_enemy_id or None,quiet=True)
        touched={e.id:e for p in self.players.values() for e in self.nearby_enemies(p,1800)}
        touched.update(self.chasing_enemies)
        for e in touched.values():
            if e.alive and e.hp<=0:await self.defeat(e)

    async def dnd_attack(self,p,target_id=None,enemy_id=None,quiet=False,surge=False):
        p.current_wall_time=self.now()
        if not p.alive or (not surge and self.now()<p.attack_cooldown_until):return
        if rules.weapon_actions.mode(p)=='throw' and rules.weapon_actions.throw_error(p):
            if not quiet:await self.notice(p,rules.weapon_actions.throw_error(p))
            return
        # The input/WebSocket handler can run just before the simulation tick.
        # A held Space or repeated attack packet must not steal the queued spell's
        # newly available main action. Expired commands never lock attacks forever.
        if p.pending_spell and not surge:
            if p.pending_spell.get('until',0)>=self.now():return
            p.pending_spell={}
        if surge and (p.class_id!='knight' or p.level<2 or p.form):return
        if surge and (rest_rules.remaining(p,'action_surge')<1 or p.rest_resources.get('surge_turn_until',0)>self.now()):
            return await self.notice(p,'Zryw akcji: brak użyć albo wykorzystano go już w tej turze. Użycia odnawia odpoczynek.')
        if target_id is not None and enemy_id is not None:return
        if target_id is None and enemy_id is None:
            target_id=p.auto_target_id or None;enemy_id=p.auto_enemy_id or None
        target=self.players.get(str(target_id)) if target_id is not None else self.selected_enemy(p,enemy_id,rules.attack_range(p)) if enemy_id else None
        if target_id is not None:
            reason=self.pvp_error(p,target)
            if reason:
                if not quiet:await self.notice(p,reason)
                return
        elif self.in_safe(p):return
        elif target is None and enemy_id is None:
            candidates=[e for e in self.nearby_enemies(p,rules.attack_range(p)) if e.alive and e.hp>0 and same_floor(p,e) and dist(p,e)<=rules.attack_range(p) and self.line_clear(p,e)]
            target=min(candidates,key=lambda e:dist(p,e)) if candidates else None
        if target is None or not target.alive or not same_floor(p,target) or dist(p,target)>rules.attack_range(p) or not self.line_clear(p,target):
            if not quiet and (enemy_id or target_id):await self.notice(p,'Cel jest poza zasięgiem albo za przeszkodą.')
            return
        if surge:
            rest_rules.spend(p,'action_surge')
            p.rest_resources['surge_turn_until']=max(self.now()+rules.ROUND_SECONDS,getattr(p,'_feat_turn_until',0))
            p.attack_until=self.time+.3
            dnd.record_spell_use(p,'action_surge')
            self.fighter_effect(p,target,'surge')
        else:self.begin_action(p)
        self.tag(p,bool(target_id));train(p,'melee' if rules.gear.melee(p) and not rules.weapon_actions.is_thrown(p) else 'magic' if rules.gear.is_focus(rules.gear.weapon(p)) else 'distance')
        unjust=self.begin_pvp_hostility(p,target) if target_id else False
        action_name = 'Zryw akcji' if surge else 'Iskra różdżki' if rules.gear.is_focus(rules.gear.weapon(p)) else 'Atak'
        touched={}
        for i in range(rules.attacks_per_round(p)):
            if not p.alive or p.hp<=0 or target.hp<=0:break
            chosen=self.circle_beast_target(p,target,i)
            if chosen is None or chosen.hp<=0:continue
            item=rules.weapon_actions.current_weapon(p)
            throwing=rules.weapon_actions.is_thrown(p)
            if rules.weapon_actions.mode(p)=='throw' and rules.weapon_actions.throw_error(p,item):break
            rules.weapon_actions.record_light_attack(p,item,self.now())
            touched[chosen.id]=chosen
            p.form_attack_index=i
            self.basic_effect(p,chosen)
            if self.is_player_target(chosen):result=self.hit_player(p,chosen,pvp=True,unjust=unjust,action=action_name,melee=rules.gear.melee(p) and not throwing)
            else:result=self.hit_enemy(p,chosen,action=action_name if p.class_id=='mage' or surge else f'Atak {i+1}/{rules.attacks_per_round(p)}',melee=rules.gear.melee(p) and not throwing)
            self.trigger_ensnaring_strike(p,chosen,result)
            self.fighter_on_weapon_hit(p,chosen,result)
            self.beast_on_hit(p,chosen,result)
            if throwing:rules.weapon_actions.throw_weapon(p,chosen,item)
            if result is not None and not throwing:
                extra=self.martial_horde_breaker(p,chosen)
                if extra is not None:touched[extra.id]=extra
        p.form_attack_index=0
        for victim in touched.values():
            if not self.is_player_target(victim) and victim.hp<=0:await self.defeat(victim)
        with self.db:self.save_player(p)

    def is_player_target(self, target):
        return target is not None and self.players.get(target.id) is target

    def target_ref(self, target):
        return ('p:' if self.is_player_target(target) else 'e:') + target.id

    def resolve_target_ref(self, ref):
        if ref.startswith('p:'):return self.players.get(ref[2:])
        if ref.startswith('e:'):return self.enemies.get(ref[2:])
        return self.enemies.get(ref)  # live compatibility with pre-0.8.1 enemy references

    def target_conditions(self, target):
        return environment_rules.conditions(target)

    def target_condition(self, target, key):
        return environment_rules.active(target,key,self.now())

    def target_save_bonus(self, target, ability):
        return rules.save_bonus(target, ability) if self.is_player_target(target) else environment_rules.enemy_spec(target).get('saves',{}).get(ability,0)

    def spell_target_save(self, source, target, ability, dc, damage, half=False):
        previous=getattr(self,'_wizard_spell_source',None)
        self._wizard_spell_source=source
        try:return self.target_save(target,ability,dc,damage,half)
        finally:self._wizard_spell_source=previous

    def target_save(self, target, ability, dc, damage, half=False):
        return rules.roll_save(self.combat_rng, self.target_save_bonus(target, ability), dc, damage, half,
            advantage=self.is_player_target(target) and self.target_condition(target, 'foresight'),
            disadvantage=(ability == 'dexterity' and self.target_condition(target, 'restrained')) or (self.is_player_target(target) and ability in ('strength','dexterity') and rules.gear.armor_penalty(target)))

    def begin_pvp_hostility(self, p, target):
        """Call only after pvp_error/range validation. Even resisted spells are aggression."""
        now = self.now()
        unjust = target.skull(now) == 'none' and p.aggressors.get(target.id, 0) <= now
        self.tag(p, True);self.tag(target, True)
        if unjust:
            p.white_until = max(p.white_until, now + 120)
            target.aggressors[p.id] = now + 120
        return unjust

    def record_pvp_effect(self, p, target, unjust):
        # Successful control counts too: pushing/rooting someone into monsters is not a loophole.
        target.last_pvp_attacker = p.id
        target.last_pvp_unjust = bool(unjust)
        target.last_pvp_hit_until = self.now() + 20

    def friendly_target_error(self, p, target, range_):
        if target is None or not target.alive or target.disconnected or not same_floor(p, target) or dist(p, target) > range_ or not self.line_clear(p, target):
            return 'Wskaż żywego członka drużyny w zasięgu i na tym samym piętrze.'
        if target.id == p.id:return ''
        if not p.party_id or p.party_id != target.party_id:
            return 'Czary wspierające działają na ciebie lub członka twojej drużyny.'
        if max(p.pvp_combat_until, target.pvp_combat_until) > self.now():
            if p.pvp_safety:return 'Wsparcie w walce PvP wymaga wyłączenia blokady PvP u rzucającego.'
            if min(p.level, target.level) < 2 or self.in_safe(p) or self.in_safe(target):
                return 'Nie można wspierać walki PvP ze strefy bezpiecznej ani z ochroną początkującego.'
        return ''

    def join_pvp_support(self, p, target):
        if target.id == p.id or max(p.pvp_combat_until, target.pvp_combat_until) <= self.now():return
        now = self.now()
        self.tag(p, True);self.tag(target, True)
        if target.skull(now) != 'none':p.white_until = max(p.white_until, now + 120)
        # Give active opponents the right to defend themselves against combat support.
        for q in self.players.values():
            if q.id in (p.id, target.id) or q.party_id and q.party_id == p.party_id:continue
            fighting = (target.aggressors.get(q.id, 0) > now or q.aggressors.get(target.id, 0) > now
                or target.last_pvp_attacker == q.id and target.last_pvp_hit_until > now
                or q.last_pvp_attacker == target.id and q.last_pvp_hit_until > now)
            if fighting:
                q.aggressors[p.id] = now + 120
                if target.aggressors.get(q.id, 0) > now:p.aggressors[q.id] = now + 120

    def cancel_player_hostility(self, p):
        """Relocking stops harmful ongoing PvP, but does not erase combat timers/crimes."""
        if p.auto_target_id:p.auto_enabled = False
        if p.pending_spell.get('target'):p.pending_spell = {}
        for q in self.players.values():
            q.buffs = {k:v for k,v in q.buffs.items() if not (v.get('hostile') and v.get('owner') == p.id)}
        if (getattr(p, 'mark_target_kind', 'enemy') == 'player' or
                p.concentration=='ensnaring_strike' and any(ref.startswith('p:') for ref in p.condition_targets)):
            self.break_concentration(p)

    def enemy_condition(self,e,key):
        return e.conditions.get(key,{}).get('until',0)>self.now()

    def break_concentration(self, p):
        p.concentration = '';p.concentration_until = 0;p.mark_target = '';p.mark_target_kind = 'enemy'
        p.concentration_profile = {};p._spell_profiles_cache = None
        # A hostile caster losing concentration must not cancel someone else's buffs on them.
        p.buffs = {k:v for k,v in p.buffs.items() if not (v.get('concentration') and v.get('owner', p.id) == p.id)}
        for f in self.spell_fields:
            if f['owner']==p.id and f['concentration']:self.end_field_effect(f)
        self.spell_fields = [f for f in self.spell_fields if not (f['owner'] == p.id and f['concentration'])]
        retained = []
        for ref in tuple(p.condition_targets):
            target = self.resolve_target_ref(ref)
            if target is None:continue
            conditions = self.target_conditions(target)
            for key, value in tuple(conditions.items()):
                if value.get('owner') == p.id and value.get('concentration'):conditions.pop(key, None)
            if any(v.get('owner') == p.id for v in conditions.values()):retained.append(ref)
        p.condition_targets = retained

    def concentration_damage(self,p,damage):
        if damage<=0 or p.concentration_until<=self.now():return
        dc=max(10,math.floor(damage/2));roll=self.combat_rng.randint(1,20);bonus=rules.save_bonus(p,'constitution')
        result=dict(check='concentration',roll=roll,rolls=[roll],bonus=bonus,total=roll+bonus,defense=dc,saved=roll+bonus>=dc,hit=False,damage=0,damage_dice='')
        self.report_roll(p,p,result,'Koncentracja',p)
        if roll+bonus<dc:self.break_concentration(p)

    def shield_reaction(self,p,result):
        if result['hit'] and not result['critical'] and result.get('roll')!=20 and p.shield_armed and dnd.spell_allowed(p,'shield') and p.mana>=dnd.SPELLS['shield']['mana'] and p.reaction_ready<=self.now() and not p.form and not rules.gear.armor_penalty(p) and not rules.active_buff(p,'no_reactions'):
            if result['total']<p.armor_class+5:
                self.spend_mana(p,dnd.SPELLS['shield']['mana']);p.buffs['shield']={'until':self.now()+3,'spell_id':'shield'};p.reaction_ready=self.now()+3
                result.update(hit=False,damage=0,shielded=True,defense=p.armor_class)
                dnd.record_spell_use(p,'shield');self.spell_effect(p,'shield',p)
                self.wizard_after_paid_spell(p,'shield',dnd.SPELLS['shield'])

    def shield_blocks_missiles(self, target):
        target.current_wall_time = self.now()
        if rules.active_buff(target, 'shield'):return True
        if (target.shield_armed and dnd.spell_allowed(target, 'shield') and target.mana >= dnd.SPELLS['shield']['mana']
                and target.reaction_ready <= self.now() and not target.form and not rules.gear.armor_penalty(target) and not rules.active_buff(target, 'no_reactions')):
            self.spend_mana(target,dnd.SPELLS['shield']['mana']);target.buffs['shield'] = {'until':self.now()+3,'spell_id':'shield'}
            target.reaction_ready = self.now()+3
            dnd.record_spell_use(target,'shield');self.spell_effect(target,'shield',target)
            self.wizard_after_paid_spell(target,'shield',dnd.SPELLS['shield'])
            return True
        return False

    def apply_status(self, p, target, key, duration, spec, hostile=True):
        if rules.magic_items.reduces_magic_condition(target,key,{'spell_id':spec.get('id',''),'magical':spec.get('magical',False)}):return False
        if self.is_player_target(target):
            if hostile and self.pvp_error(p, target):return False
            if key in ('restrained', 'slow', 'growth') and self.target_condition(target, 'freedom'):return False
        conditions = self.target_conditions(target)
        conditions[key] = {'until':self.now()+duration, 'owner':p.id, 'hostile':hostile,
            'spell_id':spec.get('id',''), 'concentration':bool(spec.get('concentration')), 'save':spec.get('save', 'strength'),
            'dc':rules.spell_dc(p), 'retry':self.now()+3}
        ref = self.target_ref(target)
        if ref not in p.condition_targets:p.condition_targets.append(ref)
        return True

    def spell_effect(self,p,key,target=None,targets=None,duration=None,area=None,spec=None,phase='cast',visual_only=False):
        s=spec if spec is not None else spell_scaling.resolve(p,key);target=target or p
        source=SimpleNamespace(id=p.id,x=p.x,y=p.y,floor=p.floor) if visual_only else p
        event=self.combat_effect(source,'spell',target,radius=s.get('radius',0),duration=duration or (.9 if s.get('area') else .72))
        event.update(spell_id=key,visual=s['visual'],shots=s.get('shots',1),cast_circle=s.get('cast_circle',s['circle']),
            phase=phase,cast_origin=[p.x,p.y],started_at=self.time,
            source=dict(id=p.id,x=p.x,y=p.y,floor=p.floor),
            targets=[dict(id=t.id,x=t.x,y=t.y,player=self.is_player_target(t)) for t in (targets if targets is not None else [target])])
        if s.get('area') or s.get('party'):
            event['area']=area or spell_geometry.build(s,p,target)
        elif area is not None:event['area']=area
        return event

    def _record_field_damage(self,p,target,s,impacts):
        """Attach rendering evidence to the existing damage resolution, once."""
        point=dict(id=target.id,x=target.x,y=target.y,player=self.is_player_target(target))
        result=self.spell_damage(p,target,s)
        if result is not None:
            point.update(damage=result.get('damage',0),hit=result.get('hit',False),
                saved=result.get('saved',False),damage_type=s.get('damage_type','force'))
            impacts.append(point)
        return result

    def _field_visual_area(self,f,s):
        center=SimpleNamespace(id='',x=f['x'],y=f['y'],floor=f['floor'],facing=f.get('direction',[0,1]))
        spec=dict(s,range=s.get('length',s['range']))
        if spec.get('shape')=='square':spec['width']=2*f['radius']
        target=center
        if f.get('direction'):
            dx,dy=f['direction'];target=SimpleNamespace(x=center.x+dx*spec['range'],y=center.y+dy*spec['range'])
            spec['width']=2*f['radius']
        return spell_geometry.build(spec,center,target)

    def _field_tick_effect(self,p,f,s,impacts):
        if not impacts:return None
        # One field activation may resolve against several creatures. Represent
        # it once; movement-triggered repeats remain explicit in impacts.
        center=SimpleNamespace(id=p.id,x=f['x'],y=f['y'],floor=f['floor'],facing=f.get('direction',[0,1]))
        point=SimpleNamespace(id='',x=f['x'],y=f['y'],floor=f['floor'])
        event=self.spell_effect(center,s['id'],point,[],duration=.72,
            area=self._field_visual_area(f,s),spec=s,phase='tick',visual_only=True)
        unique={entry['id']:entry for entry in impacts}
        event.update(targets=list(unique.values()),impacts=impacts,field_id=f.get('effect_id',f.get('id','')),
            cast_origin=list(f.get('cast_origin',[p.x,p.y])),field_started_at=f.get('visual_started_at',self.time),
            source=dict(id=p.id,x=p.x,y=p.y,floor=p.floor),field_origin=[f['x'],f['y']])
        return event

    def spell_targets(self, p, s, enemy_id=None, target_id=None):
        r = s['range']
        target = self.players.get(target_id) if target_id else self.selected_enemy(p, enemy_id, r) if enemy_id else None
        if target_id:
            if self.pvp_error(p, target) or not same_floor(p, target) or dist(p, target) > r or not self.line_clear(p, target):return []
        elif enemy_id and target is None:return []
        if target is None:
            # Never acquire a random player when no explicit target was selected.
            options = [e for e in self.nearby_enemies(p,r) if e.alive and e.hp>0 and same_floor(p,e) and dist(p,e)<=r and self.line_clear(p,e)]
            target = min(options, key=lambda e:dist(p,e)) if options else None
        if target is None:return []
        if not s.get('area'):return [target]
        area=spell_geometry.build(s,p,target)
        query=spell_geometry.query_radius(area,p)
        if s.get('shape')=='chain':query=r+s['radius']
        candidates=list(self.nearby_enemies(p,query))
        if not p.pvp_safety:candidates+=list(self.players.values())
        targets=[]
        for e in candidates:
            if not e.alive or e.hp<=0 or not same_floor(p,e):continue
            if self.is_player_target(e) and self.pvp_error(p,e):continue
            if s.get('shape')=='chain':inside=dist(e,target)<=s['radius']
            else:inside=spell_geometry.contains(area,e.x,e.y)
            origin=p if s.get('shape') in ('cone','line') else target
            if inside and self.line_clear(origin,e) and self.line_clear(p,e):targets.append(e)
        targets.sort(key=lambda e:(e is not target,dist(e,target)))
        return targets[:s.get('max_targets',200)]

    def spell_damage(self, p, target, s):
        previous=getattr(p,'_wizard_damage_spec',None)
        p._wizard_damage_spec=s
        try:return self._spell_damage_resolved(p,target,s)
        finally:p._wizard_damage_spec=previous

    def _spell_damage_resolved(self, p, target, s):
        player_target = self.is_player_target(target)
        if player_target and target.id in s.get('_wizard_protected',()):return None
        if not target.alive or target.hp<=0:return None
        if player_target:
            if self.pvp_error(p, target) or not same_floor(p, target):return None
            target.current_wall_time = self.now()
            unjust = self.begin_pvp_hostility(p, target)
        else:unjust = False
        creature_type = 'humanoid' if player_target else content.ENEMIES[target.kind]['creature_type']
        if creature_type in s.get('exclude_types', []):
            self.report_roll(p,target,dict(check='automatic',damage=0,hit=False,immune=True,damage_dice=''),s['name'],p);return None
        if not s.get('resolved'):
            s = spell_scaling.resolve(p, s['id'])
        dice = list(s['dice'])
        if s['kind'] == 'attack':
            if player_target:
                result = self.hit_player(p, target, pvp=True, unjust=unjust, dice=dice, spell=True,
                    melee=s.get('melee',False), damage_kind=s['damage_type'], action=s['name'])
            else:
                result = self.hit_enemy(p,target,dice=dice,spell=True,melee=s.get('melee',False),damage_kind=s['damage_type'],action=s['name'])
        else:
            damage = self.wizard_spell_roll_damage(p,s,dice)
            components = [{'type':s.get('damage_type','force'), 'damage':damage['damage']}]
            if s.get('extra_dice'):
                extra = self.wizard_spell_roll_damage(p,s,s['extra_dice'],empower=False)
                components.append({'type':s['extra_type'], 'damage':extra['damage']})
                damage['damage'] += extra['damage'];damage['damage_dice'] += ' + '+extra['damage_dice'];damage['extra_rolls'] = extra['damage_rolls']
                rules.record_damage_roll(damage, extra, 'Dodatkowe obrażenia')
            if s.get('save'):
                result = self.spell_target_save(p,target,s['save'],rules.spell_dc(p),damage,s.get('save_half',False))
                result['save_ability'] = s['save']
                if result['saved']:
                    potent=self.wizard_potent_cantrip(p,s)
                    components = [dict(c, damage=c['damage']//2 if s.get('save_half') or potent else 0) for c in components]
                    if potent:result['potent_cantrip']=True
                    result['damage'] = sum(c['damage'] for c in components)
            else:result = dict(check='automatic',hit=True,**damage)
            result['damage_type'] = s.get('damage_type','force')
            result['is_spell'] = True
            if player_target:
                if s['kind']=='missiles' and self.shield_blocks_missiles(target):
                    result.update(hit=False,damage=0,shielded=True);components=[]
                result['damage_components'] = components
                self.resolve_player_hit(p,target,result,s['name'],owner=p,unjust=unjust)
            else:
                result['damage']=self.environment_damage_enemy(target,result['damage'],p,result['damage_type'],components,critical=result.get('critical',False));self.remember_attacker(target,p)
                self.report_roll(p,target,result,s['name'],p)
        if result and target.alive and result.get('hit') and not result.get('potent_cantrip') and (result.get('damage',0)>0 or not result.get('saved')):
            applied = False
            for key in ('slow','no_reactions','glow'):
                if s.get(key):applied = self.apply_status(p,target,key,s[key],s) or applied
            if s.get('blind') and not result.get('saved',False):applied = self.apply_status(p,target,'blind',s['blind'],s) or applied
            pullable = player_target or not content.ENEMIES[target.kind].get('boss') and content.ENEMIES[target.kind].get('size',1)<=1.5
            if s.get('pull') and pullable:
                length = dist(p,target)
                if length>45:
                    amount=min(s['pull'],length-45)
                    self.move(target,(p.x-target.x)/length*amount,(p.y-target.y)/length*amount)
                    applied=True
            if applied and player_target:self.record_pvp_effect(p,target,unjust)
        return result

    async def cast_spell(self,p,key,enemy_id=None,target_id=None,queue=True):
        if enemy_id is not None and not isinstance(enemy_id,str) or target_id is not None and not isinstance(target_id,str):
            return await self.notice(p,'Nieprawidłowy cel czaru.')
        if enemy_id and target_id:return await self.notice(p,'Wybierz jeden cel czaru.')
        p.current_wall_time=now=self.now()
        s=dnd.SPELLS.get(key) if isinstance(key,str) else None
        if not p.alive or s is None:return
        if not dnd.spell_allowed(p,key):return await self.notice(p,f'{s["name"]}: wymaga właściwej klasy i poziomu {dnd.spell_level(s,p.class_id)}.')
        s=spell_scaling.resolve(p,key)
        if s['kind']=='reaction':
            p.shield_armed=not p.shield_armed
            with self.db:self.save_player(p)
            return await self.notice(p,'Tarcza: automatyczna reakcja włączona.' if p.shield_armed else 'Tarcza: reakcja wyłączona.')
        if s['kind']=='shape' and p.form:
            p.form='';p.form_until=0;p.temp_hp=0;return
        if p.form and not (druid_circles.circle(p)=='moon' and key in druid_circles.bonus_spells(p)):
            return await self.notice(p,'W tej przemianie nie możesz rzucić tego czaru.')
        if s['kind']=='surge':return await self.dnd_attack(p,target_id,enemy_id,surge=True)
        if s['kind']=='weapon_trigger':return await self.toggle_ensnaring_strike(p,s)
        offensive=s['kind'] in ('attack','save','missiles','mark','control','field')
        if offensive and not enemy_id and not target_id:
            enemy_id=p.auto_enemy_id or None;target_id=p.auto_target_id or None
        bonus=s['action']=='bonus';ready=p.bonus_cooldown_until if bonus else p.attack_cooldown_until
        if now<ready:
            if queue and not bonus:
                p.pending_spell={'spell':key,'enemy':enemy_id,'target':target_id,'until':now+4}
            return
        if now<p.spell_cooldowns.get(key,0):return
        recast=s.get('recast') and p.concentration==key and p.concentration_until>now
        mana,free_key=self.circle_spell_cost(p,s,recast)
        if key in ('second_wind','animal_companion') and rest_rules.remaining(p,key)<1:
            return await self.notice(p,'Brak użyć tej zdolności. Potrzebujesz odpoczynku.')
        if p.mana<mana:return await self.notice(p,f'Potrzebujesz {mana} many. Możesz wybrać niższy krąg w karcie czarów. Sztuczki są darmowe.')
        if p.gold<s.get('gold',0):return await self.notice(p,'Potrzebujesz 100 złota na składnik Kamiennej skóry.')
        targets=[];friends=[p]
        if offensive:
            if not enemy_id and not target_id:
                enemy_id=p.auto_enemy_id or None;target_id=p.auto_target_id or None
            if target_id:
                reason=self.pvp_error(p,self.players.get(target_id))
                if reason:return await self.notice(p,reason)
            targets=self.spell_targets(p,s,enemy_id,target_id)
            if self.in_safe(p) or not targets:return await self.notice(p,'Wskaż przeciwnika w zasięgu, na tym samym piętrze i poza strefą bezpieczną.')
        if s['kind'] in ('heal','buff'):
            if s.get('targeting')=='self':
                if target_id and target_id!=p.id:return await self.notice(p,'Ta zdolność działa wyłącznie na ciebie.')
            else:
                anchor=self.players.get(target_id) if target_id else p
                reason=self.friendly_target_error(p,anchor,s['range'])
                if reason:return await self.notice(p,reason)
                if s.get('party'):
                    candidates=sorted(self.players.values(),key=lambda q:(q.id!=p.id,q.hp>=q.max_hp,dist(q,anchor)))
                    friends=[q for q in candidates if same_floor(anchor,q) and dist(anchor,q)<=s['radius'] and self.line_clear(anchor,q)
                        and not self.friendly_target_error(p,q,s['range']+s['radius'])][:6]
                elif s.get('ally_targets',1)>1:
                    # Chosen ally first, then self and nearest consenting party members.
                    # Every target must independently be in touch range of the caster.
                    candidates=sorted(self.players.values(),key=lambda q:(q is not anchor,q is not p,dist(p,q),q.id))
                    friends=[q for q in candidates if not self.friendly_target_error(p,q,s['range'])][:s['ally_targets']]
                else:friends=[anchor]
            if s['kind']=='heal' and all(q.hp>=q.max_hp for q in friends):return await self.notice(p,'Brak brakującego zdrowia do uleczenia.')
        if s['kind']=='companion' and p.id in self.companions and self.companions[p.id].alive:return await self.notice(p,'Twój towarzysz jest już przy tobie.')
        if s.get('buff')=='mage_armor':
            armor=next((content.ITEMS[i['template']] for i in friends[0].inventory if i['uid']==friends[0].equipment.get('armor')), {})
            if armor.get('armor_kind','none')!='none':return await self.notice(p,'Cel musi zdjąć zbroję, aby otrzymać Zbroję maga.')
        dest=None
        if s['kind']=='teleport':
            dx,dy=p.facing;length=math.hypot(dx,dy) or 1
            for n in range(192,24,-8):
                point=SimpleNamespace(x=p.x+dx/length*n,y=p.y+dy/length*n,floor=p.floor)
                if not self.blocked(point.x,point.y,floor=p.floor) and self.line_clear(p,point) and not (p.pvp_combat_until>now and self.in_safe(point)):
                    dest=point;break
            if dest is None:return await self.notice(p,'Nie ma widocznego, wolnego miejsca na teleport.')
        self.wizard_prepare_spell(p,s,targets,target_id,mana)
        dnd.record_spell_use(p,key)
        # A new immediate main spell replaces an older queued main spell. Bonus
        # actions (e.g. Recovery) and reactions intentionally keep the queue.
        if not bonus:p.pending_spell={}
        self.begin_action(p,bonus);self.spend_mana(p,mana);p.gold-=s.get('gold',0);p.spell_cooldowns[key]=now+s['cooldown'];train(p,'magic',max(1,mana))
        self.circle_commit_spell(p,s,free_key)
        if mana>0:self.wizard_after_paid_spell(p,key,s)
        if key in ('second_wind','animal_companion'):rest_rules.spend(p,key)
        if s.get('concentration') and not recast:
            self.break_concentration(p);p.concentration=key;p.concentration_until=now+s['duration']
            p.concentration_profile=s
        if offensive:self.tag(p)
        if s['kind']=='buff':
            for q in friends:
                self.join_pvp_support(p,q)
                self.apply_status(p,q,s['buff'],s['duration'],s,hostile=False)
                if s['buff']=='freedom':
                    for status in ('restrained','slow','growth'):q.buffs.pop(status,None)
                self.spell_effect(p,key,q,spec=s)
        elif s['kind']=='heal':
            if s.get('flat_heal'):heal=dict(damage=s['flat_heal'],damage_dice=str(s['flat_heal']),damage_rolls=[])
            else:
                dice=list(s['dice'])
                heal=rules.roll_damage(self.combat_rng,dice)
            for q in friends:
                restored=min(q.max_hp-q.hp,heal['damage'])
                if restored<=0:continue
                self.join_pvp_support(p,q);q.hp+=restored
                self.spell_effect(p,key,q,spec=s)
                self.report_roll(p,q,dict(heal,check='healing',hit=True,healing=restored,damage=0),s['name'],p)
            self.circle_after_heal(p,s,friends,mana)
        elif s['kind']=='mark':
            target=targets[0];p.mark_target=target.id;p.mark_target_kind='player' if self.is_player_target(target) else 'enemy'
            if self.is_player_target(target):
                unjust=self.begin_pvp_hostility(p,target);self.record_pvp_effect(p,target,unjust)
            else:self.remember_attacker(target,p)
            self.apply_status(p,target,'hunters_mark:'+p.id,s['duration'],s)
            self.spell_effect(p,key,target,spec=s)
        elif s['kind']=='control':
            for target in targets:
                unjust=self.begin_pvp_hostility(p,target) if self.is_player_target(target) else False
                result=self.spell_target_save(p,target,s['save'],rules.spell_dc(p),dict(damage=0,damage_dice='',damage_rolls=[]),False)
                result['save_ability']=s['save']
                if not result['saved']:
                    applied=self.apply_status(p,target,s['buff'],s['duration'],s)
                    if applied and self.is_player_target(target):self.record_pvp_effect(p,target,unjust)
                if not self.is_player_target(target):self.remember_attacker(target,p)
                self.report_roll(p,target,result,s['name'],p)
            self.spell_effect(p,key,targets[0],targets,spec=s)
        elif s['kind']=='field':
            target=targets[0]
            for q in targets:
                if self.is_player_target(q) and q.id not in s.get('_wizard_protected',()):self.begin_pvp_hostility(p,q)
            field_effect=self.spell_effect(p,key,target,targets,duration=s['duration'],spec=s,phase='field')
            field_effect.update(persistent=True,field_id=field_effect['id'])
            self.spell_fields.append(dict(effect_id=field_effect['id'],owner=p.id,key=key,x=target.x,y=target.y,floor=p.floor,until=now+s['duration'],next=now,
                concentration=bool(s.get('concentration')),positions={},radius=s['radius'],profile=s,
                cast_origin=[p.x,p.y],visual_started_at=self.time))

        elif s['kind']=='teleport':
            self.spell_effect(p,key,SimpleNamespace(id=p.id,x=dest.x,y=dest.y,floor=p.floor),spec=s)
            p.x,p.y=dest.x,dest.y
        elif s['kind']=='shape':
            p.form=s['form'];p.form_until=now+s['duration'];p.temp_hp=(rules.effective_level(p)*2 if p.form=='wolf' else rules.effective_level(p)*3)
            p.spell_cooldowns['wild_shape_wolf']=p.spell_cooldowns['wild_shape_bear']=now+60
            self.spell_effect(p,key,p,spec=s)
        elif s['kind']=='companion':
            level=rules.effective_level(p);pet=Companion('pet_'+p.id,p.id,'Wilk · '+p.name,p.x,p.y,p.floor,5+5*level,5+5*level, rules.proficiency(p)+rules.ability_modifier(p,'wisdom'),13+rules.proficiency(p), (1,8,rules.proficiency(p)))
            pet.current_wall_time=now;self.companions[p.id]=pet
            self.spell_effect(p,key,p,spec=s)
        else:
            self.spell_effect(p,key,targets[0],targets,spec=s,phase='recast' if recast else 'cast')
            for e in targets:
                for shot in range(s.get('shots',1)):
                    if e.hp<=0:break
                    self.spell_damage(p,e,s)
            for e in targets:
                if e.hp<=0 and not self.is_player_target(e):await self.defeat(e)
        self.wizard_finish_spell(p,s)
        with self.db:
            self.save_player(p)
            for q in friends:
                if q is not p:self.save_player(q)
            for q in targets:
                if self.is_player_target(q):self.save_player(q)

    def tick_target_conditions(self, target):
        self.ranger_tick_protection(target)
        now=self.now();conditions=self.target_conditions(target)
        for key,value in tuple(conditions.items()):
            owner=self.players.get(value.get('owner'))
            if value.get('spell_id')=='ensnaring_strike':
                self.tick_ensnaring_strike(target,key,value,owner)
                continue
            invalid=value.get('until',0)<=now or not target.alive
            if self.is_player_target(target) and value.get('hostile'):
                invalid=invalid or owner is None or bool(self.pvp_error(owner,target)) or not same_floor(owner,target)
            if invalid:conditions.pop(key,None)
            elif value.get('hostile') and key in ('restrained','blind') and value.get('retry',float('inf'))<=now:
                value['retry']=now+3
                result=self.spell_target_save(owner,target,value['save'],value['dc'],dict(damage=0,damage_dice='',damage_rolls=[]))
                if result['saved']:conditions.pop(key,None)

    def end_field_effect(self,field):
        for effect in self.effects:
            if effect['id']==field.get('effect_id'):
                effect['duration']=max(0,self.time-effect['time'])
                effect['ended']=True

    def tick_dnd(self,dt):
        self.style_weapon_update()
        now=self.now()
        for p in tuple(self.players.values()):p.current_wall_time=now
        for p in tuple(self.players.values()):
            if not p.alive:p.ensnaring_armed=False
            if p.concentration and (not p.alive or (p.concentration_until<=now and p.concentration!='ensnaring_strike')):self.break_concentration(p)
            self.tick_target_conditions(p)
            if p.form and (p.form_until<=now or not p.alive):p.form='';p.form_until=0;p.form_attack_index=0
            if p.mark_target and getattr(p,'mark_target_kind','enemy')=='player':
                target=self.players.get(p.mark_target)
                if self.pvp_error(p,target):self.break_concentration(p)
            for ref in tuple(p.condition_targets):
                target=self.resolve_target_ref(ref)
                if target is not None:self.tick_target_conditions(target)
                if target is None or not any(v.get('owner')==p.id for v in self.target_conditions(target).values()):
                    if ref in p.condition_targets:p.condition_targets.remove(ref)
            if p.concentration=='ensnaring_strike' and p.concentration_until<=now:self.break_concentration(p)
        for f in tuple(self.spell_fields):
            if f not in self.spell_fields:continue  # a death/concentration check may remove another field
            p=self.players.get(f['owner'])
            if p is None or not p.alive or p.floor!=f['floor'] or self.in_safe(p) or f['until']<=now or f['concentration'] and p.concentration!=f['key']:
                self.end_field_effect(f);self.spell_fields.remove(f);continue
            s=f.get('profile') or spell_scaling.resolve(p,f['key']);center=SimpleNamespace(x=f['x'],y=f['y'],floor=f['floor'])
            due=now>=f['next']
            if due:f['next']=now+3
            candidates=list(self.nearby_enemies(center,f['radius']+64))
            if not p.pvp_safety:candidates+=list(self.players.values())
            nearby=[e for e in candidates if e.alive and e.hp>0 and same_floor(center,e) and dist(center,e)<=f['radius'] and self.line_clear(center,e)
                and (not self.is_player_target(e) or not self.pvp_error(p,e))]
            present=set();impacts=[]
            for target in nearby:
                ref=self.target_ref(target);present.add(ref)
                player_target=self.is_player_target(target)
                if s.get('growth'):
                    if player_target:unjust=self.begin_pvp_hostility(p,target)
                    applied=self.apply_status(p,target,'growth',.15,s)
                    if player_target and applied:self.record_pvp_effect(p,target,unjust)
                elif s.get('movement_damage'):
                    step=max(1,float(s.get('movement_step',32)))
                    cap=max(1,int(s.get('movement_tick_cap',8)))
                    prev=f['positions'].get(ref,(target.x,target.y,0.0))
                    moved=prev[2]+math.hypot(target.x-prev[0],target.y-prev[1]);ticks=min(cap,int(moved//step))
                    f['positions'][ref]=(target.x,target.y,moved%step)
                    for _ in range(ticks):
                        if not target.alive or target.hp<=0:break
                        self._record_field_damage(p,target,s,impacts)
                    if target.alive and target.hp>0:
                        if player_target:unjust=self.begin_pvp_hostility(p,target)
                        applied=self.apply_status(p,target,'slow',.15,s)
                        if player_target and applied:self.record_pvp_effect(p,target,unjust)
                elif due:self._record_field_damage(p,target,s,impacts)
            f['positions']={k:v for k,v in f['positions'].items() if k in present}
            self._field_tick_effect(p,f,s,impacts)
        for owner_id,pet in tuple(self.companions.items()):
            p=self.players.get(owner_id);pet.current_wall_time=now
            if p is None or not p.alive or p.disconnected or pet.floor!=p.floor or not pet.alive:
                self.companions.pop(owner_id,None);continue
            # Only the owner's explicit target. No independent acquisition of players.
            target=(self.enemies.get(p.auto_enemy_id) if p.auto_enemy_id else self.players.get(p.auto_target_id)) if p.auto_enabled else None
            if target and (not target.alive or target.hp<=0 or not same_floor(p,target) or dist(p,target)>650 or self.in_safe(p) or self.in_safe(pet)
                    or self.is_player_target(target) and self.pvp_error(p,target)):target=None
            dest=target or p;distance=dist(pet,dest)
            if distance>(65 if target else 55):
                dx,dy=(dest.x-pet.x)/max(1,distance),(dest.y-pet.y)/max(1,distance);pet.facing=[dx,dy]
                before=(pet.x,pet.y)
                # Do not let the pet enter a safe zone while pursuing a player.
                pet.pvp_combat_until=p.pvp_combat_until if target and self.is_player_target(target) else 0
                self.move(pet,dx*pet.speed*dt,dy*pet.speed*dt)
                if math.hypot(pet.x-before[0],pet.y-before[1])<.1:
                    for angle in (.65,-.65,1.2,-1.2):
                        vx=dx*math.cos(angle)-dy*math.sin(angle);vy=dx*math.sin(angle)+dy*math.cos(angle)
                        if not self.blocked(pet.x+vx*35,pet.y+vy*35,floor=pet.floor):self.move(pet,vx*pet.speed*dt,vy*pet.speed*dt);break
            if target and target.hp>0 and not self.in_safe(pet) and dist(pet,target)<=85 and self.line_clear(pet,target) and now>=pet.ready:
                pet.ready=now+3;pet.attack_until=self.time+.3
                player_target=self.is_player_target(target)
                unjust=self.begin_pvp_hostility(p,target) if player_target else False
                ac=rules.armor_class(target) if player_target else environment_rules.enemy_spec(target)['armor_class']
                edis,eadv=self.environment_attack_flags(pet,target)
                if player_target:
                    decoy_dis=self.wizard_attack_disadvantage(target)
                    edis=bool(edis or decoy_dis or self.ranger_protection(pet,target))
                result=rules.roll_attack(self.combat_rng,pet.attack_bonus,ac,pet.dice,
                    disadvantage=edis or player_target and self.target_condition(target,'foresight'),
                    advantage=eadv or self.target_condition(target,'restrained') or self.style_blind_disadvantage(target,pet))
                result['damage_type']='piercing'
                self.environment_adjust_damage(pet,target,result,pet.dice,True)
                if player_target:
                    self.wizard_attack_reaction(target,result)
                    self.shield_reaction(target,result)
                    self.resolve_player_hit(pet,target,result,'Ugryzienie towarzysza',owner=p,unjust=unjust)
                else:
                    if result['hit']:
                        result['damage']=self.environment_damage_enemy(target,result['damage'],pet,'piercing',critical=result.get('critical',False));self.remember_attacker(target,p);target.attacker_id=pet.id
                    self.report_roll(pet,target,result,'Ugryzienie towarzysza',p)
                self.tag(p,player_target);self.tag(pet,player_target);self.combat_effect(pet,'sword',target)
            elif not target and pet.combat_until<=now:pet.hp=min(pet.max_hp,pet.hp+dt)
