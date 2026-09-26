"""Warrior's permanent choices and weapon rules (0.8.13).

Original Polish summaries. Cooldowns, automatic standing and the level mapping
are Bractwo adaptations. Equipment, rolls and choices are server authoritative.
"""
import math

VERSION = 1
SECOND_WIND_COOLDOWN = 60
ACTION_SURGE_COOLDOWN = 90
STAND_SECONDS = 1.5  # standing spends half of a three-second movement round
STYLES = {
    'dueling': dict(name='Pojedynek', icon='assets/feats/dueling.svg',
        description='+2 do obrażeń bronią wręcz używaną jednorącz. Tarcza jest dozwolona.',
        requirement='Broń wręcz w jednej ręce.'),
    'defense': dict(name='Obrona', icon='assets/feats/defense.svg',
        description='+1 do Klasy Pancerza podczas noszenia lekkiego, średniego lub ciężkiego pancerza.',
        requirement='Lekki, średni lub ciężki pancerz.'),
    'great_weapon': dict(name='Walka wielką bronią', icon='assets/feats/great_weapon.svg',
        description='Wyniki 1 i 2 na kościach obrażeń broni używanej oburącz liczą się jak 3.',
        requirement='Broń dwuręczna albo wszechstronna używana oburącz.'),
}
MASTERIES = {
    'longsword': dict(name='Miecz długi', effect='sap', effect_name='Osłabienie',
        icon='assets/feats/sap.svg', description='Trafienie utrudnia następny rzut ataku przeciwnika przed twoją kolejną rundą.'),
    'greatsword': dict(name='Miecz dwuręczny', effect='graze', effect_name='Draśnięcie',
        icon='assets/feats/graze.svg', description='Przy pudle obrażenia równe modyfikatorowi Siły. Bez kości, premii magicznych i efektów trafienia.'),
    'maul': dict(name='Młot dwuręczny', effect='topple', effect_name='Powalenie',
        icon='assets/feats/topple.svg', description='Po trafieniu: obrona na Kondycję albo powalenie. Wstawanie zajmuje połowę rundy ruchu (1,5 s).'),
}


def _rules():
    try:
        from . import combat_rules
    except ImportError:
        import combat_rules
    return combat_rules


def equipped(p, slot):
    if not hasattr(p, 'inventory'): return {}
    return _rules().equipped_item(p, slot)


def weapon_kind(p):
    return equipped(p, 'weapon').get('weapon_type', '')


def two_handed(p):
    weapon = equipped(p, 'weapon')
    return bool(weapon.get('two_handed') or (weapon.get('versatile_dice') and
        getattr(p, 'weapon_grip', 'one') == 'two' and not p.equipment.get('shield')))


def shield_bonus(p):
    if getattr(p, 'form', '') or two_handed(p): return 0
    if not _rules().gear.shield_trained(p):return 0
    return max(0, int(equipped(p, 'shield').get('shield_ac', 0)))


def style_active(p, style=None):
    if getattr(p, 'class_id', '') != 'knight' or getattr(p, 'form', ''): return False
    style = style if style is not None else getattr(p, 'fighting_style', '')
    if style == 'defense':
        return equipped(p, 'armor').get('armor_kind') in ('light', 'medium', 'heavy')
    weapon = equipped(p, 'weapon')
    melee = bool(weapon and weapon.get('weapon') != 'bow' and 'knight' in weapon.get('class_ids', []))
    if style == 'dueling': return melee and not two_handed(p)
    if style == 'great_weapon': return melee and two_handed(p)
    return False


def mastery(p):
    if getattr(p, 'class_id', '') != 'knight' or getattr(p, 'form', ''): return ''
    return MASTERIES.get(weapon_kind(p), {}).get('effect', '')


def class_sheet(p):
    if p.class_id != 'knight': return {}
    key = getattr(p, 'fighting_style', '')
    return dict(style=key, style_name=STYLES.get(key, {}).get('name', 'Nie wybrano'),
        style_active=style_active(p), choices=[dict(id=k, **v, active_with_gear=style_active(p, k)) for k,v in STYLES.items()],
        pending=not key, masteries=[dict(id=k, **v, active=weapon_kind(p)==k and not p.form) for k,v in MASTERIES.items()],
        weapon_grip=getattr(p,'weapon_grip','one'), can_change_grip=bool(equipped(p,'weapon').get('versatile_dice')),
        two_handed=two_handed(p), shield_ac=shield_bonus(p))


def configure(items, spells, classes):
    """Called after the older loot/rarity passes; do not clobber their bonuses."""
    classes['knight'].update(description='Styl walki, mistrzostwo broni, kolczuga i tarcza. Drugi oddech bez many.',
        ability_cost=0, ability_cooldown=SECOND_WIND_COOLDOWN)
    spells['second_wind'].update(mana=0, cooldown=SECOND_WIND_COOLDOWN,
        description='Akcja dodatkowa: odzyskaj 1k10 + premię wojownika HP. Premia +1 co 5 poziomów. Bez many. Odnowienie: 60 s.')
    # The three implemented mastery types; variants retain their original damage.
    for key, item in items.items():
        if item.get('slot') != 'weapon': continue
        item.setdefault('two_handed', item.get('weapon')=='bow')
        if 'knight' not in item.get('class_ids', []): continue
        name = item.get('name', '').casefold()
        if key.startswith('knight_weapon_') or 'miecz' in name or key in ('bandit_sword','obsidian_sword'):
            category = 'greatsword' if tuple(item.get('weapon_dice',()))==(2,6) or 'dwuręcz' in name else 'longsword'
            item['weapon_type'] = category
            item['two_handed'] = category == 'greatsword'
            if category=='longsword': item['versatile_dice']=[1,10]
        elif 'dwuręcz' in name and 'młot' in name:
            item.update(weapon_type='maul', two_handed=True)
        elif tuple(item.get('weapon_dice',())) == (1,12):
            item.update(two_handed=True)  # greataxes are NOT longswords or mauls
    common = dict(attack=0, attack_bonus=0, armor=0, ac_bonus=0, class_ids=['knight'], min_level=1, rarity='common')
    items['fighter_chain_mail'] = dict(common, name='Kolczuga wojownika', slot='armor', base_ac=16,
        armor_kind='heavy', armor_summary='Ciężki pancerz · KP 16 · bez premii Zręczności',
        value=25, price=75, icon='assets/equipment/fighter_chain_mail.svg', description='Stalowe ogniwa chronią w walce wręcz.')
    items['fighter_shield'] = dict(common, name='Tarcza wojownika', slot='shield', shield_ac=2,
        armor_summary='Tarcza · +2 KP', value=3, price=10, icon='assets/equipment/fighter_shield.svg',
        description='Zajmuje drugą rękę. Nie działa z bronią używaną oburącz.')
    for key,name,kind,dtype,price in [('training_greatsword','Miecz dwuręczny rekruta','greatsword','slashing',25),
                                    ('training_maul','Młot dwuręczny rekruta','maul','bludgeoning',15)]:
        items[key]=dict(common, name=name, slot='weapon', weapon='sword', weapon_type=kind,
            two_handed=True, weapon_dice=[2,6], damage_dice='2k6', damage_type=dtype,
            value=price//3, price=price, icon='assets/equipment/'+key+'.svg', description='Broń dwuręczna. Nie można używać tarczy.')
    for item in items.values():
        if item.get('weapon_type') in MASTERIES:
            spec=MASTERIES[item['weapon_type']]
            item.update(mastery_name=spec['effect_name'], mastery_description=spec['description'], mastery_icon=spec['icon'])
    spells['action_surge']=dict(id='action_surge', name='Zryw akcji', english='Action Surge', circle=0,
        class_ids=['knight'], class_levels={'knight':5}, min_level=5, kind='surge', action='extra',
        description='Natychmiast wykonaj dodatkową akcję ataku przeciw wybranemu celowi. Obejmuje wszystkie twoje ataki; nie odnawia czarów ani Drugiego oddechu. Bez many. Odnowienie: 90 s.',
        feature=True, source='Zdolność klasy · adaptacja Bractwa', mana=0, cooldown=ACTION_SURGE_COOLDOWN,
        targeting='hostile', range=108, pvp=True, icon='assets/spells/action_surge.svg', effect='spell',
        shape='single', visual=dict(style='surge', theme='steel', colors=['#dfb654','#ffdf8b','#fff6cf'],shots=1))


class FighterGame:
    def migrate_fighter(self, p, make_item):
        p.equipment.setdefault('shield','')
        if getattr(p,'fighting_style','') not in STYLES: p.fighting_style=''
        if getattr(p,'weapon_grip','one') not in ('one','two'):p.weapon_grip='one'
        if p.class_id != 'knight': return
        if p.fighter_rules_version < VERSION:
            for key,slot in [('fighter_chain_mail','armor'),('fighter_shield','shield')]:
                all_items=p.inventory+p.depot
                item=next((i for i in all_items if i['template']==key),None)
                if item is None:
                    item=make_item(key)
                    # One-time migration may exceed the old bag cap. Never destroy gear.
                    p.inventory.append(item)
                old_template=next((i.get('template','') for i in p.inventory if i['uid']==p.equipment.get(slot)), '')
                can_wear=slot!='shield' or not two_handed(p)
                if item in p.inventory and can_wear and (not p.equipment.get(slot) or slot=='armor' and old_template=='cloth'):
                    p.equipment[slot]=item['uid']
            p.fighter_rules_version=VERSION
        # Repair incompatible historic/corrupted combinations without losing items.
        if two_handed(p) and p.equipment.get('shield'):p.equipment['shield']=''

    def fighter_choice_error(self,p):
        if p.class_id!='knight':return 'Styl walki wybiera wojownik.'
        if not p.alive:return 'Najpierw wróć do życia.'
        if p.combat_until>self.now():return 'Wybierz styl po zakończeniu walki.'
        if p.fighting_style and (not self.near_service(p,'master') or not self.in_safe(p)):
            return 'Zmienisz styl bez opłaty u mistrza profesji w osadzie.'
        return ''

    async def select_fighting_style(self,p,key):
        if not isinstance(key,str) or key not in STYLES:return await self.notice(p,'Wybierz jeden z trzech stylów walki.')
        reason=self.fighter_choice_error(p)
        if reason:return await self.notice(p,reason)
        if p.fighting_style==key:return
        p.fighting_style=key
        with self.db:self.save_player(p)
        await self.notice(p,'Styl walki: '+STYLES[key]['name']+'.')

    async def set_weapon_grip(self,p,grip):
        if p.form or not p.alive or grip not in ('one','two') or not equipped(p,'weapon').get('versatile_dice'):
            return await self.notice(p,'Tylko broń wszechstronna pozwala zmienić chwyt.')
        if p.combat_until>self.now():return await self.notice(p,'Zmienisz chwyt po walce.')
        if grip=='two':p.equipment['shield']=''
        p.weapon_grip=grip
        with self.db:self.save_player(p)
        await self.notice(p,'Chwyt oburącz; tarcza pozostaje w plecaku.' if grip=='two' else 'Chwyt jednorącz.')

    def fighter_roll_flags(self,source,target):
        """Consume Sap once, for an attack roll (never for a save)."""
        now=self.now()
        def conditions(actor):return getattr(actor,'buffs',getattr(actor,'conditions',{}))
        own=conditions(source); other=conditions(target)
        sap=own.pop('sap',{})
        prone=own.get('prone',{}).get('until',0)>now
        target_prone=other.get('prone',{}).get('until',0)>now
        close=math.hypot(source.x-target.x,source.y-target.y)<=108
        return (sap.get('until',0)>now or prone or target_prone and not close), bool(target_prone and close)

    def fighter_adjust_damage(self,p,result):
        """Preserve the actual rolled dice; no new RNG draws and no spell bonus."""
        if p.class_id!='knight' or p.form:return
        if result['hit'] and style_active(p) and p.fighting_style=='great_weapon':
            raw=list(result['damage_rolls'])
            result['raw_damage_rolls']=raw
            result['damage_rolls']=[max(3,n) for n in raw]
            result['damage']=max(0,sum(result['damage_rolls'])+result.get('damage_modifier',0))
            result['fighting_style']='great_weapon'
        if not result['hit'] and mastery(p)=='graze':
            amount=max(0,_rules().ability_modifier(p,_rules().attack_ability(p)))
            result.update(graze=True,damage=amount,damage_dice=str(amount)+' (Draśnięcie)',damage_rolls=[],damage_modifier=amount)

    def fighter_on_weapon_hit(self,p,target,result):
        if not result or p.class_id!='knight' or p.form:return
        key=mastery(p)
        if result.get('graze'):
            self.fighter_effect(p,target,'graze')
            return
        if not result.get('hit') or target.hp<=0:return
        if key not in ('sap','topple'):return
        rules=_rules()
        conditions=self.target_conditions(target)
        if key=='sap':
            conditions['sap']=dict(until=self.now()+rules.ROUND_SECONDS, owner=p.id, hostile=True,
                                   spell_id='weapon_sap',concentration=False)
        elif key=='topple':
            dc=8+rules.proficiency(p)+rules.ability_modifier(p,rules.attack_ability(p))
            save=self.target_save(target,'constitution',dc,dict(damage=0,damage_dice='',damage_rolls=[]))
            save['save_ability']='constitution'
            self.report_roll(p,target,save,'Powalenie · obrona',p)
            if save['saved']:return
            conditions['prone']=dict(until=self.now()+STAND_SECONDS,owner=p.id,hostile=True,
                                     spell_id='weapon_topple',concentration=False)
        if self.is_player_target(target):
            unjust=target.last_pvp_unjust if target.last_pvp_attacker==p.id else False
            self.record_pvp_effect(p,target,unjust)
        self.fighter_effect(p,target,key)

    def fighter_effect(self,p,target,key):
        fx=self.combat_effect(p,'fighter_'+key,target,duration=.65)
        fx.update(mastery=key)
        return fx
