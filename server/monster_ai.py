"""Local roaming, role-based combat and dodgeable, telegraphed enemy attacks."""
import math
import zlib
from types import SimpleNamespace
try:
    from . import world_content as content
    from .living_world import SURFACES
except ImportError:
    import world_content as content
    from living_world import SURFACES


class MonsterAI:
    def enemy_move_towards(self, e, x, y, dt, factor=1):
        dx,dy=x-e.x,y-e.y
        length=math.hypot(dx,dy)
        if length<4:return
        s=content.ENEMIES[e.kind]
        speed=s['speed']*SURFACES[content.SURFACE_MAP.at(e.x,e.y,e.floor)]['speed']*factor
        if e.slow_until>self.time:speed*=.55
        amount=min(length,speed*dt)
        e.facing=[dx/length,dy/length]
        old=(e.x,e.y)
        self.move(e,dx/length*amount,dy/length*amount)
        if math.dist(old,(e.x,e.y))<amount*.25:
            # Choose a stable side around boulders; no world-wide pathfinding.
            side=1 if zlib.crc32(e.id.encode())%2 else -1
            for angle in (side*.8,side*1.4,-side*1.4):
                vx=dx/length*math.cos(angle)-dy/length*math.sin(angle)
                vy=dx/length*math.sin(angle)+dy/length*math.cos(angle)
                if not self.blocked(e.x+vx*45,e.y+vy*45,floor=e.floor):
                    self.move(e,vx*amount,vy*amount);break

    def roam_enemy(self,e,dt):
        s=content.ENEMIES[e.kind]
        if math.hypot(e.x-e.home_x,e.y-e.home_y)>s['wander']+45:
            self.enemy_move_towards(e,e.home_x,e.home_y,dt,.8)
            return
        if self.time>=e.wander_ready:
            seed=zlib.crc32(e.id.encode())
            phase=seed*.001+int(self.time/6)*2.39996
            radius=s['wander']*(.35+((seed+int(self.time/6))%61)/100)
            e.wander_x=e.home_x+math.cos(phase)*radius
            e.wander_y=e.home_y+math.sin(phase*1.37)*radius*.75
            e.wander_ready=self.time+4+(seed%50)/10
            e.rest_until=self.time+(seed%15)/10
        if self.time>e.rest_until:
            self.enemy_move_towards(e,e.wander_x,e.wander_y,dt,.32)

    def queue_enemy_attack(self,e,target,projectile=None,special=False):
        s=content.ENEMIES[e.kind]
        element=projectile or s.get('projectile','stone')
        radius=(145 if special else 70 if element in ('stone','fire') else 48)
        delay=(1.15 if special else s.get('windup',.45))
        # Fixed aim allows sidesteps; special volleys punish standing and orbiting.
        lead=(delay+.32)*.9 if self.time-target.input_time<=.35 else 0
        aim_x=target.x+target.dx*target.speed*lead
        aim_y=target.y+target.dy*target.speed*lead
        points=[(aim_x,aim_y)]
        if special:
            mode=e.special_count%3;e.special_count+=1
            if mode==0 and element in ('fire','ice'):
                # Dragon breath / ice lance sweeps the line from boss toward its aim.
                dx,dy=aim_x-e.x,aim_y-e.y;length=max(1,math.hypot(dx,dy))
                points=[(e.x+dx/length*d,e.y+dy/length*d) for d in (125,250,375,500)]
                radius=85
            elif mode==1:
                points=[(target.x+math.cos(a)*125,target.y+math.sin(a)*125) for a in (0,2.0944,4.1888)]
                radius=105
            elif mode==2:
                points=[(e.x,e.y)];radius=245;delay=1.3
        for x,y in points:
            aim=SimpleNamespace(id=target.id,x=x,y=y,floor=e.floor)
            effect=self.combat_effect(e,'danger_zone',aim,radius=radius,duration=delay+.32)
            effect.update(element=element,special=special)
            self.hazards.append({'source_id':e.id,'floor':e.floor,'x':e.x,'y':e.y,'target_x':x,'target_y':y,
                                 'radius':radius,'launch':self.time+delay,'resolve':self.time+delay+.32,
                                 'damage':s['damage']*(1.55 if special else 1),'element':element,'launched':False,'special':special})
        e.mobile_cast = s.get("combat_role") == "hybrid" and not special
        e.cast_until=self.time+delay
        e.attack_until=self.time+delay

    def resolve_hazards(self):
        waiting=[]
        for h in self.hazards:
            e=self.enemies.get(h['source_id'])
            if e is None or not e.alive or e.floor!=h['floor']:
                continue
            target=SimpleNamespace(id='',x=h['target_x'],y=h['target_y'],floor=h['floor'])
            origin=SimpleNamespace(id=e.id,x=h['x'],y=h['y'],floor=h['floor'])
            if self.time>=h['launch'] and not h['launched']:
                effect=self.combat_effect(origin,'enemy_'+h['element'],target,radius=h['radius'],duration=.32)
                effect['special']=h['special'];h['launched']=True
            if self.time<h['resolve']:
                waiting.append(h);continue
            self.combat_effect(target,'enemy_impact',radius=h['radius'],duration=.35)['element']=h['element']
            for p in tuple(self.players.values()):
                if p.alive and p.floor==h['floor'] and not self.in_safe(p) and math.hypot(p.x-target.x,p.y-target.y)<=h['radius']+12 and self.line_clear(origin,p):
                    self.damage_player(p,h['damage'])
        self.hazards=waiting

    def step_monsters(self,dt,player_cells,unsafe_ids):
        self.resolve_hazards()
        active={e.id:e for p in self.players.values() if p.alive for e in self.nearby_enemies(p,1450)}
        local_cache={}
        for e in active.values():
            if not e.alive:
                if e.respawn_at and self.time>=e.respawn_at:
                    e.alive,e.hp=True,e.max_hp;e.x,e.y=e.home_x,e.home_y
                    e.contributors.clear();e.attacker_id,e.attacker_until='',0
                    e.ready,e.aoe_ready,e.taunt_id=self.time+1,self.time+4,''
                    e.cast_until=0;e.wander_ready=0;e.special_count=0;e.ranged_ready=self.time+2;e.mobile_cast=False
                    if e.kind=='boss':self.flags.update(boss_defeated=False,event_active=True)
                continue
            cell=(e.floor,int(e.x//1024),int(e.y//1024))
            if cell not in local_cache:
                local_cache[cell]=[p for dx in (-1,0,1) for dy in (-1,0,1) for p in player_cells.get((cell[0],cell[1]+dx,cell[2]+dy),())]
            nearby=local_cache[cell]
            # Roam before entering combat, throughout the visible simulation area.
            if not any(math.hypot(p.x-e.x,p.y-e.y)<1450 for p in nearby):
                continue
            s=content.ENEMIES[e.kind]
            candidates=[]
            for p in nearby:
                if p.id not in unsafe_ids or not p.alive:continue
                provoked=(e.attacker_until>self.time and p.id==e.attacker_id) or (e.taunt_until>self.time and p.id==e.taunt_id)
                d=math.hypot(p.x-e.x,p.y-e.y)
                if (provoked or d<s['aggro']) and math.hypot(p.x-e.home_x,p.y-e.home_y)<s['leash']:
                    # Passive detection respects walls; remembered attackers can be pursued around them.
                    if provoked or self.line_clear(e,p):candidates.append(p)
            target=next((p for p in candidates if e.taunt_until>self.time and p.id==e.taunt_id),None)
            if target is None:target=next((p for p in candidates if e.attacker_until>self.time and p.id==e.attacker_id),None)
            if target is None:target=min(candidates,key=lambda p:math.hypot(p.x-e.x,p.y-e.y)) if candidates else None
            if target is None:
                self.roam_enemy(e,dt)
                retreating=math.hypot(e.x-e.home_x,e.y-e.home_y)>s['wander']+45
                e.hp=min(e.max_hp,e.hp+dt*(max(3,e.max_hp*.12) if retreating else 3))
                continue
            e.attacker_id,e.attacker_until=target.id,self.time+12
            d=max(1,math.hypot(target.x-e.x,target.y-e.y))
            e.facing=[(target.x-e.x)/d,(target.y-e.y)/d]
            hybrid = s.get('combat_role') == 'hybrid'
            if self.time < e.cast_until:
                if hybrid and e.mobile_cast and d > s['melee_range']*.8:
                    self.enemy_move_towards(e,target.x,target.y,dt,.7)
                continue
            visible=self.line_clear(e,target)
            if s.get('boss') and self.time>=e.aoe_ready and d<s['special_range'] and visible:
                e.aoe_ready=self.time+(6 if e.hp<e.max_hp*.4 else 8)
                self.queue_enemy_attack(e,target,special=True)
                e.ready=max(e.ready,self.time+1.4)
                continue
            approach = s['melee_range'] if hybrid else s['range']
            if d > approach*.8 or not visible:
                self.enemy_move_towards(e,target.x,target.y,dt)
            elif s.get('combat_role') == 'ranged' and d < 115:
                rx=e.x-e.facing[0]*60;ry=e.y-e.facing[1]*60
                if math.hypot(rx-e.home_x,ry-e.home_y)<s['leash']*.8:
                    self.enemy_move_towards(e,rx,ry,dt,.6)
            # Melee and throwing have separate cooldowns. A shot never defines
            # the stopping distance for a hybrid, including every boss.
            if d <= s['melee_range'] and self.time >= e.ready and visible:
                e.ready=self.time+1.35;e.attack_until=self.time+.3
                damage=s['melee_damage'] if s.get('projectile') else s['damage']
                self.damage_player(target,damage)
                self.combat_effect(e,'sword',target,duration=.25)
            elif s.get('projectile') and d <= s['range'] and visible and self.time >= max(e.ready,e.ranged_ready):
                e.ranged_ready=self.time+s['ranged_interval']
                self.queue_enemy_attack(e,target)
            elif not s.get('projectile') and d <= s['range'] and self.time >= e.ready and visible:
                e.ready=self.time+s['attack_interval'];e.attack_until=self.time+.3
                self.damage_player(target,s['damage'])
                self.combat_effect(e,'sword',target,duration=.25)
