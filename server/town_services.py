"""Explicit city binding and protected piers for Bractwo Krain (UI25)."""
import math


def configure(content, npcs):
    content.BINDING_STONES = []
    for city in content.CITIES:
        stone = dict(id='binding_stone_'+city['id'], name='Kamień przypisania · '+city['name'],
                     role='Miejsce odrodzenia', service='binding_stone', city_id=city['id'],
                     x=city['x'], y=city['y']+100, floor=city.get('floor', 0), radius=95)
        npcs.append(stone)
        content.BINDING_STONES.append(stone)
        city.update(binding_stone_id=stone['id'], respawn_x=stone['x'], respawn_y=stone['y']+42)

    content.PORT_SAFE_ZONES = []
    for port in content.PORTS:
        # Cover the captain, arrival and the entire visible pier, including
        # long piers. The existing circular safety rules also block pursuers.
        sx, sy = port.get('shore_x', port['x']), port.get('shore_y', port['y'])
        steps = max(1, math.ceil(math.hypot(sx-port['x'], sy-port['y'])/140))
        for i in range(steps+1):
            content.PORT_SAFE_ZONES.append(dict(id=f"safe_{port['id']}_{i}", port_id=port['id'],
                name='Bezpieczna przystań · '+port['name'], kind='harbour', floor=port.get('floor', 0),
                x=port['x']+(sx-port['x'])*i/steps, y=port['y']+(sy-port['y'])*i/steps,
                radius=220 if i==0 else 115))
    content.SAFE_ZONES = [*content.CITIES, *content.PORT_SAFE_ZONES]


def respawn_position(content, city_id):
    city = next((c for c in content.CITIES if c['id']==city_id), content.CITIES[0])
    return city.get('respawn_x', city['x']), city.get('respawn_y', city['y']), city.get('floor', 0)
