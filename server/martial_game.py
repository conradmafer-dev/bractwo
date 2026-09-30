"""Validated promotion choices, commands and persistent martial resources."""
import math
try:
    from . import martial_rules as martial, combat_rules as rules
except ImportError:
    import martial_rules as martial, combat_rules as rules


class MartialGame:
    async def cast_spell(self, p, key, enemy_id=None, target_id=None, queue=True):
        if isinstance(key, str) and key.startswith('martial_'):
            maneuver = key[len('martial_'):]
            if not martial.knows(p, maneuver): return await self.notice(p, 'Ten manewr nie jest dostępny.')
            field = martial.MANEUVERS[maneuver]['kind']
            value = '' if martial.state(p).get(field) == maneuver else maneuver
            return await self.martial_command(p, dict(action='maneuver' if field == 'offense' else 'reaction', maneuver=value))
        return await super().cast_spell(p, key, enemy_id, target_id, queue)

    def migrate_martial(self, p):
        key = getattr(p, 'martial_archetype', '')
        if not isinstance(key, str) or key not in martial.ARCHETYPES or martial.ARCHETYPES[key]['class_id'] != p.class_id:
            p.martial_archetype = ''; p.martial_state = {}; return
        data = martial.state(p)
        learned = data.get('maneuvers', [])
        data['maneuvers'] = list(dict.fromkeys(k for k in learned if isinstance(k, str) and k in martial.MANEUVERS))[:3] if isinstance(learned, list) else []
        prey = data.get('hunter_choice', '')
        data['hunter_choice'] = prey if isinstance(prey, str) and prey in martial.PREY else ''
        value = data.get('superiority_spent', 0)
        # Malformed resources never grant a free refill. Legacy unchosen heroes
        # receive their initial pool only when selecting a valid archetype.
        data['superiority_spent'] = min(1000000, max(0, value)) if type(value) is int else 6
        for name in ('colossus_until', 'horde_until'):
            value = data.get(name, 0)
            data[name] = min(self.now()+rules.ROUND_SECONDS, max(0, value)) if type(value) in (int, float) and math.isfinite(value) else self.now()+rules.ROUND_SECONDS
        self.clear_martial_preparation(p)

    def clear_martial_preparation(self, p):
        data = martial.state(p)
        data['offense'] = ''; data['reaction'] = ''

    async def select_martial(self, p, data):
        p.current_wall_time = self.now()
        key = data.get('archetype')
        if not isinstance(key, str) or key not in martial.ARCHETYPES or martial.ARCHETYPES[key]['class_id'] != p.class_id:
            return await self.notice(p, 'Wybierz specjalizację swojej profesji.')
        reason = martial.selection_reason(p, self.now())
        if reason: return await self.notice(p, reason)
        choices = data.get('maneuvers', [])
        prey = data.get('prey', '')
        if key == 'battle_master':
            if (not isinstance(choices, list) or len(choices) != 3
                    or not all(isinstance(k, str) and k in martial.MANEUVERS for k in choices)
                    or len(set(choices)) != 3):
                return await self.notice(p, 'Wybierz dokładnie trzy różne manewry.')
        if key == 'hunter' and (not isinstance(prey, str) or prey not in martial.PREY):
            return await self.notice(p, 'Wybierz jedną technikę polowania.')
        p.martial_archetype = key
        p.martial_state = dict(maneuvers=list(choices) if key == 'battle_master' else [],
            hunter_choice=prey if key == 'hunter' else '', superiority_spent=0,
            offense='', reaction='', colossus_until=0, horde_until=0)
        self.clear_caster_caches(p); p._level_up_cache = None
        with self.db: self.save_player(p)
        await self.notice(p, 'Wybrano specjalizację: '+martial.ARCHETYPES[key]['name']+'.')

    async def martial_command(self, p, data):
        p.current_wall_time = self.now()
        if martial.path(p) != 'battle_master' or not martial.actions_available(p, self.now()): return
        action = data.get('action'); key = data.get('maneuver')
        if not isinstance(action, str) or action not in ('maneuver', 'reaction') or not isinstance(key, str): return
        expected = 'offense' if action == 'maneuver' else 'reaction'
        if key and (not martial.knows(p, key) or martial.MANEUVERS[key]['kind'] != expected):
            return await self.notice(p, 'Ten manewr nie należy do twoich wybranych zdolności.')
        if key and martial.remaining(p) <= 0:
            return await self.notice(p, 'Brak kości przewagi. Odnów je krótkim lub długim odpoczynkiem.')
        martial.state(p)[expected] = key
        # Arming is only a preference; dice and reaction are paid at execution.
        with self.db: self.save_player(p)

    def martial_rest(self, p, kind):
        if kind not in ('short', 'long'): return
        if martial.path(p) == 'battle_master': martial.state(p)['superiority_spent'] = 0
        self.clear_martial_preparation(p)
