"""Nearby skill challenges with server-owned context, checks and persistent claims."""
import math
from types import SimpleNamespace

try:
    from . import skill_content as content, world_content as world, environment_rules, inventory_rules
except ImportError:
    import skill_content as content, world_content as world, environment_rules, inventory_rules


def progress(p, now):
    raw = getattr(p, 'skill_progress', {})
    if not isinstance(raw, dict):raw = {}
    completed = raw.get('completed', [])
    if not isinstance(completed, list):completed = []
    completed = list(dict.fromkeys(k for k in completed if isinstance(k, str) and k in content.IDS))
    cooldowns = raw.get('cooldowns', {})
    if not isinstance(cooldowns, dict):cooldowns = {}
    # Future timestamps are bounded; malformed saved state cannot block a skill
    # forever. Expired entries are safe to discard and cannot grant a reward.
    cooldowns = {k:min(now+content.FAILURE_COOLDOWN, v) for k,v in cooldowns.items()
                 if k in content.IDS and type(v) in (int,float) and math.isfinite(v) and v>now}
    p.skill_progress = dict(completed=completed, cooldowns=cooldowns)
    return p.skill_progress


class SkillGame:
    def skill_challenge_sites(self):
        cached = getattr(self, '_skill_challenge_sites', None)
        if cached is not None:return cached
        anchors = {p['id']:p for p in (*world.LANDMARKS, *world.NPCS)}

        def dry_point(x, y, floor):
            # Fixed deterministic rings, never a client-supplied destination.
            for radius in (0,24,48,72,96,120):
                for angle in range(0,360,45):
                    px=x+radius*math.cos(math.radians(angle));py=y+radius*math.sin(math.radians(angle))
                    if not self.blocked(px,py,22,floor=floor):return round(px,2),round(py,2)
            return None

        sites = {}
        for authored in content.CHALLENGES:
            anchor=anchors.get(authored['anchor'])
            if anchor is None:continue
            floor=anchor.get('floor',0);dx,dy=authored['offset']
            point=dry_point(anchor['x']+dx,anchor['y']+dy,floor)
            if point is None:continue
            row=dict(authored,x=point[0],y=point[1],floor=floor,radius=content.INTERACTION_RADIUS,
                     min_level=authored.get('min_level',1),reward_hint=content.reward_hint(authored))
            if authored.get('route'):
                dx,dy=authored['route'];destination=dry_point(anchor['x']+dx,anchor['y']+dy,floor)
                if destination is None:continue
                row['destination']=dict(x=destination[0],y=destination[1],floor=floor)
            sites[row['id']]=row
        self._skill_challenge_sites=sites
        return sites

    @staticmethod
    def skill_challenge_public(row):
        keys=('id','name','skill','ability','dc','x','y','floor','radius','min_level','description','reward_hint')
        return {key:row[key] for key in keys}

    def skill_challenge_metadata(self):
        rows=[]
        for site in self.skill_challenge_sites().values():
            rows.append(self.skill_challenge_public(site))
            if site.get('destination'):
                rows.append(dict(self.skill_challenge_public(site),**site['destination'],endpoint='return',name=site['name']+' · powrót'))
        return rows

    def skill_challenge_position(self,p,site,done):
        positions=[dict(x=site['x'],y=site['y'],floor=site['floor'])]
        if done and site.get('destination'):positions.append(site['destination'])
        candidates=[pos for pos in positions if pos['floor']==p.floor]
        if not candidates:return positions[0],float('inf')
        pos=min(candidates,key=lambda target:math.hypot(p.x-target['x'],p.y-target['y']))
        return pos,math.hypot(p.x-pos['x'],p.y-pos['y'])

    def skill_challenge_reason(self,p,site,state,pos,distance):
        now=self.now();done=site['id'] in state['completed']
        if not p.alive:return 'Postać musi być żywa.'
        if done and not site.get('destination'):return 'Już ukończono; nagrodę odebrano.'
        if p.floor!=pos['floor'] or distance>site['radius']:return 'Podejdź do tego miejsca.'
        if not self.line_clear(p,SimpleNamespace(**pos)):return 'Podejdź bez przeszkody między tobą a miejscem.'
        if environment_rules.actions_blocked(p,now):return 'Stan postaci uniemożliwia działanie.'
        if getattr(p,'combat_until',0)>now or getattr(p,'pvp_combat_until',0)>now:return 'Najpierw zakończ walkę.'
        if p.level<site['min_level']:return f"Wymagany poziom: {site['min_level']}."
        if getattr(p,'attack_cooldown_until',0)>now:return 'Poczekaj na kolejną akcję.'
        if state['cooldowns'].get(site['id'],0)>now:return 'Przygotuj się przed ponowną próbą.'
        if site.get('destination') and environment_rules.immobile(p,now):return 'Najpierw uwolnij się z unieruchomienia.'
        if site.get('potions') and not done:
            if len(p.inventory)+inventory_rules.slots_needed(p,{'health_potion':site['potions']})>40:
                return 'Zwolnij miejsce na mikstury w plecaku.'
        return ''

    def skill_challenge_state(self,p):
        if p is None:return dict(nearby=[],completed_count=0,total=len(content.CHALLENGES))
        state=progress(p,self.now());rows=[]
        for site in self.skill_challenge_sites().values():
            done=site['id'] in state['completed'];pos,distance=self.skill_challenge_position(p,site,done)
            if distance>content.NEARBY_DISTANCE:continue
            reason=self.skill_challenge_reason(p,site,state,pos,distance)
            row=dict(self.skill_challenge_public(site),**pos,distance=round(distance),completed=done,
                     available=not reason,reason=reason,cooldown_remaining=max(0,math.ceil(state['cooldowns'].get(site['id'],0)-self.now())),
                     repeatable=bool(site.get('destination')),result=site['success'] if done else '')
            rows.append(row)
        rows.sort(key=lambda row:(row['completed'] and not row['repeatable'],row['distance'],row['id']))
        return dict(nearby=rows,completed_count=len(state['completed']),total=len(content.CHALLENGES))

    async def handle_skill_challenge(self,p,data):
        if not isinstance(data,dict):return
        key=data.get('challenge_id')
        if not isinstance(key,str):return
        site=self.skill_challenge_sites().get(key)
        if site is None:return await self.notice(p,'Nieznane miejsce próby umiejętności.')
        now=self.now();p.current_wall_time=now;state=progress(p,now)
        done=key in state['completed'];pos,distance=self.skill_challenge_position(p,site,done)
        reason=self.skill_challenge_reason(p,site,state,pos,distance)
        if reason:return await self.notice(p,reason)
        destination=None
        if site.get('destination'):
            destination=(dict(x=site['x'],y=site['y'],floor=site['floor'])
                         if pos==site['destination'] else site['destination'])
            if self.blocked(destination['x'],destination['y'],22,floor=destination['floor']):
                return await self.notice(p,'Przejście jest chwilowo zablokowane.')
        # No await between validation and durable claim. Double clicks and forged
        # packets cannot interleave a second reward or reroll the same attempt.
        self.cancel_rest(p);self.cancel_channel(p,'');self.stop_auto(p);self.begin_action(p)
        if not done:
            result=self.environment_ability_check(p,site['ability'],site['dc'],site['skill'])
            if not result['saved']:
                state['cooldowns'][key]=now+content.FAILURE_COOLDOWN
                with self.db:self.save_player(p)
                return await self.notice(p,f"{site['name']}: {result['total']} przeciw ST {site['dc']} — niepowodzenie. Ponowna próba za {content.FAILURE_COOLDOWN} s.")
        with self.db:
            if not done:
                state['completed'].append(key);state['cooldowns'].pop(key,None)
                self.award(p,site.get('xp',0),site.get('gold',0))
                if site.get('potions'):
                    self.grant_loot(p,[('potion','health_potion')]*site['potions'])
            if destination:
                p.x=destination['x'];p.y=destination['y'];p.dx=p.dy=0
                if hasattr(p,'submerged'):p.submerged=False
            self.save_player(p)
        if done:return await self.notice(p,'Korzystasz z zabezpieczonego przejścia. Nagroda została już odebrana.')
        return await self.notice(p,site['success']+' '+content.reward_hint(site)+'.')
