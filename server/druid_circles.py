"""PHB 2024 druid circles; distance and clock units retain Bractwo conventions.

Source tables: https://roll20.net/compendium/dnd5e/Subclasses:Circle%20of%20the%20Land?expansion=32231
The Moon, Sea and Stars entries use the same licensed PHB 2024 compendium.
Persistent expenditures live in druid_circle_state; active effects never survive login.
"""
from math import floor
try:
    from .profession_rules import PROMOTION_LEVEL
except ImportError:
    from profession_rules import PROMOTION_LEVEL

GATE = {3: 3, 5: 5, 6: 6, 7: 7, 9: 9, 10: 10, 14: 14}
CIRCLES = {
    'land': dict(name='Krąg Ziemi', description='Czary wybranego środowiska, pomoc ziemi i ochrona natury.'),
    'moon': dict(name='Krąg Księżyca', description='Silniejsze dzikie kształty i księżycowa magia w przemianie.'),
    'sea': dict(name='Krąg Morza', description='Aura fal, odpychanie, pływanie i moc burzy.'),
    'stars': dict(name='Krąg Gwiazd', description='Mapa nieba, trzy gwiezdne postacie i kosmiczne omeny.'),
}
LANDS = {
    'arid': dict(name='Suchy', resistance='fire'),
    'polar': dict(name='Polarny', resistance='cold'),
    'temperate': dict(name='Umiarkowany', resistance='lightning'),
    'tropical': dict(name='Tropikalny', resistance='poison'),
}
LAND_SPELLS = {
    'arid': {3: ('blur', 'burning_hands', 'fire_bolt'), 5: ('fireball',), 7: ('blight',), 9: ('wall_of_stone',)},
    'polar': {3: ('fog_cloud', 'hold_person', 'ray_of_frost'), 5: ('sleet_storm',), 7: ('ice_storm',), 9: ('cone_of_cold',)},
    'temperate': {3: ('misty_step', 'shocking_grasp', 'sleep'), 5: ('lightning_bolt',), 7: ('freedom_of_movement',), 9: ('tree_stride',)},
    'tropical': {3: ('acid_splash', 'ray_of_sickness', 'web'), 5: ('stinking_cloud',), 7: ('polymorph',), 9: ('insect_plague',)},
}
BONUS_SPELLS = {
    'moon': {3: ('cure_wounds', 'moonbeam', 'starry_wisp'), 5: ('conjure_animals',), 7: ('fount_of_moonlight',), 9: ('mass_cure_wounds',)},
    'sea': {3: ('fog_cloud', 'gust_of_wind', 'ray_of_frost', 'shatter', 'thunderwave'), 5: ('lightning_bolt', 'water_breathing'), 7: ('control_water', 'ice_storm'), 9: ('conjure_elemental', 'hold_monster')},
    'stars': {3: ('guidance', 'guiding_bolt')},
}
# (id, game level, short label, original Polish mechanical summary)
FEATURES = {
    'land': (
        ('land_spells', 3, 'Czary ziemi', 'Po długim odpoczynku wybierasz środowisko i jego dodatkowe czary.'),
        ('lands_aid', 3, 'Pomoc ziemi', 'Użycie Dzikiego kształtu: obszar 10 stóp; 2k6 nekrotycznych, KON: połowa, oraz 2k6 leczenia jednego celu. Na poz. 10/14: 3k6/4k6.'),
        ('natural_recovery', 6, 'Naturalne odzyskanie', 'Raz na długi odpoczynek darmowy czar kręgu oraz odzyskanie many po krótkim odpoczynku.'),
        ('natures_ward', 10, 'Opieka natury', 'Odporność na zatrucie i wybrany typ obrażeń środowiska.'),
        ('natures_sanctuary', 14, 'Sanktuarium natury', 'Użycie Dzikiego kształtu: sześcian 15 stóp, połowiczna osłona i odporność środowiska dla sojuszników; przesuwany akcją dodatkową.'),
    ),
    'moon': (
        ('circle_forms', 3, 'Księżycowe kształty', 'Maks. SW: poziom druida ÷3. KP co najmniej 13+Mądrość; tymczasowe HP: 3×poziom druida.'),
        ('moon_spells', 3, 'Czary Księżyca', 'Dodatkowe czary można rzucać również w Dzikim kształcie.'),
        ('improved_forms', 6, 'Ulepszone kształty', 'Ataki bestii mogą zadawać promieniste; w przemianie dodajesz Mądrość do obrony Kondycji.'),
        ('moonlight_step', 10, 'Księżycowy krok', 'Akcja dodatkowa: teleport 30 stóp i przewaga następnego ataku do końca tury. Użycia: Mądrość; zwrot za komórkę II+.'),
        ('lunar_form', 14, 'Księżycowa postać', 'Raz na turę dodatkowe 2k10 promienistych przy trafieniu bestii. Krok może zabrać pobliskiego sojusznika.'),
    ),
    'sea': (
        ('sea_spells', 3, 'Czary Morza', 'Dodatkowe zaklęcia oceanu i burzy.'),
        ('wrath_of_sea', 3, 'Gniew morza', 'Użycie Dzikiego kształtu: aura 5 stóp na 10 minut; akcja dodatkowa, KON lub k6 zimna za punkt Mądrości i odepchnięcie do 15 stóp.'),
        ('aquatic_affinity', 6, 'Więź z wodą', 'Aura zwiększa się do 10 stóp. Szybkość pływania równa szybkości ruchu.'),
        ('stormborn', 10, 'Dziecko burzy', 'Aktywna aura daje latanie i odporność na zimno, błyskawice oraz grzmot.'),
        ('oceanic_gift', 14, 'Dar oceanu', 'Aura na sojuszniku w 60 stopach; dwa użycia Dzikiego kształtu obejmują także ciebie.'),
    ),
    'stars': (
        ('star_map', 3, 'Mapa gwiazd', 'Trzymana mapa jest ogniskiem magii; daje Wskazówki i Wiodący pocisk, w tym darmowe użycia pocisku równe Mądrości.'),
        ('starry_form', 3, 'Gwiezdna postać', 'Użycie Dzikiego kształtu: Łucznik, Kielich albo Smok na 10 minut; zachowujesz własne statystyki.'),
        ('cosmic_omen', 6, 'Kosmiczny omen', 'Po długim odpoczynku losujesz omen: reakcja dodaje lub odejmuje k6 od testu k20 widocznej istoty w 30 stopach. Użycia: Mądrość.'),
        ('twinkling', 10, 'Migoczące konstelacje', 'Łucznik i Kielich: 2k8; Smok: lot 20 stóp z zawisem. Konstelację zmienisz na początku tury.'),
        ('full_of_stars', 14, 'Pełnia gwiazd', 'Gwiezdna postać daje odporność na obrażenia obuchowe, kłute i cięte.'),
    ),
}


def effective_level(p): return min(20, max(1, int(p.level)))
def circle(p):
    key = getattr(p, 'druid_circle', '')
    return key if getattr(p, 'class_id', '') == 'druid' and p.level >= 3 and key in CIRCLES else ''


def state(p):
    if not isinstance(getattr(p, 'druid_circle_state', None), dict): p.druid_circle_state = {}
    return p.druid_circle_state


def runtime(p):
    if not isinstance(getattr(p, 'druid_circle_runtime', None), dict): p.druid_circle_runtime = {}
    return p.druid_circle_runtime


def wisdom(p):
    try: from . import combat_rules as rules
    except ImportError: import combat_rules as rules
    return rules.ability_modifier(p, 'wisdom')


def land(p): return state(p).get('land', 'arid') if state(p).get('land', 'arid') in LANDS else 'arid'
def shape_max(p): return 0 if p.class_id != 'druid' or p.level < 2 else 2 + (effective_level(p) >= 6) + (effective_level(p) >= 17)
def spent(p, key): return max(0, int(state(p).get(key + '_spent', 0)))
def spend(p, key, count=1): state(p)[key + '_spent'] = spent(p, key) + count
def shape_remaining(p): return max(0, shape_max(p) - spent(p, 'shape'))


def spend_shape(p, count=1):
    if type(count) is not int or count < 1 or shape_remaining(p) < count: return False
    spend(p, 'shape', count)
    return True


def feature_remaining(p, key): return max(0, max(1, wisdom(p)) - spent(p, key))


def bonus_spells(p):
    key = circle(p)
    table = LAND_SPELLS[land(p)] if key == 'land' else BONUS_SPELLS.get(key, {})
    if key == 'stars' and not state(p).get('map_equipped', True): return {}
    return {spell: level for level, spells in table.items() if p.level >= level for spell in spells}


def beast_spell_allowed(p, key): return not active(p, 'polymorph') and circle(p) == 'moon' and key in bonus_spells(p)
def form_temp_hp(p): return effective_level(p) * (3 if circle(p) == 'moon' else 1)
def max_form_cr(p): return effective_level(p) // 3 if circle(p) == 'moon' else 1 if p.level >= 8 else .5 if p.level >= 4 else .25


def form_allowed(p, key):
    try: from . import caster_rules as caster
    except ImportError: import caster_rules as caster
    form = key.removeprefix('wild_shape_') if isinstance(key, str) else ''
    spec = caster.FORMS.get(form)
    if p.class_id != 'druid' or p.level < 2 or not spec: return False
    if spec.get('fly') and p.level < 8: return False
    text = str(spec.get('cr', '0')); parts = text.split('/')
    cr = float(parts[0])/float(parts[1]) if len(parts) == 2 else float(text)
    return cr <= max_form_cr(p)
def wild_shape_active(p): return bool(getattr(p, 'form', '')) and not active(p, 'polymorph')
def armor_class_floor(p): return 13 + wisdom(p) if circle(p) == 'moon' and wild_shape_active(p) else 0
def save_bonus(p, ability): return wisdom(p) if circle(p) == 'moon' and p.level >= 6 and wild_shape_active(p) and ability == 'constitution' else 0
def active(p, key): return getattr(p, 'buffs', {}).get(key, {}).get('until', 0) > getattr(p, 'current_wall_time', 0)


def starry_form(p):
    # The active effect is authoritative; runtime is retained for older in-memory
    # actors. Do not reconstruct a form from a spent resource or an expired buff.
    if not getattr(p, 'alive', False) or active(p, 'polymorph') or circle(p) != 'stars' or not active(p, 'starry_form'):
        return ''
    effect = p.buffs['starry_form']
    form = effect.get('form') or runtime(p).get('starry_form') or effect.get('spell_id', '').removeprefix('circle_star_')
    return form if form in ('archer', 'chalice', 'dragon') else ''


def owner_forms(p, now):
    """Small uncached owner snapshot, separate from decorative circle visuals."""
    form = starry_form(p)
    blocked = not getattr(p, 'alive', False) or any(active(p, key) for key in (
        'incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending', 'stinking_poison', 'polymorph'))
    return dict(starry_form=form,
                starry_remaining=round(max(0, p.buffs.get('starry_form', {}).get('until', 0)-now), 2) if form else 0,
                shape_remaining=shape_remaining(p), shape_maximum=shape_max(p),
                can_dismiss_star=bool(form and not blocked),
                can_shoot=bool(form == 'archer' and not blocked),
                arrow_ready_in=round(max(0, getattr(p, 'bonus_cooldown_until', 0)-now), 3))


def roll_floor(p, ability, kind):
    return 10 if starry_form(p) == 'dragon' and (kind == 'concentration' or kind == 'ability' and ability in ('intelligence', 'wisdom')) else 1


def poison_immune(p): return not active(p, 'polymorph') and circle(p) == 'land' and p.level >= 10
def can_swim(p): return not active(p, 'polymorph') and circle(p) == 'sea' and p.level >= 6


def sea_benefits(p):
    if not active(p, 'wrath_of_sea'): return False
    # Polymorph replaces the target's own class features. A gift cast by another
    # druid remains an external magical effect on the transformed creature.
    return not active(p, 'polymorph') or p.buffs['wrath_of_sea'].get('owner', getattr(p, 'id', None)) != getattr(p, 'id', None)


def flight_speed(p):
    if sea_benefits(p) and p.buffs['wrath_of_sea'].get('level', 0) >= 10: return 'walking'
    return 20 if starry_form(p) == 'dragon' and p.level >= 10 else 0


def resists(p, kind):
    if not active(p, 'polymorph') and circle(p) == 'land' and p.level >= 10 and LANDS[land(p)]['resistance'] == kind: return True
    if active(p, 'nature_sanctuary') and p.buffs['nature_sanctuary'].get('resistance') == kind: return True
    if sea_benefits(p) and p.buffs['wrath_of_sea'].get('level', 0) >= 10 and kind in ('cold', 'lightning', 'thunder'): return True
    return bool(starry_form(p) and p.level >= 14 and kind in ('bludgeoning', 'piercing', 'slashing'))


def lunar_damage_type(p):
    return 'radiant' if circle(p) == 'moon' and p.level >= 6 and wild_shape_active(p) and state(p).get('lunar_radiant', True) else None


SPELL_FEATURES = {
    'circle_lands_aid': ('land', 3, 'Pomoc ziemi', 'action'),
    'circle_natures_sanctuary': ('land', 14, 'Sanktuarium natury', 'action'),
    'circle_move_sanctuary': ('land', 14, 'Przesuń sanktuarium', 'bonus'),
    'circle_moonlight_step': ('moon', 10, 'Księżycowy krok', 'bonus'),
    'circle_wrath_of_sea': ('sea', 3, 'Gniew morza', 'bonus'),
    'circle_wrath_strike': ('', 1, 'Uderzenie fali', 'bonus'),
    'circle_oceanic_gift': ('sea', 14, 'Dar oceanu', 'bonus'),
    'circle_oceanic_gift_shared': ('sea', 14, 'Wspólny dar oceanu', 'bonus'),
    'circle_star_archer': ('stars', 3, 'Gwiezdna postać · Łucznik', 'bonus'),
    'circle_star_chalice': ('stars', 3, 'Gwiezdna postać · Kielich', 'bonus'),
    'circle_star_dragon': ('stars', 3, 'Gwiezdna postać · Smok', 'bonus'),
    'circle_star_arrow': ('stars', 3, 'Gwiezdna strzała', 'bonus'),
}


def feature_allowed(p, key):
    if key == 'circle_wrath_strike': return active(p, 'wrath_of_sea')
    spec = SPELL_FEATURES.get(key)
    if not spec or circle(p) != spec[0] or p.level < spec[1]: return False
    if key == 'circle_star_arrow': return starry_form(p) == 'archer'
    if key == 'circle_move_sanctuary': return bool(runtime(p).get('sanctuary'))
    return True


def feature_ready(p, key):
    if not feature_allowed(p, key): return False
    now = getattr(p, 'current_wall_time', 0)
    if key == 'circle_star_' + starry_form(p): return False
    if not getattr(p, 'alive', False) or any(active(p, x) for x in ('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending', 'stinking_poison', 'polymorph')): return False
    switching = key.startswith('circle_star_') and key != 'circle_star_arrow' and starry_form(p) and p.level >= 10
    if switching: return runtime(p).get('star_switch_ready', 0) <= now
    bonus = SPELL_FEATURES[key][3] == 'bonus'
    if (getattr(p, 'bonus_cooldown_until', 0) if bonus else getattr(p, 'attack_cooldown_until', 0)) > now: return False
    if key == 'circle_moonlight_step': return feature_remaining(p, 'moonlight_step') > 0
    if key in ('circle_star_arrow', 'circle_move_sanctuary', 'circle_wrath_strike'): return True
    if key == 'circle_wrath_of_sea' and active(p, 'wrath_of_sea'): return True
    return shape_remaining(p) >= (2 if key == 'circle_oceanic_gift_shared' else 1)


def configure(spells, statuses):
    for key, (subclass, level, name, action) in SPELL_FEATURES.items():
        spells[key] = dict(id=key, name=name, english=name, words=name, circle=0, class_ids=['druid'], class_levels={'druid': level}, class_min_levels={'druid': level}, min_level=level,
            kind='druid_circle', action=action, mana=0, cooldown=0, range=768, radius=0, shape='single', targeting='self', feature=True,
            source='Player’s Handbook 2024', description=name, icon='assets/spells/star_arrow.svg' if key == 'circle_star_arrow' else 'assets/spells/starry_wisp.svg', effect='spell',
            visual=dict(style='buff', theme='nature', colors=['#619da2', '#b3dcf0', '#edffff'], shots=1))
    descriptions = {
        'circle_star_archer': 'Włącz Łucznika za 1 użycie Dzikiego kształtu. Kolejne ataki wykonuj Gwiezdną strzałą: nie zużywa many ani użyć przemiany.',
        'circle_star_chalice': 'Kielich dodaje leczenie po czarze leczącym, który zużył manę. Samo włączenie nie leczy i nie daje regeneracji.',
        'circle_star_dragon': 'Smok podnosi wyniki k20 poniżej 10 do 10 przy koncentracji oraz testach Inteligencji i Mądrości. Nie jest przemianą w bestię i nie daje zionięcia.',
        'circle_star_arrow': 'Dodatkowy atak promienisty podczas postaci Łucznika. Zużywa akcję dodatkową, ale nie manę ani użycia Dzikiego kształtu.',
    }
    for key, description in descriptions.items(): spells[key]['description'] = description
    for key, name, icon in [('starry_form', 'Gwiezdna postać', '✧'), ('wrath_of_sea', 'Gniew morza', '≈'), ('nature_sanctuary', 'Sanktuarium natury', '♧'), ('moonlight_advantage', 'Blask księżyca', '☽')]:
        statuses[key] = dict(name=name, icon=icon, description='', harmful=False)


def sheet(p):
    if p.class_id != 'druid': return {}
    key = circle(p); data = state(p)
    level_met = p.level >= PROMOTION_LEVEL
    promotion_met = bool(getattr(p, 'promoted', False))
    eligible = level_met and promotion_met and not key
    def feature_rows(subclass):
        return [dict(id=id_, level=level, name=name, description=description, unlocked=p.level >= level) for id_, level, name, description in FEATURES[subclass]]
    options = [dict(id=id_, **spec, features=feature_rows(id_)) for id_, spec in CIRCLES.items()]
    resources = [dict(id='shape', name='Dziki kształt', remaining=shape_remaining(p), maximum=shape_max(p))] if p.level >= 2 else []
    for resource, name, owner, gate in [('guiding_bolt', 'Darmowy Wiodący pocisk', 'stars', 3), ('omen', 'Kosmiczny omen', 'stars', 6), ('moonlight_step', 'Księżycowy krok', 'moon', 10)]:
        if key == owner and p.level >= gate: resources.append(dict(id=resource, name=name, remaining=feature_remaining(p, resource), maximum=max(1, wisdom(p))))
    if key == 'land' and p.level >= 6:
        resources += [dict(id=id_, name=name, remaining=max(0, 1-spent(p, id_)), maximum=1) for id_, name in [('natural_free', 'Darmowy czar kręgu'), ('natural_recovery', 'Naturalne odzyskanie')]]
    enabled = bool(getattr(p, 'alive', False) and not any(active(p, x) for x in ('incapacitated', 'paralyzed', 'unconscious', 'stunned', 'sleep_pending', 'stinking_poison', 'polymorph')))
    actions = [dict(id=id_, name=s[2], level=s[1], kind='spell', enabled=feature_ready(p, id_)) for id_, s in SPELL_FEATURES.items() if feature_allowed(p, id_)]
    for id_, name, owner, gate in [('lunar_radiant', 'Promieniste ataki bestii', 'moon', 6), ('omen_armed', 'Automatyczny omen', 'stars', 6), ('star_map', 'Trzymaj mapę gwiazd', 'stars', 3), ('natural_free', 'Darmowy następny czar kręgu', 'land', 6)]:
        if key == owner and p.level >= gate: actions.append(dict(id=id_, name=name, level=gate, kind='toggle', enabled=enabled))
    if key == 'moon' and p.level >= 10: actions.append(dict(id='restore_moonlight_step', name='Przywróć krok · 30 MP', level=10, kind='command', enabled=enabled and spent(p, 'moonlight_step') > 0 and p.mana >= 30))
    if starry_form(p): actions.append(dict(id='dismiss_star_form', name='Zakończ gwiezdną postać', level=3, kind='command', enabled=enabled))
    if active(p, 'wrath_of_sea'): actions.append(dict(id='dismiss_sea', name='Zakończ Gniew morza', level=3, kind='command', enabled=enabled))
    if runtime(p).get('grapples'): actions.append(dict(id='release_grapples', name='Zwolnij chwyt', level=1, kind='command', enabled=enabled))
    return dict(id=key, name=CIRCLES.get(key, {}).get('name', ''), pending=eligible, eligible=eligible,
        required_level=PROMOTION_LEVEL, required_promotion=True, promotion_met=promotion_met, level_met=level_met,
        options=options, features=feature_rows(key) if key else [], land=land(p), lands=[dict(id=id_, **s) for id_, s in LANDS.items()], land_change_ready=data.get('land_change_ready', True),
        starry_form=starry_form(p), lunar_radiant=data.get('lunar_radiant', True), omen=data.get('omen', 'weal'), omen_armed=data.get('omen_armed', False),
        map_equipped=data.get('map_equipped', True), natural_free=data.get('natural_free_armed', False),
        chalice_target=runtime(p).get('chalice_target', ''), shared_moonlight_target=runtime(p).get('shared_moonlight_target', ''), resources=resources,
        bonus_spells=[dict(id=id_, level=level) for id_, level in bonus_spells(p).items()], actions=actions)
