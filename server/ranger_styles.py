"""Ranger's level-two Fighting Style and Druidic Warrior choices.

The server owns choices, equipment checks and defensive reactions. The ten
2024 Fighting Style benefits use their normal dice and feet; only Bractwo's
three-second turn clock replaces tabletop initiative. This module never spends
an advancement feat or grants the druid's Elemental Fury to a ranger.
"""
import math
from copy import deepcopy

REQUIRED_LEVEL = 2
FIVE_FEET = 32
BLINDSIGHT_FEET = 10
SOURCE = 'D&D 2024 · styl walki łowcy'

# Existing shared artwork represents the benefit; no missing client asset is
# advertised. The warrior keeps its separate, existing three-choice catalogue.
RANGER_STYLES = {
    'archery': dict(name='Łucznictwo', english='Archery', icon='assets/feats/martial_hunter.svg',
        description='+2 do rzutów trafienia bronią dystansową. Nie zwiększa obrażeń ani trafienia czarami; rzut bronią wręcz nie otrzymuje tej premii.',
        requirement='Atak bronią dystansową.'),
    'blind_fighting': dict(name='Walka bez wzroku', english='Blind Fighting', icon='assets/feats/alert.svg',
        description='Ślepowidzenie w promieniu 10 stóp: dostrzegasz istoty także w ciemności, mgle i mimo oślepienia. Nie widzisz przez ściany.',
        requirement='Istota w promieniu 10 stóp, bez całkowitej osłony.'),
    'defense': dict(name='Obrona', english='Defense', icon='assets/feats/defense.svg',
        description='+1 do Klasy Pancerza podczas noszenia lekkiego, średniego lub ciężkiego pancerza.',
        requirement='Lekki, średni lub ciężki pancerz.'),
    'dueling': dict(name='Pojedynek', english='Dueling', icon='assets/feats/dueling.svg',
        description='+2 do obrażeń bronią wręcz trzymaną jednorącz, jeżeli nie trzymasz innej broni. Tarcza jest dozwolona.',
        requirement='Jedna broń wręcz używana jednorącz; druga ręka bez broni.'),
    'great_weapon': dict(name='Walka wielką bronią', english='Great Weapon Fighting', icon='assets/feats/great_weapon.svg',
        description='Wyniki 1 i 2 na kościach obrażeń ataku bronią wręcz trzymaną oburącz liczą się jak 3.',
        requirement='Broń wręcz z właściwością Dwuręczna albo Wszechstronna, używana oburącz.'),
    'interception': dict(name='Przechwycenie', english='Interception', icon='assets/feats/martial_parry.svg',
        description='Reakcja: zmniejszasz obrażenia trafiającego ataku widocznego napastnika przeciw innemu sojusznikowi w zasięgu 5 stóp o 1k10 + premię z biegłości. Wymaga trzymania tarczy lub broni prostej albo żołnierskiej.',
        requirement='Tarcza albo broń; inny sojusznik do 5 stóp; widoczny napastnik i wolna reakcja.'),
    'protection': dict(name='Ochrona', english='Protection', icon='assets/feats/shields.svg',
        description='Reakcja z tarczą: widoczny napastnik ma utrudnienie ataku przeciw innemu sojusznikowi w zasięgu 5 stóp. Ochrona obejmuje kolejne ataki w tego sojusznika do twojej następnej tury, dopóki pozostajesz blisko niego.',
        requirement='Tarcza; inny sojusznik do 5 stóp; widoczny napastnik i wolna reakcja.'),
    'thrown_weapon': dict(name='Walka bronią rzucaną', english='Thrown Weapon Fighting', icon='assets/feats/piercer.svg',
        description='+2 do obrażeń trafiających ataków dystansowych bronią z właściwością Rzucana. Nie wzmacnia ciosów wręcz tą samą bronią.',
        requirement='Atak dystansowy bronią z właściwością Rzucana.'),
    'two_weapon': dict(name='Walka dwiema broniami', english='Two-Weapon Fighting', icon='assets/feats/martial_weapons.svg',
        description='Dodajesz modyfikator cechy do obrażeń dodatkowego ataku wynikającego z właściwości Lekka.',
        requirement='Dodatkowy atak właściwości Lekka inną lekką bronią.'),
    'unarmed': dict(name='Walka bez broni', english='Unarmed Fighting', icon='assets/feats/crusher.svg',
        description='Cios bez broni zadaje 1k6 + Siła, a gdy nie trzymasz broni ani tarczy: 1k8 + Siła. Na początku swojej tury możesz zadać 1k4 obuchowych jednej trzymanej przez siebie istocie.',
        requirement='Cios bez broni; dla k8 obie ręce bez broni i tarczy.'),
    'druidic_warrior': dict(name='Druidyczny wojownik', english='Druidic Warrior', icon='assets/feats/warden.svg',
        description='Zamiast atutu stylu walki poznajesz dwie różne sztuczki druida. Używasz Mądrości; sztuczki są darmowe i skalują się na poziomach 5, 11 i 17. Po zdobyciu poziomu łowcy możesz wymienić jedną z nich.',
        requirement='Wybierz dwie różne sztuczki druida.'),
}

# Guidance already has a fully working handler but its existing catalogue row
# belongs to the Circle of Stars. It is still a normal druid-list cantrip and is
# eligible here. Class-feature buttons (shape/circle/wild companion) never are.
DRUID_CANTRIPS = ('shillelagh', 'produce_flame', 'thorn_whip', 'starry_wisp', 'guidance')


def _modules():
    try:
        from . import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter, environment_rules as environment, weapon_actions
    except ImportError:
        import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter, environment_rules as environment, weapon_actions
    return rules, dnd, fighter, environment, weapon_actions


def configure(spells, classes):
    """Run after circle spells are configured so Guidance is available too."""
    for key in DRUID_CANTRIPS:
        spec = spells.get(key)
        if not spec or spec.get('circle') != 0 or spec.get('feature'):continue
        if 'ranger' not in spec['class_ids']:spec['class_ids'].append('ranger')
        spec.setdefault('class_min_levels', {})['ranger'] = REQUIRED_LEVEL
        spec.setdefault('class_levels', {})['ranger'] = REQUIRED_LEVEL
        spec['ranger_style_required'] = 'druidic_warrior'
    classes['ranger']['description'] = 'Style walki i towarzysz'


def available_cantrips():
    _, dnd, _, _, _ = _modules()
    return [key for key in DRUID_CANTRIPS if key in dnd.SPELLS and dnd.SPELLS[key].get('circle') == 0
            and not dnd.SPELLS[key].get('feature')]


def learned_cantrips(p):
    raw = getattr(p, 'ranger_style_cantrips', [])
    if not isinstance(raw, list):return []
    allowed = available_cantrips()
    return list(dict.fromkeys(key for key in raw if isinstance(key, str) and key in allowed))[:2]


def grants_cantrip(p, key):
    return bool(getattr(p, 'class_id', '') == 'ranger' and getattr(p, 'level', 1) >= REQUIRED_LEVEL
                and getattr(p, 'fighting_style', '') == 'druidic_warrior'
                and key in learned_cantrips(p))


def sanitize(p):
    """Keep validated saved choices without inventing a choice for old players."""
    if getattr(p, 'class_id', '') != 'ranger':return
    selected = getattr(p, 'fighting_style', '')
    if not isinstance(selected, str) or selected not in RANGER_STYLES:p.fighting_style = ''
    picks = learned_cantrips(p)
    if p.fighting_style == 'druidic_warrior' and len(picks) != 2:
        p.fighting_style = ''
    p.ranger_style_cantrips = picks if p.fighting_style == 'druidic_warrior' else []
    value = getattr(p, 'ranger_cantrip_replacement_level', 0)
    p.ranger_cantrip_replacement_level = max(0, min(p.level, value)) if type(value) is int else p.level
    if p.fighting_style == 'druidic_warrior' and p.ranger_cantrip_replacement_level < REQUIRED_LEVEL:
        p.ranger_cantrip_replacement_level = p.level
    if not p.fighting_style:p.ranger_cantrip_replacement_level = 0
    enabled = getattr(p, 'ranger_style_reaction_enabled', True)
    p.ranger_style_reaction_enabled = enabled if type(enabled) is bool else True


def style_active(p, key=None):
    rules, _, fighter, environment, weapons = _modules()
    if (getattr(p, 'class_id', '') != 'ranger' or getattr(p, 'level', 1) < REQUIRED_LEVEL
            or getattr(p, 'form', '') or environment.polymorph(p)):return False
    key = getattr(p, 'fighting_style', '') if key is None else key
    if not isinstance(key, str) or key not in RANGER_STYLES:return False
    weapon = rules.gear.weapon(p)
    actual_weapon = bool(weapon and not rules.gear.is_focus(weapon))
    if key == 'defense':
        return fighter.equipped(p, 'armor').get('armor_kind') in ('light', 'medium', 'heavy')
    if key == 'blind_fighting':return True
    if key == 'druidic_warrior':return len(learned_cantrips(p)) == 2
    if key == 'unarmed':return True
    shield = weapons.held_item(p, 'shield') and not fighter.two_handed(p)
    if key == 'protection':return bool(shield)
    if key == 'interception':
        return bool(shield or any(weapons.held_item(p, slot).get('weapon_category') in ('simple', 'martial')
                    for slot in ('weapon', 'offhand')))
    # Context overrides describe the actual attack hand. Unarmed attacks do not
    # inherit a bow/weapon benefit just because that item remains equipped.
    if weapons.mode(p) == 'unarmed':return False
    if key == 'archery':return actual_weapon and bool(weapon.get('ranged'))
    if key == 'dueling':
        return (actual_weapon and not weapon.get('ranged') and not fighter.two_handed(p)
                and not weapons.held_item(p, 'offhand'))
    if key == 'great_weapon':
        return (actual_weapon and weapons.mode(p) == 'weapon' and not weapon.get('ranged') and fighter.two_handed(p)
                and bool(weapon.get('two_handed') or weapon.get('versatile_dice')))
    if key == 'thrown_weapon':return actual_weapon and bool(weapon.get('thrown'))
    if key == 'two_weapon':return actual_weapon and bool(weapon.get('light'))
    return False


def attack_bonus(p):
    """Archery is for Ranged weapons, never spell attacks or thrown swords."""
    return 2 if getattr(p, 'fighting_style', '') == 'archery' and style_active(p) else 0


def damage_modifier(p, *, thrown=False):
    return 2 if thrown and getattr(p, 'fighting_style', '') == 'thrown_weapon' and style_active(p) else 0


def adjust_damage_dice(p, rolls):
    """Great Weapon Fighting covers the attack's rolled damage dice, incl. riders."""
    return [max(3, value) for value in rolls] if getattr(p, 'fighting_style', '') == 'great_weapon' and style_active(p) else list(rolls)


def blindsight(p):
    return BLINDSIGHT_FEET if getattr(p, 'fighting_style', '') == 'blind_fighting' and style_active(p) else 0


def can_replace_cantrip(p):
    return bool(getattr(p, 'class_id', '') == 'ranger' and getattr(p, 'fighting_style', '') == 'druidic_warrior'
                and len(learned_cantrips(p)) == 2 and p.level > max(REQUIRED_LEVEL, getattr(p, 'ranger_cantrip_replacement_level', 0)))


def class_sheet(p):
    _, dnd, fighter, _, _ = _modules()
    if getattr(p, 'class_id', '') != 'ranger':return {}
    key = getattr(p, 'fighting_style', '')
    picks = learned_cantrips(p)
    return dict(class_id='ranger', required_level=REQUIRED_LEVEL, style=key,
        style_name=RANGER_STYLES.get(key, {}).get('name', 'Nie wybrano'), style_active=style_active(p),
        choices=[dict(id=k, **v, active_with_gear=style_active(p, k)) for k, v in RANGER_STYLES.items()],
        pending=p.level >= REQUIRED_LEVEL and not key, can_change_style=False,
        style_change_reason='Styl walki łowcy jest jednorazowym wyborem klasy. Druidyczny wojownik pozwala wymienić jedną sztuczkę po zdobyciu poziomu.',
        masteries=[], weapon_grip=getattr(p, 'weapon_grip', 'one'),
        can_change_grip=bool(fighter.equipped(p, 'weapon').get('versatile_dice')),
        two_handed=fighter.two_handed(p), shield_ac=fighter.shield_bonus(p),
        cantrips=[dict(id=c, name=dnd.SPELLS[c]['name'], description=dnd.SPELLS[c]['description'],
                      selected=c in picks) for c in available_cantrips()], chosen_cantrips=picks,
        cantrip_replacement_available=can_replace_cantrip(p),
        cantrip_replacement_level=getattr(p, 'ranger_cantrip_replacement_level', 0),
        ranger_style_reactions=dict(enabled=getattr(p, 'ranger_style_reaction_enabled', True),
                                    available=key in ('protection', 'interception'),
                                    description='Automatyczna reakcja w obronie pobliskiego członka drużyny albo jego towarzysza. Wspólna pula reakcji; 5 stóp zasięgu.'),
        source=SOURCE)


def metadata():
    return dict(required_level=REQUIRED_LEVEL, styles=deepcopy(RANGER_STYLES),
                cantrips=available_cantrips(), cantrip_levels=[5, 11, 17],
                choice_cost=0, choice_is_feat_point=False, source=SOURCE)


class RangerStyles:
    def ranger_style_choice_error(self, p):
        _, _, _, environment, _ = _modules()
        if p.class_id != 'ranger':return 'Ten wybór należy do łowcy.'
        if p.level < REQUIRED_LEVEL:return 'Styl walki łowcy wybierzesz na poziomie 2.'
        if not p.alive or p.hp <= 0:return 'Najpierw wróć do życia.'
        if p.form or environment.polymorph(p):return 'Wybierz styl poza przemianą.'
        if environment.incapacitated(p, self.now()):return 'Nie możesz teraz dokonać wyboru.'
        if p.combat_until > self.now():return 'Dokonaj wyboru po zakończeniu walki.'
        return ''

    async def select_ranger_style(self, p, key, cantrips=None):
        if not isinstance(key, str) or key not in RANGER_STYLES:
            return await self.notice(p, 'Wybierz styl walki albo Druidycznego wojownika.')
        reason = self.ranger_style_choice_error(p)
        if reason:return await self.notice(p, reason)
        if getattr(p, 'fighting_style', ''):
            return await self.notice(p, 'Styl walki łowcy został już wybrany.')
        if key == 'druidic_warrior':
            if (not isinstance(cantrips, list) or len(cantrips) != 2
                    or any(not isinstance(c, str) or c not in available_cantrips() for c in cantrips)
                    or cantrips[0] == cantrips[1]):
                return await self.notice(p, 'Wybierz dokładnie dwie różne sztuczki druida.')
        elif cantrips not in (None, []):
            return await self.notice(p, 'Sztuczki wybierasz tylko dla Druidycznego wojownika.')
        p.fighting_style = key
        p.ranger_style_cantrips = list(cantrips) if key == 'druidic_warrior' else []
        p.ranger_cantrip_replacement_level = p.level if key == 'druidic_warrior' else 0
        self._ranger_style_refresh(p)
        with self.db:self.save_player(p)
        await self.notice(p, 'Styl walki: '+RANGER_STYLES[key]['name']+'.')

    async def replace_ranger_cantrip(self, p, old, new):
        reason = self.ranger_style_choice_error(p)
        if reason:return await self.notice(p, reason)
        if not can_replace_cantrip(p):
            return await self.notice(p, 'Wymienisz jedną sztuczkę po zdobyciu kolejnego poziomu łowcy.')
        picks = learned_cantrips(p)
        if (not isinstance(old, str) or not isinstance(new, str) or old not in picks
                or new not in available_cantrips() or new in picks):
            return await self.notice(p, 'Wskaż poznaną sztuczkę i inną sztuczkę druida.')
        p.ranger_style_cantrips = [new if key == old else key for key in picks]
        p.ranger_cantrip_replacement_level = p.level
        self._ranger_style_refresh(p)
        with self.db:self.save_player(p)
        await self.notice(p, 'Wymieniono sztuczkę Druidycznego wojownika.')

    async def set_ranger_style_reaction(self, p, enabled):
        if type(enabled) is not bool or p.class_id != 'ranger' or p.fighting_style not in ('protection', 'interception'):
            return
        p.ranger_style_reaction_enabled = enabled
        with self.db:self.save_player(p)
        await self.notice(p, 'Reakcja stylu walki: '+('włączona.' if enabled else 'wyłączona.'))

    def _ranger_style_refresh(self, p):
        _, dnd, _, _, _ = _modules()
        dnd.sync_hotbar(p)
        p._spell_profiles_cache = None
        p._level_up_cache = None
        p._equipment_preview_cache = None

    def ranger_blindsight(self, p):
        return blindsight(p)

    def _ranger_guard_friend(self, guardian, target):
        if guardian is target:return False
        if self.is_player_target(target):return not self.friendly_target_error(guardian, target, FIVE_FEET)
        if getattr(target, 'is_companion', False):
            owner = self.players.get(getattr(target, 'owner_id', ''))
            return bool(owner and not self.friendly_target_error(guardian, owner, float('inf')))
        return False

    def _ranger_guard_ready(self, guardian, source, target, key, *, reaction=True):
        _, _, _, environment, _ = _modules()
        if (guardian is target or guardian is source or guardian.class_id != 'ranger'
                or guardian.fighting_style != key or not style_active(guardian)
                or not getattr(guardian, 'ranger_style_reaction_enabled', True)
                or not guardian.alive or guardian.hp <= 0 or guardian.disconnected
                or environment.incapacitated(guardian, self.now())
                or environment.active(guardian, 'no_reactions', self.now())
                or reaction and guardian.reaction_ready > self.now()):return False
        if (guardian.floor != target.floor or guardian.floor != source.floor
                or math.hypot(guardian.x-target.x, guardian.y-target.y) > FIVE_FEET
                or not self.line_clear(guardian, target) or not self._ranger_guard_friend(guardian, target)):
            return False
        return self.environment_can_see(guardian, source)

    def _ranger_guardians(self, source, target, key):
        return sorted((p for p in self.players.values() if self._ranger_guard_ready(p, source, target, key)),
                      key=lambda p: (math.hypot(p.x-target.x, p.y-target.y), str(p.id)))

    def _ranger_support(self, guardian, target):
        recipient = target if self.is_player_target(target) else self.players.get(getattr(target, 'owner_id', ''))
        if recipient:self.join_pvp_support(guardian, recipient)

    def ranger_protection(self, source, target):
        """Before an attack roll: protect the same ally until our next turn.

        The live adjacency and visibility checks run on every subsequent roll.
        The shared feat-turn token expires the protection when the guardian
        starts its next turn, including after a bonus action or Action Surge.
        """
        rules, _, _, _, _ = _modules()
        value = self.target_conditions(target).get('ranger_protection', {})
        owner = self.players.get(value.get('owner', ''))
        if (owner and value.get('until', 0) > self.now()
                and value.get('turn') == getattr(owner, '_feat_turn_until', 0)
                and self._ranger_guard_ready(owner, source, target, 'protection', reaction=False)):
            return True
        if value:self.target_conditions(target).pop('ranger_protection', None)
        guardians = self._ranger_guardians(source, target, 'protection')
        if not guardians:return False
        guardian = guardians[0]
        guardian.reaction_ready = self.now()+rules.ROUND_SECONDS
        self.target_conditions(target)['ranger_protection'] = dict(owner=guardian.id,
            until=self.now()+rules.ROUND_SECONDS, turn=getattr(guardian, '_feat_turn_until', 0),
            spell_id='ranger_protection', concentration=False)
        self._ranger_support(guardian, target)
        with self.db:self.save_player(guardian)
        self.fighter_effect(guardian, target, 'protection')
        return True

    def ranger_tick_protection(self, target):
        """Leaving the ally ends the benefit, even if we later walk back."""
        value = self.target_conditions(target).get('ranger_protection', {})
        if not value:return
        owner = self.players.get(value.get('owner', ''))
        if (not owner or not owner.alive or not target.alive or value.get('until', 0) <= self.now()
                or value.get('turn') != getattr(owner, '_feat_turn_until', 0)
                or owner.floor != target.floor
                or math.hypot(owner.x-target.x, owner.y-target.y) > FIVE_FEET
                or not self.line_clear(owner, target)):
            self.target_conditions(target).pop('ranger_protection', None)

    def ranger_interception(self, source, target, result):
        """After a hitting attack roll, before resistance/temporary HP/damage."""
        rules, _, _, _, _ = _modules()
        if not result.get('hit') or result.get('check') != 'attack' or result.get('damage', 0) <= 0:return False
        guardians = self._ranger_guardians(source, target, 'interception')
        if not guardians:return False
        guardian = guardians[0]
        rolled = self.combat_rng.randint(1, 10)
        modifier = rules.proficiency(guardian)
        reduction = min(result['damage'], rolled+modifier)
        result['damage'] = max(0, result['damage']-reduction)
        left = reduction
        for part in result.get('damage_components', []):
            take = min(left, max(0, part.get('damage', 0)))
            part['damage'] = max(0, part.get('damage', 0)-take)
            left -= take
        result['intercepted'] = reduction
        result['interception_owner'] = guardian.id
        result['damage_reduction_rolls'] = [*result.get('damage_reduction_rolls', []),
            dict(name='Przechwycenie', sides=10, rolls=[rolled], modifier=modifier,
                 total=rolled+modifier, reduced=reduction)]
        guardian.reaction_ready = self.now()+rules.ROUND_SECONDS
        self._ranger_support(guardian, target)
        with self.db:self.save_player(guardian)
        self.fighter_effect(guardian, target, 'interception')
        return True
