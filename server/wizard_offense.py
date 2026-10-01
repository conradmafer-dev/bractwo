"""Server-authoritative Evocation and Divination school combat features."""
try:
    from . import combat_rules as rules, wizard_schools as schools, environment_rules
except ImportError:
    import combat_rules as rules, wizard_schools as schools, environment_rules

# Explicit spell schools; dealing elemental damage alone does not imply Evocation.
EVOCATION_IDS = frozenset(('fire_bolt', 'ray_of_frost', 'shocking_grasp', 'acid_splash', 'magic_missile',
    'burning_hands', 'scorching_ray', 'fireball', 'lightning_bolt', 'ice_storm',
    'cone_of_cold', 'chain_lightning', 'sunbeam', 'sunburst', 'meteor_swarm',
    'moonbeam', 'fire_storm', 'guiding_bolt', 'wall_of_fire', 'flame_strike', 'shatter', 'thunderwave'))


class WizardOffense:
    def _wizard_offense_save(self, p):
        with self.db: self.save_player(p)

    def wizard_offense_rest(self, p, kind):
        state = schools.state(p)
        if kind in ('short', 'long'): state['third_eye_used'] = 0
        if kind == 'long':
            state['overchannel_used'] = 0
            state['overchannel_armed'] = False
            state['portent_armed'] = {}
            if schools.school(p) == 'divination':
                state['portents'] = [self.combat_rng.randint(1, 20) for _ in range(3 if p.level >= 65 else 2)]
        schools.runtime(p).pop('third_eye_until', None)
        getattr(p, 'buffs', {}).pop('wizard_third_eye', None)

    async def wizard_offense_command(self, p, action, data):
        school = schools.school(p)
        if action == 'overchannel':
            if school != 'evocation' or p.level < 65:
                await self.notice(p, 'Przeciążenie wymaga szkoły Ewokacji i poziomu 65.'); return True
            state = schools.state(p)
            if 'value' in data and type(data['value']) is not bool: return True
            state['overchannel_armed'] = data.get('value', not state.get('overchannel_armed', False))
            self._wizard_offense_save(p)
            await self.notice(p, 'Przeciążenie: następny płatny czar kręgu I–V zada maksymalne obrażenia w turze rzucenia.' if state['overchannel_armed'] else 'Przeciążenie wyłączone.')
            return True
        if action in ('portent', 'arm_portent', 'clear_portent'):
            if school != 'divination':
                await self.notice(p, 'Przepowiednia wymaga szkoły Wróżbiarstwa.'); return True
            state = schools.state(p)
            if action == 'clear_portent' or data.get('mode') == 'cancel':
                state['portent_armed'] = {}; self._wizard_offense_save(p); return True
            index = data.get('index'); mode = data.get('mode')
            values = state.get('portents', [])
            if (type(index) is not int or not 0 <= index < len(values) or type(values[index]) is not int
                    or mode not in ('attack', 'enemy_save', 'self_save')):
                await self.notice(p, 'Wybierz niewykorzystaną przepowiednię i rodzaj rzutu.'); return True
            state['portent_armed'] = dict(index=index, mode=mode)
            self._wizard_offense_save(p)
            await self.notice(p, f'Przygotowano przepowiednię {values[index]}. Zastąpi następny pasujący rzut k20.')
            return True
        if action == 'third_eye':
            if school != 'divination' or p.level < 45:
                await self.notice(p, 'Trzecie oko wymaga szkoły Wróżbiarstwa i poziomu 45.'); return True
            state = schools.state(p)
            if state.get('third_eye_used', 0):
                await self.notice(p, 'Trzecie oko odnawia krótki odpoczynek.'); return True
            if (not p.alive or p.form or environment_rules.actions_blocked(p, self.now())
                    or rules.gear.armor_penalty(p) or p.bonus_cooldown_until > self.now()): return True
            self.begin_action(p, True)
            state['third_eye_used'] = 1; schools.runtime(p)['third_eye_until'] = self.now() + 30
            p.buffs['wizard_third_eye'] = dict(until=self.now()+30, spell_id='wizard_third_eye')
            self.combat_effect(p, 'spell', p, duration=.8).update(spell_id='wizard_third_eye', visual='foresight')
            self._wizard_offense_save(p)
            await self.notice(p, 'Trzecie oko: przez 30 s widzisz przez magiczną mgłę i Rozmycie.')
            return True
        return False

    def wizard_take_portent(self, p, mode):
        if schools.school(p) != 'divination': return None
        state = schools.state(p)
        armed = state.get('portent_armed', {})
        if not isinstance(armed, dict) or armed.get('mode') != mode or state.get('portent_turn_until', 0) > self.now(): return None
        values = state.get('portents', []); index = armed.get('index')
        if type(index) is not int or not 0 <= index < len(values) or type(values[index]) is not int or not 1 <= values[index] <= 20:
            state['portent_armed'] = {}; return None
        result = values[index]; values[index] = None; state['portent_armed'] = {}
        state['portent_turn_until'] = self.now() + rules.ROUND_SECONDS
        if p.level >= 25: p.mana = min(p.max_mana, p.mana + 20)
        self._wizard_offense_save(p)
        return result

    def wizard_save_portent(self, target):
        source = getattr(self, '_wizard_spell_source', None)
        result = self.wizard_take_portent(source, 'enemy_save') if source is not None and source is not target else None
        if result is None: result = self.wizard_take_portent(target, 'self_save')
        return result

    def wizard_third_eye(self, p):
        return schools.school(p) == 'divination' and p.level >= 45 and schools.runtime(p).get('third_eye_until', 0) > self.now()

    def wizard_prepare_spell(self, p, s, targets, target_id=None, mana=0):
        """Called after validation, before the committed cast: failures spend nothing."""
        if schools.school(p) != 'evocation': return
        s['_wizard_cast'] = dict(started=self.now(), empowered_used=False)
        state = schools.state(p)
        if (p.level >= 65 and state.get('overchannel_armed') and mana > 0
                and 1 <= s.get('cast_circle', s.get('circle', 0)) <= 5
                and s.get('kind') in ('attack', 'save', 'missiles', 'field', 'circle_field') and s.get('dice', [0])[0]):
            state['overchannel_armed'] = False
            used = max(0, int(state.get('overchannel_used', 0)))
            state['overchannel_used'] = used + 1
            s['_wizard_cast'].update(overchannel=True, backlash_dice=(used+1)*s.get('cast_circle', s.get('circle', 0)) if used else 0)
        if p.level >= 25 and s.get('id') in EVOCATION_IDS and s.get('area') and s.get('save'):
            protect = [t.id for t in targets if self.is_player_target(t) and t.id != target_id][:1+s.get('cast_circle', s.get('circle', 0))]
            s['_wizard_protected'] = protect
            # Preserve the original area anchor even if every creature is protected.
            # Damage resolution skips these IDs before aggression or saving throws.

    def wizard_finish_spell(self, p, s):
        count = s.get('_wizard_cast', {}).pop('backlash_dice', 0)
        if count:
            rolled = rules.roll_damage(self.combat_rng, (count, 12, 0))
            self.damage_player(p, rolled['damage'], rolled=True, damage_type='necrotic', source=p, unavoidable=True)
            self.report_roll(p, p, dict(rolled, check='automatic', hit=True, overchannel_backlash=True), 'Przeciążenie · odrzut', p)

    def wizard_maximize_spell(self, p, s):
        s = s or {}
        context = s.get('_wizard_cast', {})
        return bool(schools.school(p) == 'evocation' and p.level >= 65 and context.get('overchannel')
                    and self.now() < context.get('started', 0)+rules.ROUND_SECONDS)

    def wizard_potent_cantrip(self, p, s):
        return schools.school(p) == 'evocation' and s.get('circle') == 0 and not s.get('feature')

    def wizard_empower_roll(self, p, s, result):
        context = s.get('_wizard_cast', {})
        if (schools.school(p) != 'evocation' or p.level < 45 or s.get('id') not in EVOCATION_IDS
                or context.get('empowered_used') or not result.get('damage_rolls')): return
        # A field retains this same cast context, so later ticks cannot reapply INT.
        if not context: return
        context['empowered_used'] = True
        bonus = max(0, rules.ability_modifier(p, 'intelligence'))
        result['damage'] += bonus; result['damage_modifier'] = result.get('damage_modifier', 0)+bonus
        result['damage_dice'] += f' + {bonus} (Ewokacja)'; result['empowered_evocation'] = bonus

    def wizard_spell_roll_damage(self, p, s, dice, critical=False, empower=True):
        result = rules.roll_damage(self.combat_rng, dice, critical, maximize=self.wizard_maximize_spell(p, s))
        if empower: self.wizard_empower_roll(p, s, result)
        return result

    def wizard_adjust_spell_attack(self, p, target, result, dice):
        s = getattr(p, '_wizard_damage_spec', None)
        if not s: return
        if not result.get('hit'):
            if schools.school(p) != 'evocation' or s.get('circle') != 0 or s.get('feature'): return
            damage = self.wizard_spell_roll_damage(p, s, dice)
            result.update(damage); result['damage'] //= 2; result['potent_cantrip'] = True
        else: self.wizard_empower_roll(p, s, result)

    def concentration_damage(self, p, damage):
        # This precedes DruidCircleGame in the MRO and leaves other classes intact.
        if schools.school(p) != 'divination': return super().concentration_damage(p, damage)
        if damage <= 0 or p.concentration_until <= self.now(): return
        fixed = self.wizard_take_portent(p, 'self_save')
        if fixed is None: return super().concentration_damage(p, damage)
        check_draws=[]
        bonus = rules.save_bonus(p, 'constitution') + self.circle_roll_adjustment(p, 'concentration', ability='constitution', receipt=check_draws)
        dc = max(10, int(damage//2)); saved = fixed+bonus >= dc
        self.report_roll(p, p, dict(check='concentration', roll=fixed, rolls=[fixed], bonus=bonus, total=fixed+bonus,
            defense=dc, saved=saved, hit=False, damage=0, damage_dice='', portent=True,check_extra_rolls=check_draws), 'Koncentracja', p)
        if not saved: self.break_concentration(p)
