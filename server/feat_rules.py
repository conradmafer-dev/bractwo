"""UI_31: ten Bractwo adaptations of feats. Only the server grants effects.

Origin/advancement budgets live in equipment_rules; this module never adds
currency. Lucky spends persisted rest resources. Three-second weapon riders
share a turn with bonus actions/Action Surge, and cannot proc from spell damage.
Descriptions intentionally document the actual realtime adaptation, not every
benefit in a tabletop feat of the same name.
"""
import math

NEW_FEATS = {
    'alert': dict(name='Czujny', category='origin', abilities=[],
        description='Zwiększa Percepcję o premię z biegłości. Pomaga dostrzegać szczegóły i wskazówki w otoczeniu.'),
    'crafter': dict(name='Rzemieślnik', category='origin', abilities=[],
        description='Towary u kupców kosztują o 20% mniej (cena zaokrąglana w górę). Nie zmienia cen sprzedaży, usług ani run.'),
    'healer': dict(name='Uzdrowiciel', category='origin', abilities=[],
        description='Mikstury zdrowia leczą dodatkowo o premię z biegłości. Na krótkim odpoczynku przerzucasz każdą 1 na kości zdrowia raz; nowy wynik obowiązuje.'),
    'lucky': dict(name='Szczęściarz', category='origin', abilities=[],
        description='Automatycznie przerzucasz nieudany rzut obronny lub koncentracji i zachowujesz lepszy wynik. Liczba użyć równa premii z biegłości; odnowienie po długim odpoczynku. Nie zmienia Przepowiedni ani automatycznej porażki.'),
    'resilient': dict(name='Odporny', abilities=['strength','dexterity','constitution','intelligence','wisdom','charisma'],
        description='+1 do wybranej cechy (maks. 20) i biegłość w jej rzutach obronnych. Wybierz cechę bez posiadanej biegłości w obronie.'),
    'war_caster': dict(name='Mag bitewny', abilities=['intelligence','wisdom','charisma'], spellcasting=True,
        description='+1 Inteligencja, Mądrość lub Charyzma (maks. 20). Przewaga w rzutach utrzymania koncentracji po obrażeniach. Wymaga klasy rzucającej czary.'),
    'speedy': dict(name='Szybki', abilities=['dexterity','constitution'],
        description='+1 Zręczność lub Kondycja (maks. 20). Bez ciężkiego pancerza poruszasz się o 10 stóp na turę szybciej; teren i stany nadal ograniczają ruch.'),
    'piercer': dict(name='Przebijacz', abilities=['strength','dexterity'],
        description='+1 Siła lub Zręczność (maks. 20). Raz na turę przerzucasz niską kość kłutych obrażeń broni (nowy wynik obowiązuje). Kłuty krytyk broni dodaje jedną kość tej broni.'),
    'slasher': dict(name='Siekacz', abilities=['strength','dexterity'],
        description='+1 Siła lub Zręczność (maks. 20). Raz na turę cięte trafienie bronią spowalnia cel o 10 stóp na turę przez 3 s. Krytyk daje mu utrudnienie ataków na 3 s; spowolnienia nie sumują się.'),
    'crusher': dict(name='Miażdżyciel', abilities=['strength','constitution'],
        description='+1 Siła lub Kondycja (maks. 20). Raz na turę obuchowe trafienie bronią odpycha cel o 5 stóp, o ile droga jest wolna. Krytyk daje przewagę ataków przeciw niemu przez 3 s. Bossowie nie są odpychani.'),
}
for key,spec in NEW_FEATS.items():
    spec.update(grants=[], requires=[], icon='assets/feats/'+key+'.svg', adaptation=True)
    spec.setdefault('category','general')


def _modules():
    try: from . import combat_rules as rules, equipment_rules as gear, rest_rules as rest
    except ImportError: import combat_rules as rules, equipment_rules as gear, rest_rules as rest
    return rules,gear,rest


def save_proficiencies(p):
    rules,gear,rest=_modules()
    result=list(p.spec['saves'])
    for instance in gear.active_feats(p):
        if gear.feat_key(instance)=='resilient':
            ability=getattr(p,'training_feats',{}).get(instance,'')
            if ability in ('strength','dexterity','constitution','intelligence','wisdom','charisma') and ability not in result:result.append(ability)
    return result


def skill_bonus(p,skill):
    rules,gear,rest=_modules()
    return rules.proficiency(p) if skill=='perception' and gear.has_feat(p,'alert') else 0


def purchase_price(p,spec):
    rules,gear,rest=_modules()
    price=max(0,int(spec.get('price',0)))
    return (price*4+4)//5 if gear.has_feat(p,'crafter') else price


def shop_prices(p,items):
    rules,gear,rest=_modules()
    discount=gear.has_feat(p,'crafter')
    return {key:(int(s['price'])*4+4)//5 if discount else int(s['price']) for key,s in items.items() if 'price' in s}


def speed_bonus(p):
    rules,gear,rest=_modules()
    return 10*6.4/rules.ROUND_SECONDS if gear.has_feat(p,'speedy') and (getattr(p,'form','') or rules.equipped_item(p,'armor').get('armor_kind')!='heavy') else 0


def potion_healing(p,result):
    rules,gear,rest=_modules()
    if gear.has_feat(p,'healer'):
        amount=rules.proficiency(p)
        result['damage']+=amount
        result['damage_modifier']=result.get('damage_modifier',0)+amount
        result['damage_dice']+=f' + {amount} (Uzdrowiciel)'
        result['healer_bonus']=amount
    return result


def rest_die(p,rng,receipt=None):
    rules,gear,rest=_modules()
    first=rng.randint(1,p.spec['hit_die'])
    reroll=rng.randint(1,p.spec['hit_die']) if first==1 and gear.has_feat(p,'healer') else None
    value=reroll if reroll is not None else first
    if receipt is not None:
        receipt.update(first=first,reroll=reroll,value=value,sides=p.spec['hit_die'])
    return value


def lucky_save(p,result,rng,damage=None):
    """Use a charge only for a real, salvageable failed save; no login refill."""
    rules,gear,rest=_modules()
    if (not hasattr(p,'class_id') or result.get('saved') or result.get('automatic_failure')
            or result.get('portent') or result.get('check') not in ('save','concentration')
            or not gear.has_feat(p,'lucky') or result.get('bonus',0)+20<result.get('defense',0)
            or not rest.spend(p,'lucky')):return False
    before=result['roll'];reroll=rng.randint(1,20);chosen=max(before,reroll)
    result.update(lucky=True,lucky_previous=before,lucky_roll=reroll,roll=chosen,
                  total=chosen+result['bonus'],saved=chosen+result['bonus']>=result['defense'])
    if damage is not None:
        raw=damage.get('damage',0)
        result['damage']=raw//2 if result['saved'] and result.get('save_half') else 0 if result['saved'] else raw
    return True


def weapon_damage(p,result,rng,now):
    """Piercer touches only the base weapon pool, before other damage riders."""
    rules,gear,rest=_modules()
    if (not result.get('hit') or result.get('damage_type')!='piercing' or not gear.has_feat(p,'piercer')
            or getattr(p,'form','') or rules.environment.polymorph(p) or not gear.weapon(p) or gear.is_focus(gear.weapon(p))):return
    rules.begin_feat_turn(p,now)
    rolls=list(result.get('damage_rolls',[]));sides=rules.weapon_dice(p)[1]
    if not rolls:return
    if not getattr(p,'_piercer_used',False) and min(rolls)<(sides+1)/2:
        index=min(range(len(rolls)),key=rolls.__getitem__);old=rolls[index];rolls[index]=rng.randint(1,sides)
        result.update(piercer_reroll=[old,rolls[index]])
        p._piercer_used=True
    if result.get('critical'):
        extra=rng.randint(1,sides);rolls.append(extra);result['piercer_critical']=extra
        result['damage_dice']+=f' + 1k{sides} (Przebijacz)'
    result.update(damage_rolls=rolls,damage=max(0,sum(rolls)+result.get('damage_modifier',0)))


def weapon_riders(game,p,target,result,spell=False):
    """Shared PvE/PvP path. Collision-safe shove; timed effects never stack."""
    rules,gear,rest=_modules()
    if (spell or not result.get('hit') or not getattr(target,'alive',False) or getattr(target,'hp',0)<=0
            or not hasattr(p,'class_id') or getattr(p,'form','') or rules.environment.polymorph(p)
            or not gear.weapon(p) or gear.is_focus(gear.weapon(p))):return
    now=game.now();rules.begin_feat_turn(p,now)
    kind=result.get('damage_type');states=game.target_conditions(target)
    if kind=='slashing' and gear.has_feat(p,'slasher'):
        if not getattr(p,'_slasher_used',False):
            states['feat_slasher_slow']=dict(until=now+3,owner=p.id,hostile=True,spell_id='feat_slasher',concentration=False)
            p._slasher_used=True;result['slasher_slow']=True
        if result.get('critical'):
            states['feat_slasher_disadvantage']=dict(until=now+3,owner=p.id,hostile=True,spell_id='feat_slasher',concentration=False)
            result['slasher_critical']=True
    if kind=='bludgeoning' and gear.has_feat(p,'crusher'):
        if not getattr(p,'_crusher_used',False):
            p._crusher_used=True
            spec=rules.environment.enemy_spec(target)
            if not spec.get('boss') and getattr(target,'kind','')!='boss':
                dx,dy=target.x-p.x,target.y-p.y;length=math.hypot(dx,dy)
                if length>0:
                    before=(target.x,target.y)
                    game.environment_forced_move(target,dx/length*32,dy/length*32)
                    result['crusher_distance']=round(math.hypot(target.x-before[0],target.y-before[1]),2)
                    if not hasattr(target,'class_id'):game.reindex_enemy(target)
        if result.get('critical'):
            states['feat_crusher_exposed']=dict(until=now+3,owner=p.id,hostile=True,spell_id='feat_crusher',concentration=False)
            result['crusher_critical']=True
