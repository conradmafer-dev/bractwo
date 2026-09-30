"""Server-authoritative professions, spells, services and travel for 0.4."""
import math
import secrets
try:
    from . import world_content as content
    from .profession_rules import PROMOTION_LEVEL, PROMOTION_COST, promotion_requirements
except ImportError:
    import world_content as content
    from profession_rules import PROMOTION_LEVEL, PROMOTION_COST, promotion_requirements


def same_floor(a,b):
    def floor(o): return o.get('floor',0) if isinstance(o,dict) else getattr(o,'floor',0)
    return floor(a)==floor(b)


def near(p, obj, radius=None):
    return same_floor(p,obj) and math.hypot(p.x-obj['x'],p.y-obj['y']) <= (obj.get('radius',125) if radius is None else radius)


def skill_level(p, skill):
    divisor=150 if skill=='magic' else 30
    return (1 if skill=='magic' else 10)+math.isqrt(max(0,int(p.skill_tries.get(skill,0)))//divisor)


def skill_progress(p):
    result={}
    for key in ('melee','distance','magic','shielding'):
        level=skill_level(p,key);steps=level-(1 if key=='magic' else 10);divisor=150 if key=='magic' else 30
        result[key]={'level':level,'progress':int(p.skill_tries.get(key,0))-steps*steps*divisor,'next':(2*steps+1)*divisor}
    return result


def train(p,key,amount=1):
    p.skill_tries[key]=int(p.skill_tries.get(key,0))+int(amount)


def merchant_at(p, npc_id=None):
    sellers = [getattr(content, 'STARTER_MERCHANT', None)] + [
        n for n in content.NPCS if n.get('service') == 'merchant']
    nearby = [n for n in sellers if n and (npc_id is None or n.get('id','starter_merchant')==npc_id) and near(p, n)]
    return min(nearby, key=lambda n: math.hypot(p.x-n['x'], p.y-n['y']), default=None)


def merchant_state(p):
    seller = merchant_at(p)
    return ({'id': seller.get('id', 'starter_merchant'), 'name': seller['name'],
             'stock': list(seller.get('stock', []))} if seller else None)


def private_state(p,now):
    return {'site_cooldowns':{key:max(0,round(until-now)) for key,until in p.site_cooldowns.items() if until>now},
      'wind_remaining':max(0,p.wind_until-now), 'ward_remaining':max(0,p.ward_until-now), 'premium_demo':p.premium_demo_until>now,'premium_demo_remaining':max(0,int(p.premium_demo_until-now)),
      'surface':content.SURFACE_MAP.at(p.x,p.y,p.floor), 'floor':p.floor,'promoted':p.promoted,'profession':content.PROMOTIONS[p.class_id] if p.promoted else p.spec['name'],
      'promotion':promotion_requirements(),
      'skills':skill_progress(p),'runes':dict(p.runes),'soul':int(p.soul),'max_soul':200 if p.promoted else 100,
      'bank_gold':p.bank_gold,'depot':list(p.depot),'home_city':p.home_city,'blessed':p.blessed,
      'merchant':merchant_state(p),
      'mastery':dict(p.mastery),'mastery_points':max(0,(p.level-50)//5+1-sum(p.mastery.values())) if p.level>=50 and p.promoted else 0,
      'spell_cooldowns':{key:round(max(0,until-now),1) for key,until in p.spell_cooldowns.items() if until>now},
      'haste_remaining':max(0,p.haste_until-now),'rune_cooldown':max(0,p.rune_ready-now)}


class ExpansionGame:
    def reindex_enemy(self, enemy):
        """Keep the spatial index at the live position, or at a corpse's respawn.

        Updating only on cell boundaries avoids an all-monster rebuild per tick.
        Legacy IDs retain their small, always-queried compatibility list.
        """
        if not enemy.id.startswith('world_'):
            return
        x, y = (enemy.x, enemy.y) if enemy.alive else (enemy.home_x, enemy.home_y)
        key = (enemy.floor, int(x//1024), int(y//1024))
        previous = self.enemy_cell_keys.get(enemy.id)
        if previous == key:
            return
        if previous is not None:
            bucket = self.enemy_cells.get(previous, {})
            bucket.pop(enemy.id, None)
            if not bucket:
                self.enemy_cells.pop(previous, None)
        self.enemy_cells.setdefault(key, {})[enemy.id] = enemy
        self.enemy_cell_keys[enemy.id] = key

    def nearby_enemies(self,p,radius):
        if p is None:return []
        result=list(self.legacy_enemies)
        # Living actors are indexed where they are, not where they spawned.
        for cx in range(int((p.x-radius)//1024), int((p.x+radius)//1024)+1):
            for cy in range(int((p.y-radius)//1024), int((p.y+radius)//1024)+1):
                result.extend(self.enemy_cells.get((p.floor,cx,cy),{}).values())
        return result

    def near_service(self,p,service,npc_id=None):
        return next((n for n in content.NPCS if n.get('service')==service and (npc_id is None or n['id']==npc_id) and near(p,n)),None)

    def merchant_near(self,p):
        return merchant_at(p) is not None

    async def boat_command(self, p, data):
        if not p.alive or p.combat_until > self.now():
            return await self.notice(p, 'Rejs jest dostępny poza walką, dla żywej postaci.')
        route_id = data.get('route_id')
        route = next((r for r in getattr(content, 'SEA_ROUTES', []) if r['id'] == route_id), None)
        if route is None:
            return await self.notice(p, 'Wybierz połączenie z tablicy miejscowego przewoźnika.')
        source = next((port for port in content.PORTS if port['id'] == route['from_id']), None)
        destination = next((port for port in content.PORTS if port['id'] == route['to_id']), None)
        boatman = next((n for n in content.NPCS if source and n['id'] == source.get('npc_id')), None)
        if not boatman or not near(p, boatman) or route_id not in boatman.get('routes', []):
            return await self.notice(p, 'Podejdź do przewoźnika obsługującego ten rejs.')
        if not destination:
            return await self.notice(p, 'Nie odnaleziono przystani docelowej.')
        if p.gold < route['cost']:
            return await self.notice(p, f"Rejs kosztuje {route['cost']} złota. Brakuje {route['cost'] - p.gold} złota.")
        x, y, floor = destination['x'], destination['y'], destination.get('floor', 0)
        if self.blocked(x, y, floor=floor):
            return await self.notice(p, 'Przystań docelowa jest niedostępna.')
        self.cancel_rest(p);self.cancel_channel(p, '');self.stop_auto(p)
        self.break_concentration(p);self.companions.pop(p.id, None);self.familiars.pop(p.id, None)
        p.gold -= route['cost']
        p.x, p.y, p.floor = x, y, floor
        p.dx = p.dy = 0
        p.input_time = -10
        self.discover_landmarks(p)
        self.persist()
        await self.notice(p, f"Dopłynąłeś do: {destination['name']}.")

    def stairs_near(self,p):
        return sorted((s for s in content.STAIRS if near(p,s)),key=lambda s:math.hypot(p.x-s['x'],p.y-s['y']))

    async def expansion_command(self,p,kind,data):
        if not p.alive:
            return
        now=self.now()
        if kind=='cast':
            return await self.cast_spell(p,data.get('spell_id'),data.get('enemy_id'),data.get('target_id'))
        if kind in ('rune_use','rune_craft','rune_buy'):
            if kind=='rune_use' and ('enemy_id' in data and (not isinstance(data['enemy_id'],str) or not data['enemy_id']) or data.get('target_id') is not None):
                return await self.notice(p,'Wybierz prawidłowy cel potwora dla runy.')
            return await self.rune_command(p,kind,data.get('rune_id'),data.get('enemy_id'))
        if kind=='descend':
            stairs=self.stairs_near(p)
            if not stairs:return await self.notice(p,'Podejdź do schodów lub wejścia do podziemi [E].')
            s=stairs[0]
            if now<p.transition_ready:return
            if p.pvp_combat_until>now:return await self.notice(p,'Po walce PvP poczekaj przed zmianą piętra.')
            if p.level<s['min_level']:return await self.notice(p,f'Pieczęć wymaga poziomu {s["min_level"]}.')
            if self.blocked(s['to_x'],s['to_y'],floor=s['to_floor']):return await self.notice(p,'Przejście jest niedostępne.')
            p.x,p.y,p.floor=s['to_x'],s['to_y'],s['to_floor']
            self.stop_auto(p);self.break_concentration(p);self.companions.pop(p.id,None)
            p.dx=p.dy=0;p.input_time=-10;p.transition_ready=now+1
            self.persist()
            return await self.notice(p,f'{s["name"]} · piętro {p.floor:+d}.')
        if p.combat_until>now:return await self.notice(p,'Najpierw zakończ walkę i odczekaj blokadę.')
        if kind=='travel':
            if getattr(content, 'SEA_ROUTES', None):
                # Older clients may request a city; still enforce the local route graph.
                port = self.near_service(p, 'boat')
                destination = next((c for c in content.PORTS if c.get('city_id') == data.get('city_id')), None)
                route = next((r for r in content.SEA_ROUTES if port and destination
                              and r['id'] in port.get('routes', []) and r['to_id'] == destination['id']), None)
                return await self.boat_command(p, {'route_id': route['id'] if route else None})
            port=self.near_service(p,'captain')
            target=next((c for c in content.CITIES if c['id']==data.get('city_id')),None)
            if not port:return await self.notice(p,'Podejdź do kapitana w mieście.')
            if p.level<8:return await self.notice(p,'Rejsy są dostępne od poziomu 8.')
            if target is None or port['city_id']==target['id']:return await self.notice(p,'Wybierz inne miasto.')
            cost=40+int(math.hypot(p.x-target['x'],p.y-target['y'])/1000)*8
            if p.gold<cost:return await self.notice(p,f'Koszt podróży: {cost} złota.')
            p.gold-=cost;p.x,p.y,p.floor=target['x'],target['y'],0
            self.stop_auto(p);self.break_concentration(p);self.companions.pop(p.id,None)
            p.dx=p.dy=0;p.input_time=-10
            self.discover_landmarks(p)
        elif kind=='bind_city':
            stone_id=data.get('npc_id')
            stone=next((n for n in content.BINDING_STONES if n['id']==stone_id and near(p,n)),None)
            if stone is None:return await self.notice(p,'Podejdź do kamienia przypisania w mieście.')
            p.home_city=stone['city_id']
        elif kind in ('bank_deposit','bank_withdraw','depot_store','depot_take'):
            bank=self.near_service(p,'bank',data.get('npc_id'))
            if not bank:return await self.notice(p,'Bank i depozyt są dostępne przy bankierze.')
            if kind.startswith('bank_'):
                balance=p.gold if kind=='bank_deposit' else p.bank_gold
                amount=data.get('amount')
                if amount=='all':amount=balance
                if type(amount) is not int or not 0<amount<=balance:return await self.notice(p,'Podaj dostępną kwotę (liczba całkowita).')
                if kind=='bank_deposit':p.gold-=amount;p.bank_gold+=amount
                else:p.gold+=amount;p.bank_gold-=amount
            else:
                storing=kind=='depot_store';source=p.inventory if storing else p.depot;dest=p.depot if storing else p.inventory
                uid=data.get('uid');item=next((i for i in source if i['uid']==uid),None)
                if item is None or (storing and uid in p.equipment.values()):return await self.notice(p,'Najpierw zdejmij przedmiot, który chcesz odłożyć.')
                if len(dest)>=(120 if storing else 40):return await self.notice(p,'Brak wolnego miejsca.')
                source.remove(item);dest.append(item)
        elif kind in ('promote','bless','mastery','mastery_reset'):
            if kind != 'mastery' and not self.near_service(p,'master',data.get('npc_id')):return await self.notice(p,'Podejdź do mistrza profesji w dowolnym mieście.')
            if kind=='promote':
                if p.promoted or p.level<PROMOTION_LEVEL or p.gold<PROMOTION_COST:
                    return await self.notice(p,f'Promocja wymaga poziomu {PROMOTION_LEVEL} i {PROMOTION_COST} złota; można ją kupić tylko raz.')
                p.gold-=PROMOTION_COST;p.promoted=True;p.soul=min(200,p.soul+100)
            elif kind=='bless':
                if p.blessed or p.level<40 or p.gold<500:return await self.notice(p,'Błogosławieństwo: poziom 40, 500 złota; działa na jedną śmierć.')
                p.gold-=500;p.blessed=True
            elif kind=='mastery':
                branch=data.get('branch')
                if p.level<50 or not p.promoted:return await self.notice(p,'Mistrzostwo wymaga promocji i poziomu 50.')
                points=(p.level-50)//5+1-sum(p.mastery.values())
                if not isinstance(branch,str) or branch not in ('power','focus') or points<1 or p.mastery.get(branch,0)>=20:
                    return await self.notice(p,'Brak punktu lub wybrana gałąź osiągnęła 20 punktów.')
                p.mastery[branch]=p.mastery.get(branch,0)+1
            else:
                if not sum(p.mastery.values()):return
                if p.gold<200:return await self.notice(p,'Zmiana przydziału punktów mistrzostwa kosztuje 200 złota.')
                p.gold-=200;p.mastery={};p.hp=min(p.hp,p.max_hp);p.mana=min(p.mana,p.max_mana)
        else:return
        self.persist()
        await self.notice(p,{'travel':'Dotarłeś do portu. Kup zapasy i sprawdź atlas.', 'promote':f'Nowa profesja: {content.PROMOTIONS[p.class_id]}.',
            'bless':'Błogosławieństwo chroni połowę zwykłej kary następnej śmierci.', 'bind_city':'To miasto jest teraz twoim miejscem odrodzenia.'}.get(kind,'Zapisano.'))

    async def rune_command(self,p,kind,key,enemy_id=None):
        return await self.notice(p,"Dawne runy zastąpiła księga czarów [K]. Przy migracji zwrócono za nie złoto.")
