"""Server-authoritative actions and hooks for the four PHB 2024 druid circles.

The mixin belongs before CasterGame. Existing spell execution calls the cost,
commit, healing and damage hooks so a failed cast never spends a free use.
"""
import math
from types import SimpleNamespace

try:
    from . import druid_circles as circles, combat_rules as rules, caster_rules as caster, dnd_content as dnd
    from . import world_content as content
    from .progression import same_floor
except ImportError:
    import druid_circles as circles, combat_rules as rules, caster_rules as caster, dnd_content as dnd
    import world_content as content
    from progression import same_floor


def distance(a, b): return math.hypot(a.x-b.x, a.y-b.y)


class DruidCircleGame:
    def migrate_druid_circle(self, p):
        if p.class_id != 'druid' or getattr(p, 'druid_circle', '') not in circles.CIRCLES:
            p.druid_circle = ''
        data = circles.state(p)
        for key in ('shape', 'guiding_bolt', 'omen', 'moonlight_step', 'natural_free', 'natural_recovery'):
            try: data[key + '_spent'] = max(0, min(100, int(data.get(key + '_spent', 0))))
            except (ValueError, TypeError): data[key + '_spent'] = 0
        data['land'] = circles.land(p)
        data['omen'] = data.get('omen') if data.get('omen') in ('weal', 'woe') else ('weal' if self.combat_rng.randint(1, 6) % 2 == 0 else 'woe')
        p.druid_circle_runtime = {}

    def _circle_save(self, p):
        with self.db: self.save_player(p)

    def _circle_available(self, p, actions=True, beast=False):
        states=('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending')
        if actions:states+=('stinking_poison',)
        if not beast:states+=('polymorph',)
        return p.alive and not p.disconnected and not any(rules.active_buff(p, key) for key in states)

    def _circle_visible(self, source, target):
        return getattr(self, 'environment_can_see', self.line_clear)(source, target)

    async def select_druid_circle(self, p, key, land='arid'):
        if not isinstance(key, str) or key not in circles.CIRCLES or p.class_id != 'druid' or p.level < 10:
            return await self.notice(p, 'Wybór kręgu druida jest dostępny od poziomu 10.')
        if getattr(p, 'druid_circle', ''):
            return await self.notice(p, 'Krąg druida został już wybrany.')
        if not self._circle_available(p) or p.form or p.combat_until > self.now():
            return await self.notice(p, 'Wybierz krąg poza walką i przemianą.')
        if key == 'land' and (not isinstance(land, str) or land not in circles.LANDS):
            return await self.notice(p, 'Wybierz środowisko kręgu Ziemi.')
        p.druid_circle = key
        data = circles.state(p)
        data.update(land=land if key == 'land' else 'arid', land_change_ready=False,
                    map_owned=True, map_equipped=True, lunar_radiant=True)
        data.setdefault('omen', 'weal' if self.combat_rng.randint(1, 6) % 2 == 0 else 'woe')
        self.clear_caster_caches(p)
        self._circle_save(p)
        await self.notice(p, 'Wybrano: ' + circles.CIRCLES[key]['name'] + '.')

    async def circle_command(self, p, action, value=None, **kwargs):
        if not isinstance(action, str) or not self._circle_available(p): return
        data = circles.state(p); circle = circles.circle(p)
        if action == 'land':
            if circle != 'land' or value not in circles.LANDS or not data.get('land_change_ready', True): return
            if p.form or p.combat_until > self.now(): return await self.notice(p, 'Zmień środowisko po odpoczynku, poza walką.')
            data['land'] = value; data['land_change_ready'] = False
        elif action == 'lunar_radiant':
            if circle != 'moon' or p.level < 25 or type(value) is not bool: return
            data['lunar_radiant'] = value
        elif action == 'omen_armed':
            if circle != 'stars' or p.level < 25 or type(value) is not bool: return
            data['omen_armed'] = value
        elif action == 'natural_free':
            if circle != 'land' or p.level < 25 or type(value) is not bool: return
            data['natural_free_armed'] = value and circles.spent(p, 'natural_free') == 0
        elif action == 'star_map':
            if circle != 'stars' or type(value) is not bool or not data.get('map_owned', True): return
            data['map_equipped'] = value
        elif action == 'restore_moonlight_step':
            if circle != 'moon' or p.level < 45 or circles.spent(p, 'moonlight_step') == 0: return
            cost = dnd.MANA_COSTS[2]
            if p.mana < cost: return await self.notice(p, f'Przywrócenie Księżycowego kroku wymaga {cost} many (II krąg).')
            self.spend_mana(p, cost); data['moonlight_step_spent'] = circles.spent(p, 'moonlight_step')-1
        elif action in ('chalice_target', 'shared_moonlight_target'):
            if not isinstance(value, str): return
            ally = self.players.get(value) if value else None
            if ally and self.friendly_target_error(p, ally, 192 if action == 'chalice_target' else 64): return
            if action == 'chalice_target' and circle != 'stars' or action == 'shared_moonlight_target' and (circle != 'moon' or p.level < 65): return
            circles.runtime(p)[action] = value
        elif action == 'dismiss_star_form':
            p.buffs.pop('starry_form', None); circles.runtime(p).pop('starry_form', None)
        elif action == 'dismiss_sea':
            p.buffs.pop('wrath_of_sea', None)
        elif action == 'release_grapples':
            for ref in circles.runtime(p).get('grapples', ()):
                target = self.resolve_target_ref(ref)
                if target is None: continue
                conditions = self.target_conditions(target)
                if conditions.get('grappled', {}).get('owner') == p.id:
                    conditions.pop('grappled', None)
                    if conditions.get('restrained', {}).get('spell_id') == 'beast_grapple': conditions.pop('restrained', None)
            circles.runtime(p)['grapples'] = []; circles.runtime(p)['grapple_slow'] = False
        else: return
        self.clear_caster_caches(p)
        self._circle_save(p)

    def on_circle_rest(self, p, kind):
        """Run once on successful completion, not on request/cancel/login."""
        if p.class_id != 'druid': return
        data = circles.state(p)
        if kind in ('long', 'full'):
            for key in ('shape', 'guiding_bolt', 'omen', 'moonlight_step', 'natural_free', 'natural_recovery'):
                data[key + '_spent'] = 0
            data['land_change_ready'] = True
            data['natural_free_armed'] = False
            if circles.circle(p) == 'stars':
                data['omen'] = 'weal' if self.combat_rng.randint(1, 6) % 2 == 0 else 'woe'
                data['map_owned'] = True  # The replacement ceremony is performed during the rest.
        elif kind == 'short':
            data['shape_spent'] = max(0, circles.spent(p, 'shape')-1)
            if circles.circle(p) == 'land' and p.level >= 25 and not circles.spent(p, 'natural_recovery') and p.mana < p.max_mana:
                restored = min(p.max_mana-p.mana, caster.recovery_amount(p))
                p.mana += restored; circles.spend(p, 'natural_recovery')
                self.caster_message(p, f'Naturalne odzyskanie: +{restored:g} many.')
        self.clear_caster_caches(p)

    def circle_spell_cost(self, p, spec, recast=False):
        if recast: return 0, ''
        key = spec['id']; circle = circles.circle(p)
        if circle == 'stars' and key == 'guiding_bolt' and circles.state(p).get('map_equipped', True) and circles.feature_remaining(p, 'guiding_bolt'):
            # Free casting grants the base spell, not a free higher-level slot.
            if spec.get('cast_circle', spec.get('circle', 1)) == 1: return 0, 'guiding_bolt'
        if circle == 'land' and p.level >= 25 and circles.state(p).get('natural_free_armed') and not circles.spent(p, 'natural_free') and key in circles.bonus_spells(p) and spec.get('circle', 0) > 0:
            if spec.get('cast_circle', spec['circle']) == spec['circle']: return 0, 'natural_free'
        return spec.get('mana', 0), ''

    def circle_commit_spell(self, p, spec, free_key):
        if free_key in ('guiding_bolt', 'natural_free'):
            circles.spend(p, free_key)
            if free_key == 'natural_free': circles.state(p)['natural_free_armed'] = False

    def circle_after_heal(self, p, spec, friends, mana_spent):
        if circles.starry_form(p) != 'chalice' or mana_spent <= 0 or spec.get('circle', 0) < 1: return
        selected = self.players.get(circles.runtime(p).get('chalice_target', ''))
        candidates = [selected] if selected else [p, *friends, *self.players.values()]
        valid = [q for q in candidates if q and q.hp < q.max_hp and not self.friendly_target_error(p, q, 192)]
        if not valid: return
        target = valid[0]
        result = rules.roll_damage(self.combat_rng, (2 if p.level >= 45 else 1, 8, circles.wisdom(p)))
        amount = min(target.max_hp-target.hp, result['damage'])
        target.hp += amount; self.join_pvp_support(p, target)
        self.report_roll(p, target, dict(result, check='healing', hit=True, healing=amount, damage=0), 'Gwiezdny Kielich', p)
        self._circle_save(target)

    def circle_roll_adjustment(self, actor, kind='attack', target=None, ability=None):
        """Call before the d20, so an omen cannot be chosen after the outcome."""
        if not getattr(actor, 'alive', False): return 0
        for owner in sorted(self.players.values(), key=lambda q: str(q.id)):
            if circles.circle(owner) != 'stars' or owner.level < 25 or not self._circle_available(owner, actions=False): continue
            data = circles.state(owner)
            if not data.get('omen_armed') or circles.feature_remaining(owner, 'omen') <= 0: continue
            if owner.reaction_ready > self.now() or rules.active_buff(owner, 'no_reactions') or not same_floor(owner, actor) or distance(owner, actor) > 192 or not self._circle_visible(owner, actor): continue
            friendly = actor is owner or getattr(actor, 'party_id', '') and actor.party_id == owner.party_id
            positive = data.get('omen', 'weal') == 'weal'
            if bool(friendly) != positive: continue
            if not positive and self.is_player_target(actor) and self.pvp_error(owner, actor): continue
            delta = self.combat_rng.randint(1, 6) * (1 if positive else -1)
            owner.reaction_ready = self.now()+rules.ROUND_SECONDS; circles.spend(owner, 'omen')
            if not positive:
                if self.is_player_target(actor): self.begin_pvp_hostility(owner, actor)
                else: self.remember_attacker(actor, owner)
            self._circle_save(owner)
            return delta
        return 0

    def circle_adjust_damage(self, p, target, result, weapon=True):
        """Augment one successful beast attack before resistance/HP/death handling."""
        if not weapon or not result.get('hit') or not p.form: return
        spec = caster.form_spec(p)
        rider = spec.get('extra_attacks', {}).get(getattr(p, 'form_attack_index', 0))
        if rider:
            extra = rules.roll_damage(self.combat_rng, tuple(rider['dice']), result.get('critical', False))
            components = result.setdefault('damage_components', [dict(type=result.get('damage_type', rules.damage_type(p)), damage=result['damage'])])
            components.append(dict(type=rider['damage_type'], damage=extra['damage']))
            result['damage'] += extra['damage']; result['damage_dice'] += ' + ' + rules.dice_text(rider['dice'])
            result['beast_extra_rolls'] = extra['damage_rolls']
        if circles.circle(p) != 'moon' or p.level < 65 or not circles.wild_shape_active(p): return
        rt = circles.runtime(p); now = self.now()
        rules.begin_feat_turn(p, now)
        if rt.get('lunar_damage_turn') == p._feat_turn_until: return
        rt['lunar_damage_turn'] = p._feat_turn_until
        extra = rules.roll_damage(self.combat_rng, (2, 10, 0), result.get('critical', False))
        components = result.setdefault('damage_components', [dict(type=result.get('damage_type', rules.damage_type(p)), damage=result['damage'])])
        components.append(dict(type='radiant', damage=extra['damage']))
        result['damage'] += extra['damage']; result['damage_dice'] += ' + 2k10 (Księżyc)'
        result['lunar_rolls'] = extra['damage_rolls']

    def _circle_target_size(self, target):
        if self.is_player_target(target):
            return {'tiny': 0, 'small': 1, 'medium': 2, 'large': 3, 'huge': 4, 'gargantuan': 5}.get(caster.form_spec(target).get('size', 'medium'), 2)
        spec = content.ENEMIES.get(target.kind, {})
        if isinstance(spec.get('size'), str): return {'tiny': 0, 'small': 1, 'medium': 2, 'large': 3, 'huge': 4, 'gargantuan': 5}.get(spec['size'], 2)
        scale = spec.get('size', 1)
        return 2 if scale <= 1.2 else 3 if scale <= 2 else 4 if scale <= 2.8 else 5

    def circle_note_movement(self, p, old_x, old_y):
        if not getattr(p, 'form', ''): return
        dx, dy = p.x-old_x, p.y-old_y; length = math.hypot(dx, dy)
        if length < .001: return
        rt = circles.runtime(p)
        for ref in tuple(rt.get('grapples', ())):
            target = self.resolve_target_ref(ref)
            if target is not None and self.target_conditions(target).get('grappled', {}).get('owner') == p.id:
                getattr(self, 'environment_forced_move', self.move)(target, dx, dy)
        if not caster.form_spec(p).get('charge_prone'): return
        trace = rt.get('charge_trace', {})
        straight = trace.get('until', 0) >= self.now() and dx/length*trace.get('dx', 0)+dy/length*trace.get('dy', 0) > .98
        rt['charge_trace'] = dict(dx=dx/length, dy=dy/length, distance=trace.get('distance', 0)+length if straight else length,
                                  until=self.now()+.4, start_x=trace.get('start_x', old_x) if straight else old_x, start_y=trace.get('start_y', old_y) if straight else old_y)

    def circle_beast_target(self, p, target, attack_index):
        """A crocodile's Tail cannot attack the creature held in its jaws."""
        if not caster.form_spec(p).get('tail_no_grapple') or attack_index != 1: return target
        grip = self.target_conditions(target).get('grappled', {})
        if grip.get('owner') != p.id or grip.get('until', 0) <= self.now(): return target
        others = self._circle_hostiles(p, p, 64)
        return next((q for q in sorted(others, key=lambda q: distance(p, q)) if q is not target), None)

    def beast_on_hit(self, p, target, result):
        super().beast_on_hit(p, target, result)
        if not p.form or not result or not result.get('hit') or target.hp <= 0: return
        spec = caster.form_spec(p); index = getattr(p, 'form_attack_index', 0); size = self._circle_target_size(target)
        conditions = self.target_conditions(target); rt = circles.runtime(p)
        if index in spec.get('grapple_attacks', ()) and size <= 3:
            grips = rt.setdefault('grapples', [])
            grips[:] = [ref for ref in grips if (q := self.resolve_target_ref(ref)) is not None and self.target_conditions(q).get('grappled', {}).get('owner') == p.id]
            ref = self.target_ref(target)
            if ref in grips or len(grips) < spec.get('grapple_slots', 1):
                if ref not in grips: grips.append(ref)
                rt['grapple_slow'] = size > self._circle_target_size(p)-2
                conditions['grappled'] = dict(until=p.form_until, owner=p.id, form=p.form, hostile=True, spell_id='beast_grapple', dc=spec['grapple_dc'], reach=64, concentration=False)
                if spec.get('grapple_restrains'): conditions['restrained'] = dict(conditions['grappled'], retry=float('inf'))
        trace = rt.get('charge_trace', {})
        length = distance(p, target)
        toward = length <= .001 or ((target.x-p.x)/length*trace.get('dx', 0)+(target.y-p.y)/length*trace.get('dy', 0)) > .9
        charged = spec.get('charge_prone') and size <= 4 and trace.get('until', 0) >= self.now() and trace.get('distance', 0) >= 128 and toward
        if charged or index in spec.get('prone_attacks', ()) and size <= 3:
            conditions['prone'] = dict(until=self.now()+1.5, owner=p.id, hostile=True, spell_id='beast_prone', concentration=False)
            self.fighter_effect(p, target, 'topple')
        if self.is_player_target(target): self.record_pvp_effect(p, target, target.last_pvp_unjust)

    async def _circle_beast_action(self, p, key, enemy_id=None, target_id=None):
        if not self._circle_available(p, beast=True): return
        now = self.now()
        if key == 'escape_grapple':
            grip = p.buffs.get('grappled', {})
            if grip.get('until', 0) <= now or p.attack_cooldown_until > now: return
            self.begin_action(p)
            ability = max(('strength', 'dexterity'), key=lambda a: rules.ability_modifier(p, a))
            if hasattr(self, 'environment_ability_check'):
                success = self.environment_ability_check(p, ability, grip['dc'], 'athletics' if ability == 'strength' else 'acrobatics')['saved']
            else:
                bonus = rules.ability_modifier(p, ability)+self.circle_roll_adjustment(p, 'ability', ability=ability)
                roll = self.combat_rng.randint(1, 20); success = roll+bonus >= grip['dc']
                self.report_roll(p, p, dict(check='ability', roll=roll, rolls=[roll], bonus=bonus, total=roll+bonus, defense=grip['dc'], saved=success, hit=False, damage=0, damage_dice=''), 'Wyrwanie z chwytu', p)
            if success:
                p.buffs.pop('grappled', None)
                if p.buffs.get('restrained', {}).get('spell_id') == 'beast_grapple': p.buffs.pop('restrained', None)
            return
        spec = caster.form_spec(p).get('trample')
        if not spec or p.bonus_cooldown_until > now: return
        target = self.enemies.get(enemy_id or p.auto_enemy_id) if not target_id else self.players.get(target_id)
        if not target or not target.alive or not same_floor(p, target) or distance(p, target) > 32 or not self.line_clear(p, target) or not self.target_condition(target, 'prone') or self.in_safe(p): return
        if self.is_player_target(target) and self.pvp_error(p, target): return
        self.begin_action(p, True)
        self._circle_damage(p, target, key, tuple(spec['dice']), 'bludgeoning', 'dexterity', True, dc=spec['save_dc'])
        self.tag(p); await self._circle_kills([target]); self._circle_save(p)

    def caster_attack_advantage(self, p, target):
        inherited = super().caster_attack_advantage(p, target)
        bonus = rules.active_buff(p, 'moonlight_advantage')
        if bonus: p.buffs.pop('moonlight_advantage', None)
        return inherited or bonus

    def concentration_damage(self, p, damage):
        if damage <= 0 or p.concentration_until <= self.now(): return
        dc = max(10, math.floor(damage/2))
        bonus = rules.save_bonus(p, 'constitution') + self.circle_roll_adjustment(p, 'concentration', ability='constitution')
        raw = self.combat_rng.randint(1, 20); roll = max(raw, circles.roll_floor(p, 'constitution', 'concentration'))
        result = dict(check='concentration', roll=roll, rolls=[raw], bonus=bonus, total=roll+bonus, defense=dc, saved=roll+bonus >= dc, hit=False, damage=0, damage_dice='')
        self.report_roll(p, p, result, 'Koncentracja', p)
        if not result['saved']: self.break_concentration(p)

    def apply_status(self, p, target, key, duration, spec, hostile=True):
        if key in ('poisoned', 'stinking_poison') and circles.poison_immune(target): return False
        return super().apply_status(p, target, key, duration, spec, hostile)

    def _circle_point(self, p, enemy_id=None, target_id=None, reach=384):
        target = self.enemies.get(enemy_id) if enemy_id else self.players.get(target_id) if target_id else p
        if target is None or not same_floor(p, target) or distance(p, target) > reach or not self._circle_visible(p, target): return None
        return SimpleNamespace(id=getattr(target, 'id', p.id), x=target.x, y=target.y, floor=p.floor)

    def _circle_hostiles(self, p, center, radius):
        candidates = list(self.nearby_enemies(center, radius))
        if not p.pvp_safety: candidates += list(self.players.values())
        return [q for q in candidates if q.alive and q.hp > 0 and same_floor(center, q) and distance(center, q) <= radius and self._circle_visible(center, q)
                and not (self.is_player_target(q) and self.pvp_error(p, q))]

    def _circle_damage(self, p, target, key, dice, kind, save=None, half=False, attack=False, dc=None):
        spec = dict(dnd.SPELLS[key], name=dnd.SPELLS[key]['name'], kind='attack' if attack else 'save', dice=list(dice), damage_type=kind,
                    save=save, save_half=half, resolved=True, range=768, targeting='hostile')
        if dc is None: return self.spell_damage(p, target, spec)
        # A transferred sea aura retains its creator's spell DC, even on a noncaster.
        roll = rules.roll_damage(self.combat_rng, dice)
        result = self.target_save(target, save, dc, roll, half)
        result['damage_type'] = kind
        if self.is_player_target(target):
            unjust = self.begin_pvp_hostility(p, target)
            self.resolve_player_hit(p, target, result, spec['name'], owner=p, unjust=unjust)
        else:
            if hasattr(self, 'environment_damage_enemy'): result['damage'] = self.environment_damage_enemy(target, result['damage'], p, kind)
            else: target.hp = max(0, target.hp-result['damage'])
            self.remember_attacker(target, p)
            self.report_roll(p, target, result, spec['name'], p)
        return result

    async def _circle_kills(self, targets):
        for target in targets:
            if target.hp <= 0 and not self.is_player_target(target): await self.defeat(target)

    async def _circle_land_aid(self, p, key, enemy_id, target_id):
        center = self._circle_point(p, enemy_id, target_id)
        if center is None: return await self.notice(p, 'Wybierz widoczny punkt w zasięgu 60 stóp.')
        foes = [] if self.in_safe(p) else self._circle_hostiles(p, center, 64)
        friends = [q for q in self.players.values() if q.alive and same_floor(center, q) and distance(center, q) <= 64 and self.line_clear(center, q) and not self.friendly_target_error(p, q, 448)]
        friends.sort(key=lambda q: (q.id != target_id, q is not p, q.hp/max(1, q.max_hp)))
        if not foes and not any(q.hp < q.max_hp for q in friends): return await self.notice(p, 'Brak celu pomocy ziemi w tym miejscu.')
        if not circles.spend_shape(p): return await self.notice(p, 'Brak użyć Dzikiego kształtu.')
        self.begin_action(p); dice = 2+(p.level >= 45)+(p.level >= 65)
        for foe in foes: self._circle_damage(p, foe, key, (dice, 6, 0), 'necrotic', 'constitution', True)
        if friends:
            ally = next((q for q in friends if q.hp < q.max_hp), friends[0]); roll = rules.roll_damage(self.combat_rng, (dice, 6, 0))
            restored = min(ally.max_hp-ally.hp, roll['damage']); ally.hp += restored; self.join_pvp_support(p, ally)
            self.report_roll(p, ally, dict(roll, check='healing', hit=True, healing=restored, damage=0), 'Pomoc ziemi', p)
        self.spell_effect(p, key, center, foes, spec=dict(dnd.SPELLS[key], radius=64, area=True, shape='circle'))
        if foes: self.tag(p)
        await self._circle_kills(foes)

    async def _circle_sanctuary(self, p, key, enemy_id, target_id):
        center = self._circle_point(p, enemy_id, target_id, 768)
        if center is None or self.blocked(center.x, center.y, radius=2, floor=p.floor): return await self.notice(p, 'Sanktuarium wymaga widocznego gruntu w zasięgu 120 stóp.')
        rt = circles.runtime(p); old = rt.get('sanctuary')
        if key == 'circle_move_sanctuary':
            if not old or old['until'] <= self.now() or math.hypot(center.x-old['x'], center.y-old['y']) > 384: return
            old.update(x=center.x, y=center.y); self.begin_action(p, True)
        else:
            if not circles.spend_shape(p): return await self.notice(p, 'Brak użyć Dzikiego kształtu.')
            self.begin_action(p)
            rt['sanctuary'] = dict(x=center.x, y=center.y, floor=p.floor, until=self.now()+30)
        self.spell_effect(p, key, center, spec=dict(dnd.SPELLS[key], area=True, shape='square', width=96, radius=68), duration=1)

    async def _circle_moonlight(self, p, key):
        if circles.feature_remaining(p, 'moonlight_step') <= 0: return await self.notice(p, 'Brak użyć Księżycowego kroku. Możesz przywrócić użycie za 30 many.')
        dx, dy = p.facing; length = math.hypot(dx, dy) or 1; destination = None
        for step in range(192, 7, -8):
            point = SimpleNamespace(id=p.id, x=p.x+dx/length*step, y=p.y+dy/length*step, floor=p.floor)
            if not self.blocked(point.x, point.y, floor=p.floor) and self._circle_visible(p, point) and not (p.pvp_combat_until > self.now() and self.in_safe(point)):
                destination = point; break
        if destination is None: return await self.notice(p, 'Nie ma widocznego wolnego miejsca na teleport.')
        companion = self.players.get(circles.runtime(p).get('shared_moonlight_target', '')) if p.level >= 65 else None
        ally_dest = None
        if companion and not self.friendly_target_error(p, companion, 64):
            for ox, oy in ((32, 0), (-32, 0), (0, 32), (0, -32), (32, 32), (-32, -32)):
                point = SimpleNamespace(x=destination.x+ox, y=destination.y+oy, floor=p.floor)
                if not self.blocked(point.x, point.y, floor=p.floor) and self._circle_visible(p, point) and not (companion.pvp_combat_until > self.now() and self.in_safe(point)):
                    ally_dest = point; break
        self.begin_action(p, True); circles.spend(p, 'moonlight_step')
        self.spell_effect(p, key, destination)
        p.x, p.y = destination.x, destination.y
        p.buffs['moonlight_advantage'] = dict(until=p._feat_turn_until, spell_id=key)
        if ally_dest:
            companion.x, companion.y = ally_dest.x, ally_dest.y; self.join_pvp_support(p, companion); self._circle_save(companion)

    async def _circle_sea(self, p, key, enemy_id, target_id, initial=False):
        now = self.now()
        if key in ('circle_oceanic_gift', 'circle_oceanic_gift_shared'):
            target = self.players.get(target_id) if target_id else None
            if target is None or target is p or self.friendly_target_error(p, target, 384): return await self.notice(p, 'Wskaż sojusznika w zasięgu 60 stóp.')
            holders = [target, p] if key.endswith('_shared') else [target]
            if not circles.spend_shape(p, len(holders)): return await self.notice(p, 'Brak wymaganych użyć Dzikiego kształtu.')
            for q in self.players.values():
                if q.buffs.get('wrath_of_sea', {}).get('owner') == p.id: q.buffs.pop('wrath_of_sea', None)
            self.begin_action(p, True)
            for holder in holders:
                holder.buffs['wrath_of_sea'] = dict(until=now+300, owner=p.id, level=p.level, wisdom=max(1, circles.wisdom(p)), dc=rules.spell_dc(p), spell_id=key)
                self.join_pvp_support(p, holder); self.spell_effect(p, key, holder)
                await self._circle_sea(holder, 'circle_wrath_strike', None, None, initial=True)
            return
        activating = key == 'circle_wrath_of_sea' and not circles.active(p, 'wrath_of_sea')
        if activating:
            if not circles.spend_shape(p): return await self.notice(p, 'Brak użyć Dzikiego kształtu.')
            p.buffs['wrath_of_sea'] = dict(until=now+300, owner=p.id, level=p.level, wisdom=max(1, circles.wisdom(p)), dc=rules.spell_dc(p), spell_id=key)
        aura = p.buffs.get('wrath_of_sea', {})
        if aura.get('until', 0) <= now: return
        radius = 64 if aura.get('level', 0) >= 25 else 32
        foes = [] if self.in_safe(p) else self._circle_hostiles(p, p, radius)
        selected = enemy_id or target_id or p.auto_enemy_id or p.auto_target_id
        foes.sort(key=lambda q: (q.id != selected, distance(p, q)))
        if not foes and not activating and not initial: return await self.notice(p, 'Brak przeciwnika w aurze Gniewu morza.')
        if not initial: self.begin_action(p, True)
        self.spell_effect(p, key, p, foes[:1])
        if foes:
            target = foes[0]; result = self._circle_damage(p, target, key, (aura['wisdom'], 6, 0), 'cold', 'constitution', False, dc=aura['dc'])
            if result and not result.get('saved') and target.alive:
                if self._circle_target_size(target) <= 3:
                    length = distance(p, target)
                    dx, dy = ((target.x-p.x)/length, (target.y-p.y)/length) if length else tuple(p.facing)
                    mover = getattr(self, 'environment_forced_move', self.move)
                    mover(target, dx*96, dy*96)
            self.tag(p); await self._circle_kills(foes[:1])

    async def _circle_star(self, p, key, enemy_id, target_id):
        rt = circles.runtime(p); now = self.now(); current = circles.starry_form(p)
        if key != 'circle_star_arrow':
            form = key.rsplit('_', 1)[-1]
            if form not in ('archer', 'chalice', 'dragon'): return
            if form == current: return
            switching = bool(current and p.level >= 45)
            if switching:
                if rt.get('star_switch_ready', 0) > now: return
                rt['star_switch_ready'] = now+rules.ROUND_SECONDS
                rt['starry_form'] = form
                self.spell_effect(p, key, p)
                return  # Switching at turn start uses neither a bonus action nor a Wild Shape.
            if not circles.spend_shape(p): return await self.notice(p, 'Brak użyć Dzikiego kształtu.')
            p.form = ''; p.form_until = 0
            p.buffs['starry_form'] = dict(until=now+300, spell_id=key)
            rt.update(starry_form=form, star_switch_ready=now+rules.ROUND_SECONDS)
            self.begin_action(p, True); self.spell_effect(p, key, p)
            if form != 'archer': return
        elif current != 'archer': return
        else: self.begin_action(p, True)
        spec = dict(dnd.SPELLS[key], range=384, area=False)
        targets = [] if self.in_safe(p) else self.spell_targets(p, spec, enemy_id or p.auto_enemy_id or None, target_id or p.auto_target_id or None)
        if not targets: return
        target = targets[0]
        self._circle_damage(p, target, key, (2 if p.level >= 45 else 1, 8, circles.wisdom(p)), 'radiant', attack=True)
        self.tag(p); await self._circle_kills([target])

    async def cast_circle_feature(self, p, key, enemy_id=None, target_id=None):
        p.current_wall_time = self.now()
        if not circles.feature_allowed(p, key) or not self._circle_available(p): return
        if enemy_id is not None and not isinstance(enemy_id, str) or target_id is not None and not isinstance(target_id, str) or enemy_id and target_id: return
        spec = dnd.SPELLS[key]
        switching = key.startswith('circle_star_') and key != 'circle_star_arrow' and circles.starry_form(p) and p.level >= 45
        ready = p.bonus_cooldown_until if spec['action'] == 'bonus' else p.attack_cooldown_until
        if self.now() < ready and not switching: return
        self.cancel_rest(p); self.cancel_channel(p, '')
        if key == 'circle_lands_aid': await self._circle_land_aid(p, key, enemy_id, target_id)
        elif key in ('circle_natures_sanctuary', 'circle_move_sanctuary'): await self._circle_sanctuary(p, key, enemy_id, target_id)
        elif key == 'circle_moonlight_step': await self._circle_moonlight(p, key)
        elif key in ('circle_wrath_of_sea', 'circle_wrath_strike', 'circle_oceanic_gift', 'circle_oceanic_gift_shared'): await self._circle_sea(p, key, enemy_id, target_id)
        elif key.startswith('circle_star_'): await self._circle_star(p, key, enemy_id, target_id)
        self.clear_caster_caches(p)
        self._circle_save(p)

    async def cast_spell(self, p, key, enemy_id=None, target_id=None, queue=True):
        if key in ('beast_trample', 'escape_grapple'):
            return await self._circle_beast_action(p, key, enemy_id, target_id)
        if isinstance(key, str) and key in circles.SPELL_FEATURES:
            return await self.cast_circle_feature(p, key, enemy_id, target_id)
        return await super().cast_spell(p, key, enemy_id, target_id, queue)

    def tick_dnd(self, dt):
        super().tick_dnd(dt)
        now = self.now()
        for owner in self.players.values():
            rt = circles.runtime(owner); kept = []
            for ref in rt.get('grapples', ()):
                q = self.resolve_target_ref(ref)
                if q is None: continue
                conditions = self.target_conditions(q); grip = conditions.get('grappled', {})
                valid = (grip.get('owner') == owner.id and grip.get('until', 0) > now and owner.form == grip.get('form')
                         and self._circle_available(owner, actions=False, beast=True) and q.alive and same_floor(owner, q) and distance(owner, q) <= grip.get('reach', 64))
                if valid:
                    kept.append(ref)
                    if not self.is_player_target(q) and now >= grip.get('escape_ready', 0):
                        grip['escape_ready'] = now+rules.ROUND_SECONDS
                        # A held monster spends its next action trying to escape.
                        bonus = content.ENEMIES[q.kind].get('save_bonus', 0)
                        if self.combat_rng.randint(1, 20)+bonus >= grip['dc']: valid = False
                        q.ready = max(getattr(q, 'ready', 0), self.time+rules.ROUND_SECONDS)
                        q.ranged_ready = max(getattr(q, 'ranged_ready', 0), self.time+rules.ROUND_SECONDS)
                if not valid and grip.get('owner') == owner.id:
                    conditions.pop('grappled', None)
                    if conditions.get('restrained', {}).get('spell_id') == 'beast_grapple': conditions.pop('restrained', None)
            rt['grapples'] = kept
            rt['grapple_slow'] = any(self._circle_target_size(self.resolve_target_ref(ref)) > self._circle_target_size(owner)-2 for ref in kept if self.resolve_target_ref(ref))
        for p in self.players.values():
            rt = circles.runtime(p)
            if not p.alive or p.disconnected or any(rules.active_buff(p, key) for key in ('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending')):
                p.buffs.pop('starry_form', None); p.buffs.pop('wrath_of_sea', None); rt.pop('sanctuary', None)
            if not circles.active(p, 'starry_form'): rt.pop('starry_form', None)
            if circles.poison_immune(p): p.buffs.pop('poisoned', None); p.buffs.pop('stinking_poison', None)
            aura = p.buffs.get('wrath_of_sea', {})
            if aura and (aura.get('until', 0) <= now or aura.get('owner') not in self.players): p.buffs.pop('wrath_of_sea', None)
            sanctuary = rt.get('sanctuary')
            if not sanctuary: continue
            if sanctuary['until'] <= now:
                rt.pop('sanctuary', None); continue
            for q in self.players.values():
                if not q.alive or q.floor != sanctuary['floor'] or abs(q.x-sanctuary['x']) > 48 or abs(q.y-sanctuary['y']) > 48: continue
                if q is not p and (not p.party_id or p.party_id != q.party_id): continue
                q.buffs['nature_sanctuary'] = dict(until=min(now+.15, sanctuary['until']), owner=p.id, resistance=circles.LANDS[circles.land(p)]['resistance'], spell_id='circle_natures_sanctuary')
