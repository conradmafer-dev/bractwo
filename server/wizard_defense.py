"""Authoritative Abjuration and Illusion features, adapted to Bractwo combat.

Ward points and spent rest resources survive reconnects. Temporary illusions,
projected targets and ground shelters deliberately do not survive a logout.
"""
import math
from types import SimpleNamespace

try:
    from . import combat_rules as rules, dnd_content as dnd
    from .dnd_game import Companion
except ImportError:
    import combat_rules as rules, dnd_content as dnd
    from dnd_game import Companion


ABJURATION_SPELLS = frozenset(('shield', 'mage_armor', 'protection_from_evil',
    'protection_from_energy', 'dispel_magic', 'counterspell', 'stoneskin',
    'greater_restoration', 'lesser_restoration', 'freedom_of_movement',
    'remove_curse', 'globe_of_invulnerability', 'protection_from_evil_and_good',
    'mind_blank', 'resistance', 'barkskin'))


def _state(p):
    if not isinstance(getattr(p, 'wizard_school_state', None), dict):
        p.wizard_school_state = {}
    return p.wizard_school_state


def _runtime(p):
    if not isinstance(getattr(p, 'wizard_school_runtime', None), dict):
        p.wizard_school_runtime = {}
    return p.wizard_school_runtime


def _school(p, key, level=10):
    return (getattr(p, 'class_id', '') == 'mage' and getattr(p, 'promoted', False)
            and getattr(p, 'level', 0) >= level and getattr(p, 'wizard_school', '') == key)


def _count(data, key):
    try: return max(0, int(data.get(key, 0)))
    except (TypeError, ValueError, OverflowError): return 0


class WizardDefense:
    def wizard_ward_max(self, p):
        return max(1, 2*rules.effective_level(p)+rules.ability_modifier(p, 'intelligence')) if _school(p, 'abjuration') else 0

    def wizard_defense_migrate(self, p):
        data = _state(p)
        for key, maximum in (('decoy_spent', 2), ('phantasm_spent', 1), ('self_spent', 1), ('shelter_spent', 1)):
            data[key] = min(maximum, _count(data, key))
        data['ward_created'] = data.get('ward_created') is True
        data['ward_hp'] = min(self.wizard_ward_max(p), _count(data, 'ward_hp')) if data['ward_created'] else 0
        data['self_armed'] = data.get('self_armed') is True
        # Do not discard another school's migration/runtime data.
        for key in ('projected_ward_target', 'decoy_until', 'shelter'):
            _runtime(p).pop(key, None)

    def _wizard_defense_save(self, p):
        if hasattr(self, 'db') and hasattr(self, 'save_player'):
            with self.db: self.save_player(p)

    def _wizard_defense_available(self, p, action=True):
        p.current_wall_time = self.now()
        states = ('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending', 'polymorph')
        if action: states += ('stinking_poison',)
        return (p.alive and not p.disconnected and not p.form
                and not rules.gear.armor_penalty(p)
                and not any(rules.active_buff(p, key) for key in states))

    def _wizard_defense_effect(self, p, key, target=None, phase='cast', duration=.85, area=None):
        visuals = {'ward_recharge': 'shield', 'arcane_ward': 'shield',
                   'projected_ward': 'shield', 'decoy': 'mirror_image',
                   'phantasm': 'conjure_animals', 'illusory_self': 'mirror_image',
                   'self_restore': 'mirror_image', 'shelter': 'globe_of_invulnerability'}
        spec = dict(id='wizard_'+key, visual=visuals.get(key, 'shield'), circle=0, mana=0,
                    range=192, radius=96 if key == 'shelter' else 0)
        if area is not None: spec['area'] = True
        event = self.spell_effect(p, 'wizard_'+key, target or p, spec=spec,
                                 phase=phase, duration=duration, area=area)
        event.update(wizard_feature=key, ward_hp=_count(_state(p), 'ward_hp'),
                     ward_max=self.wizard_ward_max(p))
        return event

    def wizard_after_paid_spell(self, p, key, spec):
        """Call after a valid cast whose actual mana cost was positive."""
        if not _school(p, 'abjuration') or float(spec.get('mana', 0)) <= 0: return
        circle = int(spec.get('cast_circle', spec.get('circle', 0)))
        if circle <= 0 or not (key in ABJURATION_SPELLS or spec.get('school') == 'abjuration'): return
        data = _state(p); maximum = self.wizard_ward_max(p)
        if not data.get('ward_created'):
            data['ward_created'] = True; data['ward_hp'] = maximum
        else:
            data['ward_hp'] = min(maximum, _count(data, 'ward_hp')+2*circle)
        self._wizard_defense_effect(p, 'arcane_ward')
        self._wizard_defense_save(p)

    def wizard_spell_resistance(self, p):
        return _school(p, 'abjuration', 65)

    def wizard_spell_save_advantage(self, p):
        return _school(p, 'abjuration', 65)

    def wizard_absorb_damage(self, p, damage, source=None, **kwargs):
        """Reduce already resisted damage before concentration and temporary HP."""
        remaining = max(0, int(damage))
        if remaining <= 0: return remaining
        candidates = []
        if _school(p, 'abjuration'): candidates.append(p)
        # Stable order when several allies have armed protection. A second ward
        # is only spent if the previous ward did not absorb the complete hit.
        candidates.extend(q for q in sorted(self.players.values(), key=lambda q: q.id)
                          if q is not p and _school(q, 'abjuration', 25)
                          and _runtime(q).get('projected_ward_target') == p.id)
        for owner in candidates:
            data = _state(owner); available = _count(data, 'ward_hp')
            if not data.get('ward_created') or available <= 0: continue
            if owner is not p:
                if (not self._wizard_defense_available(owner, action=False)
                        or owner.reaction_ready > self.now() or rules.active_buff(owner, 'no_reactions')
                        or self.friendly_target_error(owner, p, 192)): continue
                self.join_pvp_support(owner, p)
                owner.reaction_ready = self.now()+rules.ROUND_SECONDS
            absorbed = min(remaining, available)
            data['ward_hp'] = available-absorbed; remaining -= absorbed
            event = self._wizard_defense_effect(owner, 'arcane_ward' if owner is p else 'projected_ward', p, phase='absorb')
            event['absorbed'] = absorbed
            self.report_roll(owner, p, dict(check='ward', hit=False, damage=0, absorbed=absorbed,
                             damage_dice='', ward_hp=data['ward_hp']), 'Magiczna osłona', owner)
            self.tag(owner, getattr(p, 'pvp_combat_until', 0) > self.now())
            self._wizard_defense_save(owner)
            if remaining <= 0: break
        return remaining

    def wizard_attack_disadvantage(self, target):
        if not _school(target, 'illusion') or _runtime(target).get('decoy_until', 0) <= self.now(): return False
        _runtime(target).pop('decoy_until', None)
        target.buffs.pop('wizard_decoy', None)
        self._wizard_defense_effect(target, 'decoy', phase='shatter')
        return True

    def wizard_attack_reaction(self, target, result):
        if not result.get('hit') or not _school(target, 'illusion', 45): return False
        data = _state(target)
        if (not data.get('self_armed') or _count(data, 'self_spent') >= 1
                or target.reaction_ready > self.now() or not self._wizard_defense_available(target, action=False)
                or rules.active_buff(target, 'no_reactions')): return False
        data['self_spent'] = 1
        target.reaction_ready = self.now()+rules.ROUND_SECONDS
        result.update(hit=False, damage=0, illusory_self=True, critical=False)
        result.pop('damage_components', None)
        self._wizard_defense_effect(target, 'illusory_self', phase='shatter')
        self._wizard_defense_save(target)
        return True

    def wizard_defense_rest(self, p, kind):
        data = _state(p)
        if kind in ('long', 'full'):
            for key in ('decoy_spent', 'phantasm_spent', 'self_spent', 'shelter_spent'): data[key] = 0
            data['ward_created'] = False; data['ward_hp'] = 0
            for key in ('decoy_until', 'shelter'): _runtime(p).pop(key, None)
            p.buffs.pop('wizard_decoy', None)
        else:
            data['self_spent'] = 0
            if _school(p, 'abjuration', 45) and data.get('ward_created'):
                data['ward_hp'] = self.wizard_ward_max(p)

    async def wizard_defense_command(self, p, action, data):
        if not isinstance(action, str) or action not in ('projected_ward', 'illusory_self'): return False
        if not isinstance(data, dict): return True
        return await self.wizard_defense_action(p, action, target_id=data.get('target_id', data.get('target')),
                                               value=data.get('value'))

    async def wizard_defense_action(self, p, key, enemy_id=None, target_id=None, **kwargs):
        if not isinstance(key, str): return False
        key = key.removeprefix('wizard_')
        features = {'ward_recharge': ('abjuration', 10, True), 'projected_ward': ('abjuration', 25, None),
                    'decoy': ('illusion', 10, True), 'phantasm': ('illusion', 25, False),
                    'illusory_self': ('illusion', 45, None), 'self_restore': ('illusion', 45, True),
                    'shelter': ('illusion', 65, False)}
        if key not in features: return False
        school, level, bonus = features[key]
        if not _school(p, school, level) or not self._wizard_defense_available(p): return True
        if (enemy_id is not None and not isinstance(enemy_id, str)
                or target_id is not None and not isinstance(target_id, str)
                or enemy_id): return True
        data = _state(p); rt = _runtime(p); now = self.now()
        if key == 'projected_ward':
            if not target_id or target_id == p.id:
                rt.pop('projected_ward_target', None)
                await self.notice(p, 'Przekazywanie osłony wyłączone.'); return True
            ally = self.players.get(target_id)
            reason = self.friendly_target_error(p, ally, 192)
            if reason: await self.notice(p, reason); return True
            rt['projected_ward_target'] = ally.id
            await self.notice(p, 'Przekazywana osłona: '+ally.name+'. Reakcja zostanie zużyta przy obrażeniach.')
            return True
        if key == 'illusory_self':
            value = kwargs.get('value')
            if value is not None and type(value) is not bool: return True
            data['self_armed'] = not data.get('self_armed', False) if value is None else value
            self._wizard_defense_save(p)
            await self.notice(p, 'Iluzoryczne ja: '+('reakcja włączona.' if data['self_armed'] else 'reakcja wyłączona.'))
            return True
        if target_id and target_id != p.id: return True
        if now < (p.bonus_cooldown_until if bonus else p.attack_cooldown_until): return True
        cost = 20 if key == 'ward_recharge' else 30 if key == 'self_restore' or key == 'phantasm' and _count(data, 'phantasm_spent') else 0
        if p.mana < cost: await self.notice(p, f'Potrzebujesz {cost} many.'); return True
        if key == 'ward_recharge' and (not data.get('ward_created') or _count(data, 'ward_hp') >= self.wizard_ward_max(p)):
            await self.notice(p, 'Najpierw utwórz osłonę płatnym czarem Odpychania. Odnowa wymaga brakujących punktów osłony.'); return True
        if key == 'decoy' and _count(data, 'decoy_spent') >= 2 or key == 'shelter' and _count(data, 'shelter_spent') >= 1:
            await self.notice(p, 'Brak użyć tej zdolności. Potrzebujesz długiego odpoczynku.'); return True
        if key == 'decoy' and rt.get('decoy_until', 0) > now:
            await self.notice(p, 'Twój sobowtór jest już aktywny.'); return True
        if key == 'self_restore' and _count(data, 'self_spent') == 0:
            await self.notice(p, 'Iluzoryczne ja jest już gotowe.'); return True
        if key == 'phantasm' and p.id in self.companions and self.companions[p.id].alive:
            await self.notice(p, 'Twój towarzysz jest już przy tobie.'); return True
        self.cancel_rest(p); self.cancel_channel(p, '')
        self.begin_action(p, bonus); self.spend_mana(p, cost)
        if key == 'ward_recharge': data['ward_hp'] = min(self.wizard_ward_max(p), _count(data, 'ward_hp')+2)
        elif key == 'decoy':
            data['decoy_spent'] = _count(data, 'decoy_spent')+1; rt['decoy_until'] = now+30
            p.buffs['wizard_decoy'] = dict(until=now+30, spell_id='wizard_decoy')
        elif key == 'self_restore': data['self_spent'] = 0
        elif key == 'phantasm':
            data['phantasm_spent'] = 1
            full_hp = 5+5*rules.effective_level(p)
            hp = max(1, full_hp//2) if cost == 0 else full_hp
            pet = Companion('pet_'+p.id, p.id, 'Widmowy wilk · '+p.name, p.x, p.y, p.floor, hp, hp,
                            rules.proficiency(p)+rules.ability_modifier(p, 'intelligence'),
                            13+rules.proficiency(p), (1, 8, rules.proficiency(p)))
            pet.current_wall_time = now; pet.wizard_phantasm = True
            self.companions[p.id] = pet
        elif key == 'shelter':
            data['shelter_spent'] = 1
            rt['shelter'] = dict(x=p.x, y=p.y, floor=p.floor, until=now+30)
        dnd.record_spell_use(p, 'wizard_'+key)
        area = dict(shape='circle', x=p.x, y=p.y, radius=96) if key == 'shelter' else None
        self._wizard_defense_effect(p, key, duration=30 if key in ('decoy', 'shelter') else .85, area=area)
        self.wizard_defense_tick()
        self._wizard_defense_save(p)
        return True

    def wizard_defense_tick(self):
        now = self.now()
        # Recompute owner contributions to remove protection immediately on
        # leaving the zone, teleporting, logout or a new PvP restriction.
        protected = {}
        for p in self.players.values():
            rt = _runtime(p)
            if not p.alive or p.disconnected:
                for key in ('decoy_until', 'shelter', 'projected_ward_target'): rt.pop(key, None)
                p.buffs.pop('wizard_decoy', None)
                continue
            if rt.get('decoy_until', 0) <= now: p.buffs.pop('wizard_decoy', None)
            shelter = rt.get('shelter')
            if not shelter: continue
            if not _school(p, 'illusion', 65) or shelter['until'] <= now or p.floor != shelter['floor']:
                rt.pop('shelter', None); continue
            center = SimpleNamespace(x=shelter['x'], y=shelter['y'], floor=shelter['floor'])
            for q in self.players.values():
                if (not q.alive or q.disconnected or q.floor != center.floor
                        or math.hypot(q.x-center.x, q.y-center.y) > 96
                        or not self.line_clear(center, q)
                        or self.friendly_target_error(p, q, 384)): continue
                self.join_pvp_support(p, q)
                protected[q.id] = dict(until=min(now+.2, shelter['until']), owner=p.id, spell_id='wizard_shelter')
        for p in self.players.values():
            if p.id in protected: p.buffs['wizard_shelter'] = protected[p.id]
            else: p.buffs.pop('wizard_shelter', None)
