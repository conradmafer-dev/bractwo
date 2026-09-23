"""Server-authoritative professions, spells, services and travel for 0.4."""
import math
import secrets
try:
    from . import world_content as content
except ImportError:
    import world_content as content


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


def private_state(p,now):
    return {'site_cooldowns':{key:max(0,round(until-now)) for key,until in p.site_cooldowns.items() if until>now},
      'wind_remaining':max(0,p.wind_until-now), 'ward_remaining':max(0,p.ward_until-now), 'premium_demo':p.premium_demo_until>now,'premium_demo_remaining':max(0,int(p.premium_demo_until-now)),
      'surface':content.SURFACE_MAP.at(p.x,p.y,p.floor), 'floor':p.floor,'promoted':p.promoted,'profession':content.PROMOTIONS[p.class_id] if p.promoted else p.spec['name'],
      'skills':skill_progress(p),'runes':dict(p.runes),'soul':int(p.soul),'max_soul':200 if p.promoted else 100,
      'bank_gold':p.bank_gold,'depot':list(p.depot),'home_city':p.home_city,'blessed':p.blessed,
      'mastery':dict(p.mastery),'mastery_points':max(0,(p.level-50)//5+1-sum(p.mastery.values())) if p.level>=50 and p.promoted else 0,
      'spell_cooldowns':{key:round(max(0,until-now),1) for key,until in p.spell_cooldowns.items() if until>now},
      'haste_remaining':max(0,p.haste_until-now),'rune_cooldown':max(0,p.rune_ready-now)}


class ExpansionGame:
    def nearby_enemies(self,p,radius):
        if p is None:return []
        # Include fixed legacy actors for backward-compatible fixtures and IDs.
        result=list(self.legacy_enemies)
        pad=radius+1120  # includes the 1100-unit boss leash, indexed by home
        for cx in range(int((p.x-pad)//1024), int((p.x+pad)//1024)+1):
            for cy in range(int((p.y-pad)//1024), int((p.y+pad)//1024)+1):
                result.extend(self.enemy_cells.get((p.floor,cx,cy),[]))
        return result

    def near_service(self,p,service):
        return next((n for n in content.NPCS if n.get('service')==service and near(p,n)),None)

    def merchant_near(self,p):
        return (p.floor==0 and math.hypot(p.x-680,p.y-1180)<=150) or bool(self.near_service(p,'merchant'))

    def stairs_near(self,p):
        return sorted((s for s in content.STAIRS if near(p,s)),key=lambda s:math.hypot(p.x-s['x'],p.y-s['y']))

    async def expansion_command(self,p,kind,data):
        if not p.alive:
            return
        now=self.now()
        if kind=='cast':
            return await self.cast_spell(p,data.get('spell_id'))
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
            p.dx=p.dy=0;p.input_time=-10;p.transition_ready=now+1
            self.persist()
            return await self.notice(p,f'{s["name"]} · piętro {p.floor:+d}.')
        if p.combat_until>now:return await self.notice(p,'Najpierw zakończ walkę i odczekaj blokadę.')
        if kind=='travel':
            port=self.near_service(p,'captain')
            target=next((c for c in content.CITIES if c['id']==data.get('city_id')),None)
            if not port:return await self.notice(p,'Podejdź do kapitana w mieście.')
            if p.level<8:return await self.notice(p,'Rejsy są dostępne od poziomu 8.')
            if target is None or port['city_id']==target['id']:return await self.notice(p,'Wybierz inne miasto.')
            cost=40+int(math.hypot(p.x-target['x'],p.y-target['y'])/1000)*8
            if p.gold<cost:return await self.notice(p,f'Koszt podróży: {cost} złota.')
            p.gold-=cost;p.x,p.y,p.floor=target['x'],target['y'],0
            p.dx=p.dy=0;p.input_time=-10
            self.discover_landmarks(p)
        elif kind in ('bank_deposit','bank_withdraw','depot_store','depot_take','bind_city'):
            bank=self.near_service(p,'bank')
            if not bank:return await self.notice(p,'Bank i depozyt są dostępne przy bankierze.')
            if kind=='bind_city':p.home_city=bank['city_id']
            elif kind.startswith('bank_'):
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
            if not self.near_service(p,'master'):return await self.notice(p,'Podejdź do mistrza profesji w dowolnym mieście.')
            if kind=='promote':
                if p.promoted or p.level<20 or p.gold<2000:return await self.notice(p,'Promocja wymaga poziomu 20 i 2000 złota; można ją kupić tylko raz.')
                p.gold-=2000;p.promoted=True;p.soul=min(200,p.soul+100)
            elif kind=='bless':
                if p.blessed or p.level<40 or p.gold<500:return await self.notice(p,'Błogosławieństwo: poziom 40, 500 złota; działa na jedną śmierć.')
                p.gold-=500;p.blessed=True
            elif kind=='mastery':
                branch=data.get('branch')
                if p.level<50 or not p.promoted:return await self.notice(p,'Specjalizacja wymaga promocji i poziomu 50.')
                points=(p.level-50)//5+1-sum(p.mastery.values())
                if not isinstance(branch,str) or branch not in ('power','vitality','focus') or points<1 or p.mastery.get(branch,0)>=20:
                    return await self.notice(p,'Brak punktu lub wybrana gałąź osiągnęła 20 punktów.')
                p.mastery[branch]=p.mastery.get(branch,0)+1
            else:
                if not sum(p.mastery.values()):return
                if p.gold<200:return await self.notice(p,'Zmiana specjalizacji kosztuje 200 złota.')
                p.gold-=200;p.mastery={};p.hp=min(p.hp,p.max_hp);p.mana=min(p.mana,p.max_mana)
        else:return
        self.persist()
        await self.notice(p,{'travel':'Dotarłeś do portu. Kup zapasy i sprawdź atlas.', 'promote':f'Nowa profesja: {content.PROMOTIONS[p.class_id]}.',
            'bless':'Błogosławieństwo chroni połowę zwykłej kary następnej śmierci.', 'bind_city':'To miasto jest teraz twoim miejscem odrodzenia.'}.get(kind,'Zapisano.'))

    async def cast_spell(self,p,key):
        spec=content.SPELLS.get(key) if isinstance(key,str) else None
        now=self.now()
        if spec is None:return await self.notice(p,'Nieznany czar.')
        if p.level<spec['min_level'] or (spec.get('promotion') and not p.promoted) or p.class_id not in spec.get('class_ids',[p.class_id]):
            return await self.notice(p,'Nie spełniasz wymagań czaru. Sprawdź księgę rozwoju [K].')
        if now<max(p.spell_cooldowns.get(key,0),p.spell_ready):return
        if p.mana<spec['mana']:return await self.notice(p,'Za mało many.')
        targets=[]
        if spec['kind']=='heal' and p.hp>=p.max_hp:return await self.notice(p,'Masz pełne zdrowie.')
        if spec['kind']=='area':
            targets=[e for e in self.nearby_enemies(p, 650) if e.alive and same_floor(p,e) and math.hypot(p.x-e.x,p.y-e.y)<=spec['radius'] and self.line_clear(p,e)]
            if self.in_safe(p) or not targets:return await self.notice(p,'Brak potworów w zasięgu poza strefą ochronną.')
        p.mana-=spec['mana'];train(p,'magic',spec['mana'])
        p.spell_cooldowns[key]=now+spec['cooldown'];p.spell_ready=now+1
        if spec['kind']=='heal':
            p.hp=min(p.max_hp,p.hp+35+p.level*3+skill_level(p,'magic')*2)
            self.combat_effect(p,'heal',p,radius=60,duration=.8)
        elif spec['kind']=='haste':
            p.haste_until=now+15;self.combat_effect(p,'haste',p,radius=60,duration=.8)
        else:
            self.tag(p)
            self.combat_effect(p,spec['effect'],min(targets,key=lambda e:math.hypot(p.x-e.x,p.y-e.y)),radius=spec['radius'],duration=.9)
            for e in targets:
                e.hp=max(0,e.hp-p.attack*spec['multiplier']);self.remember_attacker(e,p)
                if p.class_id=='druid':e.slow_until=self.time+4
            for e in targets:
                if e.hp<=0:await self.defeat(e)
        p.speech_text,p.speech_until=spec['words'],self.time+2
        self.persist()

    async def rune_command(self,p,kind,key,enemy_id=None):
        spec=content.RUNES.get(key) if isinstance(key,str) else None
        now=self.now()
        if spec is None or p.level<spec['min_level']:return await self.notice(p,'Runa wymaga wyższego poziomu. Sprawdź księgę [K].')
        count=p.runes.get(key,0)
        if kind=='rune_buy':
            if not self.merchant_near(p) or p.combat_until>now:return await self.notice(p,'Kupuj runy przy kupcu, poza walką.')
            if count>=99 or p.gold<spec['price']:return await self.notice(p,'Za mało złota albo masz już 99 run.')
            p.gold-=spec['price'];p.runes[key]=count+1
        elif kind=='rune_craft':
            if now<p.rune_ready:return
            if p.class_id not in ('mage','druid') or count>=99 or p.mana<spec['mana'] or p.soul<spec['soul']:
                return await self.notice(p,'Runy tworzą magowie i druidzi: potrzebujesz many, duszy i miejsca (99 run).')
            p.mana-=spec['mana'];p.soul-=spec['soul'];train(p,'magic',spec['mana'])
            p.runes[key]=count+1;p.rune_ready=now+2
        else:
            if now<max(p.rune_ready,p.spell_ready):return
            if count<1:return await self.notice(p,'Nie masz tej runy.')
            targets=sorted((e for e in self.nearby_enemies(p, 650) if e.alive and same_floor(p,e) and math.hypot(p.x-e.x,p.y-e.y)<=310 and self.line_clear(p,e)),key=lambda e:math.hypot(p.x-e.x,p.y-e.y))
            if enemy_id is not None:
                selected=self.selected_enemy(p,enemy_id,310)
                if selected is None:return await self.notice(p,'Wybrany potwór jest poza zasięgiem runy lub za ścianą.')
                targets=[selected]
            if self.in_safe(p) or not targets:return await self.notice(p,'Brak potwora w zasięgu runy.')
            target=targets[0]
            hits=[target] if spec['radius']==0 else [e for e in self.nearby_enemies(p, 650) if e.alive and same_floor(p,e) and math.hypot(target.x-e.x,target.y-e.y)<=spec['radius'] and self.line_clear(p,e) and self.line_clear(target,e)]
            p.runes[key]=count-1;p.rune_ready=now+3;p.spell_ready=now+1
            self.tag(p);fx=self.combat_effect(p,spec['effect'],target,radius=spec['radius'],duration=.9)
            if spec['radius']:fx['x'],fx['y']=target.x,target.y
            for e in hits:
                e.hp=max(0,e.hp-(p.attack+skill_level(p,'magic')*2)*spec['power']);self.remember_attacker(e,p)
                if key=='ice':e.slow_until=self.time+3
            for e in hits:
                if e.hp<=0:await self.defeat(e)
        self.persist()
