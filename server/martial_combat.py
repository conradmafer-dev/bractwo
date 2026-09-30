"""Weapon-only 2014 martial archetypes on Bractwo's three-second turn clock.

Extra attacks resolve synchronously through the ordinary combat pipeline. They
never spend a main action or generate another Horde Breaker attack. Defensive
reactions can respond to an extra attack; each spends its actor's shared reaction.
"""
import math

try:
    from . import combat_rules as rules, martial_rules as martial, environment_rules as environment, dnd_content as dnd
    from .progression import same_floor
except ImportError:
    import combat_rules as rules, martial_rules as martial, environment_rules as environment, dnd_content as dnd
    from progression import same_floor

FIVE_FEET = 32  # The published world scale: 6.4 units per foot.
NAMES = {'precision':'Precyzyjny atak', 'riposte':'Riposta', 'parry':'Parowanie',
         'trip':'Atak powalający', 'menacing':'Atak zastraszający',
         'colossus_slayer':'Pogromca kolosów', 'horde_breaker':'Rozbijacz hord',
         'giant_killer':'Zabójca olbrzymów'}


class MartialCombat:
    def martial_weapon_source(self, p, spell=False):
        return bool(not spell and self.is_player_target(p) and p.alive and p.hp > 0
                    and not p.form and not environment.polymorph(p)
                    and rules.gear.weapon(p) and not rules.gear.is_focus(rules.gear.weapon(p)))

    def martial_critical_threshold(self, p, spell=False):
        return martial.critical_threshold(p) if self.martial_weapon_source(p, spell) else 20

    def _martial_save(self, p):
        with self.db: self.save_player(p)

    def _martial_ready(self, p, reaction=False):
        return (self.is_player_target(p) and p.alive and p.hp > 0 and not p.disconnected
                and not p.form and not environment.polymorph(p) and not environment.incapacitated(p, self.now())
                and (not reaction or p.reaction_ready <= self.now()
                     and not environment.active(p, 'no_reactions', self.now())))

    def _martial_spend(self, p, key, reaction=False):
        if not self._martial_ready(p, reaction) or not martial.knows(p, key) or not martial.spend(p): return False
        if reaction: p.reaction_ready = self.now() + rules.ROUND_SECONDS
        else: martial.state(p)['offense'] = ''
        dnd.record_spell_use(p, 'martial_'+key)
        self._martial_save(p)
        return True

    def martial_precision(self, p, target, result, dice, spell=False, after_shield=False):
        """Precision may rescue a miss before damage, including Shield's new AC.

        Natural ones and attacks redirected to an illusion cannot be rescued.
        The same superiority die cannot be spent twice on a Shielded attack.
        """
        if (not self.martial_weapon_source(p, spell) or result.get('hit')
                or result.get('roll') in (1, 20) or result.get('martial_maneuver')
                or result.get('illusory_self') or getattr(p, '_martial_extra', '') == 'riposte'
                or martial.state(p).get('offense') != 'precision'
                or after_shield and not result.get('shielded')): return False
        if not self._martial_spend(p, 'precision'): return False
        value = self.combat_rng.randint(1, martial.die_sides(p))
        result.update(martial_maneuver='precision', superiority_rolls=[value])
        result['total'] += value; result['bonus'] += value
        result['hit'] = result['total'] >= result['defense']
        if result['hit']:
            if after_shield and result.get('damage_rolls'):
                result['damage'] = max(0, sum(result['damage_rolls'])+result.get('damage_modifier', dice[2]))
            else:
                result.update(rules.roll_damage(self.combat_rng, dice, result.get('critical', False)))
            # Retain the Shield spell itself: only its attempt to stop this hit failed.
            result['shield_overcome'] = bool(result.get('shielded'))
        self.fighter_effect(p, target, 'precision')
        return result['hit']

    def _martial_add_die(self, p, result, label, sides, metadata):
        extra = rules.roll_damage(self.combat_rng, (1, sides, 0), result.get('critical', False))
        components = result.setdefault('damage_components', [dict(type=result['damage_type'], damage=result['damage'])])
        component = next((part for part in components if part['type'] == result['damage_type']), None)
        if component is None: components.append(dict(type=result['damage_type'], damage=extra['damage']))
        else: component['damage'] += extra['damage']
        result['damage'] += extra['damage']; result['damage_dice'] += f' + 1k{sides} ({NAMES[label]})'
        result[metadata] = extra['damage_rolls']

    def martial_damage_riders(self, p, target, result, spell=False):
        if not self.martial_weapon_source(p, spell) or not result.get('hit'): return
        extra = getattr(p, '_martial_extra', '')
        state = martial.state(p)
        if extra == 'riposte':
            result['martial_maneuver'] = 'riposte'
            self._martial_add_die(p, result, 'riposte', martial.die_sides(p), 'superiority_rolls')
        elif not result.get('martial_maneuver'):
            key = state.get('offense', '')
            if key in ('trip', 'menacing') and self._martial_spend(p, key):
                result['martial_maneuver'] = key
                self._martial_add_die(p, result, key, martial.die_sides(p), 'superiority_rolls')
        # Once on each compressed turn, and the target must already be wounded.
        if (martial.hunter_choice(p) == 'colossus_slayer' and target.hp < target.max_hp
                and state.get('colossus_until', 0) <= self.now()):
            state['colossus_until'] = self.now() + rules.ROUND_SECONDS
            self._martial_add_die(p, result, 'colossus_slayer', 8, 'colossus_rolls')
            self.fighter_effect(p, target, 'colossus_slayer'); self._martial_save(p)

    def _martial_target_size(self, target):
        if environment.polymorph(target):
            size = environment.physical_form(target).get('size', 'medium')
            return {'tiny':0,'small':1,'medium':2,'large':3,'huge':4,'gargantuan':5}.get(size,2)
        return self._circle_target_size(target)

    def martial_after_weapon_hit(self, p, target, result, spell=False):
        if not self.martial_weapon_source(p, spell) or not result or not result.get('hit') or target.hp <= 0: return
        key = result.get('martial_maneuver')
        if key not in ('trip', 'menacing') or key == 'trip' and self._martial_target_size(target) > 3: return
        ability = 'strength' if key == 'trip' else 'wisdom'
        dc = 8 + rules.proficiency(p) + max(rules.ability_modifier(p, 'strength'), rules.ability_modifier(p, 'dexterity'))
        save = self.target_save(target, ability, dc, dict(damage=0, damage_dice='', damage_rolls=[]))
        save.update(save_ability=ability, martial_maneuver=key)
        self.report_roll(p, target, save, NAMES[key]+' · obrona', p)
        if save['saved']: return
        status = 'prone' if key == 'trip' else 'frightened'
        duration = 1.5 if key == 'trip' else rules.ROUND_SECONDS
        # Existing standing-up action is 1.5 s; fear ends at the END of the next turn.
        if key == 'menacing':
            duration = max(self.now()+rules.ROUND_SECONDS, getattr(p, '_feat_turn_until', 0))+rules.ROUND_SECONDS-self.now()
        if self.apply_status(p, target, status, duration, dict(id='martial_'+key, save=ability)):
            self.target_conditions(target)[status]['dc'] = dc
            if self.is_player_target(target):
                unjust = target.last_pvp_unjust if target.last_pvp_attacker == p.id else False
                self.record_pvp_effect(p, target, unjust)
            self.fighter_effect(p, target, key)

    def martial_parry(self, source, target, result):
        """Reduce a damaging melee attack before resistances; saves never qualify."""
        if (not self.is_player_target(target) or not result.get('hit') or result.get('check') != 'attack' or not result.get('is_melee')
                or result.get('damage', 0) <= 0 or source is target
                or martial.state(target).get('reaction') != 'parry'
                or not self._martial_spend(target, 'parry', reaction=True)): return
        die = self.combat_rng.randint(1, martial.die_sides(target))
        reduction = max(0, die + rules.ability_modifier(target, 'dexterity'))
        reduction = min(reduction, result['damage'])
        result.update(parry_reduction=reduction, parry_roll=die)
        result['damage'] -= reduction
        remaining = reduction
        for component in result.get('damage_components', []):
            amount = min(remaining, component['damage']); component['damage'] -= amount; remaining -= amount
        self.fighter_effect(target, source, 'parry')

    def _martial_target_legal(self, p, target, melee=False):
        if (not self._martial_ready(p) or not self.martial_weapon_source(p) or target is None
                or target is p or not target.alive or target.hp <= 0 or not same_floor(p, target)
                or self.in_safe(p) or self.in_safe(target) or not self.line_clear(p, target)
                or math.hypot(p.x-target.x, p.y-target.y) > rules.attack_range(p)
                or melee and not rules.gear.melee(p)): return False
        if self.is_player_target(target): return not target.disconnected and not self.pvp_error(p, target)
        return self.enemies.get(target.id) is target

    def _martial_extra_attack(self, p, target, key):
        """No main action; legal defensive reactions consume their own shared slot."""
        if not self._martial_target_legal(p, target, melee=key == 'riposte'): return None
        old = getattr(p, '_martial_extra', '')
        depth = getattr(self, '_martial_extra_depth', 0)
        p._martial_extra = key; self._martial_extra_depth = depth+1
        try:
            self.basic_effect(p, target); self.fighter_effect(p, target, key)
            self.tag(p, self.is_player_target(target))
            if self.is_player_target(target):
                result = self.hit_player(p, target, pvp=True, action=NAMES[key])
            else:
                result = self.hit_enemy(p, target, action=NAMES[key], melee=rules.gear.melee(p))
            self.trigger_ensnaring_strike(p, target, result)
            self.fighter_on_weapon_hit(p, target, result)
            return result
        finally:
            p._martial_extra = old; self._martial_extra_depth = depth

    def martial_after_incoming_attack(self, source, target, result):
        if (not result or result.get('check') != 'attack' or getattr(self, '_martial_extra_depth', 0) >= 32
                or not self._martial_ready(target, reaction=True)): return
        key = ''
        if (martial.state(target).get('reaction') == 'riposte' and result.get('is_melee')
                and not result.get('hit') and self.environment_can_see(target, source) and self._martial_target_legal(target, source, melee=True)
                and self._martial_spend(target, 'riposte', reaction=True)):
            key = 'riposte'
        elif (martial.hunter_choice(target) == 'giant_killer'
                and self._martial_target_legal(target, source) and self._martial_target_size(source) >= 3
                and math.hypot(target.x-source.x, target.y-source.y) <= FIVE_FEET
                and self.environment_can_see(target, source)):
            target.reaction_ready = self.now()+rules.ROUND_SECONDS; self._martial_save(target)
            key = 'giant_killer'
        if key: self._martial_extra_attack(target, source, key)

    def martial_horde_breaker(self, p, primary):
        if (martial.hunter_choice(p) != 'horde_breaker' or getattr(self, '_martial_extra_depth', 0)
                or not self.martial_weapon_source(p) or martial.state(p).get('horde_until', 0) > self.now()): return None
        now = self.now()
        candidates = [e for e in self.nearby_enemies(primary, FIVE_FEET+1)]
        # An automatic extra shot never starts a new fight with an uninvolved player.
        candidates += [q for q in self.players.values() if q is not p and
                       (p.aggressors.get(q.id, 0) > now or q.aggressors.get(p.id, 0) > now)]
        candidates = [q for q in candidates if q is not primary
                      and math.hypot(q.x-primary.x, q.y-primary.y) <= FIVE_FEET
                      and self._martial_target_legal(p, q)]
        if not candidates: return None
        target = min(candidates, key=lambda q: (math.hypot(q.x-primary.x, q.y-primary.y), str(q.id)))
        martial.state(p)['horde_until'] = now+rules.ROUND_SECONDS; self._martial_save(p)
        self._martial_extra_attack(p, target, 'horde_breaker')
        return target

    def _martial_fear_source(self, actor):
        fear = environment.conditions(actor).get('frightened', {})
        if fear.get('until', 0) <= self.now(): return None
        source = self.players.get(fear.get('owner'))
        if source is None or not source.alive or source.disconnected or not same_floor(source, actor): return None
        if self.is_player_target(actor) and self.pvp_error(source, actor): return None
        return source

    def martial_frightened(self, actor):
        source = self._martial_fear_source(actor)
        return source is not None and self.environment_can_see(actor, source)

    def environment_attack_flags(self, source, target):
        dis, adv = super().environment_attack_flags(source, target)
        return dis or self.martial_frightened(source), adv

    def blocked_for(self, actor, x, y, radius=18):
        source = self._martial_fear_source(actor)
        if (source is not None and not getattr(actor, '_environment_forced', False)
                and math.hypot(x-source.x, y-source.y) < math.hypot(actor.x-source.x, actor.y-source.y)-.001): return True
        return super().blocked_for(actor, x, y, radius)
