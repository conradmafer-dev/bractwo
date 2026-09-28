"""One persistent discovery catalogue for named world sites and entrances."""
import math
from itertools import chain


def discovery_xp(biome_level, enemy_level, city_distance, previous_xp=0):
    """Fixed world difficulty, independent of the visitor's level or live enemies."""
    base = 10 + 2 * max(1, biome_level) + 3 * max(0, enemy_level)
    travel = 1 + .3 * math.log1p(max(0, city_distance) / 1600)
    return max(int(previous_xp), round(base * travel))


def configure(content, landmarks, zones, enemies):
    # Preserve old IDs: saved discoveries and quest objectives refer to them.
    by_id = {point['id']: point for point in landmarks}
    if len(by_id) != len(landmarks):
        raise ValueError('Duplicate discovery ID in world content')
    regions = content.REGIONS
    grounds = {g['id']: g for g in content.HUNTING_GROUNDS if g.get('name')}
    for ident, ground in grounds.items():
        if ident not in by_id:
            point = dict(id=ident, name=ground['name'], x=ground['x'], y=ground['y'],
                         floor=ground.get('floor', 0), radius=115,
                         biome='wilderness', decoration=ground.get('decoration'),
                         description='Charakterystyczne łowisko. ' + ', '.join(
                             enemies[k]['name'] for k in ground.get('members', []) if k in enemies) + '.',
                         reward={'xp': 0, 'gold': 0})
            landmarks.append(point)
            by_id[ident] = point
        ground['discovery_id'] = ident
        # The drawn habitat and its discovery share their final relocated position.
        by_id[ident].update(x=ground['x'], y=ground['y'], floor=ground.get('floor', 0))

    for stair in content.STAIRS:
        nearby = [point for point in landmarks
                  if point.get('floor', 0) == stair.get('floor', 0)
                  and math.hypot(point['x'] - stair['x'], point['y'] - stair['y']) <= min(120, point.get('radius', 125))]
        point = min(nearby, key=lambda p: math.hypot(p['x'] - stair['x'], p['y'] - stair['y']), default=None)
        if point is None:
            ident = 'discovery_' + stair['id']
            point = dict(id=ident, name=stair['name'], x=stair['x'], y=stair['y'],
                         floor=stair.get('floor', 0), radius=100, source_kind='stair',
                         biome='dungeon' if stair.get('floor', 0) < 0 else 'mountain',
                         recommended_level=stair.get('min_level', 1),
                         description='Przejście na piętro ' + str(stair['to_floor']) + '. Użyj E przy schodach.',
                         reward={'xp': 0, 'gold': 0})
            landmarks.append(point)
            by_id[ident] = point
        stair['discovery_id'] = point['id']
    for city in content.CITIES:
        city['discovery_id'] = 'city_' + city['id']

    # Build once during content loading; no global spawn scans on movement ticks.
    spawn_cells = {}
    starter_spawns = ((kind, x, y, 0) for kind, x, y in getattr(content, 'STARTER_SPAWNS', ()))
    for kind, x, y, floor in chain(content.SPAWNS, starter_spawns):
        spawn_cells.setdefault((floor, int(x // 700), int(y // 700)), []).append((kind, x, y))
    for point in landmarks:
        x, y, floor = point['x'], point['y'], point.get('floor', 0)
        region = next((r for r in regions if r['x'] <= x < r['x'] + r['w']
                       and r['y'] <= y < r['y'] + r['h']), {})
        local_zones = [z for z in zones if z.get('floor', 0) == floor
                       and z['x'] <= x < z['x'] + z.get('w', 0)
                       and z['y'] <= y < z['y'] + z.get('h', 0)]
        site_level = point.get('discovery_difficulty', {}).get('site_level',
                     max(point.get('recommended_level', 1), point.get('min_level', 1)))
        biome_level = max([1, region.get('min_level', 1), site_level]
                          + [z.get('min_level', 1) for z in local_zones])
        cx, cy = int(x // 700), int(y // 700)
        kinds = {kind for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 for kind, sx, sy in spawn_cells.get((floor, cx + dx, cy + dy), ())
                 if math.hypot(sx - x, sy - y) <= 700}
        kinds.update(grounds.get(point['id'], {}).get('members', []))
        # Legacy starter creatures have no level: use their authoritative HP tier.
        enemy_level = max((enemies[k].get('level', max(1, math.ceil(enemies[k].get('hp', 10) / 10)))
                           * (1.25 if enemies[k].get('boss') else 1)
                           for k in kinds if k in enemies), default=0)
        city_distance = min((math.hypot(x - c['x'], y - c['y']) for c in content.CITIES), default=0)
        reward = point.setdefault('reward', {})
        reward['xp'] = discovery_xp(biome_level, enemy_level, city_distance, reward.get('xp', 0))
        reward.setdefault('gold', 0)
        point['recommended_level'] = max(biome_level, math.ceil(enemy_level))
        point['discovery_difficulty'] = dict(site_level=site_level, biome_level=biome_level, enemy_level=enemy_level,
                                             city_distance=round(city_distance))

    for quest in content.QUESTS_REF:
        for objective in quest['objectives']:
            if objective['type'] == 'discover' and objective['target'] in by_id:
                point = by_id[objective['target']]
                objective.update(x=point['x'], y=point['y'], floor=point.get('floor', 0))
