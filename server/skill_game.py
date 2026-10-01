"""Personal world events: visible scenes, contextual choices and durable outcomes."""
import math
from types import SimpleNamespace

try:
    from . import skill_content as content, world_content as world, environment_rules, inventory_rules
    from . import skill_rules, dnd_content, spell_scaling, combat_rules
    from .progression import train
except ImportError:
    import skill_content as content, world_content as world, environment_rules, inventory_rules
    import skill_rules, dnd_content, spell_scaling, combat_rules
    from progression import train


def progress(p, now):
    """Migrate old claims by group; never refund or silently repeat their rewards."""
    raw=getattr(p,'skill_progress',{})
    if not isinstance(raw,dict):raw={}
    old=[]
    for field in ('completed','legacy_completed'):
        values=raw.get(field,[])
        if isinstance(values,list):old.extend(k for k in values[:256] if isinstance(k,str) and k in content.IDS)
    completed=list(dict.fromkeys(content.CANONICAL[k] for k in old))
    legacy=list(dict.fromkeys(k for k in old if k not in content.BY_ID))
    cooldowns={}
    entries=raw.get('cooldowns',{})
    if isinstance(entries,dict):
        for k,v in list(entries.items())[:256]:
            if k in content.CANONICAL and type(v) in (int,float) and math.isfinite(v) and v>now:
                key=content.CANONICAL[k]
                cooldowns[key]=max(cooldowns.get(key,0),min(now+content.FAILURE_COOLDOWN,v))
    resolved={}
    records=raw.get('resolved',{})
    if isinstance(records,dict):
        for k,record in list(records.items())[:64]:
            if k in completed and isinstance(record,dict):
                at=record.get('at',0)
                if type(at) not in (int,float) or not math.isfinite(at):at=0
                method=record.get('method','')
                methods={o['id'] for o in content.BY_ID[k]['options']}
                resolved[k]=dict(at=max(0,min(now,at)),method=method if isinstance(method,str) and method in methods else '')
    discovered=raw.get('discovered',[])
    if not isinstance(discovered,list):discovered=[]
    discovered=list(dict.fromkeys([k for k in discovered[:64] if isinstance(k,str) and k in content.BY_ID]+completed))
    p.skill_progress=dict(version=2,completed=completed,legacy_completed=legacy,cooldowns=cooldowns,
                          resolved=resolved,discovered=discovered)
    return p.skill_progress


class SkillGame:
    def skill_challenge_sites(self):
        cached=getattr(self,'_skill_challenge_sites',None)
        if cached is not None:return cached
        anchors={p['id']:p for p in (*world.LANDMARKS,*world.NPCS)}
        sites={}
        for authored in content.CHALLENGES:
            anchor=anchors.get(authored['anchor'])
            if anchor is None:continue
            floor=anchor.get('floor',0);dx,dy=authored['offset'];point=None
            # Scene centre and at least one approach must both stand on dry land.
            for radius in (0,24,48,72,96,120):
                for angle in range(0,360,45):
                    x=anchor['x']+dx+radius*math.cos(math.radians(angle))
                    y=anchor['y']+dy+radius*math.sin(math.radians(angle))
                    if self.blocked(x,y,30,floor=floor):continue
                    if not any(not self.blocked(x+ax,y+ay,22,floor=floor)
                               and self.line_clear(SimpleNamespace(x=x,y=y,floor=floor),SimpleNamespace(x=x+ax,y=y+ay,floor=floor))
                               for ax,ay in ((0,70),(70,0),(-70,0),(0,-70))):continue
                    point=(round(x,2),round(y,2));break
                if point:break
            if point is None:continue
            sites[authored['id']]=dict(authored,x=point[0],y=point[1],floor=floor,
                radius=content.INTERACTION_RADIUS,reward_hint=content.reward_hint(authored))
        self._skill_challenge_sites=sites
        return sites

    @staticmethod
    def skill_challenge_public(row):
        # Outcomes, passive hints and affordability belong to the private state.
        keys=('id','name','scene','skill','ability','dc','x','y','floor','radius','min_level','description','dialogue','reward_hint')
        return {key:row[key] for key in keys}

    def skill_challenge_metadata(self):
        return [self.skill_challenge_public(s) for s in self.skill_challenge_sites().values()]

    def skill_challenge_position(self,p,site,done=False):
        pos={k:site[k] for k in ('x','y','floor')}
        return pos,math.hypot(p.x-pos['x'],p.y-pos['y']) if p.floor==pos['floor'] else float('inf')

    def skill_challenge_reason(self,p,site,state,pos,distance,option=None):
        now=self.now()
        if not p.alive or getattr(p,'disconnected',False):return 'Postać musi być żywa i połączona z grą.'
        if site['id'] in state['completed']:return 'Już pomogłeś w tym miejscu.'
        if p.floor!=pos['floor'] or distance>site['radius']:return 'Podejdź bliżej.'
        if not self.line_clear(p,SimpleNamespace(**pos)):return 'Podejdź od strony, której nie zasłania przeszkoda.'
        if environment_rules.actions_blocked(p,now):return 'Stan postaci uniemożliwia działanie.'
        if getattr(p,'form','') or environment_rules.polymorph(p):return 'Najpierw wróć do swojej postaci.'
        if getattr(p,'combat_until',0)>now or getattr(p,'pvp_combat_until',0)>now:return 'Najpierw zakończ walkę.'
        if p.level<site['min_level']:return f"Wymagany poziom: {site['min_level']}."
        if getattr(p,'attack_cooldown_until',0)>now:return 'Poczekaj na kolejną akcję.'
        if (option is None or option['kind']=='check') and state['cooldowns'].get(site['id'],0)>now:
            return 'Odpocznij przed kolejną próbą.'
        if site.get('potions') and len(p.inventory)+inventory_rules.slots_needed(p,{'health_potion':site['potions']})>40:
            return 'Zwolnij miejsce na nagrodę w plecaku.'
        if option:
            if option['kind']=='potion' and inventory_rules.count(p,option['item'])<option['quantity']:
                return 'Potrzebujesz jednej małej mikstury zdrowia.'
            if option['kind']=='spell':
                key=option['spell']
                if not dnd_content.spell_allowed(p,key):return 'Nie znasz Leczenia ran.'
                spec=spell_scaling.resolve(p,key)
                if distance>spec['range']:return 'Podejdź bliżej rannego.'
                if now<p.spell_cooldowns.get(key,0):return 'Czar jeszcze się odnawia.'
                mana,_=self.circle_spell_cost(p,spec)
                if p.mana<mana:return f'Potrzebujesz {mana} many.'
        return ''

    def skill_challenge_state(self,p):
        if p is None:return dict(nearby=[],completed_count=0,total=len(content.CHALLENGES))
        now=self.now();state=progress(p,now);rows=[]
        passive=10+skill_rules.bonus(p,'perception')-getattr(p,'exhaustion',0)*2
        # Passive sight does not roll dice or award rewards. Blind actors cannot
        # see hints, even if their underlying character-sheet bonus is high.
        can_see=p.alive and not environment_rules.active(p,'blind',now)
        for site in self.skill_challenge_sites().values():
            key=site['id'];done=key in state['completed'];pos,distance=self.skill_challenge_position(p,site)
            if distance>content.NEARBY_DISTANCE:continue
            line=distance<=content.HINT_DISTANCE and self.line_clear(p,SimpleNamespace(**pos))
            if can_see and line and key not in state['discovered']:state['discovered'].append(key)
            hint=site['hint'] if can_see and line and not done and passive>=site['hint_dc'] else ''
            options=[]
            if not done:
                for option in site['options']:
                    reason=self.skill_challenge_reason(p,site,state,pos,distance,option)
                    row=dict(option,available=not reason,reason=reason)
                    if option['kind']=='check':
                        row['skill_name']=skill_rules.SKILLS[option['skill']]['name']
                        row['bonus']=skill_rules.bonus(p,option['skill'],option['ability'])
                    elif option['kind']=='potion':row['cost_hint']='1 mała mikstura'
                    elif option['kind']=='spell' and dnd_content.spell_allowed(p,option['spell']):
                        mana,_=self.circle_spell_cost(p,spell_scaling.resolve(p,option['spell']))
                        row['cost_hint']=f'{mana} many'
                    options.append(row)
            record=state['resolved'].get(key,{})
            cooldown=max(0,math.ceil(state['cooldowns'].get(key,0)-now))
            reason='' if any(o['available'] for o in options) else self.skill_challenge_reason(p,site,state,pos,distance)
            rows.append(dict(self.skill_challenge_public(site),distance=round(distance),completed=done,
                available=any(o['available'] for o in options),reason=reason,cooldown_remaining=cooldown,
                repeatable=False,options=options,result=site['success'] if done else '',
                aftermath=site['aftermath'] if done else '',failure=site['failure'] if cooldown else '',
                hint=hint,discovered=key in state['discovered'],
                completed_age=max(0,min(60,now-record.get('at',0))) if done else 0))
        rows.sort(key=lambda r:(r['completed'],r['distance'],r['id']))
        return dict(nearby=rows,completed_ids=list(state['completed']),completed_count=len(state['completed']),total=len(content.CHALLENGES))

    async def handle_skill_challenge(self,p,data):
        if not isinstance(data,dict):return
        key=data.get('challenge_id')
        if not isinstance(key,str):return
        key=content.CANONICAL.get(key,key);site=self.skill_challenge_sites().get(key)
        if site is None:return await self.notice(p,'Nieznane wydarzenie.')
        action=data.get('action_id')
        if action is None:action=site['options'][0]['id']  # Old UI_31 client compatibility.
        if not isinstance(action,str):return
        option=next((o for o in site['options'] if o['id']==action),None)
        if option is None:return await self.notice(p,'Ta czynność nie pasuje do wydarzenia.')
        now=self.now();p.current_wall_time=now;state=progress(p,now)
        pos,distance=self.skill_challenge_position(p,site)
        reason=self.skill_challenge_reason(p,site,state,pos,distance,option)
        if reason:return await self.notice(p,reason)
        # Validation, resource consumption and claim have no await between them.
        # One player cannot double-claim with simultaneous or replayed packets.
        target=SimpleNamespace(**pos,id='event:'+key,name=site['name'],hp=1,max_hp=12,alive=True)
        self.cancel_rest(p);self.cancel_channel(p,'');self.stop_auto(p)
        p.dx=p.dy=0
        self.begin_action(p)
        result=None
        if option['kind']=='check':
            result=self.environment_ability_check(p,option['ability'],option['dc'],option['skill'],
                                                  action_name=option['label'],target=target)
            if not result['saved']:
                state['cooldowns'][key]=now+content.FAILURE_COOLDOWN
                with self.db:self.save_player(p)
                return await self.notice(p,site['failure'])
        elif option['kind']=='potion':
            if not inventory_rules.consume(p,option['item'],option['quantity']):return
            inventory_rules.sync(p,set(p.potions)|{option['item']})
        elif option['kind']=='spell':
            spell=option['spell'];spec=spell_scaling.resolve(p,spell)
            mana,free_key=self.circle_spell_cost(p,spec)
            self.spend_mana(p,mana);p.spell_cooldowns[spell]=now+spec['cooldown']
            self.circle_commit_spell(p,spec,free_key)
            dnd_content.record_spell_use(p,spell);train(p,'magic',max(1,mana))
            self.environment_reveal(p,'Leczenie zdradza twoją kryjówkę.')
            if mana>0:self.wizard_after_paid_spell(p,spell,spec)
            heal=combat_rules.roll_damage(self.combat_rng,spec['dice'])
            self.spell_effect(p,spell,target,spec=spec)
            self.report_roll(p,target,dict(heal,check='healing',hit=True,healing=min(11,heal['damage']),damage=0),spec['name'],p)
            # Player-only healing riders retain their normal targets, never a
            # fictitious player account or a public NPC added to the player list.
            self.circle_after_heal(p,spec,[],mana)
        with self.db:
            state['completed'].append(key);state['cooldowns'].pop(key,None)
            state['resolved'][key]=dict(at=now,method=action)
            if key not in state['discovered']:state['discovered'].append(key)
            self.award(p,site.get('xp',0),site.get('gold',0))
            if site.get('potions'):self.grant_loot(p,[('potion','health_potion')]*site['potions'])
            self.save_player(p)
        return await self.notice(p,site['success'])
