"""Authoritative caster features, training choices and non-attacking familiars.

No client-supplied damage, HP, mana refund, training source or ritual duration is
trusted. Channels are committed once, only on successful completion. Runtime
summons/alarms do not survive disconnect; paid cooldowns do survive it.
"""
import math
from dataclasses import dataclass
from types import SimpleNamespace
try:
    from . import rest_rules, druid_circles as circles
    from . import caster_rules as caster, equipment_rules as gear, combat_rules as rules, dnd_content as dnd, spell_scaling, world_content as content
    from .dnd_game import Companion
    from .progression import same_floor
except ImportError:
    import rest_rules, druid_circles as circles
    import caster_rules as caster, equipment_rules as gear, combat_rules as rules, dnd_content as dnd, spell_scaling, world_content as content
    from dnd_game import Companion
    from progression import same_floor


def distance(a,b):return math.hypot(a.x-b.x,a.y-b.y)

@dataclass
class Familiar(Companion):
    mode: str='follow'
    help_ready: float=0
    scout_ready: float=0
    is_familiar: bool=True
    kind: str='owl'
    def public(self):
        v=super().public();v.update(kind='owl',is_familiar=True,mode=self.mode)
        return v


class CasterGame:
    def init_dnd(self):
        super().init_dnd()
        self.familiars={};self.alarms={}
        self.nature_sites=[
            dict(id='fox_trail',kind='fox',name='Leśny lis',x=965,y=1240,floor=0,
                text='Na wschodzie słychać wodę. Most przez rzekę jest na wysokości drogi z Przystani.',hint_x=1590,hint_y=1155),
            dict(id='reed_frog',kind='frog',name='Żaba w trzcinach',x=1420,y=1320,floor=0,
                text='Nie schodź daleko od drogi za mostem. W mokradłach kryją się pająki i ogniki.',hint_x=1900,hint_y=1490),
            dict(id='druid_stone',kind='sign',name='Znak druidów',x=1005,y=1560,floor=0,
                text='Szlak prowadzi na północ, ku wilczym ostępom. Woda oddziela je od ruin.',hint_x=960,hint_y=720),
        ]

    def migrate_caster(self,p):
        p.primal_order=p.primal_order if p.class_id=='druid' and p.primal_order in caster.ORDERS else ''
        gear.migrate_advancement(p)
        p.casting_channel={};p.caster_messages=[];p.familiar_state={}
        # Existing medium armor is not deleted or silently turned into a free feat.
        # A legacy druid gets a grace period until the first explicit path choice.
        if p.caster_rules_version<caster.VERSION:
            if p.class_id=='druid' and gear.weapon(p):
                p.legacy_medium_grace=rules.equipped_item(p,'armor').get('armor_kind')=='medium'
            p.caster_rules_version=caster.VERSION
        p._hotbar_level=None;dnd.sync_hotbar(p)

    def caster_message(self,p,text):
        p.caster_messages=(getattr(p,'caster_messages',[])+[text])[-8:]

    def clear_caster_caches(self,p):
        for key in ('_profile_cache','_profile_signature','_spell_profile_cache','_spell_profiles_cache','_equipment_preview_cache'):
            p.__dict__.pop(key,None)
        p._hotbar_level=None;dnd.sync_hotbar(p)

    async def select_primal_order(self,p,key):
        if p.class_id!='druid' or not isinstance(key,str) or key not in caster.ORDERS:
            return await self.notice(p,'Wybierz ścieżkę druida.')
        if not p.alive or p.form or p.combat_until>self.now():
            return await self.notice(p,'Wybierz ścieżkę poza walką i przemianą.')
        if p.primal_order and (not self.near_service(p,'master') or not self.in_safe(p)):
            return await self.notice(p,'Ścieżkę zmienisz bez opłaty u mistrza w osadzie.')
        if p.primal_order==key:return
        fraction=p.hp/max(1,p.max_hp)
        p.primal_order=key;p.legacy_medium_grace=False
        p.hp=max(1,min(p.max_hp,p.max_hp*fraction))
        self.clear_caster_caches(p)
        with self.db:self.save_player(p)
        await self.notice(p,'Ścieżka: '+caster.ORDERS[key]['name']+'.'+(' Średni pancerz kupisz lub zdobędziesz.' if key=='warden' else ''))

    async def choose_training_feat(self,p,key,ability='',abilities=None,expected_spent=None):
        if not isinstance(key,str) or key not in gear.GENERAL_FEATS:return
        s=gear.GENERAL_FEATS[key]
        if self.development_blocked(p):return await self.notice(p,'Wybierz atut poza walką i przemianą.')
        hp_fraction=p.hp/max(1,p.max_hp)
        reason=gear.select_feat(p,key,ability,abilities,expected_spent=expected_spent)
        if reason:return await self.notice(p,reason)
        p.hp=min(p.max_hp,hp_fraction*p.max_hp)
        p._level_up_cache=None
        self.clear_caster_caches(p)
        with self.db:self.save_player(p)
        await self.notice(p,'Nowy atut: '+s['name']+'.')

    def cancel_channel(self,p,reason='Rzucanie przerwane.'):
        channel=getattr(p,'casting_channel',{})
        if not channel:return
        p.casting_channel={}
        if p.attack_cooldown_until<=channel['until']+.01:
            p.attack_cooldown_until=max(self.now(),channel.get('old_action',0))
        p.buffs.pop('arcane_channel',None);p.buffs.pop('ritual_channel',None)
        if reason:self.caster_message(p,reason)

    async def cast_arcane_recovery(self,p):
        if p.class_id!='mage' or not p.alive:return
        if not rest_rules.remaining(p,'arcane_recovery'):
            return await self.notice(p,'Odzyskanie mocy odnowi długi odpoczynek.')
        if p.mana>=p.max_mana:return await self.notice(p,'Masz już pełną manę.')
        return await self.start_rest(p,'short',recover=True)

    async def start_caster_channel(self,p,key,ritual=False):
        p.current_wall_time=now=self.now()
        if not isinstance(key,str) or key not in dnd.SPELLS or not dnd.spell_allowed(p,key):return
        s=spell_scaling.resolve(p,key)
        if ritual and not s.get('ritual'):return await self.notice(p,'Tego czaru nie można rzucać rytualnie.')
        if s['kind'] not in ('ritual_alarm','familiar','animal_speech'):return
        if not p.alive or p.form:return await self.notice(p,'Potrzebujesz własnej, żywej postaci.')
        if p.combat_until>now or p.pvp_combat_until>now:return await self.notice(p,'Skup się poza walką.')
        if gear.armor_penalty(p):return await self.notice(p,'Brak wyszkolenia w tym pancerzu: nie możesz rzucać czarów.')
        if p.casting_channel:return await self.notice(p,'Rzucanie już trwa. Możesz je przerwać ruchem.')
        if now<p.spell_cooldowns.get(key,0) or now<p.attack_cooldown_until:return
        cost=0 if ritual else s.get('mana',0)
        if p.mana<cost:return await self.notice(p,f'Potrzebujesz {cost} many. Dostępny jest także rytuał.')
        if p.gold<s.get('gold',0):return await self.notice(p,f'Składniki kosztują {s["gold"]} złota.')
        seconds=float(s.get('ritual_seconds',10) if ritual else s.get('channel_seconds',3))
        self.cancel_rest(p)
        self.stop_auto(p)
        # A currently held movement key still cancels, instead of silently eating it.
        p.casting_channel=dict(key=key,name=s['name'],until=now+seconds,total=seconds,x=p.x,y=p.y,floor=p.floor,
            cost=cost,gold=s.get('gold',0),ritual=bool(ritual),profile=s,old_action=p.attack_cooldown_until)
        p.attack_cooldown_until=now+seconds
        p.buffs['ritual_channel']=dict(until=now+seconds,spell_id=key)
        self.spell_effect(p,key,p,spec=s)
        await self.notice(p,('Rytuał: ' if ritual else '')+s['name']+f' · {int(seconds)} s.')

    def summon_familiar(self,p):
        self.familiars[p.id]=Familiar('familiar_'+p.id,p.id,'Leśna sowa' if p.class_id=='druid' else 'Chowaniec · sowa',
            p.x,p.y,p.floor,3,3,0,11,(0,1,0),speed=155)
        p.familiar_state=dict(mode='follow',hp=3,max_hp=3)
        self.caster_message(p,'Sowa towarzyszy ci. W Atutach wybierzesz pomoc lub zwiad. Nie atakuje.')

    def complete_channel(self,p):
        ch=p.casting_channel
        if not ch:return
        s=ch['profile'];key=ch['key'];now=self.now()
        if p.mana<ch['cost'] or p.gold<ch['gold']:
            self.cancel_channel(p,'Rzucanie przerwane: zabrakło many lub składników.');return
        if not dnd.spell_allowed(p,key) or gear.armor_penalty(p):
            self.cancel_channel(p,'Rzucanie przerwane: zmieniły się wymagania.');return
        self.cancel_channel(p,'')
        self.spend_mana(p,ch['cost']);p.gold-=ch['gold']
        if s['kind']=='familiar':self.summon_familiar(p)
        elif s['kind']=='ritual_alarm':
            self.alarms[p.id]=dict(x=p.x,y=p.y,floor=p.floor,until=now+s['duration'],occupants=set(),ready=now,primed=False)
            p.buffs['ritual_alarm']=dict(until=now+s['duration'],spell_id=key)
            self.caster_message(p,'Alarm zabezpiecza to miejsce. Nowy Alarm zastąpi poprzedni.')
        elif s['kind']=='animal_speech':
            p.buffs['speak_with_animals']=dict(until=now+s['duration'],spell_id=key)
            self.caster_message(p,'Rozumiesz spokojne zwierzęta. Podejdź do lisa lub żaby i użyj E.')
        dnd.record_spell_use(p,key);self.spell_effect(p,key,p,spec=s)
        with self.db:self.save_player(p)

    async def cast_wild_shape(self,p,s):
        now=self.now();p.current_wall_time=now
        if rules.active_buff(p,'polymorph'):return await self.notice(p,'Polimorfii nie można odwołać Dzikim kształtem.')
        if p.form:
            if now<p.bonus_cooldown_until:return
            self.cancel_channel(p,'');self.begin_action(p,True);p.form='';p.form_until=0;p.form_attack_index=0
            self.spell_effect(p,s['id'],p,spec=s)
            return
        if now<p.bonus_cooldown_until:return
        if not circles.spend_shape(p):return await self.notice(p,"Brak użyć Dzikiego kształtu. Odpocznij.")
        self.cancel_channel(p,'');self.begin_action(p,True)
        p.form=s['form'];p.form_until=now+caster.form_duration(p);p.form_attack_index=0
        p.temp_hp=max(p.temp_hp,circles.form_temp_hp(p))
        self.set_shape_cooldown(p,now)
        dnd.record_spell_use(p,s['id']);self.spell_effect(p,s['id'],p,spec=s)
        with self.db:self.save_player(p)

    def set_shape_cooldown(self,p,now):
        for key in ('wild_shape_shared','wild_companion',*('wild_shape_'+f for f in caster.FORMS)):
            p.spell_cooldowns.pop(key,None)

    async def cast_spell(self,p,key,enemy_id=None,target_id=None,queue=True):
        s=dnd.SPELLS.get(key) if isinstance(key,str) else None
        if not s or not p.alive or not dnd.spell_allowed(p,key):return await super().cast_spell(p,key,enemy_id,target_id,queue)
        if enemy_id is not None and not isinstance(enemy_id,str) or target_id is not None and not isinstance(target_id,str):return
        if enemy_id and target_id:return
        p.current_wall_time=self.now()
        if s['kind']=='recovery':return await self.cast_arcane_recovery(p)
        if s['kind'] in ('ritual_alarm','familiar','animal_speech'):
            return await self.start_caster_channel(p,key)
        if s['kind']=='shape':return await self.cast_wild_shape(p,spell_scaling.resolve(p,key))
        if s['kind']=='wild_familiar':
            if p.form:return await self.notice(p,'Przywołaj towarzysza po zakończeniu przemiany.')
            if self.now()<p.attack_cooldown_until:return
            if not circles.spend_shape(p):return await self.notice(p,"Brak użyć Dzikiego kształtu. Odpocznij.")
            self.cancel_channel(p,'');self.begin_action(p);self.set_shape_cooldown(p,self.now());self.summon_familiar(p)
            dnd.record_spell_use(p,key);self.spell_effect(p,key,p,spec=s)
            with self.db:self.save_player(p)
            return
        if not s.get('feature') and gear.armor_penalty(p):return await self.notice(p,'Brak wyszkolenia w tym pancerzu: nie możesz rzucać czarów.')
        if key=='shillelagh' and gear.weapon(p).get('weapon_type') not in ('quarterstaff','club'):
            return await self.notice(p,'Shillelagh wymaga laski lub maczugi.')
        self.cancel_channel(p)
        return await super().cast_spell(p,key,enemy_id,target_id,queue)

    async def dnd_attack(self,p,*args,**kwargs):
        self.cancel_channel(p)
        return await super().dnd_attack(p,*args,**kwargs)

    async def process_player_actions(self):
        for p in tuple(self.players.values()):
            for text in getattr(p,'caster_messages',[]):await self.notice(p,text)
            p.caster_messages=[]
        await super().process_player_actions()

    def caster_attack_advantage(self,p,target):
        helped=False
        if rules.active_buff(p,'familiar_help'):
            buff=p.buffs['familiar_help']
            if buff.get('target')==self.target_ref(target):p.buffs.pop('familiar_help',None);helped=True
        pack=False
        if p.form=='wolf':
            allies=[q for q in self.players.values() if q is not p and p.party_id and p.party_id==q.party_id]
            allies+=list(self.companions.values())+list(self.familiars.values())
            pack=any(q.alive and same_floor(q,target) and distance(q,target)<=32 and (not hasattr(q,'owner_id') or q.owner_id==p.id or self.players.get(q.owner_id) in allies) for q in allies)
        return helped or pack

    def beast_on_hit(self,p,target,result):
        if not p.form or not result or not result.get('hit') or target.hp<=0:return
        knock=p.form=='wolf' or p.form=='bear' and p.form_attack_index==1
        size=1 if self.is_player_target(target) else content.ENEMIES[target.kind].get('size',1)
        if not knock or size>(1.2 if p.form=='wolf' else 1.7):return
        self.target_conditions(target)['prone']=dict(until=self.now()+1.5,owner=p.id,hostile=True,spell_id='beast_prone',concentration=False)
        if self.is_player_target(target):self.record_pvp_effect(p,target,target.last_pvp_unjust)
        self.fighter_effect(p,target,'topple')

    async def familiar_command(self,p,mode):
        pet=self.familiars.get(p.id)
        if pet is None or not pet.alive or not p.alive:return await self.notice(p,'Najpierw przywołaj chowańca.')
        if mode=='dismiss':
            self.familiars.pop(p.id,None);p.familiar_state={};p.buffs.pop('familiar_help',None);return
        if mode=='scout':
            if self.now()<pet.scout_ready:return
            pet.scout_ready=self.now()+10
            nearby=[e for e in self.nearby_enemies(pet,420) if e.alive and same_floor(e,pet) and distance(e,pet)<=420 and self.line_clear(pet,e)]
            nearby.sort(key=lambda e:distance(e,pet))
            names=list(dict.fromkeys(content.ENEMIES[e.kind]['name'] for e in nearby))[:5]
            return await self.notice(p,'Zwiad sowy: '+(', '.join(names) if names else 'nie widać pobliskich zagrożeń')+'.')
        if mode not in ('follow','help'):return
        pet.mode=mode;p.familiar_state=dict(mode=mode,hp=pet.hp,max_hp=pet.max_hp)
        if mode=='follow':p.buffs.pop('familiar_help',None)
        await self.notice(p,'Sowa: '+('pomaga przeciw wskazanemu celowi.' if mode=='help' else 'podąża za tobą.'))

    async def nature_interaction(self,p,site_id=None):
        sites=[s for s in self.nature_sites if (site_id is None or site_id==s['id']) and same_floor(p,s) and math.hypot(p.x-s['x'],p.y-s['y'])<=110]
        if not sites:return False
        s=min(sites,key=lambda x:math.hypot(p.x-x['x'],p.y-x['y']))
        if not self.line_clear(p,SimpleNamespace(**s)):return False
        if s['kind']=='sign' and p.class_id!='druid':await self.notice(p,'Nie rozpoznajesz tych znaków.');return True
        if s['kind']!='sign' and not rules.active_buff(p,'speak_with_animals'):
            await self.notice(p,'Do rozmowy potrzebujesz Rozmowy ze zwierzętami.');return True
        await self.notice(p,s['name']+': '+s['text'])
        await self.send(p.ws,dict(type='nature_hint',x=s['hint_x'],y=s['hint_y'],floor=s['floor'],name=s['name']))
        return True

    def tick_dnd(self,dt):
        super().tick_dnd(dt)
        now=self.now()
        for p in tuple(self.players.values()):
            ch=p.casting_channel
            if ch:
                moving=abs(p.x-ch['x'])+abs(p.y-ch['y'])>.05 or (self.time-p.input_time<=.35 and (p.dx or p.dy))
                if not p.alive or p.disconnected or p.floor!=ch['floor'] or moving or p.combat_until>now:
                    self.cancel_channel(p)
                elif now>=ch['until']:self.complete_channel(p)
        for owner,pet in tuple(self.familiars.items()):
            p=self.players.get(owner)
            if p is None or not p.alive or p.disconnected or not pet.alive:
                self.familiars.pop(owner,None)
                if p:p.buffs.pop('familiar_help',None);p.familiar_state={}
                continue
            pet.current_wall_time=now;p.familiar_state=dict(mode=pet.mode,hp=round(pet.hp,1),max_hp=pet.max_hp)
            if pet.floor!=p.floor or distance(p,pet)>1400:
                # Following a staircase never scouts or attacks through another floor.
                pet.x,pet.y,pet.floor=p.x,p.y,p.floor
            target=self.enemies.get(p.auto_enemy_id) if p.auto_enemy_id else self.players.get(p.auto_target_id)
            if not target or not target.alive or not same_floor(target,p) or distance(p,target)>550 or self.in_safe(p) or (self.is_player_target(target) and self.pvp_error(p,target)):
                target=None
            dest=target if pet.mode=='help' and target else p
            length=distance(pet,dest)
            if length>(28 if dest is target else 42):
                dx=(dest.x-pet.x)/max(1,length);dy=(dest.y-pet.y)/max(1,length);pet.facing=[dx,dy]
                self.move(pet,dx*min(length,pet.speed*dt),dy*min(length,pet.speed*dt))
            if dest is target and target and distance(pet,target)<=36 and self.line_clear(pet,target) and now>=pet.help_ready and not self.in_safe(pet):
                pet.help_ready=now+3
                if self.is_player_target(target):self.begin_pvp_hostility(p,target)
                else:self.provoke_enemy(target,pet)
                p.buffs['familiar_help']=dict(until=now+3,spell_id='find_familiar',target=self.target_ref(target))
                self.tag(p,self.is_player_target(target));self.tag(pet)
        for owner,a in tuple(self.alarms.items()):
            p=self.players.get(owner)
            if not p or not p.alive or p.disconnected or a['until']<=now:
                self.alarms.pop(owner,None)
                if p:p.buffs.pop('ritual_alarm',None)
                continue
            center=SimpleNamespace(**{k:a[k] for k in ('x','y','floor')})
            subjects=list(self.nearby_enemies(center,100))+[q for q in self.players.values() if q is not p and not(p.party_id and q.party_id==p.party_id)]
            entered={q.id for q in subjects if q.alive and same_floor(q,center) and abs(q.x-center.x)<=64 and abs(q.y-center.y)<=64}
            if a['primed'] and entered-a['occupants'] and now>=a['ready'] and same_floor(p,center) and distance(p,center)<=33792:
                self.caster_message(p,'Alarm! Obce stworzenie weszło na zabezpieczony obszar.')
                a['ready']=now+3
            a['primed']=True;a['occupants']=entered
