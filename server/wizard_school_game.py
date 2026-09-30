"""Selection, lifecycle and validated dispatch for all four wizard schools."""
import math
try:
    from . import wizard_schools as schools
    from .wizard_offense import WizardOffense
    from .wizard_defense import WizardDefense
except ImportError:
    import wizard_schools as schools
    from wizard_offense import WizardOffense
    from wizard_defense import WizardDefense


class WizardSchoolGame(WizardOffense, WizardDefense):
    def migrate_wizard_school(self, p):
        key = getattr(p, 'wizard_school', '')
        if p.class_id != 'mage' or not isinstance(key, str) or key not in schools.SCHOOLS:
            p.wizard_school = ''; p.wizard_school_state = {}
        data = schools.state(p)
        p.wizard_school_runtime = {}
        for key in ('overchannel_used', 'third_eye_used'):
            value = data.get(key, 0)
            data[key] = min(1000000, max(0, value)) if type(value) is int else 0
        data['overchannel_armed'] = bool(data.get('overchannel_armed', False))
        deadline=data.get('portent_turn_until',0)
        data['portent_turn_until']=min(self.now()+3,max(0,deadline)) if type(deadline) in (int,float) and math.isfinite(deadline) else 0
        values = data.get('portents', [])
        data['portents'] = [v if type(v) is int and 1 <= v <= 20 else None for v in values[:3]] if isinstance(values, list) else []
        # Armed choices and live fields end on disconnect; spent uses and dice never refresh.
        data.pop('portent_armed', None)
        self.wizard_defense_migrate(p)

    async def select_wizard_school(self, p, key):
        if p.class_id != 'mage' or not isinstance(key, str) or key not in schools.SCHOOLS:
            return await self.notice(p, 'Wybierz jedną ze szkół czarodzieja.')
        if p.wizard_school:
            return await self.notice(p, 'Szkoła czarodzieja została już wybrana.')
        if p.level < schools.PROMOTION_LEVEL:
            return await self.notice(p, f'Wybór szkoły wymaga poziomu {schools.PROMOTION_LEVEL}.')
        if not p.promoted:
            return await self.notice(p, 'Najpierw kup promocję u mistrza profesji w mieście.')
        if not self._circle_available(p) or p.form or p.combat_until > self.now() or p.rest_state or p.casting_channel:
            return await self.notice(p, 'Wybierz szkołę poza walką, odpoczynkiem i rzucaniem czarów.')
        p.wizard_school = key; p.wizard_school_state = {}; p.wizard_school_runtime = {}
        self.wizard_offense_rest(p, 'long')
        self.wizard_defense_rest(p, 'long')
        self.clear_caster_caches(p); p._level_up_cache = None
        with self.db: self.save_player(p)
        await self.notice(p, 'Wybrano szkołę: ' + schools.SCHOOLS[key]['name'] + '.')

    def wizard_school_rest(self, p, kind):
        if not schools.school(p): return
        self.wizard_offense_rest(p, kind)
        self.wizard_defense_rest(p, kind)
        self.clear_caster_caches(p)

    async def wizard_school_command(self, p, data):
        action = data.get('action')
        if not isinstance(action, str) or not schools.school(p) or not self._circle_available(p) or p.form:
            return
        if await self.wizard_offense_command(p, action, data): return
        if await self.wizard_defense_command(p, action, data): return
        await self.notice(p, 'Ta zdolność nie jest dostępna dla wybranej szkoły.')

    async def cast_spell(self, p, key, enemy_id=None, target_id=None, queue=True):
        if isinstance(key, str) and key in schools.SPELL_FEATURES:
            if not schools.feature_allowed(p, key):
                return await self.notice(p, 'Ta zdolność wymaga odpowiedniej szkoły i poziomu.')
            if not self._circle_available(p) or p.form: return
            if key == 'wizard_third_eye':
                return await self.wizard_offense_command(p, 'third_eye', {})
            return await self.wizard_defense_action(p, key, enemy_id, target_id)
        return await super().cast_spell(p, key, enemy_id, target_id, queue)
