"""Chase, local search, then an interruptible walk home (never an HP reset)."""
import math
import zlib
from types import SimpleNamespace
try:
    from . import world_content as content, environment_rules as environment
    from .living_world import SURFACES
except ImportError:
    import world_content as content, environment_rules as environment
    from living_world import SURFACES


ACTIVE_RADIUS = 1450
SIGHT_MEMORY_SECONDS = 12.0
REGEN_DELAY_SECONDS = 12.0
IDLE_REGEN_PER_SECOND = 0.25
SEARCH_SECONDS = 24.0
SEARCH_RADIUS = 68.0
RETURN_SPEED_FACTOR = 0.7


class MonsterAI:
    def provoke_enemy(self, enemy, source):
        """A hit or attempted attack prevents patrol even if the source disappears."""
        enemy.attacker_id, enemy.attacker_until = source.id, self.time + 20
        enemy.has_engaged = True
        enemy.return_at = 0
        enemy.returning = False
        self.recovering_enemies.pop(enemy.id, None)
        enemy.regen_at = max(enemy.regen_at, self.time + REGEN_DELAY_SECONDS)
        self.chasing_enemies[enemy.id] = enemy

    def stop_enemy_chase(self, enemy):
        """Start a fixed local-search timer only once, not again every tick."""
        active = enemy.chase_id or enemy.attacker_id or enemy.id in self.chasing_enemies
        if not active:return
        enemy.regen_at = max(enemy.regen_at, self.time + REGEN_DELAY_SECONDS)
        enemy.has_engaged = True
        enemy.chase_id = ''
        enemy.attacker_id, enemy.attacker_until = '', 0
        enemy.taunt_id, enemy.taunt_until = '', 0
        enemy.last_seen_until = 0
        enemy.search_x, enemy.search_y = enemy.x, enemy.y
        enemy.wander_x, enemy.wander_y = enemy.x, enemy.y
        enemy.wander_ready = self.time + 1.5
        enemy.return_at = self.time + SEARCH_SECONDS
        enemy.returning = False
        self.chasing_enemies.pop(enemy.id, None)
        self.recovering_enemies[enemy.id] = enemy

    def record_home_trail(self, e):
        # Waypoints are actual walked positions, including successful detours.
        if not e.home_trail:
            e.home_trail.append((e.home_x, e.home_y))
        if math.dist(e.home_trail[-1], (e.x, e.y)) >= 28:
            e.home_trail.append((e.x, e.y))
        if len(e.home_trail) > 1024:
            # Keep origin and distributed historical waypoints, bounded memory.
            e.home_trail = e.home_trail[::2]

    def enemy_move_towards(self, e, x, y, dt, factor=1):
        if environment.immobile(e,self.now()) or self.enemy_condition(e,'prone'):return
        dx,dy=x-e.x,y-e.y
        length=math.hypot(dx,dy)
        if length<4:return
        s=environment.enemy_spec(e)
        speed=s['speed']*factor
        if e.slow_until>self.time or self.enemy_condition(e,'slow'):speed*=.5
        if self.enemy_condition(e,'growth'):speed*=.25
        e.dx,e.dy=dx/length,dy/length
        self.environment_bind(e)
        speed=environment.movement_speed(e,speed,SURFACES[content.SURFACE_MAP.at(e.x,e.y,e.floor)]['speed'])
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
        if e.chase_id or e.id in self.chasing_enemies:self.record_home_trail(e)

    def roam_enemy(self, e, dt):
        s=environment.enemy_spec(e)
        if e.has_engaged:
            if not e.return_at:
                # Compatibility with an already-disengaged runtime actor.
                e.search_x,e.search_y=e.x,e.y
                e.return_at=self.time+SEARCH_SECONDS
                self.recovering_enemies[e.id]=e
            if self.time >= e.return_at:
                e.returning=True
                while e.home_trail and math.dist((e.x,e.y),e.home_trail[-1])<26:
                    e.home_trail.pop()
                point=e.home_trail[-1] if e.home_trail else (e.home_x,e.home_y)
                self.enemy_move_towards(e,*point,dt,RETURN_SPEED_FACTOR)
                if math.hypot(e.x-e.home_x,e.y-e.home_y)<28:
                    e.return_at=0;e.returning=False;e.has_engaged=False
                    e.home_trail.clear();e.wander_ready=self.time+2
                    self.recovering_enemies.pop(e.id,None)
                return
            anchor_x,anchor_y=e.search_x,e.search_y
            wander=min(SEARCH_RADIUS,s['wander'])
        else:
            anchor_x,anchor_y=e.home_x,e.home_y
            wander=s['wander']
            if math.hypot(e.x-e.home_x,e.y-e.home_y)>wander+45:
                self.enemy_move_towards(e,e.home_x,e.home_y,dt,.8)
                return
        if self.time>=e.wander_ready:
            seed=zlib.crc32(e.id.encode())
            phase=seed*.001+int(self.time/6)*2.39996
            radius=wander*(.35+((seed+int(self.time/6))%61)/100)
            e.wander_x=anchor_x+math.cos(phase)*radius
            e.wander_y=anchor_y+math.sin(phase*1.37)*radius*.75
            e.wander_ready=self.time+4+(seed%50)/10
            e.rest_until=self.time+(seed%15)/10
        if self.time>e.rest_until:
            self.enemy_move_towards(e,e.wander_x,e.wander_y,dt,.32)

    def queue_enemy_attack(self,e,target,projectile=None,special=False):
        if environment.actions_blocked(e,self.now()):return
        s=environment.enemy_spec(e)
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

    def enemy_escape_control(self,e,chosen=None):
        """Spend the next action escaping Web/a whirlpool when no foe is in reach."""
        now=self.now()
        if environment.actions_blocked(e,now) or self.time<max(e.ready,e.ranged_ready,e.cast_until):return False
        if chosen and chosen[2] and chosen[1]<=environment.enemy_spec(e)['melee_range']:return False
        values=environment.conditions(e)
        for key in ('web_restrained','whirlpool'):
            value=values.get(key,{})
            if value.get('until',0)<=now:continue
            escaped=values.get('whirlpool_escape',{})
            if key=='whirlpool' and escaped.get('until',0)>now and escaped.get('field_id')==value.get('field_id'):continue
            result=self.environment_ability_check(e,'strength',value['dc'],'athletics')
            e.ready=e.ranged_ready=e.cast_until=self.time+3
            if result['saved']:
                if key=='web_restrained':values.pop(key,None)
                else:values['whirlpool_escape']=dict(until=now+3,field_id=value.get('field_id'))
            return True
        return False

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
            for p in (*self.players.values(), *self.companions.values(), *self.familiars.values()):
                if p.alive and p.floor==h['floor'] and not self.in_safe(p) and math.hypot(p.x-target.x,p.y-target.y)<=h['radius']+12 and self.line_clear(origin,p):
                    self.hit_player(e,p,h['damage'],area=h['special'],damage_kind={'fire':'fire','ice':'cold','venom':'poison','arrow':'piercing','magic':'force','shadow':'necrotic'}.get(h['element'],'bludgeoning'))
        self.hazards=waiting

    def step_monsters(self, dt, player_cells, unsafe_ids):
        self.resolve_hazards()
        active = {e.id: e for p in self.players.values() if p.alive
                  for e in self.nearby_enemies(p, ACTIVE_RADIUS)}
        # Evaluate each running chase once more if its player left the simulation
        # area, died, changed floor or disconnected. Never scan all world actors.
        active.update(self.chasing_enemies)
        active.update(self.recovering_enemies)
        local_cache = {}
        for e in active.values():
            if not e.alive:
                self.chasing_enemies.pop(e.id, None)
                self.recovering_enemies.pop(e.id, None)
                if e.respawn_at and self.time >= e.respawn_at:
                    e.alive, e.hp = True, e.max_hp
                    e.x, e.y = e.home_x, e.home_y
                    e.contributors.clear()
                    e.attacker_id, e.attacker_until = '', 0
                    e.ready, e.aoe_ready = self.time + 1, self.time + 4
                    e.taunt_id, e.taunt_until = '', 0
                    e.conditions.clear()
                    e.cast_until = e.attack_until = e.slow_until = 0
                    e.wander_ready = e.rest_until = e.special_count = 0
                    e.ranged_ready, e.mobile_cast = self.time + 2, False
                    e.has_engaged, e.chase_id = False, ''
                    e.return_at = 0;e.returning = False;e.home_trail.clear()
                    e.last_seen_x, e.last_seen_y = e.x, e.y
                    e.last_seen_until = e.regen_at = e.respawn_at = 0
                    self.reindex_enemy(e)
                    if e.kind == 'boss':
                        self.flags.update(boss_defeated=False, event_active=True)
                continue
            if e.hp <= 0:
                # The asynchronous reward/death phase will finalize the kill.
                # Never heal or act in the intervening simulation tick.
                continue
            cell = (e.floor, int(e.x//1024), int(e.y//1024))
            if cell not in local_cache:
                # A boss may see a target 1100 units away across TWO cell edges.
                local_cache[cell] = [p for dx in range(-2, 3) for dy in range(-2, 3)
                    for p in player_cells.get((cell[0], cell[1]+dx, cell[2]+dy), ())]
            nearby = local_cache[cell]
            if (e.id not in self.chasing_enemies and e.id not in self.recovering_enemies and not e.chase_id
                    and not any(math.hypot(p.x-e.x, p.y-e.y) < ACTIVE_RADIUS for p in nearby)):
                continue
            e.current_wall_time=self.now()
            if environment.actions_blocked(e,self.now()):continue
            spec = environment.enemy_spec(e)
            candidates = []
            for player in nearby:
                if player.id not in unsafe_ids or not player.alive or player.floor != e.floor:
                    continue
                distance = math.hypot(player.x-e.x, player.y-e.y)
                # The old value is retained as a *relative* loss distance, not
                # a circle around the spawn. Crossing the spawn boundary is harmless.
                if distance >= spec['leash']:
                    continue
                provoked = ((e.attacker_until > self.time and player.id == e.attacker_id)
                    or (e.taunt_until > self.time and player.id == e.taunt_id))
                pursuing = player.id == e.chase_id
                if not (provoked or pursuing or distance < spec['aggro']):
                    continue
                visible = self.environment_can_see(e, player)
                if not visible:
                    # Pursue the last SEEN position, not live coordinates through
                    # a wall. The timer does not refresh itself while occluded.
                    if pursuing and self.time >= e.last_seen_until:
                        continue
                    if not pursuing and not provoked:
                        continue
                candidates.append((player, distance, visible))
            chosen = next((c for c in candidates if e.taunt_until > self.time and c[0].id == e.taunt_id), None)
            if chosen is None:
                chosen = next((c for c in candidates if e.attacker_until > self.time and c[0].id == e.attacker_id), None)
            if chosen is None:
                chosen = next((c for c in candidates if c[0].id == e.chase_id), None)
            if chosen is None and candidates:
                chosen = min(candidates, key=lambda c: c[1])
            if self.enemy_escape_control(e,chosen):continue
            if chosen is None:
                self.stop_enemy_chase(e)
                self.roam_enemy(e, dt)
                if self.time >= e.regen_at:
                    e.hp = min(e.max_hp, e.hp + dt * IDLE_REGEN_PER_SECOND)
                continue
            target, distance, visible = chosen
            if visible or e.chase_id != target.id:
                e.last_seen_x, e.last_seen_y = target.x, target.y
                e.last_seen_until = self.time + SIGHT_MEMORY_SECONDS
            e.chase_id, e.has_engaged = target.id, True
            e.return_at=0;e.returning=False
            self.recovering_enemies.pop(e.id,None)
            self.record_home_trail(e)
            e.regen_at = self.time + REGEN_DELAY_SECONDS
            self.chasing_enemies[e.id] = e
            d = max(1, distance)
            aim_x, aim_y = (target.x, target.y) if visible else (e.last_seen_x, e.last_seen_y)
            facing_distance = max(1, math.hypot(aim_x-e.x, aim_y-e.y))
            e.facing = [(aim_x-e.x)/facing_distance, (aim_y-e.y)/facing_distance]
            hybrid = spec.get('combat_role') == 'hybrid'
            if self.time < e.cast_until:
                if hybrid and e.mobile_cast and d > spec['melee_range']*.8:
                    self.enemy_move_towards(e, aim_x, aim_y, dt, .7)
                continue
            if not visible:
                self.enemy_move_towards(e, aim_x, aim_y, dt)
                continue
            if spec.get('boss') and self.time >= e.aoe_ready and d < spec['special_range']:
                e.aoe_ready = self.time + (6 if e.hp < e.max_hp*.4 else 8)
                self.queue_enemy_attack(e, target, special=True)
                e.ready = max(e.ready, self.time + 1.4)
                continue
            approach = spec['melee_range'] if hybrid else spec['range']
            if d > approach*.8:
                self.enemy_move_towards(e, target.x, target.y, dt)
            elif spec.get('combat_role') == 'ranged' and d < 115:
                # Tactical spacing is relative to the foe, never to the spawn.
                self.enemy_move_towards(e, e.x-e.facing[0]*60, e.y-e.facing[1]*60, dt, .6)
            if d <= spec['melee_range'] and self.time >= e.ready:
                e.ready = self.time + spec['attack_interval']
                e.attack_until = self.time + .3
                damage = spec['melee_damage'] if spec.get('projectile') else spec['damage']
                self.hit_player(e, target, damage)
                self.combat_effect(e, 'sword', target, duration=.25)
            elif (spec.get('projectile') and d <= spec['range']
                    and self.time >= max(e.ready, e.ranged_ready)):
                e.ranged_ready = self.time + spec['ranged_interval']
                e.ready = self.time + spec['attack_interval']
                self.queue_enemy_attack(e, target)
            elif not spec.get('projectile') and d <= spec['range'] and self.time >= e.ready:
                e.ready = self.time + spec['attack_interval']
                e.attack_until = self.time + .3
                self.hit_player(e, target, spec['damage'])
                self.combat_effect(e, 'sword', target, duration=.25)
