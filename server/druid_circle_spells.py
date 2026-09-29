"""Circle bonus spells, PHB 2024 mechanics in Bractwo's distance/round units.

Primary rules: https://www.dndbeyond.com/sources/dnd/br-2024/spell-descriptions
Fields live separately from DNDGame's unconditional periodic damage fields.
All target choices, payments and ongoing PvP effects are server validated.
"""
import math
import json
from fractions import Fraction
from types import SimpleNamespace

try:
    from . import combat_rules as rules, caster_rules as caster, dnd_content as dnd
    from . import spell_scaling, druid_circles as circles, world_content as content
    from .progression import same_floor, train
    from .fighter_rules import STAND_SECONDS
except ImportError:
    import combat_rules as rules, caster_rules as caster, dnd_content as dnd
    import spell_scaling, druid_circles as circles, world_content as content
    from progression import same_floor, train
    from fighter_rules import STAND_SECONDS

FT = 6.4
TURN = 3.0
SKILLS = ('acrobatics', 'animal_handling', 'arcana', 'athletics', 'deception', 'history',
          'insight', 'intimidation', 'investigation', 'medicine', 'nature', 'perception',
          'performance', 'persuasion', 'religion', 'sleight_of_hand', 'stealth', 'survival')
ELEMENTS = {'air': 'lightning', 'earth': 'thunder', 'fire': 'fire', 'water': 'cold'}
FIELD_KEYS = frozenset(('fog_cloud', 'sleet_storm', 'wall_of_stone', 'web', 'stinking_cloud',
    'insect_plague', 'gust_of_wind', 'control_water', 'conjure_elemental', 'conjure_animals'))
SPELL_KEYS = FIELD_KEYS | frozenset(('blur', 'hold_person', 'sleep', 'tree_stride', 'ray_of_sickness',
    'polymorph', 'shatter', 'thunderwave', 'water_breathing', 'hold_monster', 'fount_of_moonlight',
    'guidance', 'guiding_bolt'))


def distance(a, b): return math.hypot(a.x-b.x, a.y-b.y)


def configure(spells, statuses):
    """Called after base catalogue; deliberately no global class unlocks."""
    def add(key, name, circle, kind, range_ft, **kw):
        spec = dict(id=key, name=name, english=key.replace('_', ' ').title(), words=name,
            circle=circle, class_ids=[], class_levels={}, class_min_levels={}, min_level=max(1,(circle-1)*10),
            kind=kind, action='action', mana=dnd.MANA_COSTS[circle], cooldown=0,
            range=range_ft*FT, radius=0, shape='circle', targeting='enemy', source='PHB 2024',
            description='', icon=f'assets/spells/{key}.svg', effect='spell',
            visual=dict(style='field' if key in FIELD_KEYS else kind, theme='nature',
                        colors=['#578879','#a2d9bd','#e2fff0'], shots=1))
        spec.update(kw)
        if key in FIELD_KEYS or key in ('sleep','shatter'): spec['ground_target'] = True
        spells[key]=spec
    add('blur','Rozmycie',2,'buff',0,buff='blur',targeting='self',duration=30,concentration=True,
        description='Ataki przeciw tobie mają utrudnienie; ślepowidzenie i prawdziwe widzenie je omijają.')
    add('fog_cloud','Mglista chmura',1,'circle_field',120,radius=20*FT,duration=1800,concentration=True,
        obscure=True,description='Silnie przesłaniająca mgła. Silny wiatr ją rozprasza; +20 stóp promienia za wyższy krąg.')
    add('hold_person','Unieruchomienie osoby',2,'circle_control',60,save='wisdom',buff='paralyzed',
        duration=30,concentration=True,max_targets=1,humanoid_only=True,description='Humanoid: obrona Mądrości albo paraliż; ponawia obronę co turę.')
    add('sleet_storm','Śnieżyca',3,'circle_field',150,radius=20*FT,duration=30,concentration=True,
        obscure=True,difficult_terrain=True,save='dexterity',description='Śliska, silnie przesłonięta strefa; nieudana obrona Zręczności przewraca i przerywa koncentrację.')
    add('wall_of_stone','Kamienny mur',5,'circle_field',120,duration=300,concentration=True,
        environment_wall=True,description='Dziesięć połączonych kamiennych paneli: KP 15, 180 HP. Po pełnym czasie koncentracji mur pozostaje.',
        circle_options={'variants':[{'id':'thick','name':'Panele 10 stóp, 180 HP'},{'id':'thin','name':'Panele 20 stóp, 90 HP'}],
                        'actions':[{'id':'attack_wall','name':'Atakuj panel'}]})
    add('sleep','Sen',1,'circle_control',60,radius=5*FT,area=True,save='wisdom',duration=30,concentration=True,
        description='Obrona Mądrości: najpierw niezdolność do działania; kolejna porażka usypia. Obrażenia lub akcja budzenia kończą efekt.',
        circle_options={'actions':[{'id':'wake','name':'Obudź pobliski cel'}]})
    add('tree_stride','Wędrówka drzew',5,'buff',0,buff='tree_stride',targeting='self',duration=30,concentration=True,
        description='Raz na turę przechodzisz między żywymi drzewami tego samego rodzaju w 500 stopach; koszt ruchu 10 stóp.',
        circle_options={'actions':[{'id':'tree_step','name':'Przejdź do drzewa'}]})
    add('ray_of_sickness','Promień choroby',1,'attack',60,dice=[2,8,0],damage_type='poison',
        description='Atak czarem: 2k8 trucizny i zatrucie do końca następnej tury.')
    add('web','Pajęczyna',2,'circle_field',60,radius=10*FT,shape='square',duration=1800,concentration=True,
        light_obscure=True,difficult_terrain=True,save='dexterity',description='Sześcian pajęczyn 20 stóp; obrona Zręczności albo spętanie. Akcja Atletyki uwalnia; ogień wypala pajęczynę.',
        circle_options={'actions':[{'id':'escape_web','name':'Wyrwij się'}]})
    add('stinking_cloud','Śmierdząca chmura',3,'circle_field',90,radius=20*FT,duration=30,concentration=True,
        obscure=True,save='constitution',description='Obrona Kondycji na początku tury; porażka zatruwa i blokuje akcję oraz akcję dodatkową na tę turę.')
    add('polymorph','Polimorfia',4,'circle_control',60,save='wisdom',duration=1800,concentration=True,
        description='Zamiana w bestię o SW do poziomu/SW celu; tymczasowe HP bestii. Ich utrata kończy przemianę.',
        circle_options={'forms':[dict(id=k,name=v['name'],cr=v.get('cr','0')) for k,v in caster.FORMS.items()]})
    add('insect_plague','Plaga owadów',5,'circle_field',300,radius=20*FT,duration=300,concentration=True,
        light_obscure=True,difficult_terrain=True,save='constitution',save_half=True,dice=[4,10,0],damage_type='piercing',
        description='Przy pojawieniu, wejściu lub końcu tury: 4k10 kłutych, obrona Kondycji zmniejsza o połowę; raz na turę.')
    add('gust_of_wind','Podmuch wiatru',2,'circle_field',60,radius=5*FT,shape='line',length=60*FT,
        duration=30,concentration=True,save='strength',description='Linia wiatru 60×10 stóp; obrona Siły albo odepchnięcie 15 stóp. Ruch pod wiatr kosztuje podwójnie.',
        circle_options={'actions':[{'id':'redirect_wind','name':'Zmień kierunek (akcja dodatkowa)'}]})
    add('shatter','Roztrzaskanie',2,'save',60,radius=10*FT,area=True,dice=[3,8,0],damage_type='thunder',save='constitution',save_half=True,
        description='Sfera 10 stóp: 3k8 grzmotu; obrona Kondycji zmniejsza o połowę. Konstrukty mają utrudnienie obrony.')
    add('thunderwave','Fala gromu',1,'save',15,radius=7.5*FT,area=True,shape='square',dice=[2,8,0],damage_type='thunder',save='constitution',save_half=True,
        description='Sześcian 15 stóp przy tobie: 2k8 grzmotu; nieudana obrona odpycha o 10 stóp.')
    add('water_breathing','Oddychanie wodą',3,'buff',30,buff='water_breathing',ally_targets=10,targeting='ally',duration=43200,
        ritual=True,ritual_seconds=300,description='Do 10 chętnych celów oddycha pod wodą przez 24 godziny. Rytuał: 10 minut (300 s gry), bez many.')
    add('control_water','Kontrola wody',4,'circle_field',300,radius=50*FT,shape='square',duration=300,concentration=True,
        description='Kontrolujesz wodę w sześcianie 100 stóp: wezbranie, rozstąpienie, zmiana nurtu lub wir. Akcja zmienia wariant.',
        circle_options={'variants':[dict(id=k,name=n) for k,n in [('flood','Wezbranie'),('part','Rozstąpienie'),('redirect','Nurt'),('whirlpool','Wir')]],
                        'actions':[{'id':'control_water','name':'Zmień kontrolę wody (akcja)'},{'id':'escape_whirlpool','name':'Wypłyń z wiru (Atletyka)'}]})
    add('conjure_elemental','Przywołanie żywiołaka',5,'circle_field',60,radius=10*FT,duration=300,concentration=True,
        save='dexterity',dice=[8,8,0],damage_type='fire',description='Duch żywiołu: 8k8 i spętanie po nieudanej obronie Zręczności; kolejne porażki 4k8. Jeden spętany cel naraz.',
        circle_options={'variants':[dict(id=k,name=n) for k,n in [('air','Powietrze'),('earth','Ziemia'),('fire','Ogień'),('water','Woda')]]})
    add('hold_monster','Unieruchomienie potwora',5,'circle_control',90,save='wisdom',buff='paralyzed',
        duration=30,concentration=True,max_targets=1,description='Istota: obrona Mądrości albo paraliż; powtarza obronę co turę.')
    add('conjure_animals','Przywołanie zwierząt',3,'circle_field',60,radius=15*FT,duration=300,concentration=True,
        save='dexterity',dice=[3,10,0],damage_type='slashing',description='Widmowa wataha: przy zbliżeniu lub końcu tury obrona Zręczności albo 3k10 ciętych, raz na turę. Możesz przesuwać ją przy swoim ruchu.',
        circle_options={'actions':[{'id':'move_pack','name':'Przesuń watahę (30 stóp)'}]})
    add('fount_of_moonlight','Źródło księżycowego blasku',4,'buff',0,buff='fount_of_moonlight',targeting='self',duration=300,concentration=True,
        description='Odporność na promieniste, +2k6 promienistych w zwarciu. Reakcja po obrażeniach: widoczny napastnik w 60 stopach broni Kondycją przed oślepieniem.')
    add('guidance','Wskazówki',0,'buff',5,buff='guidance',targeting='ally',duration=30,concentration=True,
        description='+1k4 do każdego testu wybranej umiejętności przez czas koncentracji.',
        circle_options={'skills':[dict(id=k,name=k.replace('_',' ')) for k in SKILLS]})
    add('guiding_bolt','Wiodący pocisk',1,'attack',120,dice=[4,6,0],damage_type='radiant',
        description='Atak czarem: 4k6 promienistych. Następny atak przeciw celowi przed końcem twojej następnej tury ma ułatwienie.')
    spell_scaling.UPCAST.update(fog_cloud={'radius':20*FT},hold_person={'max_targets':1},
        hold_monster={'max_targets':1},ray_of_sickness={'dice':1},insect_plague={'dice':1},
        shatter={'dice':1},thunderwave={'dice':1},conjure_elemental={'dice':1},
        conjure_animals={'dice':1},guiding_bolt={'dice':1})
    for key,name,harmful in [('blur','Rozmycie',False),('paralyzed','Paraliż',True),('sleep_pending','Senność',True),
        ('unconscious','Nieprzytomność',True),('poisoned','Zatrucie',True),('stinking_poison','Mdłości',True),
        ('web_restrained','Spętanie pajęczyną',True),('elemental_restrained','Uścisk żywiołu',True),
        ('guiding_bolt','Wiodący blask',True),('guidance','Wskazówki',False),('tree_stride','Wędrówka drzew',False),
        ('water_breathing','Oddychanie wodą',False),('fount_of_moonlight','Blask księżyca',False),('polymorph','Polimorfia',True)]:
        statuses[key]=dict(name=name,icon='✦',description=name,harmful=harmful)
    statuses.update(difficult_terrain=dict(name='Trudny teren',icon='↘',description='Ruch kosztuje podwójnie.',harmful=True),
        headwind=dict(name='Pod wiatr',icon='≋',description='Ruch przeciw kierunkowi wiatru kosztuje podwójnie.',harmful=True),
        whirlpool=dict(name='Wir',icon='◎',description='Wypłynięcie wymaga akcji i udanej Atletyki.',harmful=True))
    for status,action in (('web_restrained','escape_web'),('whirlpool','escape_whirlpool'),('sleep_pending','wake'),('unconscious','wake')):
        statuses[status]['escape_action_id']=action


class DruidCircleSpells:
    def init_circle_spells(self):
        self.circle_spell_fields=[]
        self.db.execute('CREATE TABLE IF NOT EXISTS circle_stone_walls (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        for _,raw in self.db.execute('SELECT id,data FROM circle_stone_walls'):
            try: f=json.loads(raw)
            except (ValueError,TypeError): continue
            if not isinstance(f,dict) or f.get('key')!='wall_of_stone' or not isinstance(f.get('segments'),list):continue
            f.update(until=float('inf'),concentration=False,positions={},hits={},entered=set())
            self.circle_spell_fields.append(f)
        self.db.commit()

    def _circle_fields(self):
        if not hasattr(self,'circle_spell_fields'): self.init_circle_spells()
        return self.circle_spell_fields

    def _persist_circle_wall(self,f):
        if f.get('concentration'):return
        record={k:f[k] for k in ('id','owner','key','x','y','floor','radius','profile','segments')}
        with self.db:self.db.execute('INSERT OR REPLACE INTO circle_stone_walls(id,data) VALUES(?,?)',(f['id'],json.dumps(record)))

    def _erase_circle_wall(self,f):
        if not f.get('concentration'):
            with self.db:self.db.execute('DELETE FROM circle_stone_walls WHERE id=?',(f['id'],))

    def _spell_visible(self,a,b):
        return self.line_clear(a,b) and (not hasattr(self,'environment_can_see') or self.environment_can_see(a,b))

    def _spell_legal(self,p,t,range_=float('inf'),visible=False):
        return (t is not None and t.alive and t.hp>0 and same_floor(p,t) and distance(p,t)<=range_
            and not self.in_safe(p) and not self.in_safe(t)
            and (not self.is_player_target(t) or not self.pvp_error(p,t))
            and (not visible or self._spell_visible(p,t)))

    def _spell_candidates(self,p,center,radius):
        values=list(self.nearby_enemies(center,radius+64))
        if not p.pvp_safety: values+=list(self.players.values())
        return [t for t in values if self._spell_legal(p,t) and distance(center,t)<=radius and self.line_clear(center,t)]

    def _circle_status(self,p,t,key,duration,s,hostile=True,**extra):
        if key in ('web_restrained','elemental_restrained') and self.target_condition(t,'freedom'): return False
        if not self.apply_status(p,t,key,duration,s,hostile=hostile): return False
        self.target_conditions(t)[key].update(extra)
        if hostile:
            if self.is_player_target(t): self.record_pvp_effect(p,t,self.begin_pvp_hostility(p,t))
            else: self.remember_attacker(t,p)
        if key in ('paralyzed','sleep_pending','unconscious') and self.is_player_target(t): self.break_concentration(t)
        return True

    def _circle_save_roll(self,p,t,s,ability=None):
        result=self.target_save(t,ability or s.get('save','wisdom'),rules.spell_dc(p),
            dict(damage=0,damage_dice='',damage_rolls=[]),False)
        self.report_roll(p,t,result,s['name'],p)
        return result.get('saved',False)

    def _circle_spell_point(self,p,s,options,target=None,visible=True,clear_path=True):
        raw=options.get('point')
        if raw is not None:
            if not isinstance(raw,dict): return None
            try: x,y=float(raw['x']),float(raw['y']); floor=int(raw.get('floor',p.floor))
            except (KeyError,ValueError,TypeError,OverflowError): return None
            if not math.isfinite(x) or not math.isfinite(y) or floor!=p.floor: return None
        elif target: x,y,floor=target.x,target.y,target.floor
        else:
            dx,dy=p.facing; norm=math.hypot(dx,dy) or 1
            x,y,floor=p.x+dx/norm*min(s['range'],60*FT),p.y+dy/norm*min(s['range'],60*FT),p.floor
        point=SimpleNamespace(id='',x=x,y=y,floor=floor)
        return point if distance(p,point)<=s['range']+.01 and (self._spell_visible(p,point) if visible else not clear_path or self.line_clear(p,point)) else None

    def _circle_unoccupied_point(self,p,s,point):
        # Creature-targeted controls choose the closest empty Large space.
        candidates=[point]
        for radius in (10*FT,15*FT):
            for angle in range(0,360,45):
                candidates.append(SimpleNamespace(id='',x=point.x+math.cos(math.radians(angle))*radius,
                    y=point.y+math.sin(math.radians(angle))*radius,floor=p.floor))
        for q in candidates:
            if distance(p,q)>s['range'] or not self.line_clear(p,q) or self.blocked_for(p,q.x,q.y,radius=5*FT):continue
            actors=list(self.players.values())+list(self.nearby_enemies(q,80))
            if any(t.alive and same_floor(q,t) and distance(q,t)<5*FT+18 for t in actors):continue
            return q
        return None

    async def cast_circle_spell(self,p,key,enemy_id=None,target_id=None,options=None):
        if not isinstance(options,(dict,type(None))): return
        return await self._cast_circle_spell(p,key,enemy_id,target_id,options or {})

    async def cast_spell(self,p,key,enemy_id=None,target_id=None,queue=True):
        if isinstance(key,str) and key in SPELL_KEYS:
            return await self._cast_circle_spell(p,key,enemy_id,target_id,{},queue=queue)
        return await super().cast_spell(p,key,enemy_id,target_id,queue=queue)

    async def process_player_actions(self):
        for p in tuple(self.players.values()):
            pending=getattr(p,'pending_spell',{})
            if 'circle_options' not in pending or p.attack_cooldown_until>self.now():continue
            p.pending_spell={}
            if pending.get('until',0)>=self.now() and p.alive and not p.disconnected:
                await self._cast_circle_spell(p,pending['spell'],pending.get('enemy'),pending.get('target'),pending['circle_options'],queue=False)
        return await super().process_player_actions()

    def circle_note_movement(self,p,old_x,old_y):
        if self.is_player_target(p) and not getattr(p,'_environment_forced',False) and math.hypot(p.x-old_x,p.y-old_y)>.01:
            p._circle_spell_motion_time=self.now()
        return super().circle_note_movement(p,old_x,old_y)

    async def start_caster_channel(self,p,key,ritual=False):
        if key!='water_breathing': return await super().start_caster_channel(p,key,ritual)
        if not ritual: return await self.cast_spell(p,key)
        now=self.now()
        if not p.alive or p.form or not dnd.spell_allowed(p,key) or rules.gear.armor_penalty(p): return
        if p.combat_until>now or p.pvp_combat_until>now or p.attack_cooldown_until>now or p.casting_channel: return
        s=spell_scaling.resolve(p,key);self.cancel_rest(p);self.stop_auto(p)
        p.casting_channel=dict(key=key,name=s['name'],until=now+300,total=300,x=p.x,y=p.y,floor=p.floor,
            cost=0,gold=0,ritual=True,profile=s,old_action=p.attack_cooldown_until)
        p.attack_cooldown_until=now+300;p.buffs['ritual_channel']=dict(until=now+300,spell_id=key)
        await self.notice(p,'Rytuał Oddychania wodą: 300 s. Ruch lub obrażenia przerwą rzucanie.')

    def complete_channel(self,p):
        ch=getattr(p,'casting_channel',{})
        if ch.get('key')!='water_breathing': return super().complete_channel(p)
        if not p.alive or not dnd.spell_allowed(p,'water_breathing') or rules.gear.armor_penalty(p):
            self.cancel_channel(p);return
        self.cancel_channel(p,'');s=ch['profile']
        targets=sorted((t for t in self.players.values() if not self.friendly_target_error(p,t,s['range'])),key=lambda t:(t is not p,distance(p,t)))[:10]
        for t in targets:
            self.join_pvp_support(p,t);self._circle_status(p,t,'water_breathing',s['duration'],s,False)
        dnd.record_spell_use(p,'water_breathing');self.spell_effect(p,'water_breathing',p,targets,spec=s)
        with self.db:
            for t in targets:self.save_player(t)

    async def _cast_circle_spell(self,p,key,enemy_id,target_id,options,queue=True):
        if not isinstance(key,str) or key not in SPELL_KEYS or not dnd.spell_allowed(p,key) or not p.alive: return
        if not isinstance(enemy_id,(str,type(None))) or not isinstance(target_id,(str,type(None))) or enemy_id and target_id: return
        now=self.now();p.current_wall_time=now
        if any(self.target_condition(p,k) for k in ('incapacitated','paralyzed','unconscious','sleep_pending','stinking_poison','stunned')): return
        if self.target_condition(p,'polymorph') or p.form and not circles.beast_spell_allowed(p,key): return await self.notice(p,'Nie możesz rzucać tego czaru w przemianie.')
        if rules.gear.armor_penalty(p): return await self.notice(p,'Brak wyszkolenia w założonym pancerzu blokuje czary.')
        if now<p.attack_cooldown_until:
            if queue:
                if not enemy_id and not target_id and dnd.SPELLS[key]['kind']!='buff':enemy_id=p.auto_enemy_id or None;target_id=p.auto_target_id or None
                p.pending_spell={'spell':key,'enemy':enemy_id,'target':target_id,'circle_options':dict(options),'until':now+4}
            return
        s=spell_scaling.resolve(p,key);mana,free=self.circle_spell_cost(p,s)
        if p.mana<mana: return await self.notice(p,f'Potrzebujesz {mana} many.')
        if key=='guidance' and options.get('skill','perception') not in SKILLS: return
        if key=='conjure_elemental' and (not isinstance(options.get('variant','fire'),str) or options.get('variant','fire') not in ELEMENTS): return
        if key=='control_water' and options.get('variant','flood') not in ('flood','part','redirect','whirlpool'): return
        if key=='wall_of_stone' and options.get('variant','thick') not in ('thick','thin'):return
        target=self.players.get(target_id) if target_id else self.enemies.get(enemy_id) if enemy_id else None
        if target is None and s['kind'] not in ('buff',):
            target=self.players.get(p.auto_target_id) if p.auto_target_id else self.enemies.get(p.auto_enemy_id)
        if target is None and s['kind'] not in ('buff',) and key not in FIELD_KEYS and not s.get('area'):
            options=[e for e in self.nearby_enemies(p,s['range']) if self._spell_legal(p,e,s['range'],s['kind']=='circle_control') and self.line_clear(p,e)]
            target=min(options,key=lambda e:distance(p,e)) if options else None
        targets=[];point=None;form=None;friendly=False
        if s['kind']=='buff':
            if s.get('targeting')=='self':
                if target_id and target_id!=p.id: return
                targets=[p]
            else:
                anchor=self.players.get(target_id) if target_id else p
                reason=self.friendly_target_error(p,anchor,s['range'])
                if reason: return await self.notice(p,reason)
                targets=[anchor]
                if s.get('ally_targets',1)>1:
                    targets=sorted((q for q in self.players.values() if not self.friendly_target_error(p,q,s['range'])),key=lambda q:(q is not anchor,distance(p,q)))[:s['ally_targets']]
        elif key in FIELD_KEYS or s.get('area'):
            if key=='thunderwave':
                dx,dy=p.facing;norm=math.hypot(dx,dy) or 1
                point=SimpleNamespace(id='',x=p.x+dx/norm*7.5*FT,y=p.y+dy/norm*7.5*FT,floor=p.floor)
            else:point=self._circle_spell_point(p,s,options,target,visible=False)
            if point is None or self.in_safe(p) or self.in_safe(point): return await self.notice(p,'Wskaż dostępne miejsce w zasięgu poza strefą bezpieczną.')
            if key in ('conjure_animals','conjure_elemental'):
                point=self._circle_unoccupied_point(p,s,point)
                if point is None:return await self.notice(p,'Duch potrzebuje wolnej przestrzeni 10×10 stóp.')
            radius=s.get('radius',0);targets=self._spell_candidates(p,point,radius*(math.sqrt(2) if s.get('shape')=='square' else 1))
            if s.get('shape')=='square':targets=[t for t in targets if max(abs(t.x-point.x),abs(t.y-point.y))<=radius]
            if key=='control_water':
                info=self.environment_water_info(point) if hasattr(self,'environment_water_info') else {}
                if not info.get('water'): return await self.notice(p,'Kontrola wody wymaga istniejącego zbiornika.')
                if options.get('variant')=='whirlpool' and (info.get('depth_ft',0)<25 or info.get('width_ft',0)<50):
                    return await self.notice(p,'Wir wymaga wody głębokiej na 25 i szerokiej na 50 stóp.')
            if key=='wall_of_stone':
                segments=self._wall_segments(p,point,options)
                if segments is None: return await self.notice(p,'Mur wymaga połączonych paneli wspartych na kamieniu i wolnych od istot.')
        else:
            if key=='polymorph':
                friendly=self.is_player_target(target) and not self.friendly_target_error(p,target,s['range']) if target else False
                if not isinstance(options.get('form','cat'),str):return
                form=caster.FORMS.get(options.get('form','cat'))
                if form is None or target is None: return
                cr=Fraction(str(form.get('cr','0')))
                limit=rules.effective_level(target) if self.is_player_target(target) else Fraction(str(content.ENEMIES[target.kind].get('cr',0)))
                if cr>limit: return await self.notice(p,'SW bestii przekracza poziom lub SW celu.')
            if not friendly and (not self._spell_legal(p,target,s['range'],s['kind']=='circle_control') or not self.line_clear(p,target)): return await self.notice(p,'Wskaż legalny cel w zasięgu.')
            targets=[target]
            extra=options.get('targets',[])
            if not isinstance(extra,list) or len(extra)>20: return
            for ref in extra:
                t=self.resolve_target_ref(ref) if isinstance(ref,str) else None
                if t in targets: continue
                if len(targets)>=s.get('max_targets',1): break
                if not self._spell_legal(p,t,s['range'],True): return
                targets.append(t)
            if s.get('humanoid_only') and any(not self.is_player_target(t) and content.ENEMIES[t.kind].get('creature_type')!='humanoid' for t in targets):
                return await self.notice(p,'Ten czar działa tylko na humanoidy.')
        # No resources or previous concentration change before all validation passes.
        self.cancel_channel(p) if hasattr(self,'cancel_channel') else None
        self.begin_action(p);self.spend_mana(p,mana);self.circle_commit_spell(p,s,free)
        dnd.record_spell_use(p,key);p.pending_spell={};train(p,'magic',max(1,mana))
        if s.get('concentration'):
            self.break_concentration(p);p.concentration=key;p.concentration_until=now+s['duration'];p.concentration_profile=s
        if s['kind']!='buff' and not friendly: self.tag(p)
        if s['kind']=='buff':
            for t in targets:
                self.join_pvp_support(p,t)
                self._circle_status(p,t,s['buff'],s['duration'],s,False,skill=options.get('skill','perception'))
        elif key in FIELD_KEYS:
            self._new_circle_field(p,s,point,options,segments if key=='wall_of_stone' else None)
        elif s['kind']=='circle_control':
            for t in targets:
                unjust=self.begin_pvp_hostility(p,t) if self.is_player_target(t) and not friendly else False
                if key=='sleep' and self._sleep_immune(t): continue
                if not friendly and self._circle_save_roll(p,t,s): continue
                if key=='polymorph': self._polymorph(p,t,s,options.get('form','cat'),friendly)
                elif key=='sleep': self._circle_status(p,t,'sleep_pending',s['duration'],s,next_save=now+TURN)
                else: self._circle_status(p,t,'paralyzed',s['duration'],s,next_save=now+TURN)
                if self.is_player_target(t) and not friendly: self.record_pvp_effect(p,t,unjust)
                elif not self.is_player_target(t): self.remember_attacker(t,p)
        else:
            for t in targets:
                self.spell_damage(p,t,s)
                if t.hp<=0 and not self.is_player_target(t): await self.defeat(t)
            if key=='shatter':self._shatter_objects(p,s,point)
        self.spell_effect(p,key,targets[0] if targets else point or p,targets or None,spec=s)
        with self.db:
            self.save_player(p)
            for t in targets:
                if self.is_player_target(t) and t is not p: self.save_player(t)

    def spell_damage(self,p,t,s):
        shatter=s.get('id')=='shatter' and not self.is_player_target(t) and content.ENEMIES[t.kind].get('creature_type')=='construct'
        if shatter:t._shatter_save_disadvantage=True
        try: result=super().spell_damage(p,t,s)
        finally:
            if shatter:t._shatter_save_disadvantage=False
        if not result or not result.get('hit') or t.hp<=0: return result
        key=s.get('id')
        if key=='ray_of_sickness': self._circle_status(p,t,'poisoned',2*TURN,s)
        if key=='guiding_bolt': self._circle_status(p,t,'guiding_bolt',2*TURN,s)
        if key=='thunderwave' and not result.get('saved'):
            n=distance(p,t) or 1;self.environment_forced_move(t,(t.x-p.x)/n*10*FT,(t.y-p.y)/n*10*FT)
        if s.get('damage_type')=='fire' and key!='web' and result.get('damage',0)>0:
            for f in self._circle_fields():
                if f['key']=='web' and self._field_contains(f,t):
                    cell=(math.floor((t.x-f['x'])/(5*FT)),math.floor((t.y-f['y'])/(5*FT)))
                    f.setdefault('burning',{})[cell]=self.now()+TURN
        return result

    def _sleep_immune(self,t):
        spec={} if self.is_player_target(t) else content.ENEMIES[t.kind]
        return bool(spec.get('no_sleep') or 'exhaustion' in spec.get('condition_immunities',[]) or self.target_condition(t,'sleep_immune'))

    def _polymorph(self,p,t,s,form,friendly):
        beast=caster.FORMS[form]
        previous=dict(form=getattr(t,'form',''),form_until=getattr(t,'form_until',0),temp_hp=getattr(t,'temp_hp',0))
        hp=beast.get('hp',{'cat':2,'wolf':11,'black_bear':19,'bear':34}.get(form,1))
        self._circle_status(p,t,'polymorph',s['duration'],s,not friendly,form=form,previous=previous,
            attributes={**beast['attributes'],**beast.get('mental_attributes',{})},ac=beast['ac'],attacks=beast['attacks'],attack_bonus=beast.get('attack_bonus',0),speed=beast['speed'],temporary_hp=hp)
        t.form=form;t.form_until=self.now()+s['duration'];t.temp_hp=hp

    def _end_polymorph(self,t,value):
        old=value.get('previous',{})
        active=old.get('form_until',0)>self.now()
        t.form=old.get('form','') if active else '';t.form_until=old.get('form_until',0) if active else 0;t.temp_hp=0
        self.target_conditions(t).pop('polymorph',None)

    def circle_spell_damage_received(self,t,damage,source=None):
        if damage<=0: return
        for key in ('sleep_pending','unconscious'):
            value=self.target_conditions(t).get(key,{})
            if value.get('spell_id')=='sleep': self.target_conditions(t).pop(key,None)
        poly=self.target_conditions(t).get('polymorph')
        if poly and getattr(t,'temp_hp',0)<=0: self._end_polymorph(t,poly)
        if (source and self.target_condition(t,'fount_of_moonlight') and self.is_player_target(t)
            and getattr(t,'reaction_ready',0)<=self.now() and distance(t,source)<=60*FT
            and self._spell_visible(t,source) and self._spell_legal(t,source)):
            if any(self.target_condition(t,k) for k in ('no_reactions','paralyzed','unconscious','sleep_pending','stunned')): return
            t.reaction_ready=self.now()+TURN
            spec=dict(dnd.SPELLS['fount_of_moonlight'],save='constitution',concentration=False)
            if not self._circle_save_roll(t,source,spec): self._circle_status(t,source,'blind',2*TURN,spec,retry=float('inf'))

    def _wall_segments(self,p,point,options):
        supplied=options.get('segments')
        if supplied is not None and (not isinstance(supplied,list) or not 1<=len(supplied)<=10): return None
        dx,dy=p.facing;n=math.hypot(dx,dy) or 1;dx,dy=-dy/n,dx/n
        thin=options.get('variant')=='thin';length=(20 if thin else 10)*FT;thickness=(.25 if thin else .5)*FT
        supplied=supplied or [dict(x=point.x+dx*(i-4.5)*length,y=point.y+dy*(i-4.5)*length) for i in range(10)]
        segments=[]
        for raw in supplied:
            try: x,y=float(raw['x']),float(raw['y'])
            except (KeyError,ValueError,TypeError,OverflowError): return None
            q=SimpleNamespace(x=x,y=y,floor=p.floor)
            if not math.isfinite(x) or not math.isfinite(y) or distance(p,q)>120*FT: return None
            if segments and min(math.hypot(x-z['cx'],y-z['cy']) for z in segments)>length+1: return None
            if any(t.alive and same_floor(t,q) and distance(t,q)<length/2+18 for t in list(self.players.values())+list(self.nearby_enemies(q,length))): return None
            if hasattr(self,'environment_stone_support') and not self.environment_stone_support(q): return None
            horizontal=raw.get('axis','x' if abs(dx)>=abs(dy) else 'y')=='x'
            width,height=(length,thickness) if horizontal else (thickness,length)
            segments.append(dict(x=x-width/2,y=y-height/2,cx=x,cy=y,w=width,h=height,hp=90 if thin else 180,ac=15))
        for t in self._wall_enclosed(p,segments):
            if self.is_player_target(t) and t is not p and self.friendly_target_error(p,t,float('inf')) and self.pvp_error(p,t):return None
        return segments

    def _wall_enclosed(self,p,segments):
        if len(segments)<4:return []
        first,last=segments[0],segments[-1]
        if math.hypot(first['cx']-last['cx'],first['cy']-last['cy'])>max(first['w'],first['h'])+1:return []
        def inside(t):
            result=False;j=len(segments)-1
            for i,a in enumerate(segments):
                b=segments[j]
                if (a['cy']>t.y)!=(b['cy']>t.y) and t.x<(b['cx']-a['cx'])*(t.y-a['cy'])/(b['cy']-a['cy'])+a['cx']:result=not result
                j=i
            return result
        return [t for t in list(self.players.values())+list(self.nearby_enemies(p,120*FT)) if t.alive and same_floor(p,t) and inside(t)]

    def _wall_escape_reactions(self,p,s,segments):
        for t in self._wall_enclosed(p,segments):
            if not self.is_player_target(t) or t is p or not self.friendly_target_error(p,t,float('inf')):
                legal=True
            else:legal=not self.pvp_error(p,t)
            if not legal or getattr(t,'reaction_ready',0)>self.now() or any(self.target_condition(t,k) for k in ('no_reactions','paralyzed','unconscious','sleep_pending','stunned')):continue
            if not self._circle_save_roll(p,t,dict(s,save='dexterity')):continue
            # Resolve before the panels become obstacles; the reaction can cross their future positions.
            candidates=[]
            minx=min(z['x'] for z in segments)-24;maxx=max(z['x']+z['w'] for z in segments)+24
            miny=min(z['y'] for z in segments)-24;maxy=max(z['y']+z['h'] for z in segments)+24
            for x,y in ((minx,t.y),(maxx,t.y),(t.x,miny),(t.x,maxy)):
                if math.hypot(x-t.x,y-t.y)<=30*FT and not self.blocked_for(t,x,y):candidates.append((x,y))
            if not candidates:continue
            x,y=min(candidates,key=lambda point:math.hypot(point[0]-t.x,point[1]-t.y))
            t.reaction_ready=self.now()+TURN;self.environment_forced_move(t,x-t.x,y-t.y)

    def _shatter_objects(self,p,s,point):
        if point is None:return
        damage=rules.roll_damage(self.combat_rng,s['dice'])['damage']
        for f in tuple(self._circle_fields()):
            if f['key']!='wall_of_stone' or f['floor']!=p.floor:continue
            touched=False
            for z in f.get('segments',[]):
                x=max(z['x'],min(point.x,z['x']+z['w']));y=max(z['y'],min(point.y,z['y']+z['h']))
                if z['hp']>0 and math.hypot(x-point.x,y-point.y)<=s['radius']:
                    z['hp']=max(0,z['hp']-damage);touched=True
            if not touched:continue
            if not any(z['hp']>0 for z in f['segments']):self.end_field_effect(f);self.circle_spell_fields.remove(f);self._erase_circle_wall(f)
            else:self._persist_circle_wall(f)

    def _new_circle_field(self,p,s,point,options,segments=None):
        key=s['id'];now=self.now()
        if segments is not None:self._wall_escape_reactions(p,s,segments)
        f=dict(id=f'circle:{p.id}:{key}:{now}',owner=p.id,key=key,x=point.x,y=point.y,floor=p.floor,
            radius=s['radius'],until=now+s['duration'],next=now+TURN,concentration=True,profile=dict(s),
            positions={},hits={},entered=set(),born=now,options=dict(options),dc=rules.spell_dc(p))
        if segments is not None: f['segments']=segments
        if key=='gust_of_wind':
            dx,dy=point.x-p.x,point.y-p.y;n=math.hypot(dx,dy) or 1
            f.update(x=p.x,y=p.y,direction=[dx/n,dy/n])
        if key=='control_water':
            variant=options.get('variant','flood');f['profile'].update(water_variant=variant,
                water_level_ft=20 if variant=='flood' else -20 if variant=='part' else 0,whirlpool=variant=='whirlpool',flow=list(p.facing))
        if key=='conjure_elemental': f['profile']['damage_type']=ELEMENTS[options.get('variant','fire')]
        occupants=[t for t in self._spell_candidates(p,point,max(f['radius']*1.5,60*FT if key=='gust_of_wind' else 0)) if self._field_contains(f,t)]
        f['entered']={self.target_ref(t) for t in occupants}
        f['spirit_space']={self.target_ref(t) for t in occupants if distance(point,t)<=5*FT}
        self._circle_fields().append(f)
        effect=self.spell_effect(p,key,point,duration=s['duration'],spec=s);effect['persistent']=True;f['effect_id']=effect['id']
        if key in ('insect_plague','gust_of_wind'): self._tick_circle_field(f,initial=True)

    def _field_contains(self,f,t):
        if getattr(t,'floor',0)!=f['floor']: return False
        dx,dy=t.x-f['x'],t.y-f['y'];s=f['profile']
        if f['key']=='gust_of_wind':
            ux,uy=f['direction'];along=dx*ux+dy*uy;cross=abs(dx*uy-dy*ux)
            return 0<=along<=60*FT and cross<=5*FT
        if s.get('shape')=='square': return max(abs(dx),abs(dy))<=f['radius']
        return math.hypot(dx,dy)<=f['radius']

    def break_concentration(self,p):
        for t in list(self.players.values())+list(getattr(self,'enemies',{}).values()):
            value=self.target_conditions(t).get('polymorph')
            if value and value.get('owner')==p.id: self._end_polymorph(t,value)
        for f in tuple(self._circle_fields()):
            if f['owner']!=p.id or not f.get('concentration'): continue
            if f['key']=='wall_of_stone' and f['until']<=self.now():
                f['concentration']=False;f['until']=float('inf');self._persist_circle_wall(f)
            else: self.end_field_effect(f);self.circle_spell_fields.remove(f)
        return super().break_concentration(p)

    def tick_target_conditions(self,t):
        now=self.now();conditions=self.target_conditions(t)
        for key in ('paralyzed','sleep_pending','unconscious','polymorph'):
            v=conditions.get(key)
            if not v: continue
            owner=self.players.get(v.get('owner'))
            invalid=v.get('until',0)<=now or not t.alive or owner is None or (v.get('hostile') and self.is_player_target(t) and self.pvp_error(owner,t))
            if invalid:
                if key=='polymorph': self._end_polymorph(t,v)
                else: conditions.pop(key,None)
                continue
            if key in ('paralyzed','sleep_pending') and v.get('next_save',float('inf'))<=now:
                v['next_save']=now+TURN;s=dict(dnd.SPELLS[v['spell_id']],save=v.get('save','wisdom'))
                if self._circle_save_roll(owner,t,s): conditions.pop(key,None)
                elif key=='sleep_pending':
                    conditions.pop(key,None);conditions['unconscious']=dict(v,next_save=float('inf'))
        return super().tick_target_conditions(t)

    def tick_dnd(self,dt):
        super().tick_dnd(dt)
        for f in tuple(self._circle_fields()):
            if f['key']=='wall_of_stone' and not f.get('concentration'):continue
            p=self.players.get(f['owner']);now=self.now()
            invalid=(p is None or not p.alive or p.floor!=f['floor'] or (f.get('concentration') and p.concentration!=f['key']) or f['until']<=now)
            if invalid:
                if f['key']=='wall_of_stone' and f['until']<=now and p and p.concentration==f['key']:
                    f['concentration']=False;f['until']=float('inf');self._persist_circle_wall(f)
                else: self.end_field_effect(f);self.circle_spell_fields.remove(f);continue
            if f.get('concentration'): self._tick_circle_field(f)

    def _tick_circle_field(self,f,initial=False):
        p=self.players.get(f['owner']);now=self.now()
        if p is None or self.in_safe(p): return
        s=f['profile'];key=f['key'];center=SimpleNamespace(x=f['x'],y=f['y'],floor=f['floor'])
        if key=='gust_of_wind': f['x'],f['y']=p.x,p.y
        radius=60*FT if key=='gust_of_wind' else f['radius']*1.5
        candidates=self._spell_candidates(p,center,radius)
        nearby=[t for t in candidates if self._field_contains(f,t)]
        if s.get('difficult_terrain') or key=='gust_of_wind':
            terrain=list(nearby)
            for t in self.players.values():
                if t not in terrain and self._field_contains(f,t) and not self.friendly_target_error(p,t,float('inf')):terrain.append(t)
            for t in terrain:
                hostile=not self.is_player_target(t) or bool(self.friendly_target_error(p,t,float('inf')))
                if s.get('difficult_terrain'):
                    cell=(math.floor((t.x-f['x'])/(5*FT)),math.floor((t.y-f['y'])/(5*FT)))
                    if key!='web' or cell not in f.get('burnt',set()):self._circle_status(p,t,'difficult_terrain',.2,s,hostile)
                if key=='gust_of_wind':self._circle_status(p,t,'headwind',.2,s,hostile,direction=list(f['direction']))
        due=now>=f['next']
        if due:f['next']=now+TURN
        present=set();spirit_space=set();newly_restrained=False
        for t in nearby:
            ref=self.target_ref(t);present.add(ref);entered=ref not in f['entered']
            if distance(center,t)<=5*FT:spirit_space.add(ref)
            turn=int(max(0,now-f['born'])//TURN)
            ready=f['hits'].get(ref)!=turn
            if key=='sleet_storm' and (entered or due) and ready:
                f['hits'][ref]=turn
                if not self._circle_save_roll(p,t,s):
                    self._circle_status(p,t,'prone',STAND_SECONDS,s,concentration=False)
                    if self.is_player_target(t): self.break_concentration(t)
            elif key=='web' and (entered or due) and ready:
                cell=(math.floor((t.x-f['x'])/(5*FT)),math.floor((t.y-f['y'])/(5*FT)))
                if cell in f.get('burnt',set()): continue
                f['hits'][ref]=turn
                if f.get('burning',{}).get(cell,0)>now:
                    self.spell_damage(p,t,dict(s,kind='save',save='',dice=[2,4,0],damage_type='fire',resolved=True))
                elif not self._circle_save_roll(p,t,s): self._circle_status(p,t,'web_restrained',max(.1,f['until']-now),s,field_id=f['id'])
            elif key=='stinking_cloud' and due and not self._circle_save_roll(p,t,s):
                self._circle_status(p,t,'stinking_poison',TURN,s,concentration=False)
            elif key in ('insect_plague','conjure_animals') and (entered or due or initial or f.get('moved')) and ready:
                if key=='conjure_animals' and not self._spell_visible(p,t): continue
                f['hits'][ref]=turn;self.spell_damage(p,t,dict(s,kind='save'))
            elif key=='gust_of_wind' and (due or initial) and not self._circle_save_roll(p,t,s):
                dx,dy=f['direction'];self.environment_forced_move(t,dx*15*FT,dy*15*FT)
            elif key=='conjure_elemental' and (due or ref in spirit_space and ref not in f.get('spirit_space',set())) and not f.get('restrained') and ready and self._spell_visible(p,t):
                f['hits'][ref]=turn;result=self.spell_damage(p,t,dict(s,kind='save'))
                if result and not result.get('saved') and t.hp>0:
                    if self._circle_status(p,t,'elemental_restrained',max(.1,f['until']-now),s,field_id=f['id']): f['restrained']=ref;newly_restrained=True
        if key=='web':
            for cell,end in tuple(f.get('burning',{}).items()):
                if end<=now: f.setdefault('burnt',set()).add(cell);del f['burning'][cell]
            for ref in f['entered']-present:
                t=self.resolve_target_ref(ref)
                if t and self.target_conditions(t).get('web_restrained',{}).get('field_id')==f['id']: self.target_conditions(t).pop('web_restrained',None)
            for t in nearby:
                cell=(math.floor((t.x-f['x'])/(5*FT)),math.floor((t.y-f['y'])/(5*FT)))
                if cell in f.get('burnt',set()) and self.target_conditions(t).get('web_restrained',{}).get('field_id')==f['id']:
                    self.target_conditions(t).pop('web_restrained',None)
        if key=='conjure_elemental' and f.get('restrained') and due and not newly_restrained:
            t=self.resolve_target_ref(f['restrained'])
            if t is None or not self._spell_legal(p,t) or not self.target_condition(t,'elemental_restrained'): f.pop('restrained',None)
            else:
                profile=dict(s,kind='save',dice=[4+s.get('cast_circle',5)-5,8,0])
                result=self.spell_damage(p,t,profile)
                if not result or result.get('saved') or t.hp<=0: self.target_conditions(t).pop('elemental_restrained',None);f.pop('restrained',None)
        if key=='gust_of_wind':
            for other in tuple(self._circle_fields()):
                if other is f or other['key'] not in ('fog_cloud','stinking_cloud'):continue
                if self._field_contains(f,SimpleNamespace(x=other['x'],y=other['y'],floor=other['floor'])):
                    self.end_field_effect(other);self.circle_spell_fields.remove(other)
        if key=='conjure_animals' and distance(p,center)<=10*FT:
            self._circle_status(p,p,'conjure_animals_strength',.2,s,False)
        if key=='control_water':
            if hasattr(self,'environment_control_water'): self.environment_control_water(f,nearby,due)
            if s.get('water_variant')=='whirlpool':
                try:from .environment_rules import flying
                except ImportError:from environment_rules import flying
                for t in nearby:
                    ref=self.target_ref(t);turn=int(max(0,now-f['born'])//TURN)
                    if distance(center,t)>25*FT or not self.environment_water_info(t).get('water') or flying(t):continue
                    self._circle_status(p,t,'whirlpool',.2,s,field_id=f['id'])
                    if (due or ref not in f['entered']) and f['hits'].get(ref)!=turn:
                        f['hits'][ref]=turn
                        self.spell_damage(p,t,dict(s,kind='save',save='strength',save_half=True,dice=[2,8,0],damage_type='bludgeoning',resolved=True))
        f['entered']=present;f['spirit_space']=spirit_space;f.pop('moved',None)

    async def circle_spell_action(self,p,action,options=None):
        options=options or {}
        if not isinstance(options,dict) or not isinstance(action,str) or not p.alive: return
        if any(self.target_condition(p,k) for k in ('paralyzed','unconscious','sleep_pending','stunned','stinking_poison')): return
        now=self.now();fields=[f for f in self._circle_fields() if f['owner']==p.id and f.get('concentration')]
        key={'move_pack':'conjure_animals','redirect_wind':'gust_of_wind','control_water':'control_water'}.get(action)
        if key:
            f=next((f for f in fields if f['key']==key),None)
            if not f: return
            s=dict(f['profile'],range=500*FT)
            point=SimpleNamespace(x=f['x'],y=f['y'],floor=f['floor']) if action=='control_water' else self._circle_spell_point(p,s,options,
                visible=action=='move_pack',clear_path=action=='move_pack')
            if point is None:return
            if action=='move_pack':
                turn=int((now-f['born'])//TURN)
                if f.get('moved_turn')==turn or distance(SimpleNamespace(x=f['x'],y=f['y']),point)>30*FT or getattr(p,'_circle_spell_motion_time',-1)<f['born']+turn*TURN: return
                x,y=f['x'],f['y'];steps=max(1,math.ceil(math.hypot(point.x-x,point.y-y)/(5*FT)))
                for step in range(1,steps+1):
                    f.update(x=x+(point.x-x)*step/steps,y=y+(point.y-y)*step/steps,moved=True)
                    self._tick_circle_field(f)
                f['moved_turn']=turn
            elif action=='redirect_wind':
                if p.bonus_cooldown_until>now:return
                self.begin_action(p,True);dx,dy=point.x-p.x,point.y-p.y;n=math.hypot(dx,dy) or 1;f['direction']=[dx/n,dy/n]
            else:
                variant=options.get('variant')
                if variant not in ('flood','part','redirect','whirlpool') or p.attack_cooldown_until>now:return
                info=self.environment_water_info(SimpleNamespace(x=f['x'],y=f['y'],floor=f['floor'])) if hasattr(self,'environment_water_info') else {}
                if variant=='whirlpool' and (info.get('depth_ft',0)<25 or info.get('width_ft',0)<50):return
                self.begin_action(p);f['profile'].update(water_variant=variant,water_level_ft=20 if variant=='flood' else -20 if variant=='part' else 0,whirlpool=variant=='whirlpool',flow=list(p.facing))
            return
        if action=='escape_web':
            value=self.target_conditions(p).get('web_restrained')
            if not value or p.attack_cooldown_until>now:return
            self.begin_action(p);result=self.environment_ability_check(p,'strength',value['dc'],skill='athletics')
            if result.get('success',result.get('total',0)>=value['dc']): self.target_conditions(p).pop('web_restrained',None)
            return
        if action=='escape_whirlpool':
            value=self.target_conditions(p).get('whirlpool')
            if not value or p.attack_cooldown_until>now:return
            self.begin_action(p);result=self.environment_ability_check(p,'strength',value['dc'],skill='athletics')
            if result.get('saved',result.get('total',0)>=value['dc']):
                p.buffs['whirlpool_escape']=dict(until=now+TURN,field_id=value.get('field_id'))
            return
        if action=='wake':
            t=self.players.get(options.get('target_id')) or self.enemies.get(options.get('enemy_id'))
            if t is None or not same_floor(p,t) or distance(p,t)>5*FT or not self.line_clear(p,t) or p.attack_cooldown_until>now:return
            if self.is_player_target(t) and self.friendly_target_error(p,t,5*FT):return
            values=self.target_conditions(t)
            if not any(values.get(k,{}).get('spell_id')=='sleep' for k in ('sleep_pending','unconscious')):return
            self.begin_action(p)
            for k in ('sleep_pending','unconscious'):
                if values.get(k,{}).get('spell_id')=='sleep':values.pop(k,None)
            return
        if action=='tree_step': return await self._tree_step(p,options)
        if action=='attack_wall': return await self._attack_wall(p,options)

    async def _tree_step(self,p,options):
        buff=p.buffs.get('tree_stride',{});now=self.now()
        if buff.get('until',0)<=now or buff.get('step_until',0)>now or not hasattr(self,'environment_trees'):return
        trees=self.environment_trees();point=self._circle_spell_point(p,{'range':500*FT},options,visible=False,clear_path=False)
        if point is None:return
        living=[t for t in trees if t.get('living',True) and t.get('floor',0)==p.floor and t.get('size','large') in ('large','huge','gargantuan')]
        origins=[t for t in living if math.hypot(t['x']-p.x,t['y']-p.y)<=5*FT+t.get('radius',0)]
        dests=[t for t in living if math.hypot(t['x']-point.x,t['y']-point.y)<=5*FT+t.get('radius',0)]
        pair=next(((a,b) for a in origins for b in dests if a is not b and a.get('kind')==b.get('kind') and math.hypot(a['x']-b['x'],a['y']-b['y'])<=500*FT),None)
        if not pair:return await self.notice(p,'Podejdź do żywego drzewa i wskaż drugie tego samego rodzaju.')
        dest=pair[1]
        for angle in range(0,360,45):
            x=dest['x']+math.cos(math.radians(angle))*(dest.get('radius',0)+40);y=dest['y']+math.sin(math.radians(angle))*(dest.get('radius',0)+40)
            q=SimpleNamespace(x=x,y=y,floor=p.floor)
            if self.blocked_for(p,x,y) or p.pvp_combat_until>now and self.in_safe(q):continue
            p.x,p.y=x,y;buff['step_until']=now+TURN;p.buffs['tree_movement_cost']={'until':now+TURN,'feet':10};return

    async def _attack_wall(self,p,options):
        if not options.get('field_id'):
            choices=[(f,i,z) for f in self._circle_fields() if f['key']=='wall_of_stone' and f['floor']==p.floor
                     for i,z in enumerate(f.get('segments',[])) if z['hp']>0 and math.hypot(z['x']-p.x,z['y']-p.y)<=rules.attack_range(p)]
            if not choices:return
            f,i,z=min(choices,key=lambda item:math.hypot(item[2]['x']-p.x,item[2]['y']-p.y))
            options=dict(options,field_id=f['id'],segment=i)
        f=next((f for f in self._circle_fields() if f['id']==options.get('field_id') and f['key']=='wall_of_stone'),None)
        idx=options.get('segment',0)
        if f is None or type(idx) is not int or not 0<=idx<len(f.get('segments',[])) or p.attack_cooldown_until>self.now():return
        segment=f['segments'][idx];q=SimpleNamespace(id=f['id']+':'+str(idx),name='Kamienny panel',
            x=segment['x'],y=segment['y'],floor=f['floor'],conditions={},kind='wall')
        if segment['hp']<=0 or not same_floor(p,q) or distance(p,q)>rules.attack_range(p) or self.in_safe(p):return
        self.begin_action(p)
        kind=rules.damage_type(p) if hasattr(rules,'damage_type') else 'bludgeoning'
        for _ in range(rules.attacks_per_round(p)):
            if segment['hp']<=0:break
            dis,adv=self.environment_attack_flags(p,q)
            result=rules.roll_attack(self.combat_rng,rules.attack_bonus(p)-getattr(p,'exhaustion',0)*2,15,rules.weapon_dice(p),
                disadvantage=dis or rules.gear.weapon_disadvantage(p),advantage=adv or self.target_condition(p,'foresight'))
            result['damage_type']=kind
            rules.savage_attacker_damage(p,result,self.combat_rng,self.now());self.fighter_adjust_damage(p,result)
            self.environment_attack_riders(p,q,result,melee=rules.gear.melee(p))
            components=result.get('damage_components',[{'type':kind,'damage':result['damage']}])
            damage=sum(c['damage'] for c in components if c['type'] not in ('poison','psychic')) if result.get('hit') else 0
            segment['hp']=max(0,segment['hp']-damage);self.report_roll(p,q,dict(result,damage=damage),'Atak na kamienny mur',p)
        if not any(z['hp']>0 for z in f['segments']):self.end_field_effect(f);self.circle_spell_fields.remove(f);self._erase_circle_wall(f)
        else:self._persist_circle_wall(f)
