"""Ranger weapon-triggered magic and action-cost escapes.

The one-shot arm is an input convenience, not a spell cast. Resources, the bonus
turn and concentration are committed only AFTER a legal, nonlethal weapon hit.
Ordinary spells, pet attacks and misses cannot trigger it. No client roll is used.
"""
try:
    from . import combat_rules as rules, dnd_content as dnd, spell_scaling
    from .progression import same_floor, train
except ImportError:
    import combat_rules as rules, dnd_content as dnd, spell_scaling
    from progression import same_floor, train

ENSNARING = 'ensnaring_strike'


class RangerMagic:
    async def toggle_ensnaring_strike(self, p, spec):
        if p.ensnaring_armed:
            p.ensnaring_armed = False
            return await self.notice(p, 'Uderzenie oplątujące: przygotowanie wyłączone.')
        if p.mana < spec['mana']:
            return await self.notice(p, f'Potrzebujesz {spec["mana"]} many na oplątanie po trafieniu.')
        p.ensnaring_armed = True
        replaces = ' Po trafieniu zastąpi '+dnd.SPELLS[p.concentration]['name']+'.' if p.concentration in dnd.SPELLS else ''
        return await self.notice(p, 'Uderzenie oplątujące: gotowe na następne trafienie bronią.'+replaces)

    def trigger_ensnaring_strike(self, p, target, hit):
        now = self.now()
        if (not p.ensnaring_armed or not dnd.spell_allowed(p, ENSNARING) or not p.alive or p.form
                or not hit or not hit.get('hit') or not target.alive or target.hp <= 0
                or not same_floor(p, target) or self.in_safe(p) or self.in_safe(target)
                or now < p.bonus_cooldown_until):
            return False
        player_target = self.is_player_target(target)
        if player_target and self.pvp_error(p, target):return False
        spec = spell_scaling.resolve(p, ENSNARING)
        if p.mana < spec['mana']:return False
        self.begin_action(p, bonus=True)
        self.spend_mana(p, spec['mana'])
        p.ensnaring_armed = False
        dnd.record_spell_use(p, ENSNARING)
        train(p, 'magic', max(1, spec['mana']))
        self.break_concentration(p)
        p.concentration = ENSNARING
        p.concentration_until = now + spec['duration']
        p.concentration_profile = {**spec, 'target_ref':self.target_ref(target)}
        # Use the world's explicit size rather than boss status. Bear is also
        # Large even though its existing visual size is only 1.4.
        creature = {} if player_target else dnd_enemy_spec(target)
        large = (getattr(target, 'form', '') == 'bear' if player_target else
                 creature.get('size', 1) >= 1.5 or target.kind == 'bear')
        result = rules.roll_save(self.combat_rng, self.target_save_bonus(target, 'strength'),
            rules.spell_dc(p), dict(damage=0, damage_dice='', damage_rolls=[]),
            advantage=large or player_target and self.target_condition(target, 'foresight'))
        result['save_ability'] = 'strength'
        unjust = self.begin_pvp_hostility(p, target) if player_target else False
        if not player_target:self.remember_attacker(target, p)
        applied = False
        if not result['saved']:
            applied = self.apply_status(p, target, 'restrained', spec['duration'], spec)
            if applied:
                value = self.target_conditions(target)['restrained']
                value.update(profile=spec, next_damage=now+rules.ROUND_SECONDS,
                             retry=float('inf'), escape_action=True)
                if player_target:self.record_pvp_effect(p, target, unjust)
        self.report_roll(p, target, result, spec['name'], p)
        self.spell_effect(p, ENSNARING, target, spec=spec)
        if not applied:self.break_concentration(p)
        return True

    def end_ensnaring_strike(self, target, key, value, owner):
        conditions = self.target_conditions(target)
        if conditions.get(key) is value:conditions.pop(key, None)
        if (owner and owner.concentration == ENSNARING
                and owner.concentration_profile.get('target_ref') == self.target_ref(target)):
            self.break_concentration(owner)

    def tick_ensnaring_strike(self, target, key, value, owner):
        now = self.now()
        player_target = self.is_player_target(target)
        valid = (owner is not None and owner.alive and owner.concentration == ENSNARING
                 and same_floor(owner, target) and target.alive and target.hp > 0
                 and not self.in_safe(owner) and not self.in_safe(target))
        if player_target:
            valid = valid and not self.pvp_error(owner, target) and not self.target_condition(target, 'freedom')
        if not valid:
            self.end_ensnaring_strike(target, key, value, owner)
            return
        until = value['until']
        due = value.get('next_damage', now + rules.ROUND_SECONDS)
        # Include the tenth turn at the effect's final boundary. Never replay a
        # backlog of ticks after a paused/disconnected simulation.
        if now + 1e-6 >= due and due <= until + 1e-6 and now < until + rules.ROUND_SECONDS:
            value['next_damage'] = now + rules.ROUND_SECONDS
            paid = value['profile']
            periodic = {**paid, 'kind':'periodic', 'save':None}
            impacts=[]
            self._record_field_damage(owner,target,periodic,impacts)
            self._field_tick_effect(owner,dict(x=target.x,y=target.y,floor=target.floor,
                effect_id='condition:'+owner.id+':'+self.target_ref(target)+':'+ENSNARING),periodic,impacts)
            if target.hp <= 0 or not target.alive:
                self.end_ensnaring_strike(target, key, value, owner)
                return
            if not player_target and self.time >= max(target.ready, target.cast_until):
                # Monster chooses an escape instead of its attack this turn.
                self.try_restraint_escape(target, target, value, owner)
        if now >= until:
            self.end_ensnaring_strike(target, key, value, owner)

    def try_restraint_escape(self, actor, target, value, owner):
        player_actor = self.is_player_target(actor)
        if player_actor:
            if self.now() < actor.attack_cooldown_until:return False
            self.begin_action(actor)
            # No Athletics proficiencies have been assigned in Bractwo yet:
            # this is an untrained Strength (Athletics) check, not a saving throw.
            bonus = rules.ability_modifier(actor, 'strength')
        else:
            actor.ready = max(actor.ready, self.time + rules.ROUND_SECONDS)
            actor.ranged_ready = max(actor.ranged_ready, self.time + rules.ROUND_SECONDS)
            actor.aoe_ready = max(actor.aoe_ready, self.time + rules.ROUND_SECONDS)
            bonus = dnd_enemy_spec(actor).get('athletics_bonus', self.target_save_bonus(actor, 'strength'))
        advantage = self.target_condition(actor, 'foresight')
        rolls = [self.combat_rng.randint(1,20) for _ in range(2 if advantage else 1)]
        roll = max(rolls)
        result = dict(check='escape', roll=roll, rolls=rolls, bonus=bonus,
                      total=roll+bonus, defense=value['dc'], saved=roll+bonus>=value['dc'],
                      hit=False, damage=0, damage_dice='', advantage=advantage)
        self.report_roll(actor, target, result, 'Wyrwanie z pnączy', actor if player_actor else owner)
        if result['saved']:
            self.end_ensnaring_strike(target, 'restrained', value, owner)
        return True

    async def escape_restraint(self, p, target_id=None):
        if not p.alive:return
        if target_id is not None and not isinstance(target_id, str):return
        target = self.players.get(target_id) if target_id else p
        reason = self.friendly_target_error(p, target, 80)
        if reason:return await self.notice(p, reason)
        value = target.buffs.get('restrained', {})
        if value.get('spell_id') != ENSNARING or value.get('until', 0) <= self.now():
            return await self.notice(p, 'Brak pnączy, z których możesz się uwolnić.')
        if self.now() < p.attack_cooldown_until:
            return await self.notice(p, 'Poczekaj na następną akcję, aby się wyrwać.')
        self.join_pvp_support(p, target)
        self.try_restraint_escape(p, target, value, self.players.get(value.get('owner')))
        with self.db:
            self.save_player(p)
            if target is not p:self.save_player(target)


def dnd_enemy_spec(target):
    # Late lookup: content is configured by the server during initialisation.
    try:
        from . import world_content as content
    except ImportError:
        import world_content as content
    return content.ENEMIES[target.kind]
