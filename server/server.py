"""Pogranicze: authoritative shared-world RPG prototype, version 0.8.18.

One process owns a SQLite database; all economy, combat and crimes are server-owned.
"""
from __future__ import annotations
import argparse
import asyncio
import contextlib
from collections import deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
from pathlib import Path
from types import SimpleNamespace
import random
import re
import secrets
import sqlite3
import time
from aiohttp import web, WSMsgType
try:
    from . import world_content as content
    from . import seo
    from . import living_world, vertical_world, loot_tables, combat_rules, loot_content, hunt_content, discovery_rules
    from . import continent_world, adventure_content, expedition_content, terrain_detail
    from .adventure_combat import AdventureGame
    from .google_accounts import GoogleAccountGame
    from .google_auth import GoogleAuthService, register_routes as register_google_routes
    from .combat_rules import CombatRounds
    from .dnd_game import DNDGame
    from . import dnd_content
    from .monster_ai import MonsterAI
    from . import level_up, spell_scaling, inventory_rules, fighter_rules
    from .fighter_rules import FighterGame
    from . import equipment_rules, caster_rules, magic_items, loot_economy
    from .caster_game import CasterGame
    from . import wizard_schools
    from . import town_services
    from .wizard_school_game import WizardSchoolGame
    from . import martial_rules, skill_rules, ability_rules
    from .character_development import CharacterDevelopmentGame
    from .skill_game import SkillGame
    from .martial_game import MartialGame
    from .martial_combat import MartialCombat
    from . import rest_rules, druid_circles, environment_rules
    from .environment_rules import EnvironmentGame
    from .druid_circle_game import DruidCircleGame
    from .druid_circle_spells import DruidCircleSpells, configure as configure_circle_spells
    from .progression import ExpansionGame, same_floor, near, train, skill_level, private_state, merchant_at
    from . import progression_guide
except ImportError:
    import world_content as content
    import seo
    import living_world, vertical_world, loot_tables, combat_rules, loot_content, hunt_content, discovery_rules
    import continent_world, adventure_content, expedition_content, terrain_detail
    from adventure_combat import AdventureGame
    from google_accounts import GoogleAccountGame
    from google_auth import GoogleAuthService, register_routes as register_google_routes
    from combat_rules import CombatRounds
    from dnd_game import DNDGame
    import dnd_content
    from monster_ai import MonsterAI
    import level_up, spell_scaling, inventory_rules, fighter_rules
    from fighter_rules import FighterGame
    import equipment_rules, caster_rules, magic_items, loot_economy
    from caster_game import CasterGame
    import wizard_schools
    import town_services
    from wizard_school_game import WizardSchoolGame
    import martial_rules, skill_rules, ability_rules
    from character_development import CharacterDevelopmentGame
    from skill_game import SkillGame
    from martial_game import MartialGame
    from martial_combat import MartialCombat
    import rest_rules, druid_circles, environment_rules
    from environment_rules import EnvironmentGame
    from druid_circle_game import DruidCircleGame
    from druid_circle_spells import DruidCircleSpells, configure as configure_circle_spells
    from progression import ExpansionGame, same_floor, near, train, skill_level, private_state, merchant_at
    import progression_guide

WIDTH, HEIGHT, SPEED, RADIUS = content.WIDTH, content.HEIGHT, 100, 18
MAX_CONNECTIONS, MAX_PLAYERS, MAX_MESSAGE = 48, 24, 2048
SPAWN = {"x": 560, "y": 1180}
RIVER = {"x": 1500, "y": 0, "w": 180, "h": 2304,
         "bridge_y": 1080, "bridge_h": 150}
TRAIL_GATE = {"x": 2370, "y": 1450, "w": 300, "h": 55}
OBSTACLES = [
    {"x": 235, "y": 1510, "w": 90, "h": 86, "type": "mill"},
    {"x": 340, "y": 1030, "w": 100, "h": 76, "type": "house"},
    {"x": 420, "y": 1300, "w": 108, "h": 80, "type": "house"},
    {"x": 710, "y": 990, "w": 110, "h": 84, "type": "house"},
    {"x": 330, "y": 310, "w": 190, "h": 100},
    {"x": 760, "y": 350, "w": 100, "h": 170},
    {"x": 1060, "y": 440, "w": 170, "h": 95},
    {"x": 310, "y": 800, "w": 120, "h": 100},
    {"x": 1120, "y": 1470, "w": 190, "h": 100},
    {"x": 1940, "y": 600, "w": 120, "h": 230},
    {"x": 2380, "y": 410, "w": 95, "h": 170},
    {"x": 2760, "y": 740, "w": 180, "h": 90},
    {"x": 2230, "y": 900, "w": 160, "h": 80},
    {"x": 2250, "y": 1450, "w": 55, "h": 670},
    {"x": 2780, "y": 1450, "w": 55, "h": 670},
    {"x": 2250, "y": 2065, "w": 585, "h": 55},
    {"x": 2250, "y": 1450, "w": 120, "h": 55},
    {"x": 2670, "y": 1450, "w": 165, "h": 55},
]
SITES, CHESTS = [], []
SAFE_ZONE = {**SPAWN, "radius": 260}
MERCHANT = {"x": 680, "y": 1180, "name": "Kupiec", "radius": 150,
            "prices": {"health_potion": 15}}
INVENTORY_CAP, PARTY_CAP, PARTY_RANGE = 40, 4, 650
PVP_RULES = {"min_level": 8, "white_seconds": 120, "combat_seconds": 20,
             "red_kills": 3, "crime_window_seconds": 86400, "red_seconds": 86400,
             "normal_gold_loss": .05, "normal_xp_loss": .10,
             "red_gold_loss": .20, "red_xp_loss": .20,
             "red_item_loss": "one_unequipped; transferred_to_killer_if_space_else_destroyed"}
REST_RULES = {"short_seconds": 10, "long_seconds": 30,
              "short_cooldown_seconds": 15, "long_cooldown_seconds": 60,
              "pve_delay_seconds": 3, "long_safe_only": False}


def rest_block_status(p, now, simulation_time, kind=None):
    """Rest has its own PvE wait and per-kind completion deadline."""
    if not p.alive:
        return "dead", 0
    if p.disconnected:
        return "disconnected", 0
    if p.casting_channel:
        return "channel", 0
    if (p.dx or p.dy) and simulation_time-p.input_time <= .35:
        return "moving", 0
    pvp = max(0, p.pvp_combat_until-now)
    # Existing persisted combat deadlines also protect reconnects without a migration.
    pve = max(0, p.combat_until-(PVP_RULES["combat_seconds"]-REST_RULES["pve_delay_seconds"])-now)
    if pvp:
        return "combat_pvp", max(pvp, pve)
    if pve:
        return "combat_pve", pve
    cooldown = max(0, (p.rest_resources.get(kind+"_ready",0) if kind else 0)-now)
    if cooldown:
        return "cooldown", cooldown
    return "", 0


POTIONS = {"health_potion": {"name": "Mikstura zdrowia", "price": 15, "restore": 65}}
CLASSES = dict(dnd_content.CLASS_SPECS)

WEAPONS = {"sword": {"range": 108, "cooldown": combat_rules.ROUND_SECONDS}, "bow": {"range": 310, "cooldown": combat_rules.ROUND_SECONDS},
           "staff": {"range": 285, "cooldown": combat_rules.ROUND_SECONDS}}
ITEMS = {}
for class_id, weapon, noun in [("knight", "sword", "Miecz"), ("ranger", "bow", "Łuk"),
                              ("mage", "staff", "Kostur maga"), ("druid", "staff", "Laska druida")]:
    for tier, adjective, damage, level, value, rarity in [
        (1, "podróżnika", 0, 1, 4, "common"), (2, "strażnika", 5, 3, 24, "uncommon"),
        (3, "pogranicza", 12, 8, 70, "rare")]:
        ITEMS[f"{class_id}_weapon_{tier}"] = {"name": f"{noun} {adjective}", "slot": "weapon",
            "attack": damage, "armor": 0, "class_ids": [class_id], "min_level": level, "value": value,
            "rarity": rarity, "weapon": weapon}
for key, name, armor, level, value, rarity in [
    ("cloth", "Kurtka podróżnika", 1, 1, 6, "common"),
    ("leather", "Zbroja ze skóry", 3, 3, 22, "uncommon"),
    ("scale", "Pancerz strażnika", 6, 8, 65, "rare")]:
    ITEMS[key] = {"name": name, "slot": "armor", "attack": 0, "armor": armor,
                  "class_ids": list(CLASSES), "min_level": level, "value": value, "rarity": rarity}
ITEMS["copper_ring"] = {"name": "Miedziany pierścień", "slot": "ring", "attack": 1, "armor": 0,
                        "class_ids": list(CLASSES), "min_level": 1, "value": 12, "rarity": "common"}
ITEMS["hunter_ring"] = {"name": "Pierścień łowcy", "slot": "ring", "attack": 3, "armor": 1,
                        "class_ids": list(CLASSES), "min_level": 5, "value": 40, "rarity": "uncommon"}
ZONES = [
    {"id": "town", "name": "Przystań", "x": 260, "y": 960, "w": 740, "h": 420, "color": "#b7be70"},
    {"id": "meadow", "name": "Słoneczne Łąki", "x": 180, "y": 1390, "w": 1270, "h": 720, "color": "#89bc53"},
    {"id": "forest", "name": "Szmaragdowy Las", "x": 220, "y": 220, "w": 1080, "h": 690, "color": "#448b4b"},
    {"id": "goblin_camp", "name": "Obóz Zielonego Kła", "x": 1080, "y": 140, "w": 360, "h": 530, "color": "#b7a467"},
    {"id": "swamp", "name": "Błękitne Mokradła", "x": 1720, "y": 1360, "w": 510, "h": 680, "color": "#58a88c"},
    {"id": "ruins", "name": "Ruiny Świtu", "x": 2080, "y": 310, "w": 900, "h": 720, "color": "#b9b3a0"},
    {"id": "sanctuary", "name": "Twierdza Strażnika", "x": 2250, "y": 1450, "w": 585, "h": 670, "color": "#8b829e"},
]
NPCS = [
    {"id": "strazniczka", "name": "Strażniczka Mira", "x": 600, "y": 1100, "role": "Straż Przystani", "radius": 150},
    {"id": "kartograf", "name": "Kartograf Oren", "x": 430, "y": 1130, "role": "Mapy i odkrycia", "radius": 150},
    {"id": "zwiadowca", "name": "Zwiadowca Borys", "x": 740, "y": 1260, "role": "Wyprawy na pogranicze", "radius": 150},
]
LANDMARKS = [
    {"id": "old_mill", "name": "Stary Młyn", "x": 340, "y": 1640, "radius": 90, "biome": "meadow",
     "description": "Złote pola i skrzypiące łopaty młyna. Droga na południowy zachód omija leśne wilki.", "reward": {"xp": 20, "gold": 8}},
    {"id": "goblin_camp", "name": "Obóz Zielonego Kła", "x": 1310, "y": 320, "radius": 90, "biome": "goblin_camp",
     "description": "Za namiotami dymi kuchnia goblinów. Na skraju lasu można walczyć z nimi pojedynczo.", "reward": {"xp": 25, "gold": 10}},
    {"id": "old_bridge", "name": "Most Wędrowców", "x": 1740, "y": 1160, "radius": 90, "biome": "river",
     "description": "Jedyna przeprawa przez szeroką rzekę. Za mostem czekają ruiny i mokradła.", "reward": {"xp": 20, "gold": 8}},
    {"id": "marsh_shrine", "name": "Kapliczka Świetlików", "x": 1860, "y": 1730, "radius": 90, "biome": "swamp",
     "description": "Pośród turkusowych rozlewisk świecą kwiaty. Pająki pilnują suchej ścieżki.", "reward": {"xp": 30, "gold": 12}},
    {"id": "dawn_ruins", "name": "Dziedziniec Świtu", "x": 2590, "y": 370, "radius": 90, "biome": "ruins",
     "description": "Białe kolumny i popękane mozaiki. Szkielety krążą tam, gdzie dawniej stał targ.", "reward": {"xp": 35, "gold": 15}},
    {"id": "fortress", "name": "Brama Twierdzy", "x": 2530, "y": 1580, "radius": 90, "biome": "sanctuary",
     "description": "Otwarta brama prowadzi do Władcy Twierdzy. Zbierz drużynę i zapas mikstur.", "reward": {"xp": 40, "gold": 15}},
]
QUESTS = [
    {"id": "q_rats", "title": "Szczury na łąkach", "description": "Mira prosi o oczyszczenie łąki za południowo-wschodnim wyjściem. Pokonaj 3 szczury i wróć po zapasy.",
     "npc_id": "strazniczka", "requires": [],
     "objectives": [{"type": "kill", "target": "rat", "label": "Szczury na Słonecznych Łąkach", "required": 3, "x": 810, "y": 1460}],
     "reward": {"xp": 55, "gold": 25, "potions": {"health_potion": 2}}},
    {"id": "q_mill", "title": "Droga do Starego Młyna", "description": "Oren zaznaczył młyn na południowym zachodzie. Odkryj go, wróć do kartografa i odbierz lepszą broń dla swojej klasy.",
     "npc_id": "kartograf", "requires": ["q_rats"],
     "objectives": [{"type": "discover", "target": "old_mill", "label": "Odkryj Stary Młyn", "required": 1, "x": 340, "y": 1640}],
     "reward": {"xp": 70, "gold": 35, "item": "class_weapon_2"}},
    {"id": "q_goblins", "title": "Zielony Kieł", "description": "Borys wypatrzył obóz daleko na północnym wschodzie lasu, po tej stronie rzeki. Odkryj obóz i pokonaj 3 gobliny.",
     "npc_id": "zwiadowca", "requires": ["q_mill"],
     "objectives": [{"type": "discover", "target": "goblin_camp", "label": "Odkryj obóz goblinów", "required": 1, "x": 1310, "y": 320},
                    {"type": "kill", "target": "goblin", "label": "Gobliny Zielonego Kła", "required": 3, "x": 1320, "y": 580}],
     "reward": {"xp": 120, "gold": 60, "item": "leather"}},
    {"id": "q_ruins", "title": "Kości dawnego miasta", "description": "Przejdź przez Most Wędrowców, potem skieruj się na północ. Odkryj Dziedziniec Świtu i pokonaj 3 szkielety w ruinach.",
     "npc_id": "kartograf", "requires": ["q_goblins"],
     "objectives": [{"type": "discover", "target": "dawn_ruins", "label": "Odkryj Dziedziniec Świtu", "required": 1, "x": 2590, "y": 370},
                    {"type": "kill", "target": "skeleton", "label": "Szkielety w Ruinach Świtu", "required": 3, "x": 2720, "y": 520}],
     "reward": {"xp": 180, "gold": 100, "item": "hunter_ring"}},
    {"id": "q_boss", "title": "Władca za otwartą bramą", "description": "Wyprawa drużynowa: odkryj bramę na południowym wschodzie i pokonaj Władcę Twierdzy. Możesz wracać po jego łupy także po ukończeniu zadania.",
     "npc_id": "strazniczka", "requires": ["q_ruins"],
     "objectives": [{"type": "discover", "target": "fortress", "label": "Odkryj bramę twierdzy", "required": 1, "x": 2530, "y": 1580},
                    {"type": "kill", "target": "boss", "label": "Władca Twierdzy", "required": 1, "x": 2530, "y": 1900}],
     "reward": {"xp": 300, "gold": 180, "item": "class_weapon_3"}},
]
ENEMY_TYPES = {
    "rat": {"name": "Szczur polny", "hp": 24, "damage": 4, "range": 34, "speed": 52, "xp": 12, "gold": 3, "respawn": 14, "aggro": 110, "leash": 180},
    "boar": {"name": "Dzik", "hp": 68, "damage": 9, "range": 43, "speed": 68, "xp": 28, "gold": 8, "respawn": 20, "aggro": 140, "leash": 230},
    "goblin": {"name": "Goblin Zielonego Kła", "hp": 82, "damage": 11, "range": 44, "speed": 68, "xp": 36, "gold": 10, "respawn": 22, "aggro": 150, "leash": 240},
    "spider": {"name": "Szmaragdowy pająk", "hp": 120, "damage": 15, "range": 46, "speed": 74, "xp": 52, "gold": 14, "respawn": 24, "aggro": 150, "leash": 250},
    "skeleton": {"name": "Szkielet wartownika", "hp": 145, "damage": 17, "range": 48, "speed": 62, "xp": 64, "gold": 17, "respawn": 26, "aggro": 160, "leash": 270},
    "wolf": {"name": "Wilk cienia", "hp": 54, "damage": 8, "range": 43, "speed": 83, "xp": 24, "gold": 7, "respawn": 16, "aggro": 180, "leash": 280},
    "wisp": {"name": "Błędny ognik", "hp": 95, "damage": 12, "range": 160, "speed": 58, "xp": 42, "gold": 11, "respawn": 20, "aggro": 190, "leash": 290},
    "guardian": {"name": "Kamienny strażnik", "hp": 185, "damage": 19, "range": 65, "speed": 45, "xp": 75, "gold": 19, "respawn": 25, "aggro": 190, "leash": 300},
    "boss": {"name": "Władca Twierdzy", "hp": 1050, "damage": 28, "range": 85, "speed": 38, "xp": 400, "gold": 95, "respawn": 90, "aggro": 380, "leash": 420},
}


content.STARTER_SPAWNS = [
    ("wolf", 600, 790), ("wolf", 650, 620), ("wolf", 970, 640), ("wolf", 1090, 870),
    ("wolf", 990, 280), ("wolf", 1280, 840),
    ("wisp", 1940, 1010), ("wisp", 2140, 1240), ("wisp", 1880, 1530),
    ("guardian", 2500, 750), ("guardian", 2660, 1030), ("guardian", 2190, 510),
    ("boss", 2530, 1900),
    ("rat", 810, 1460), ("rat", 700, 1580), ("rat", 910, 1660),
    ("boar", 1060, 1840), ("boar", 1240, 1930), ("boar", 460, 530),
    ("goblin", 1320, 580), ("goblin", 1350, 390), ("goblin", 1160, 200),
    ("spider", 1840, 1900), ("spider", 2120, 1740), ("spider", 2100, 1490),
    ("skeleton", 2720, 520), ("skeleton", 2630, 320), ("skeleton", 2880, 980),
]
content.configure(ITEMS, ZONES, NPCS, LANDMARKS, QUESTS, ENEMY_TYPES, OBSTACLES, MERCHANT)
content.QUESTS_REF = QUESTS
content.expand_wilderness(ZONES, NPCS, LANDMARKS, OBSTACLES)
living_world.configure(content, OBSTACLES, LANDMARKS, QUESTS, ENEMY_TYPES)
vertical_world.configure(content, OBSTACLES, LANDMARKS, ZONES, ENEMY_TYPES)
loot_tables.configure(ITEMS, ENEMY_TYPES, content.TIER_LEVELS)
combat_rules.configure(ITEMS, ENEMY_TYPES)
hunt_content.configure(ENEMY_TYPES)
loot_content.configure(ITEMS, ENEMY_TYPES, content.TIER_LEVELS)
hunt_content.place(content, OBSTACLES, LANDMARKS)
continent_world.configure(content, OBSTACLES, LANDMARKS, ZONES, NPCS, QUESTS, ENEMY_TYPES)
adventure_content.configure(content, OBSTACLES, LANDMARKS, ZONES, ENEMY_TYPES, NPCS, QUESTS)
expedition_content.configure(content, OBSTACLES, LANDMARKS, ZONES, ENEMY_TYPES, NPCS, QUESTS)
town_services.configure(content, NPCS)
for monster_id, monster_spec in ENEMY_TYPES.items():
    monster_spec['respawn'] = max(180 if monster_spec.get('boss') or monster_id=='boss' else 45,
                                  round(monster_spec.get('respawn',35)*1.75))
discovery_rules.configure(content, LANDMARKS, ZONES, ENEMY_TYPES)
content.VERSION = "0.8.18"
WIDTH, HEIGHT = content.WIDTH, content.HEIGHT
for tier, level, amount, cost in ((2, 20, 220, 45), (3, 50, 520, 95), (4, 80, 950, 165)):
    POTIONS[f"health_potion_{tier}"] = {"name": f"Mikstura zdrowia {tier}", "price": cost, "restore": amount, "min_level": level}

dnd_content.configure(content, CLASSES, POTIONS)
for potion_spec in POTIONS.values():
    potion_spec.update(min_level=1, action="bonus")
inventory_rules.configure(ITEMS, POTIONS)
for potion_id in POTIONS:
    ITEMS[potion_id]["action"] = "bonus"
fighter_rules.configure(ITEMS, dnd_content.SPELLS, CLASSES)
equipment_rules.configure(ITEMS)
magic_items.configure(ITEMS)
loot_economy.configure(ITEMS, ENEMY_TYPES)
caster_rules.configure(dnd_content.SPELLS, CLASSES, dnd_content.STATUS_SPECS)
druid_circles.configure(dnd_content.SPELLS,dnd_content.STATUS_SPECS)
configure_circle_spells(dnd_content.SPELLS,dnd_content.STATUS_SPECS)
rest_rules.configure(dnd_content.SPELLS)
wizard_schools.configure(dnd_content.SPELLS,dnd_content.STATUS_SPECS)
martial_rules.configure(dnd_content.SPELLS,dnd_content.STATUS_SPECS)
environment_rules.configure_world()
continent_world.finalize(content, OBSTACLES)
terrain_detail.configure(content, OBSTACLES, LANDMARKS)
content.WORLD_REVISION = 29
MERCHANT['stock'] = list(content.STARTER_MERCHANT_STOCK)
content.STARTER_MERCHANT = MERCHANT
# Powerful rings are deliberate rewards; repeatable monster drops remain rare.
for monster_spec in ENEMY_TYPES.values():
    for entry in monster_spec.get('loot',{}).get('entries',[]):
        spec = ITEMS.get(entry.get('template'),{})
        if spec.get('slot') == 'ring' and spec.get('magic_id'):
            entry['chance'] = min(entry['chance'], .02 if monster_spec.get('boss') else .003)
dnd_content.DEFAULT_HOTBARS["knight"] = ["second_wind", "action_surge"]
dnd_content.STATUS_SPECS.update({
    "sap": dict(name="Osłabienie",icon="⚔",description="Następny rzut ataku z utrudnieniem. Efekt kończy się po tym ataku lub przed kolejną rundą wojownika.",harmful=True),
    "prone": dict(name="Powalenie",icon="↘",description="Wstawanie: 1,5 s bez ruchu. Własne ataki z utrudnieniem; ataki z bliska z ułatwieniem, z daleka z utrudnieniem.",harmful=True),
})

def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def point_distance(p, obj):
    return math.hypot(p.x - obj["x"], p.y - obj["y"])


def intersects(x, y, rect, radius=RADIUS):
    return (x + radius > rect["x"] and x - radius < rect["x"] + rect["w"]
            and y + radius > rect["y"] and y - radius < rect["y"] + rect["h"])


def player_speed(level):
    """Gentle, unbounded-level movement growth; clients never supply speed."""
    return 100 + 90 * (level - 1) / (level + 79)


def xp_next(level):
    # Integer arithmetic: intentionally no gameplay level cap.
    return 55 + (level - 1) * 35


def make_item(template):
    return {"uid": secrets.token_hex(8), "template": template, **ITEMS[template]}


@dataclass
class Player:
    id: str
    name: str
    ws: object = None
    x: float = 560
    y: float = 1180
    floor: int = 0
    skill_tries: dict = field(default_factory=dict)
    promoted: bool = False
    soul: float = 100
    runes: dict = field(default_factory=dict)
    bank_gold: int = 0
    depot: list = field(default_factory=list)
    home_city: str = "przystan"
    world_revision: int = 20
    magic_items_version: int = 0
    magic_attunements: list = field(default_factory=list)
    blessed: bool = False
    mastery: dict = field(default_factory=dict)
    primal_order: str = ""
    training_feats: dict = field(default_factory=dict)
    ability_build: dict = field(default_factory=dict)
    skill_training: dict = field(default_factory=dict)
    skill_progress: dict = field(default_factory=dict)
    origin_feat: str = ""
    feat_rules_version: int = 0
    feat_legacy_choices: dict = field(default_factory=dict)
    feat_migration_notice: str = ""
    wizard_school: str = ""
    wizard_school_state: dict = field(default_factory=dict)
    wizard_school_runtime: dict = field(default_factory=dict)
    martial_archetype: str = ""
    martial_state: dict = field(default_factory=dict)
    druid_circle: str = ""
    druid_circle_state: dict = field(default_factory=dict)
    druid_circle_runtime: dict = field(default_factory=dict)
    rest_resources: dict = field(default_factory=dict)
    submerged: bool = False
    breath_until: float = 0
    exhaustion: int = 0
    _feat_turn_until: float = 0
    _savage_attack_used: bool = False
    caster_rules_version: int = 0
    legacy_medium_grace: bool = False
    casting_channel: dict = field(default_factory=dict)
    rest_state: dict = field(default_factory=dict)  # Session only; never persisted.
    rest_cooldown_until: float = 0  # Legacy save field; new deadlines are in rest_resources.
    familiar_state: dict = field(default_factory=dict)
    caster_messages: list = field(default_factory=list)
    form_attack_index: int = 0
    fighting_style: str = ""
    weapon_grip: str = "one"
    fighter_rules_version: int = 0
    spell_cooldowns: dict = field(default_factory=dict)
    spell_ready: float = 0
    rune_ready: float = 0
    haste_until: float = 0
    transition_ready: float = 0
    site_cooldowns: dict = field(default_factory=dict)
    wind_until: float = 0
    ward_until: float = 0
    premium_demo_until: float = 0
    current_wall_time: float = 0
    hp: float = 12
    mana: float = 45
    level: int = 1
    level_up_batches: list = field(default_factory=list)
    _level_up_cache: object = None
    xp: int = 0
    gold: int = 0
    class_id: str = "knight"
    class_chosen: bool = True
    weapon: str = "sword"
    kills: int = 0
    boss_kills: int = 0
    relics: list = field(default_factory=list)
    chests: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    equipment: dict = field(default_factory=lambda: {"weapon": "", "armor": "", "ring": "", "shield": ""})
    inventory_rules_version: int = 0
    potion_slots: dict = field(default_factory=lambda: {"q":"health_potion"})
    loot_discoveries: dict = field(default_factory=dict)
    potions: dict = field(default_factory=lambda: {"health_potion": 3})
    facing: list = field(default_factory=lambda: [0, 1])
    attack_facing: list = field(default_factory=lambda: [0, 1])
    speech_text: str = ""
    speech_until: float = 0
    quest_progress: dict = field(default_factory=dict)
    discoveries: list = field(default_factory=list)
    attack_until: float = 0
    attack_ready: float = 0  # compatibility: simulation animation only; cooldown uses wall time
    attack_cooldown_until: float = 0
    last_roll: dict = field(default_factory=dict)
    ability_cooldown_until: float = 0
    potion_cooldown_until: float = 0
    bulwark_until: float = 0
    combat_until: float = 0
    pvp_combat_until: float = 0
    last_pvp_attacker: str = ""
    last_pvp_unjust: bool = False
    last_pvp_hit_until: float = 0
    white_until: float = 0
    red_until: float = 0
    unjust_kills: list = field(default_factory=list)
    aggressors: dict = field(default_factory=dict)
    respawn_until: float = 0
    respawn_at: float = 0
    pvp_safety: bool = True
    party_id: str = ""
    dx: float = 0
    dy: float = 0
    input_time: float = -10
    chat_at: float = -10
    rules_version: int = 8
    mana_rules_version: int = dnd_content.MANA_RULES_VERSION
    hp_rules_version: int = combat_rules.HP_RULES_VERSION
    mana_recovery_until: float = 0
    _hotbar_level: tuple = field(default_factory=tuple)
    hotbar: list = field(default_factory=list)
    spell_history: list = field(default_factory=list)
    spell_circle_choices: dict = field(default_factory=dict)
    _spell_profiles_cache: object = None
    ensnaring_armed: bool = False  # one-shot intent; never restored across login
    concentration_profile: dict = field(default_factory=dict)
    buffs: dict = field(default_factory=dict)
    concentration: str = ""
    concentration_until: float = 0
    condition_targets: list = field(default_factory=list)
    mark_target: str = ""
    mark_target_kind: str = "enemy"
    form: str = ""
    form_until: float = 0
    temp_hp: float = 0
    bonus_cooldown_until: float = 0
    reaction_ready: float = 0
    shield_armed: bool = False
    combat_log: list = field(default_factory=list)
    auto_enemy_id: str = ""
    auto_target_id: str = ""
    auto_enabled: bool = False
    pending_spell: dict = field(default_factory=dict)

    @property
    def spec(self):
        return CLASSES[self.class_id]

    @property
    def base_speed(self):
        return player_speed(self.level)

    @property
    def speed(self):
        surface=living_world.SURFACES[content.SURFACE_MAP.at(self.x,self.y,self.floor)]["speed"]
        freedom=combat_rules.active_buff(self,'freedom')
        if freedom:surface=max(1.0,surface)
        slow=0.0 if combat_rules.active_buff(self,'restrained') else .25 if combat_rules.active_buff(self,'growth') else .5 if combat_rules.active_buff(self,'slow') else 1.0
        if combat_rules.active_buff(self,"prone"):return 0
        speed=(self.base_speed*(caster_rules.form_spec(self).get('speed',30)/30 if self.form else 1)-equipment_rules.armor_speed_penalty(self)+(dnd_content.LONGSTRIDER_SPEED_BONUS if combat_rules.active_buff(self,'longstrider') else 0))*(1.2 if self.premium_demo_until > self.current_wall_time else 1)*(1.15 if self.wind_until > self.current_wall_time else 1)*(1.0 if freedom else slow)
        return environment_rules.movement_speed(self,max(0,speed-self.exhaustion*5*100/30),surface)

    @property
    def max_hp(self):
        return combat_rules.max_hp(self)

    @property
    def max_mana(self):
        return dnd_content.max_mana(self)

    def gear_bonus(self, stat):
        if self.form:return 0
        equipped = set(self.equipment.values())
        return sum(ITEMS[i["template"]].get(stat, 0) for i in self.inventory if i["uid"] in equipped)

    @property
    def attack(self):
        n, sides, modifier = combat_rules.weapon_dice(self)
        return round(n*(sides+1)/2+modifier, 1)

    @property
    def armor(self):
        return max(0, self.armor_class-10)

    @property
    def armor_class(self):
        return combat_rules.armor_class(self)

    @property
    def attack_bonus(self):
        return combat_rules.attack_bonus(self)

    @property
    def alive(self):
        return self.hp > 0

    @property
    def disconnected(self):
        return self.ws is None or self.ws.closed

    def skull(self, now):
        return "red" if self.red_until > now else ("white" if self.white_until > now else "none")

    def public(self, now, simulation_time=0, private=False, party_members=None):
        self.current_wall_time = now
        skull = self.skull(now)
        result = {"id": self.id, "name": self.name, "x": round(self.x, 2), "y": round(self.y, 2),
                  "hp": round(max(0, self.hp), 1), "max_hp": self.max_hp, "form": self.form, "temp_hp": self.temp_hp, "mana": round(self.mana, 1),
                  "max_mana": self.max_mana, "level": self.level, "weapon": equipment_rules.weapon(self).get("weapon",self.spec["weapon"]),
                  "shield_equipped": fighter_rules.shield_bonus(self)>0, "weapon_type": fighter_rules.weapon_kind(self), "two_handed": fighter_rules.two_handed(self),
                  "floor": self.floor, "promoted": self.promoted, "class_id": self.class_id, "class_chosen": self.class_chosen,
                  "attack": self.attack, "armor": self.armor, "armor_class": self.armor_class, "attack_bonus": self.attack_bonus, "kills": self.kills, "boss_kills": self.boss_kills,
                  "ability_name": self.spec["ability_name"], "ability_cooldown": max(0, self.spell_cooldowns.get(self.spec["default_ability"],0)-now),
                  "facing": list(self.facing), "attack_facing": list(self.attack_facing),
                  "speech_text": self.speech_text if self.speech_until > simulation_time else "",
                  "speech_until": self.speech_until, "speed": round(self.speed, 3),
                  "attack_until": self.attack_until, "alive": self.alive,
                  "respawn_in": max(0, self.respawn_until-now) if not self.alive else 0,
                  "skull": skull, "skull_remaining": max(0, (self.red_until if skull == "red" else self.white_until)-now),
                  "combat_remaining": max(0, self.combat_until-now),
                  "pvp_combat_remaining": max(0, self.pvp_combat_until-now), "disconnected": self.disconnected,
                  "party_id": self.party_id, "party_members": party_members or []}
        result["status_effects"] = dnd_content.status_effects(self.buffs,now,self)
        result['environment']=environment_rules.public(self, private)
        aura=self.buffs.get('wrath_of_sea',{})
        sanctuary=druid_circles.runtime(self).get('sanctuary')
        result['circle_visual']={'starry_form':druid_circles.starry_form(self),
            'sea_radius':(64 if aura.get('level',0)>=25 else 32) if aura.get('until',0)>now else 0,
            'sanctuary':sanctuary if sanctuary and sanctuary.get('until',0)>now else None,
            'flight':environment_rules.flying(self),'submerged':self.submerged}
        result['wizard_visual']=wizard_schools.public_visual(self,now)
        if private:
            result['druid_forms'] = druid_circles.owner_forms(self, now)
            inventory_rules.ensure(self, ITEMS, POTIONS, make_item)
            try:
                from .character_sheet import build as sheet_data
            except ImportError:
                from character_sheet import build as sheet_data
            result['character_sheet'] = sheet_data(self)
            result['item_previews'] = equipment_rules.shop_previews(self)
            result['spell_profiles'] = spell_scaling.client_profiles(self)
            result.update(level_up.pending(self))
            if self._hotbar_level != dnd_content.hotbar_signature(self):dnd_content.sync_hotbar(self)
            result.update(private_state(self, now))
            rest_reason, rest_wait = rest_block_status(self, now, simulation_time)
            result.update({"rest": {"kind": self.rest_state["kind"], "total": self.rest_state["total"],
                                     "remaining": round(max(0, self.rest_state["until"]-now), 3)} if self.rest_state else {},
                           "rest_block_reason": rest_reason, "rest_block_remaining": round(rest_wait, 3),
                           "rest_cooldown_remaining": 0,
                           "rest_short_remaining": round(max(0,self.rest_resources.get("short_ready",0)-now),3),
                           "rest_long_remaining": round(max(0,self.rest_resources.get("long_ready",0)-now),3),
                           "rest_resources": rest_rules.sheet(self),
                           "rest_safe": any(near(self, zone) for zone in content.SAFE_ZONES)})
            result.update({"action_remaining": round(max(0, self.attack_cooldown_until-now), 3),
                           "action_duration": combat_rules.ROUND_SECONDS,
                           "damage_dice": combat_rules.dice_text(combat_rules.weapon_dice(self)),
                           "save_bonus": combat_rules.save_bonus(self), "save_dc": combat_rules.spell_dc(self),
                           "last_roll": self.last_roll if self.last_roll.get("expires_at", 0) > now else {}})
            result.update({"hotbar": list(self.hotbar), "grouped_hotbar": dnd_content.grouped_hotbar(self), "hotbar_page_size": dnd_content.HOTBAR_PAGE_SIZE, "hotbar_row_size": dnd_content.HOTBAR_ROW_SIZE, "favorite_spell": dnd_content.favorite_spell(self), "mana_budget": dnd_content.mana_budget_info(self),
                           "mana_recovery_remaining": max(0,self.mana_recovery_until-now), "attributes": combat_rules.attributes(self),
                           "proficiency": combat_rules.proficiency(self), "effective_level": combat_rules.effective_level(self),
                           "spell_circle": dnd_content.circle_for(self.class_id,self.level),
                           "attacks_per_round": combat_rules.attacks_per_round(self), "attack_range": combat_rules.attack_range(self),
                           "bonus_remaining": max(0,self.bonus_cooldown_until-now), "shield_armed": self.shield_armed, "ensnaring_armed": self.ensnaring_armed,
                           "concentration": self.concentration if self.concentration_until>now else "", "concentration_remaining": max(0,self.concentration_until-now),
                           "statuses": {k:round(v['until']-now,1) for k,v in self.buffs.items() if v.get('until',0)>now},
                           "form_remaining": max(0,self.form_until-now), "auto_enemy_id": self.auto_enemy_id,
                           "auto_target_id": self.auto_target_id, "auto_enabled": self.auto_enabled,
                           "weapon_auto_attack": combat_rules.weapon_autoattack(self),
                           "queued_spell": self.pending_spell.get('spell',''),
                           "combat_log": self.combat_log[-8:]})
            result.update({"xp": self.xp, "xp_next": xp_next(self.level), "gold": self.gold,
                           "pvp_safety": self.pvp_safety, "unjust_kills": len([t for t in self.unjust_kills if t > now-86400]),
                           "inventory": [inventory_rules.public_item(self, i, ENEMY_TYPES) for i in self.inventory], "equipment": dict(self.equipment),
                           "potions": dict(self.potions), "potion_slots": dict(self.potion_slots), "known_loot": inventory_rules.known_loot(self, ENEMY_TYPES), "potion_cooldown": max(0, self.bonus_cooldown_until-now),
                           "quests": self.quest_entries(), "discoveries": list(self.discoveries)})
            result["depot"] = [inventory_rules.public_item(self, i, ENEMY_TYPES) for i in self.depot]
        return result

    def quest_entries(self):
        result = []
        for quest in QUESTS:
            progress = self.quest_progress.get(quest["id"], {})
            objectives = []
            for index, objective in enumerate(quest["objectives"]):
                if objective["type"] == "discover":
                    count = int(objective["target"] in self.discoveries)
                else:
                    counts = progress.get("counts", [])
                    count = counts[index] if index < len(counts) else 0
                objectives.append({**objective, "count": min(objective["required"], count)})
            if progress.get("claimed"):
                status = "claimed"
            elif progress.get("accepted"):
                status = "ready" if all(o["count"] >= o["required"] for o in objectives) else "active"
            else:
                status = "available" if self.level >= quest.get("min_level", 1) and all(self.quest_progress.get(q, {}).get("claimed") for q in quest["requires"]) else "locked"
            result.append({**quest, "objectives": objectives, "status": status})
        return result

    def save_data(self):
        return {key: getattr(self, key) for key in (
            "primal_order", "training_feats", "caster_rules_version", "legacy_medium_grace",
            "ability_build", "skill_training", "skill_progress", "origin_feat",
            "feat_rules_version", "feat_legacy_choices", "feat_migration_notice",
            "world_revision", "magic_items_version", "magic_attunements",
            "wizard_school", "wizard_school_state", "druid_circle", "druid_circle_state", "rest_resources", "_feat_turn_until", "_savage_attack_used", "exhaustion",
            "martial_archetype", "martial_state",
            "fighting_style", "weapon_grip", "fighter_rules_version",
            "level_up_batches", "rules_version", "mana_rules_version", "hp_rules_version", "mana_recovery_until", "rest_cooldown_until", "hotbar", "spell_history", "spell_circle_choices", "bonus_cooldown_until", "reaction_ready", "shield_armed", "pvp_safety",
            "site_cooldowns", "wind_until", "ward_until", "premium_demo_until", "floor", "skill_tries", "promoted", "soul", "runes", "bank_gold", "depot", "home_city", "blessed", "mastery", "spell_cooldowns", "spell_ready", "rune_ready", "haste_until", "transition_ready",
            "x", "y", "hp", "mana", "level", "xp", "gold", "class_id", "class_chosen", "weapon", "kills", "boss_kills",
            "inventory_rules_version", "potion_slots", "loot_discoveries",
            "relics", "chests", "inventory", "equipment", "potions", "quest_progress", "discoveries", "attack_cooldown_until", "ability_cooldown_until",
            "potion_cooldown_until", "bulwark_until", "combat_until", "pvp_combat_until", "white_until", "red_until",
            "unjust_kills", "aggressors", "respawn_until", "last_pvp_attacker", "last_pvp_unjust", "last_pvp_hit_until")}


@dataclass
class Enemy:
    id: str
    kind: str
    x: float
    y: float
    hp: float
    home_x: float
    home_y: float
    floor: int = 0
    slow_until: float = 0
    alive: bool = True
    ready: float = 0
    attack_until: float = 0
    respawn_at: float = 0
    facing: list = field(default_factory=lambda: [0, 1])
    contributors: dict = field(default_factory=dict)
    aoe_ready: float = 0
    taunt_id: str = ""
    taunt_until: float = 0
    attacker_id: str = ""
    attacker_until: float = 0
    wander_x: float = 0
    wander_y: float = 0
    wander_ready: float = 0
    rest_until: float = 0
    cast_until: float = 0
    special_count: int = 0
    ranged_ready: float = 0
    mobile_cast: bool = False
    # Runtime-only pursuit state. A disengaged monster holds its actual position.
    has_engaged: bool = False
    chase_id: str = ""
    last_seen_x: float = 0
    last_seen_y: float = 0
    last_seen_until: float = 0
    regen_at: float = 0
    return_at: float = 0
    search_x: float = 0
    search_y: float = 0
    home_trail: list = field(default_factory=list)
    returning: bool = False
    conditions: dict = field(default_factory=dict)

    @property
    def max_hp(self):
        return ENEMY_TYPES[self.kind]["hp"]

    def public(self, now=0):
        self.current_wall_time=now
        spec=environment_rules.enemy_spec(self)
        return {"id": self.id, "kind": self.kind, "name": ENEMY_TYPES[self.kind]["name"], "x": round(self.x, 2),
                "form":getattr(self,'form',''), "temp_hp":getattr(self,'temp_hp',0),
                "y": round(self.y, 2), "floor": self.floor, "hp": round(self.hp, 1), "max_hp": self.max_hp, "alive": self.alive,
                "attack_until": self.attack_until, "facing": self.facing, "armor_class": spec["armor_class"], "attack_bonus": spec["attack_bonus"], "damage_dice": combat_rules.dice_text(spec["damage_dice"]), "statuses": [k for k,v in self.conditions.items() if v.get("until",0)>now], "status_effects": dnd_content.status_effects(self.conditions,now), "size": ENEMY_TYPES[self.kind].get("size", 1)}


class Game(CharacterDevelopmentGame,SkillGame,GoogleAccountGame,MartialGame,MartialCombat,AdventureGame,EnvironmentGame,WizardSchoolGame,DruidCircleSpells,DruidCircleGame,CasterGame, FighterGame, DNDGame, CombatRounds, ExpansionGame, MonsterAI):
    def __init__(self, db_path, clock=None):
        self.clock = clock or time.time
        self.rng = random.Random()
        self.combat_rng = random.Random()  # independent from loot and world generation
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            name_key TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, password_hash BLOB NOT NULL, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS shared(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS boss_rewards(player_id INTEGER PRIMARY KEY);
        """)
        self.init_google_accounts()
        # Old relic flags and boss claims never gate the new game.
        self.flags = {"bridge_open": True, "trail_open": True, "event_active": True, "boss_defeated": False}
        self.players, self.enemies, self.parties, self.invites = {}, {}, {}, {}
        self.connections, self.auth_attempts = set(), {}
        self.compact_clients, self.owner_cache = set(), {}
        self.time, self.tick, self.last_save, self.task = 0.0, 0, 0, None
        self.effects, self.effect_serial = [], 0
        self.hazards = []
        self.init_dnd()
        self.init_circle_spells()
        for i, (kind, x, y) in enumerate(content.STARTER_SPAWNS):
            e = Enemy("boss" if kind == "boss" else f"e{i}", kind, x, y, ENEMY_TYPES[kind]["hp"], x, y)
            e.aoe_ready = 7
            self.enemies[e.id] = e
        for i, (kind, x, y, floor) in enumerate(content.SPAWNS):
            e = Enemy(f"world_{i}", kind, x, y, ENEMY_TYPES[kind]["hp"], x, y, floor=floor)
            self.enemies[e.id] = e
        self.legacy_enemies = [e for e in self.enemies.values() if not e.id.startswith("world_")]
        self.enemy_cells, self.enemy_cell_keys = {}, {}
        self.chasing_enemies = {}
        self.recovering_enemies = {}
        for e in self.enemies.values():
            self.reindex_enemy(e)
        self.obstacle_cells = {}
        for obstacle in OBSTACLES:
            for cx in range(int(obstacle["x"]//256), int((obstacle["x"]+obstacle["w"]+36)//256)+1):
                for cy in range(int(obstacle["y"]//256), int((obstacle["y"]+obstacle["h"]+36)//256)+1):
                    self.obstacle_cells.setdefault((obstacle.get("floor", 0), cx, cy), []).append(obstacle)
        self.room_cells = {}
        for area in [*content.DUNGEONS, *content.ELEVATIONS]:
            for room in area["rooms"]:
                for cx in range(int(room["x"]//512), int((room["x"]+room["w"])//512)+1):
                    for cy in range(int(room["y"]//512), int((room["y"]+room["h"])//512)+1):
                        self.room_cells.setdefault((area["floor"], cx, cy), []).append(room)
        self.landmark_cells = {}
        for landmark in LANDMARKS:
            self.landmark_cells.setdefault((landmark.get("floor", 0), int(landmark["x"]//512), int(landmark["y"]//512)), []).append(landmark)
        # Preserve targetable avatars even across a quick server restart.
        for pid, name, encoded in self.db.execute("SELECT id,name,data FROM accounts"):
            saved = json.loads(encoded)
            if saved.get("combat_until", 0) > self.now():
                p = self.load_player(str(pid), name, None, saved)
                self.players[p.id] = p

    def now(self):
        return float(self.clock())

    def metadata(self):
        return {"version": content.VERSION, "combat_rules": combat_rules.RULES, "regions": content.REGIONS, "cities": content.CITIES, "stairs": content.STAIRS,
                "world_revision": getattr(content,"WORLD_REVISION",20), "landmasses": getattr(content,"LANDMASSES",[]),
                "ports": getattr(content,"PORTS",[]), "sea_routes": getattr(content,"SEA_ROUTES",[]),
                "magic_items": magic_items.metadata(),
                "skill_challenge_catalog": self.skill_challenge_metadata(),
                "terrain": content.TERRAIN, "terrain_detail": getattr(content,"TERRAIN_DETAIL",{}), "surfaces": content.SURFACES, "premium": content.PREMIUM,
                "elevations": content.ELEVATIONS, "waterways": content.WATERWAYS, "bridges": content.BRIDGES,
                "pois": content.POIS, "canyons": content.CANYONS, "rarities": loot_tables.RARITIES,
                "environment_trees": self.environment_trees(),
                "dungeons": content.DUNGEONS, "hunting_grounds": content.HUNTING_GROUNDS, "roads": content.ROADS, "safe_zones": content.SAFE_ZONES, "binding_stones": content.BINDING_STONES,
                "spells": content.SPELLS, "class_progression": progression_guide.catalog(), "default_hotbars": dnd_content.DEFAULT_HOTBARS, "hotbar_groups": dnd_content.hotbar_group_catalog(), "status_catalog": dnd_content.STATUS_SPECS, "runes": content.RUNES, "milestones": [{"level":v[0], "name":v[1], "description":v[2]} for v in content.MILESTONES],
                "width": WIDTH, "height": HEIGHT, "sites": [], "chests": [], "obstacles": OBSTACLES,
                "zones": ZONES, "npcs": NPCS, "landmarks": LANDMARKS, "quests": QUESTS,
                "enemy_types": inventory_rules.metadata_enemies(ENEMY_TYPES), "loot_hunts": content.LOOT_HUNTS, "spawn": SPAWN, "river": RIVER, "trail_gate": TRAIL_GATE, "weapons": WEAPONS,
                "nature_sites": [{k:v for k,v in s.items() if k not in ("text","hint_x","hint_y")} for s in self.nature_sites],
                "classes": CLASSES, "items": inventory_rules.metadata_items(ITEMS), "merchant": MERCHANT, "safe_zone": SAFE_ZONE,
                "pvp_rules": PVP_RULES, "rest_rules": REST_RULES, "potions": POTIONS, "inventory_cap": INVENTORY_CAP,
                "party_rules": {"max_members": PARTY_CAP, "range": PARTY_RANGE, "bonus_per_extra_member": .10,
                                "participation_seconds": 30, "max_level_ratio": 3},
                "abilities": {"offense": "PvE_and_unlocked_PvP", "druid_party_heal": "party_and_unlocked_PvP_support",
                              "pvp_safety_applies_to": ["weapon", "spell", "field", "companion"]}}

    def snapshot(self, for_player=None, public_players=None):
        pid = for_player.id if isinstance(for_player, Player) else str(for_player or "")
        now = self.now()
        viewer = self.players.get(pid)
        def visible(obj):
            return viewer is None or (same_floor(viewer, obj) and distance(viewer, obj) <= 1800)
        return {"type": "state", "tick": self.tick, "time": self.time,
                "skill_challenges": self.skill_challenge_state(viewer) if viewer else {},
                "players": [self.players[pid].public(now, self.time, True, self.parties.get(self.players[pid].party_id, [])) if entry["id"] == pid else entry for entry in public_players] if public_players is not None else
                           [p.public(now, self.time, p.id == pid, self.parties.get(p.party_id, [])) for p in self.players.values()],
                "companions": [c.public() for c in (*self.companions.values(),*self.familiars.values()) if visible(c)],
                "alarms": [dict(x=a["x"],y=a["y"],floor=a["floor"],remaining=max(0,a["until"]-now)) for owner,a in self.alarms.items() if owner==pid],
                "enemies": [e.public(now) for e in (self.nearby_enemies(viewer, 1800) if viewer else self.enemies.values()) if visible(e)], "world": dict(self.flags),
                "active_field_effects": [f.get("effect_id", "") for f in self.environment_fields()],
                "circle_fields": [self.circle_field_snapshot(f,now)
                    for f in getattr(self,'circle_spell_fields',[]) if f.get('until',0)>now and (viewer is None or same_floor(viewer,f) and point_distance(viewer,f)<=2200)],
                "effects": [dict(effect) for effect in self.effects if self.time-effect["time"] <= max(1.5,effect.get("duration",0)) and (viewer is None or (same_floor(viewer, effect) and point_distance(viewer, effect) <= 1800))]}

    def persist(self, extra_players=()):
        with self.db:
            for p in (*self.players.values(), *extra_players):
                self.save_player(p)
            self.db.execute("INSERT OR REPLACE INTO shared VALUES(1,?)", (json.dumps(self.flags),))

    def save_player(self, p):
        magic_items.maintain(p, self.now())
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)
        self.db.execute("UPDATE accounts SET data=? WHERE id=?", (json.dumps(p.save_data()), p.id))
        self.save_score(p)

    def starter(self, p):
        p.hotbar = [];dnd_content.sync_hotbar(p)
        p.inventory = [make_item(f"{p.class_id}_weapon_1"), make_item("druid_leather" if p.class_id=="druid" else "cloth")]
        p.equipment = {"weapon": p.inventory[0]["uid"], "armor": p.inventory[1]["uid"], "ring": ""}
        p.weapon = p.spec["weapon"]
        self.migrate_fighter(p, make_item)
        self.migrate_caster(p)
        skill_rules.normalize(p)
        self.migrate_druid_circle(p)
        self.migrate_wizard_school(p)
        self.migrate_martial(p)
        rest_rules.migrate(p,self.now())
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)

    def load_player(self, pid, name, ws, saved):
        p = Player(pid, name, ws)
        for attr in p.save_data():
            if attr in saved:
                setattr(p, attr, saved[attr])
        p.hp_rules_version=saved.get('hp_rules_version',0)
        if "class_id" not in saved:
            p.class_chosen = False
            p.class_id = "knight"
        self.migrate_dnd(p,saved)
        if "inventory" not in saved:
            self.starter(p)
        p.weapon = p.spec["weapon"]
        # Refresh canonical item stats without changing ownership or equipment UIDs.
        for bag in (p.inventory, p.depot):
            for item in bag:
                item.update(ITEMS.get(item["template"], {}))
        p.current_wall_time = self.now()
        magic_items.migrate(p, ITEMS)
        p.bonus_cooldown_until = max(p.bonus_cooldown_until, p.potion_cooldown_until)
        p.potion_cooldown_until = 0
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)
        self.migrate_fighter(p, make_item)
        self.migrate_caster(p)
        skill_rules.normalize(p)
        self.migrate_druid_circle(p)
        self.migrate_wizard_school(p)
        self.migrate_martial(p)
        rest_rules.migrate(p,self.now())
        refunded=combat_rules.migrate_hp(p)
        if refunded:self.caster_message(p,f'Przeliczono HP według klasy i Kondycji. Zwrócono punkty Witalności: {refunded}.')
        if "mana" not in saved:
            p.mana = p.max_mana
        p.hp, p.mana = min(p.hp, p.max_hp), min(p.mana, p.max_mana)
        # Existing dead characters retain death; v0.1 had no persistent timer.
        if p.hp <= 0 and not p.respawn_until:
            p.respawn_until = self.now() + 4
        # Old relic progression may have saved a character in an invalid tile.
        stranded = p.floor == 0 and getattr(content.WATER_MAP,"ocean_blocked",lambda *_:False)(p.x,p.y,18)
        p._shore_recovery_pending = stranded
        p._terrain_recovery_pending = (not stranded and p.floor == 0 and saved.get('world_revision',20) < 29
                                      and self.terrain_obstacle_at(p) and self.blocked_for(p,p.x,p.y))
        if stranded:
            self.environment_recover_shore(p)
        elif p._terrain_recovery_pending:
            self.recover_terrain_position(p)
        elif self.blocked_for(p,p.x,p.y) and max(p.combat_until,p.pvp_combat_until) <= self.now():
            p.x,p.y,p.floor = town_services.respawn_position(content,p.home_city)
        p.world_revision = saved.get("world_revision",18) if p._shore_recovery_pending or p._terrain_recovery_pending else getattr(content,"WORLD_REVISION",20)
        p.unjust_kills = [t for t in p.unjust_kills if t > self.now()-86400]
        p.aggressors = {k: t for k, t in p.aggressors.items() if t > self.now()}
        return p

    def terrain_obstacle_at(self,p):
        """Only new static relief can trigger the one-time geography migration."""
        if p.floor:return False
        return any(o.get('relief_theme') and intersects(p.x,p.y,o,18)
                   for cx in range(int((p.x-18)//256),int((p.x+18)//256)+1)
                   for cy in range(int((p.y-18)//256),int((p.y+18)//256)+1)
                   for o in self.obstacle_cells.get((0,cx,cy),()))

    def recover_terrain_position(self,p):
        """Move a pre-update save out of new relief locally, after combat ends."""
        if not getattr(p,'_terrain_recovery_pending',False) or not p.alive:return False
        if max(p.combat_until,p.pvp_combat_until)>self.now():return False
        if not self.terrain_obstacle_at(p) or not self.blocked_for(p,p.x,p.y):
            p._terrain_recovery_pending=False
            p.world_revision=getattr(content,'WORLD_REVISION',29)
            return False
        origin=(p.x,p.y)
        destination=None
        for radius in (32,64,96,128,192,256,384,512,768,1024):
            candidates=[(origin[0]+math.cos(i*math.tau/32)*radius,
                         origin[1]+math.sin(i*math.tau/32)*radius) for i in range(32)]
            destination=next((q for q in candidates if not self.blocked(*q,radius=18,floor=0)),None)
            if destination:break
        if destination is None:return False
        p.x,p.y=destination;p.dx=p.dy=0;p.input_time=-10
        p.world_revision=getattr(content,'WORLD_REVISION',29)
        p._terrain_recovery_pending=False
        self.caster_message(p,'Po zmianie terenu przeniesiono postać na pobliskie dostępne miejsce.')
        return True

    async def send(self, ws, message):
        if ws is not None and not ws.closed:
            try:
                await asyncio.wait_for(ws.send_json(message), timeout=1)
            except (ConnectionError, RuntimeError, asyncio.TimeoutError):
                await ws.close()

    async def broadcast(self, message):
        await asyncio.gather(*(self.send(p.ws, message) for p in tuple(self.players.values())))

    async def broadcast_states(self):
        now = self.now()
        public = [p.public(now, self.time, False, self.parties.get(p.party_id, [])) for p in self.players.values()]
        await asyncio.gather(*(self.send(p.ws, self.wire_snapshot(p, public)) for p in tuple(self.players.values()) if not p.disconnected))

    def wire_snapshot(self, p, public_players=None):
        packet = self.snapshot(p, public_players)
        if p.id not in self.compact_clients:
            return packet
        # Ordered WebSockets: send unchanged private catalogs only once per login.
        # Public actor fields always remain complete; legacy clients get full states.
        previous = self.owner_cache.setdefault(p.id, {})
        private_keys = ("quests", "discoveries", "inventory", "equipment", "depot", "skills", "runes", "mastery", "potions", "hotbar", "grouped_hotbar", "character_sheet", "spell_profiles", "favorite_spell", "attributes", "combat_log", "pending_level_ups", "potion_slots", "known_loot", "item_previews")
        own = next(entry for entry in packet["players"] if entry["id"] == p.id)
        for key in private_keys:
            encoded = json.dumps(own[key], ensure_ascii=False, separators=(",", ":"))
            if previous.get(key) == encoded:
                del own[key]
            else:
                previous[key] = encoded
        packet["owner_delta"] = True
        return packet

    async def notice(self, p, text):
        await self.send(p.ws, {"type": "notice", "text": text})

    async def error(self, ws, text):
        await self.send(ws, {"type": "error", "text": text})

    @staticmethod
    def password_hash(password, salt):
        return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)

    async def hello(self, ws, data):
        # UI22: passwords can prove ownership of an old character only after
        # Google verification. They are never an independent login method.
        await self.send(ws, {"type": "error", "code": "google_required",
            "text": "Wejdź przez Google, a następnie wybierz lub przypisz postać."})

    async def complete_login(self, ws, p, data):
        # All identity, ownership and capacity checks happen before this call.
        # Bind synchronously before the first send, including a reconnect while
        # the old character is still retained in combat.
        pid = str(p.id)
        p.ws = ws
        self.cancel_rest(p, "")
        p.pvp_safety, p.dx, p.dy, p.input_time = True, 0, 0, -10
        self.players[pid] = p
        self.owner_cache.pop(pid, None)
        self.compact_clients.discard(pid)
        if data.get("compact_state") is True:
            self.compact_clients.add(pid)
        self.persist()
        await self.send(ws, {"type": "welcome", "id": pid, "world": self.metadata(), "owner_deltas": pid in self.compact_clients})
        await self.send(ws, self.wire_snapshot(p))
        await self.notice(p, "Witaj w Przystani! Strażniczka Mira przy placu ma pierwsze zadanie: szczury na łące. Podejdź i otwórz dziennik (J / E).")

    def in_safe(self, p):
        return any(near(p, zone) for zone in content.SAFE_ZONES)

    def blocked(self, x, y, radius=RADIUS, floor=0, ignore_water=False, ignore_low=False):
        if x < radius or y < radius or x > WIDTH-radius or y > HEIGHT-radius:
            return True
        if floor != 0:
            for px, py in [(x-radius,y-radius),(x+radius,y-radius),(x-radius,y+radius),(x+radius,y+radius)]:
                rooms = self.room_cells.get((floor, int(px//512), int(py//512)), ())
                if not any(r["x"] <= px <= r["x"]+r["w"] and r["y"] <= py <= r["y"]+r["h"] for r in rooms):
                    return True
        for cx in range(int((x-radius)//256), int((x+radius)//256)+1):
            for cy in range(int((y-radius)//256), int((y+radius)//256)+1):
                if any(intersects(x, y, r, radius) for r in self.obstacle_cells.get((floor,cx,cy), []) if not (ignore_low and r.get('type') in ('rock','grove'))):
                    return True
        if self.environment_wall_blocked(x,y,radius,floor):return True
        if floor != 0:
            return False
        if ignore_water:return False
        if content.WATER_MAP.blocked(x, y, radius):
            return True
        if y-radius < RIVER["h"] and x+radius > RIVER["x"] and x-radius < RIVER["x"]+RIVER["w"]:
            if y-radius < RIVER["bridge_y"] or y+radius > RIVER["bridge_y"]+RIVER["bridge_h"]:
                return True
        return False

    def move(self, obj, dx, dy):
        if environment_rules.immobile(obj,self.now()) and not getattr(obj,'_environment_forced',False):return
        old_x,old_y=obj.x,obj.y
        parts = max(1, math.ceil(max(abs(dx), abs(dy))/10))
        def allowed(x, y):
            if self.blocked_for(obj,x,y):
                return False
            if (isinstance(obj, Player) or getattr(obj, "is_companion", False)) and obj.pvp_combat_until > self.now():
                for zone in content.SAFE_ZONES:
                    new_distance = math.hypot(x-zone["x"], y-zone["y"])
                    if obj.floor == 0 and new_distance <= zone["radius"] and new_distance < point_distance(obj, zone):
                        return False
            if isinstance(obj, Enemy) and obj.floor == 0 and any(math.hypot(x-zone["x"],y-zone["y"]) <= zone["radius"] for zone in content.SAFE_ZONES):
                return False
            return True
        for _ in range(parts):
            if allowed(obj.x+dx/parts, obj.y):
                obj.x += dx/parts
            if allowed(obj.x, obj.y+dy/parts):
                obj.y += dy/parts
        if isinstance(obj, Enemy):
            self.reindex_enemy(obj)
        if hasattr(self,'circle_note_movement'):self.circle_note_movement(obj,old_x,old_y)

    def line_clear(self, a, b):
        if not same_floor(a, b):
            return False
        steps = max(1, math.ceil(distance(a, b)/12))
        return all(not self.blocked(a.x+(b.x-a.x)*i/steps, a.y+(b.y-a.y)*i/steps, 2, floor=a.floor,ignore_water=True) for i in range(1, steps))

    def award(self, p, xp, gold):
        p.xp += int(xp)
        p.gold += int(gold)
        # Solve total XP cost algebraically with integer sqrt. No loop or level cap.
        # Cost of k levels: k * current_cost + 35*k*(k-1)/2.
        b = 2*xp_next(p.level)-35
        levels = max(0, (math.isqrt(b*b+280*p.xp)-b)//70)
        if levels:
            p.xp -= levels*xp_next(p.level)+35*levels*(levels-1)//2
            level_up.record(p, p.level+1, p.level+levels)
            p.level += levels
            p.hp = p.max_hp
            p.mana = p.max_mana

    def advance_kill_quests(self, p, enemy_kind):
        # Called only for eligible recipients of an authoritative kill reward.
        for quest in QUESTS:
            progress = p.quest_progress.get(quest["id"])
            if not progress or not progress.get("accepted") or progress.get("claimed"):
                continue
            for index, objective in enumerate(quest["objectives"]):
                if objective["type"] == "kill" and objective["target"] == enemy_kind:
                    progress["counts"][index] = min(objective["required"], progress["counts"][index]+1)

    def discover_landmarks(self, p):
        if not p.alive:
            return
        cx, cy = int(p.x//512), int(p.y//512)
        found = [landmark for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 for landmark in self.landmark_cells.get((p.floor, cx+dx, cy+dy), ())
                 if landmark["id"] not in p.discoveries and near(p, landmark)]
        if not found:
            return
        # The discovery marker and its reward commit together before another command.
        with self.db:
            for landmark in found:
                p.discoveries.append(landmark["id"])
                self.award(p, landmark["reward"]["xp"], landmark["reward"]["gold"])
            self.save_player(p)

    async def quest_command(self, p, kind, data):
        quest_id = data.get("quest_id")
        quest = next((q for q in QUESTS if q["id"] == quest_id), None) if isinstance(quest_id, str) else None
        if quest is None:
            return await self.notice(p, "Nieznane zadanie.")
        npc = next(n for n in NPCS if n["id"] == quest["npc_id"])
        if not p.alive or not near(p, npc):
            return await self.notice(p, f"Podejdź do postaci: {npc['name']}.")
        entry = next(q for q in p.quest_entries() if q["id"] == quest_id)
        if kind == "quest_accept":
            if entry["status"] != "available":
                return await self.notice(p, "To zadanie jest już przyjęte albo wymaga ukończenia wcześniejszej wyprawy.")
            p.quest_progress[quest_id] = {"accepted": True, "claimed": False, "counts": [0]*len(quest["objectives"])}
            with self.db:
                self.save_player(p)
            return await self.notice(p, f"Przyjęto zadanie: {quest['title']}. Cel znajdziesz w dzienniku (J).")
        if entry["status"] != "ready":
            return await self.notice(p, "Najpierw wykonaj wszystkie cele. Nagrodę można odebrać tylko raz.")
        reward = quest["reward"]
        template = reward.get("item")
        if template and template.startswith("class_weapon_"):
            if not p.class_chosen:
                return await self.notice(p, "Najpierw wybierz klasę swojej dawnej postaci, aby otrzymać właściwą broń.")
            template = f"{p.class_id}_weapon_{template.rsplit('_', 1)[1]}"
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)
        if len(p.inventory) + int(bool(template)) + inventory_rules.slots_needed(p, reward.get("potions", {})) > INVENTORY_CAP:
            return await self.notice(p, "Zwolnij miejsce w plecaku. Gwarantowana nagroda pozostaje u zleceniodawcy.")
        # Validate everything before mutation. One SQLite commit includes claim, XP, gold and item.
        with self.db:
            p.quest_progress[quest_id]["claimed"] = True
            self.award(p, reward["xp"], reward["gold"])
            if template:
                p.inventory.append(make_item(template))
            for key, amount in reward.get("potions", {}).items():
                inventory_rules.add(p, key, amount, make_item, INVENTORY_CAP)
            self.save_player(p)
        item_text = f" · {ITEMS[template]['name']}" if template else ""
        await self.notice(p, f"Ukończono: {quest['title']} · +{reward['xp']} PD · +{reward['gold']} złota{item_text}")

    def combat_effect(self, p, kind, target=None, radius=0, duration=.32):
        # Capture world coordinates now. Walking later changes facing, never this aim.
        tx, ty = (target.x, target.y) if target is not None else (p.x, p.y)
        d = math.hypot(tx-p.x, ty-p.y)
        if d > .001:
            p.attack_facing = [(tx-p.x)/d, (ty-p.y)/d]
        self.effect_serial += 1
        effect = {"id": f"fx{self.effect_serial}", "kind": kind, "source_id": p.id,
                  "target_id": target.id if target is not None else "", "floor": p.floor, "x": p.x, "y": p.y,
                  "target_x": tx, "target_y": ty, "time": self.time, "duration": duration, "radius": radius}
        self.effects = [e for e in self.effects if self.time-e["time"] <= max(1.5,e.get("duration",0))]
        self.effects.append(effect)
        return effect

    def basic_effect(self, p, target):
        kind = "sword" if equipment_rules.melee(p) else "magic_bolt" if equipment_rules.is_focus(equipment_rules.weapon(p)) else "arrow"
        return self.combat_effect(p, kind, target, duration=.22 if kind == "sword" else .32)

    def cancel_rest(self, p, message="Odpoczynek przerwany."):
        if not getattr(p, "rest_state", None):
            return False
        p.rest_state = {}
        if message and not p.disconnected:
            self.caster_message(p, message)
        return True

    async def start_rest(self, p, kind="short", recover=True):
        if not isinstance(kind, str) or kind not in ("short", "long"):
            return await self.notice(p, "Wybierz krótki albo długi odpoczynek.")
        if p.rest_state:
            return await self.notice(p, "Odpoczynek już trwa.")
        now = self.now()
        reason, remaining = rest_block_status(p, now, self.time, kind)
        if reason:
            messages = {"dead": "Nie możesz odpoczywać po śmierci.",
                        "disconnected": "Odpoczynek wymaga połączenia z grą.",
                        "moving": "Zatrzymaj się, aby rozpocząć odpoczynek.",
                        "channel": "Najpierw zakończ rzucanie rytuału.",
                        "cooldown": f"Następny odpoczynek za {math.ceil(remaining)} s.",
                        "combat_pvp": f"Odpoczynek po walce PvP za {math.ceil(remaining)} s.",
                        "combat_pve": f"Odpoczynek po walce za {math.ceil(remaining)} s."}
            return await self.notice(p, messages[reason])
        if kind == "long" and REST_RULES['long_safe_only'] and not self.in_safe(p):
            return await self.notice(p, "Długi odpoczynek wymaga bezpiecznej strefy miasta. W terenie wybierz krótki.")
        seconds = REST_RULES[kind+"_seconds"]
        self.stop_auto(p)
        p.rest_state = {"kind": kind, "total": seconds, "until": now+seconds,
                        "x": p.x, "y": p.y, "floor": p.floor, "recover": bool(recover)}
        await self.notice(p, f'{"Krótki" if kind=="short" else "Długi"} odpoczynek · {seconds} s. Ruch lub akcja przerywa odpoczynek.')

    def tick_rest(self, p):
        rest = p.rest_state
        if not rest:
            return
        now = self.now()
        reason, _ = rest_block_status(p, now, self.time)
        if (reason or (p.x, p.y, p.floor) != (rest["x"], rest["y"], rest["floor"])
                or (rest["kind"] == "long" and REST_RULES['long_safe_only'] and not self.in_safe(p))):
            self.cancel_rest(p)
            return
        if now < rest["until"]:
            return
        p.rest_state = {}
        summary=rest_rules.finish(p,rest["kind"],self.combat_rng,rest.get("recover",True))
        attunement_message = magic_items.finish_rest(p, rest)
        self.on_circle_rest(p,rest["kind"])
        self.wizard_school_rest(p,rest["kind"])
        self.martial_rest(p,rest["kind"])
        p.rest_resources[rest["kind"]+"_ready"]=now+REST_RULES[rest["kind"]+"_cooldown_seconds"]
        p.rest_cooldown_until=0
        if rest["kind"]=="long":
            self.break_concentration(p);p.form="";p.form_until=0
            p.buffs={};p.druid_circle_runtime={}
        with self.db:
            self.save_player(p)
        self.combat_effect(p, "heal", radius=65, duration=.9)
        if attunement_message:self.caster_message(p, attunement_message)
        self.caster_message(p, "Długi odpoczynek: pełne zdrowie, mana i użycia zdolności." if rest["kind"]=="long" else f'Krótki odpoczynek: +{summary["hp"]:g} HP ({summary["hit_dice"]} kości), +{summary["mana"]:g} many; odnowiono zdolności krótkiego odpoczynku.')

    def begin_action(self, p, bonus=False):
        self.cancel_rest(p)
        return super().begin_action(p, bonus=bonus)

    def tag(self, p, pvp=False):
        self.cancel_rest(p)
        p.combat_until = max(p.combat_until, self.now()+PVP_RULES["combat_seconds"])
        if pvp:
            p.pvp_combat_until = max(p.pvp_combat_until, p.combat_until)

    def grant_loot(self, p, drops, source_kind=None):
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)
        names, overflow = [], False
        for kind, template in drops:
            if kind == "potion":
                delivered = inventory_rules.add(p, template, 1, make_item, INVENTORY_CAP)
            else:
                delivered = len(p.inventory) < INVENTORY_CAP
                if delivered:p.inventory.append(make_item(template))
            if delivered:
                names.append(ITEMS[template]["name"])
                if source_kind:inventory_rules.discover(p, template, source_kind, ENEMY_TYPES)
            else:overflow = True
        inventory_rules.sync(p, POTIONS)
        return (" · Łup: "+", ".join(names) if names else "")+(" · Brak miejsca: część łupu przepadła." if overflow else "")

    def reward_groups(self, enemy):
        # Only recent damage contributors qualify; nearby party support shares with them.
        candidates = [p for pid, when in enemy.contributors.items()
                      if self.time-when <= 30 and (p := self.players.get(pid)) and p.alive
                      and not p.disconnected and same_floor(p, enemy) and distance(p, enemy) <= PARTY_RANGE]
        groups, seen = [], set()
        for p in candidates:
            if p.id in seen:
                continue
            members = [p]
            if p.party_id:
                members = [q for pid in self.parties.get(p.party_id, [])
                           if (q := self.players.get(pid)) and q.alive and not q.disconnected
                           and same_floor(q, enemy) and distance(q, enemy) <= PARTY_RANGE and not self.in_safe(q)
                           and max(q.level, p.level) <= 3*min(q.level, p.level)]
                if p not in members:
                    members.append(p)
            members = [q for q in members if q.id not in seen]
            # The 3:1 limit applies to every pair inside the rewarded subset.
            eligible, low, high = [], p.level, p.level
            for q in sorted(members, key=lambda q: abs(q.level-p.level)):
                if max(high, q.level) <= 3*min(low, q.level):
                    eligible.append(q)
                    low, high = min(low, q.level), max(high, q.level)
            members = eligible
            if members:
                groups.append(members)
                seen.update(q.id for q in members)
        return groups

    async def defeat(self, enemy):
        if not enemy.alive:
            return
        enemy.alive, enemy.hp = False, 0
        enemy.respawn_at = self.time+ENEMY_TYPES[enemy.kind]["respawn"]
        self.chasing_enemies.pop(enemy.id, None)
        self.recovering_enemies.pop(enemy.id, None)
        self.reindex_enemy(enemy)  # lazy respawn is discoverable at the original spawn
        if enemy.kind == "boss":
            self.flags["boss_defeated"], self.flags["event_active"] = True, False
        groups = self.reward_groups(enemy)
        notices = []
        spec = ENEMY_TYPES[enemy.kind]
        # One base reward pool across independent groups; parties add 10% per extra member.
        with self.db:
            for group in groups:
                total = len(groups)*len(group)
                xp = max(1, math.floor(spec["xp"]*(1+.1*(len(group)-1))/total))
                gold = max(1, spec["gold"]//total)
                for p in group:
                    self.award(p, xp, gold)
                    p.kills += 1
                    p.soul = min(200 if p.promoted else 100, p.soul+2)
                    self.advance_kill_quests(p, enemy.kind)
                    if enemy.kind == "boss" or spec.get("boss"):
                        p.boss_kills += 1
                    detail = f"{spec['name']}: +{xp} PD · +{gold} złota"
                    detail += self.grant_loot(p, loot_tables.roll(p.class_id, spec, self.rng), source_kind=enemy.kind)
                    self.save_player(p)
                    notices.append((p, detail))
            self.db.execute("INSERT OR REPLACE INTO shared VALUES(1,?)", (json.dumps(self.flags),))
        enemy.contributors.clear()
        for p, text in notices:
            await self.notice(p, text)

    def pvp_error(self, p, target):
        if not p.alive or target is None or target.id == p.id or not target.alive:
            return "Wskaż żywą postać przeciwnika."
        if not same_floor(p,target):
            return "Cel PvP jest na innym piętrze."
        if p.pvp_safety:
            return "Najpierw świadomie wyłącz ochronę przed atakowaniem graczy."
        if p.level < PVP_RULES["min_level"] or target.level < PVP_RULES["min_level"]:
            return "PvP jest dostępne od poziomu 8; początkujący są chronieni."
        if self.in_safe(p) or self.in_safe(target):
            return "Przystań jest bezpieczna: nie można tu walczyć."
        if p.party_id and p.party_id == target.party_id:
            return "Nie można atakować członków drużyny."
        return ""

    def remember_attacker(self, enemy, p):
        enemy.contributors[p.id] = self.time
        self.provoke_enemy(enemy, p)

    def selected_enemy(self, p, enemy_id, attack_range):
        enemy = self.enemies.get(enemy_id) if isinstance(enemy_id, str) else None
        if enemy and enemy.alive and same_floor(p, enemy) and distance(p, enemy) <= attack_range and self.line_clear(p, enemy):
            return enemy
        return None

    async def attack(self, p, target_id=None, enemy_id=None):
        return await self.dnd_attack(p,target_id,enemy_id)

    async def ability(self, p, enemy_id=None, target_id=None):
        return await self.cast_spell(p,dnd_content.favorite_spell(p),enemy_id,target_id)

    async def interact(self, p):
        if not p.alive:
            return
        if await self.nature_interaction(p):return
        sites = [site for site in content.POIS if near(p, site) and self.line_clear(p, SimpleNamespace(**site))]
        if sites:
            site = min(sites, key=lambda s: point_distance(p, s))
            now = self.now()
            if p.combat_until > now:
                return await self.notice(p, "Najpierw zakończ walkę, aby skorzystać z tego miejsca.")
            if p.level < site["min_level"]:
                return await self.notice(p, f'To miejsce wymaga poziomu {site["min_level"]}.')
            remaining = p.site_cooldowns.get(site["id"], 0)-now
            if remaining > 0:
                return await self.notice(p, f'Miejsce odnawia się jeszcze przez {math.ceil(remaining)} s.')
            action = site["action"]
            duration, detail = 300, ""
            if action == "cache":
                if len(p.inventory) > INVENTORY_CAP-3:
                    return await self.notice(p, "Skrytka wymaga 3 wolnych miejsc w plecaku.")
                drops = loot_tables.cache(p.class_id, site["min_level"], content.TIER_LEVELS, self.rng)
                detail = self.grant_loot(p, drops); duration = 1800
            elif action == "spring":
                p.hp, p.mana = p.max_hp, p.max_mana
                duration = 180; detail = " · Odnowiono zdrowie i manę."
            elif action == "wind":
                p.wind_until = now+90; detail = " · Wiatr: +15% szybkości przez 90 s."
            elif action == "ward":
                p.ward_until = now+90; detail = " · Kamienna osłona: −12% obrażeń od potworów przez 90 s."
            p.site_cooldowns[site["id"]] = now+duration
            self.combat_effect(p, "heal" if action == "spring" else "bulwark", radius=65, duration=.9)
            self.persist()
            return await self.notice(p, site["name"]+detail)
        if self.merchant_near(p):
            return await self.start_rest(p, "long")
        await self.notice(p, "Kupiec w Przystani sprzedaje mikstury, skupuje sprzęt i pozwala odpocząć.")

    async def inventory_command(self, p, kind, data):
        inventory_rules.ensure(p, ITEMS, POTIONS, make_item)
        if not p.alive:
            return
        uid = data.get("uid")
        item = next((i for i in p.inventory if i["uid"] == uid), None)
        if kind == "potion_bind":
            slot = data.get("slot")
            template = data.get("item", "")
            if slot != "q" or not isinstance(template, str):
                return await self.notice(p, "Nieznany skrót mikstury.")
            if template and (template not in POTIONS or not inventory_rules.count(p, template) or p.level < POTIONS[template].get("min_level", 1)):
                return await self.notice(p, "Wybierz posiadaną miksturę odpowiednią dla swojego poziomu.")
            p.potion_slots[slot] = template
        elif kind == "equip":
            if item is None:
                return await self.notice(p, "Nie masz tego przedmiotu.")
            spec = ITEMS[item["template"]]
            if spec["slot"] not in ("weapon", "armor", "ring", "shield"):
                return await self.notice(p, "Trofeum można sprzedać lub przechować; nie jest wyposażeniem.")
            equip_error=equipment_rules.check_equip(p,spec)
            if equip_error:return await self.notice(p,equip_error)
            self.cancel_channel(p)
            if spec["slot"] == "shield" and fighter_rules.two_handed(p):
                return await self.notice(p, "Najpierw wybierz broń jednoręczną lub chwyt jednorącz.")
            if spec["slot"] == "weapon":
                p.weapon_grip = "one"
                if spec.get("two_handed"):
                    p.equipment["shield"] = ""
            p.equipment[spec["slot"]] = item["uid"]
            if not equipment_rules.shillelagh_applies(p):p.buffs.pop("shillelagh",None)
        elif kind == "unequip":
            if p.form:return await self.notice(p,"Zmień wyposażenie po zakończeniu przemiany.")
            self.cancel_channel(p)
            slot = data.get("slot")
            if slot not in ("weapon", "armor", "ring", "shield"):
                return await self.notice(p, "Nieznane miejsce wyposażenia.")
            p.equipment[slot] = ""
            if slot=="weapon":p.buffs.pop("shillelagh",None)
        elif kind == "sell":
            if not merchant_at(p, data.get("npc_id")) or p.combat_until > self.now():
                return await self.notice(p, "Sprzedaż jest dostępna przy kupcu, poza walką.")
            if item is None or uid in p.equipment.values():
                return await self.notice(p, "Sprzedawać można tylko posiadany, niezałożony sprzęt.")
            quantity = data.get("quantity", 1)
            if type(quantity) is not int or not 1 <= quantity <= int(item.get("quantity", 1)):
                return await self.notice(p, "Podaj posiadaną liczbę przedmiotów.")
            if quantity == int(item.get("quantity", 1)):p.inventory.remove(item)
            else:item["quantity"] -= quantity
            p.gold += ITEMS[item["template"]]["value"] * quantity
        elif kind == "buy":
            if not merchant_at(p, data.get("npc_id")) or p.combat_until > self.now():
                return await self.notice(p, "Podejdź do kupca poza walką.")
            kind_id = data.get("item")
            spec = ITEMS.get(kind_id) if isinstance(kind_id, str) else None
            seller = merchant_at(p, data.get("npc_id"))
            if not seller or kind_id not in seller.get("stock", []):
                return await self.notice(p, "Ten kupiec nie sprzedaje takiego towaru. Sprawdź jego miejscowy asortyment.")
            if spec is None or "price" not in spec or p.level < spec.get("min_level",1) or p.gold < spec["price"]:
                return await self.notice(p,"Nieznany towar, za niski poziom lub za mało złota.")
            if spec.get("slot") == "potion":
                if not inventory_rules.add(p,kind_id,1,make_item,INVENTORY_CAP):
                    return await self.notice(p,"Zwolnij miejsce w plecaku na mikstury.")
            else:
                if len(p.inventory)>=INVENTORY_CAP:return await self.notice(p,"Zwolnij miejsce w plecaku.")
                p.inventory.append(make_item(kind_id))
            p.gold -= spec["price"]
        elif kind == "potion":
            if "slot" in data and data["slot"] != "q":
                return
            kind_id = p.potion_slots.get("q", "") if "slot" in data else data.get("item")
            spec = POTIONS.get(kind_id) if isinstance(kind_id, str) else None
            if spec is None or p.level < spec.get("min_level", 1) or not p.potions.get(kind_id):
                return
            if environment_rules.actions_blocked(p,self.now()) or p.casting_channel:
                return await self.notice(p, "Nie możesz teraz wypić mikstury.")
            if self.now() < p.bonus_cooldown_until:
                return await self.notice(p, "Mikstura wymaga wolnej akcji dodatkowej.")
            attr, maximum = "hp", p.max_hp
            if getattr(p, attr) >= maximum:
                return
            self.begin_action(p, bonus=True)
            inventory_rules.consume(p, kind_id)
            restored = combat_rules.roll_damage(self.combat_rng,spec["dice"]) if "dice" in spec else {"damage":spec["restore"],"damage_dice":str(spec["restore"]),"damage_rolls":[]}
            amount=min(maximum-getattr(p,attr),restored["damage"])
            setattr(p, attr, getattr(p, attr)+amount)
            self.report_roll(p,p,{**restored,"check":"healing","hit":True,"healing":amount,"damage":0},spec["name"],p)
            p.potion_cooldown_until = 0  # Legacy field; potions now share the bonus action.
        inventory_rules.sync(p, POTIONS)
        self.persist()

    def leave_party(self, p):
        leader = p.party_id
        members = self.parties.get(leader, [])
        if p.id in members:
            members.remove(p.id)
        p.party_id = ""
        if not members:
            self.parties.pop(leader, None)
        elif leader == p.id:
            self.parties.pop(leader, None)
            new_leader = members[0]
            self.parties[new_leader] = members
            for pid in members:
                if pid in self.players:
                    self.players[pid].party_id = new_leader
            self.invites = {k: v for k, v in self.invites.items() if v[0] != leader}

    async def party_command(self, p, kind, data):
        now = self.now()
        if kind == "party_leave":
            self.leave_party(p)
            return await self.notice(p, "Opuściłeś drużynę.")
        if kind == "party_invite":
            target = self.players.get(str(data.get("target_id")))
            if not target or target.id == p.id or target.disconnected or target.party_id:
                return await self.notice(p, "Wskaż dostępnego gracza bez drużyny.")
            if p.party_id and p.party_id != p.id:
                return await self.notice(p, "Tylko przywódca może zapraszać.")
            if len(self.parties.get(p.id, [p.id])) >= PARTY_CAP:
                return await self.notice(p, "Drużyna liczy już 4 osoby.")
            self.invites[(target.id, p.id)] = (p.id, now+30)
            await self.send(target.ws, {"type": "party_invite", "leader_id": p.id, "name": p.name})
            return await self.notice(p, "Zaproszenie wysłane; wygasa za 30 sekund.")
        leader_id = str(data.get("leader_id"))
        invite = self.invites.pop((p.id, leader_id), None)
        leader = self.players.get(leader_id)
        if not invite or invite[1] <= now or not leader or leader.disconnected or p.party_id:
            return await self.notice(p, "Zaproszenie jest nieważne.")
        if leader.party_id and leader.party_id != leader.id:
            return await self.notice(p, "Przywódca zmienił drużynę.")
        members = self.parties.setdefault(leader.id, [leader.id])
        if len(members) >= PARTY_CAP:
            return await self.notice(p, "Drużyna jest pełna.")
        members.append(p.id)
        leader.party_id = p.party_id = leader.id
        await self.notice(p, "Dołączyłeś do drużyny. PD dzielicie w promieniu 650, przy różnicy poziomów najwyżej 3:1.")

    async def on_packet(self, ws, data):
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            return await self.error(ws, "Nieprawidłowy komunikat.")
        kind = data["type"]
        if kind == "hello":
            return await self.hello(ws, data)
        if kind == "ranking":
            return await self.send(ws, self.ranking())
        if kind == "ping":
            return await self.send(ws, {"type": "pong"})
        p = next((p for p in self.players.values() if p.ws is ws), None)
        if p is None:
            return await self.error(ws, "Najpierw zaloguj postać.")
        if kind in ("ability_build", "skill_train", "origin_feat"):
            return await self.development_command(p,kind,data)
        if kind == "skill_challenge":
            return await self.handle_skill_challenge(p,data)
        if kind == "boat":
            return await self.boat_command(p, data)
        if kind == "magic_item":
            return await magic_items.command(self, p, data)
        if kind == "rest":
            return await self.start_rest(p, data.get("kind", "short"),data.get("recover",True) is not False)
        if kind == "rest_cancel":
            self.cancel_rest(p)
            return
        if kind == "dismiss_level_up":
            if level_up.dismiss(p, data.get("id")):
                self.persist()
            return
        if kind == "cast_circle_spell":
            if environment_rules.incapacitated(p,self.now()):return
            return await self.cast_circle_spell(p,data.get("spell"),data.get("enemy_id"),data.get("target_id"),data.get("options"))
        if kind == "circle_spell_action":return await self.circle_spell_action(p,data.get("action"),data)
        if kind == "environment_action":return await self.environment_action(p,data.get("action"),data.get("enabled"),data.get("enemy_id"),data.get("target_id"))
        if kind == "wizard_school":return await self.select_wizard_school(p,data.get("school"))
        if kind == "wizard_school_action":return await self.wizard_school_command(p,data)
        if kind == "martial_choice":return await self.select_martial(p,data)
        if kind == "martial_action":return await self.martial_command(p,data)
        if kind == "druid_circle":return await self.select_druid_circle(p,data.get("circle"),data.get("land","arid"))
        if kind == "circle_command":return await self.circle_command(p,data.get("action"),data.get("value"))
        if kind == "primal_order":return await self.select_primal_order(p,data.get("order"))
        if kind == "training_feat":
            if type(data.get("expected_spent")) is not int:return await self.notice(p,"Odśwież kartę postaci przed wyborem atutu.")
            return await self.choose_training_feat(p,data.get("feat"),data.get("ability",''),data.get("abilities"),data["expected_spent"])
        if kind == "ritual":return await self.start_caster_channel(p,data.get("spell_id"),ritual=True)
        if kind == "channel_cancel":self.cancel_channel(p);return
        if kind == "familiar_command":return await self.familiar_command(p,data.get("mode"))
        if kind == "nature_interact":return await self.nature_interaction(p,data.get("id"))
        if kind == "fighting_style":
            return await self.select_fighting_style(p,data.get("style"))
        if kind == "weapon_grip":
            return await self.set_weapon_grip(p,data.get("grip"))
        if kind == "select_target":
            return await self.select_combat_target(p,data)
        if kind == "spell_power":
            if not spell_scaling.choose_circle(p, data.get("spell_id"), data.get("circle")):
                return await self.notice(p, "Wybierz dostępny krąg tego czaru.")
            with self.db:self.save_player(p)
            return
        if kind == "escape_restraint":
            return await self.escape_restraint(p,data.get("target_id"))
        if kind == "stop_concentration":
            self.break_concentration(p)
            p.pending_spell = {}
            return
        if kind == "hotbar":
            if data.get("grouped") is True:
                return await self.bind_grouped_spell(p,data.get("slot"),data.get("spell_id"))
            return await self.bind_spell(p,data.get("slot"),data.get("spell_id"))
        if kind == "auto_pause":
            if type(data.get("paused")) is bool:
                p.auto_enabled = not data["paused"] and bool(p.auto_enemy_id or p.auto_target_id)
                if data["paused"]:p.pending_spell={}
            return
        if kind == "input":
            x, y = data.get("x"), data.get("y")
            if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e6 for v in (x, y)):
                return await self.error(ws, "Nieprawidłowy kierunek ruchu.")
            norm = max(1, math.hypot(x, y))
            p.dx, p.dy, p.input_time = x/norm, y/norm, self.time
            if x or y:
                self.cancel_rest(p)
                self.cancel_channel(p)
                p.facing = [x/norm, y/norm]
        elif kind == "premium_demo":
            enabled = data.get("enabled")
            if type(enabled) is not bool:
                return await self.notice(p, "Wybierz włączenie lub wyłączenie symulacji premium.")
            now = self.now()
            if enabled and p.premium_demo_until <= now:
                p.premium_demo_until = now + 30*86400
            elif not enabled:
                p.premium_demo_until = 0
            with self.db:
                self.save_player(p)
            await self.notice(p, "Premium testowe: +20% szybkości przez 30 dni. Brak opłat i automatycznego odnowienia." if enabled else "Symulacja premium wyłączona.")
        elif kind == "attack":
            if "enemy_id" in data and (not isinstance(data["enemy_id"], str) or not data["enemy_id"]):
                return await self.notice(p, "Nieprawidłowy cel potwora.")
            await self.attack(p, data.get("target_id"), data.get("enemy_id"))
        elif kind == "ability":
            if "enemy_id" in data and (not isinstance(data["enemy_id"], str) or not data["enemy_id"]):
                return await self.notice(p, "Nieprawidłowy cel potwora.")
            await self.ability(p, data.get("enemy_id"), data.get("target_id"))
        elif kind in ("cast", "rune_use", "rune_craft", "rune_buy", "descend", "travel", "promote", "bless", "mastery", "mastery_reset", "bank_deposit", "bank_withdraw", "depot_store", "depot_take", "bind_city"):
            await self.expansion_command(p, kind, data)
        elif kind in ("quest_accept", "quest_claim"):
            await self.quest_command(p, kind, data)
        elif kind in ("equip", "unequip", "sell", "buy", "potion", "potion_bind"):
            await self.inventory_command(p, kind, data)
        elif kind == "pvp_safety":
            if type(data.get("enabled")) is not bool:
                return await self.error(ws, "Ochrona wymaga true albo false.")
            p.pvp_safety = data["enabled"]
            if p.pvp_safety:self.cancel_player_hostility(p)
            elif p.auto_target_id:
                target=self.players.get(p.auto_target_id)
                p.auto_enabled=not bool(self.pvp_error(p,target))
            with self.db:self.save_player(p)
            await self.notice(p, "Ataki, czary i towarzysz nie atakują już graczy. Kary i czas walki pozostają." if p.pvp_safety else "PvP odblokowane: broń, czary, obszary i wilk. Obszar może trafić inne osoby; agresja podlega karom.")
        elif kind.startswith("party_") and kind in ("party_invite", "party_accept", "party_leave"):
            await self.party_command(p, kind, data)
        elif kind == "choose_class":
            class_id = data.get("class_id")
            if (p.class_chosen or not p.alive or not self.in_safe(p) or p.combat_until > self.now()
                    or not isinstance(class_id, str) or class_id not in CLASSES):
                return await self.notice(p, "Jednorazowy wybór klasy przysługuje dawnej postaci w Przystani, poza walką.")
            if len(p.inventory) >= INVENTORY_CAP and not any(i["template"].endswith("_weapon_1") for i in p.inventory):
                return await self.notice(p, "Zwolnij miejsce w plecaku na broń nowej klasy.")
            p.class_id, p.class_chosen = class_id, True
            skill_rules.normalize(p)
            # Replace only the zero-bonus starter weapon; keep all other earned gear.
            old_starter = next((i for i in p.inventory if i["template"].endswith("_weapon_1")), None)
            if old_starter:
                p.inventory.remove(old_starter)
                if p.equipment.get("weapon") == old_starter["uid"]:
                    p.equipment["weapon"] = ""
            new_item = make_item(f"{class_id}_weapon_1")
            if len(p.inventory) < INVENTORY_CAP:
                p.inventory.append(new_item)
                p.equipment["weapon"] = new_item["uid"]
            p.hotbar = [];dnd_content.sync_hotbar(p)
            p.weapon, p.hp, p.mana = p.spec["weapon"], p.max_hp, p.max_mana
            self.persist()
            await self.notice(p, f"Klasa wybrana na stałe: {p.spec['name']}.")
        elif kind == "interact":
            await self.interact(p)
        elif kind in ("weapon", "relic"):
            await self.notice(p, "Relikty wycofano. Broń i umiejętność wynikają z klasy; sprzęt zmieniasz w plecaku.")
        elif kind == "chat":
            text = data.get("text")
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 160:
                return await self.error(ws, "Wiadomość musi mieć 1–160 znaków.")
            if self.time-p.chat_at < 1.5:
                return await self.error(ws, "Poczekaj chwilę przed kolejną wiadomością.")
            text = "".join(c for c in text.strip() if c.isprintable())
            if not text:
                return await self.error(ws, "Pusta wiadomość.")
            self.environment_reveal(p,"Mówienie zdradza kryjówkę.")
            p.chat_at = self.time
            p.speech_text, p.speech_until = text, self.time+6
            await self.broadcast({"type": "chat", "id": p.id, "name": p.name, "text": text})
        else:
            await self.error(ws, "Nieznana komenda.")

    def damage_player(self, p, damage, killer=None, unjust=False, rolled=False, damage_type="bludgeoning", damage_components=None, is_attack=False, source=None, is_spell=False, unavoidable=False):
        if not p.alive:
            return
        now = self.now()
        if getattr(p,"is_companion",False):
            p.hp=max(0,p.hp-max(0,int(damage)));self.tag(p)
            return
        p.current_wall_time=now
        # Rolled combat uses KP for defense; do not subtract the old armor twice.
        def resist(amount, kind):
            amount=max(0,int(amount)-equipment_rules.heavy_armor_reduction(p,kind,is_attack=is_attack))
            amount=magic_items.reduce_damage(p,amount,kind,self.combat_rng)
            amount=int(amount*combat_rules.resistance_multiplier(p,kind))
            return amount
        # Separate mixed damage (Ice Storm, Meteor Swarm, Hunter's Mark) before resistance.
        if unavoidable:
            actual = max(0, int(damage))
        elif damage_components is not None:
            grouped = {}
            for component in damage_components:
                kind = component['type']
                grouped[kind] = grouped.get(kind,0)+component['damage']
            actual = sum(resist(amount,kind) for kind,amount in grouped.items())
        else:
            actual = resist(damage,damage_type)
        if is_spell and not unavoidable and self.wizard_spell_resistance(p):actual//=2
        if actual>0:
            self.tag(p,killer is not None)
            if killer is not None:
                p.last_pvp_attacker=killer.id;p.last_pvp_unjust=bool(unjust)
                p.last_pvp_hit_until=now+PVP_RULES["combat_seconds"]
        if not unavoidable:actual=self.wizard_absorb_damage(p,actual,source or killer)
        if actual<=0:return
        damage_received=actual
        self.cancel_channel(p)
        self.concentration_damage(p,actual)
        if not unavoidable and p.temp_hp>0:
            absorbed=min(p.temp_hp,actual);p.temp_hp-=absorbed;actual-=absorbed
            # Losing temporary HP does not end a 2024 Wild Shape.
        if not unavoidable and p.bulwark_until > now:
            actual *= .5
        if not unavoidable and killer is None and p.ward_until > now:
            actual *= .88
        self.tag(p, killer is not None)
        if killer is not None:
            p.last_pvp_attacker = killer.id
            p.last_pvp_unjust = bool(unjust)
            p.last_pvp_hit_until = now+PVP_RULES["combat_seconds"]
        train(p, "shielding")
        p.hp = max(0, p.hp-actual)
        self.circle_spell_damage_received(p,damage_received,source or killer)
        if p.alive:
            return
        magic_items.on_death(p)
        # A monster finishing a recently assaulted victim does not erase the crime.
        # Resolve offline attackers from their latest save if their avatar already died.
        offline_killer = False
        if killer is None and p.last_pvp_hit_until > now and p.last_pvp_attacker:
            killer = self.players.get(p.last_pvp_attacker)
            if killer is None:
                row = self.db.execute("SELECT name,data FROM accounts WHERE id=?", (p.last_pvp_attacker,)).fetchone()
                if row:
                    killer = self.load_player(p.last_pvp_attacker, row[0], None, json.loads(row[1]))
                    offline_killer = True
            unjust = p.last_pvp_unjust
        was_red = p.skull(now) == "red"
        protection = .5 if p.blessed and not was_red else 1
        p.blessed = False
        p.haste_until = 0
        p.wind_until = p.ward_until = 0
        p.gold -= math.ceil(p.gold*(.20 if was_red else .05)*protection)
        p.xp -= math.ceil(p.xp*(.20 if was_red else .10)*protection)
        if was_red:
            loose = [i for i in p.inventory if i["uid"] not in p.equipment.values()]
            if loose:
                item = self.rng.choice(loose)
                p.inventory.remove(item)
                if killer and len(killer.inventory) < INVENTORY_CAP:
                    killer.inventory.append(item)
        if killer and unjust:
            killer.unjust_kills = [t for t in killer.unjust_kills if t > now-86400]+[now]
            if len(killer.unjust_kills) >= 3:
                killer.red_until = now+86400
        p.last_pvp_attacker, p.last_pvp_hit_until, p.last_pvp_unjust = "", 0, False
        self.stop_auto(p);self.break_concentration(p);self.companions.pop(p.id,None)
        p.form="";p.form_until=0;p.temp_hp=0;p.buffs={}
        self.clear_martial_preparation(p)
        p.dx, p.dy = 0, 0
        p.respawn_until, p.respawn_at = now+4, self.time+4
        p.combat_until = p.pvp_combat_until = 0
        # Do not clear crimes/white/red on death. Persist before any network await.
        self.persist([killer] if offline_killer and killer else [])

    def step(self, dt):
        dt = min(.05, max(0, dt))
        self.time += dt
        self.tick += 1
        self.effects = [effect for effect in self.effects if self.time-effect["time"] <= max(1.5,effect.get("duration",0))]
        now = self.now()
        # Maintain equipment effects before ongoing combat effects.
        for p in tuple(self.players.values()):
            magic_items.maintain(p, now)
        self.tick_dnd(dt)
        self.wizard_defense_tick()
        for p in tuple(self.players.values()):
            p.current_wall_time = now
            if not p.alive:
                self.cancel_rest(p, "")
                if now >= p.respawn_until:
                    p.x, p.y, p.floor = town_services.respawn_position(content, p.home_city)
                    p.hp, p.mana = p.max_hp, p.max_mana
                    p.input_time, p.respawn_until = -10, 0
                elif p.disconnected:
                    # Dead avatars no longer fight, but retain death timer in the save.
                    self.remove_player(p)
                    continue
            if p.disconnected and p.combat_until <= now:
                self.remove_player(p)
                continue
            if not p.alive:
                continue
            self.recover_terrain_position(p)
            if not p.disconnected and self.time-p.input_time <= .35:
                self.move(p, p.dx*p.speed*dt, p.dy*p.speed*dt)
            # Health and spell resources recover through the explicit rest rules.
            if not p.disconnected:
                self.discover_landmarks(p)
            p.unjust_kills = [t for t in p.unjust_kills if t > now-86400]
            p.aggressors = {pid: until for pid, until in p.aggressors.items() if until > now}
        self.invites = {key: value for key, value in self.invites.items() if value[1] > now}
        player_cells, unsafe_ids = {}, set()
        for p in (*self.players.values(), *self.companions.values(), *self.familiars.values()):
            if p.alive:
                player_cells.setdefault((p.floor, int(p.x//1024), int(p.y//1024)), []).append(p)
                if not self.in_safe(p):
                    unsafe_ids.add(p.id)
        self.step_monsters(dt, player_cells, unsafe_ids)
        # Resolve incoming damage before awarding a rest that ends on this tick.
        for p in tuple(self.players.values()):
            self.tick_rest(p)

    async def run(self):
        loop = asyncio.get_running_loop()
        next_tick = loop.time()
        while True:
            self.step(.05)
            await self.process_player_actions()
            if self.tick % 2 == 0:
                await self.broadcast_states()
            if self.time-self.last_save >= 2:
                self.persist()
                self.last_save = self.time
            next_tick += .05
            if next_tick < loop.time()-.2:
                next_tick = loop.time()
            await asyncio.sleep(max(0, next_tick-loop.time()))

    def remove_player(self, p):
        self.cancel_rest(p, "")
        self.cancel_channel(p,'');self.familiars.pop(p.id,None);self.alarms.pop(p.id,None)
        self.stop_auto(p);self.break_concentration(p);self.companions.pop(p.id,None)
        with self.db:
            self.save_player(p)
        self.leave_party(p)
        self.players.pop(p.id, None)
        self.compact_clients.discard(p.id)
        self.owner_cache.pop(p.id, None)

    async def disconnect(self, ws):
        p = next((p for p in self.players.values() if p.ws is ws), None)
        if p:
            self.cancel_rest(p, "")
            self.stop_auto(p);self.companions.pop(p.id,None)
            p.ws, p.dx, p.dy, p.input_time = None, 0, 0, -10
            if p.alive and p.combat_until > self.now():
                self.persist()
            else:
                self.remove_player(p)
        self.connections.discard(ws)


async def websocket(request):
    game = request.app["game"]
    google_auth = request.app["google_auth"]
    if not google_auth.enabled:
        raise web.HTTPServiceUnavailable(text="Logowanie Google nie jest jeszcze skonfigurowane.")
    if request.headers.getall("Origin", []) != [google_auth.allowed_origin]:
        raise web.HTTPForbidden(text="Połącz się przez stronę gry.")
    if len(game.connections)>=MAX_CONNECTIONS:
        raise web.HTTPServiceUnavailable(text="Serwer jest pełny.")
    ws = web.WebSocketResponse(heartbeat=20,max_msg_size=MAX_MESSAGE)
    await ws.prepare(request)
    if len(game.connections)>=MAX_CONNECTIONS:
        await ws.close(code=1013,message=b"Server full")
        return ws
    game.connections.add(ws)
    recent = deque()
    bad = 0
    peer = request.remote or "unknown"
    try:
        while not ws.closed:
            authenticated = any(p.ws is ws for p in game.players.values())
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=90 if authenticated else 20)
            except asyncio.TimeoutError:
                await ws.close(code=1008,message=b"Login timeout")
                break
            if msg.type in (WSMsgType.CLOSE,WSMsgType.CLOSING,WSMsgType.CLOSED,WSMsgType.ERROR):
                break
            if msg.type!=WSMsgType.TEXT:
                await game.error(ws,"Wymagany komunikat JSON.")
                bad+=1
                if bad>=5:
                    break
                continue
            now=time.monotonic()
            while recent and recent[0]<now-1:
                recent.popleft()
            recent.append(now)
            if len(recent)>60:
                await game.error(ws,"Zbyt wiele wiadomości. Połącz się ponownie.")
                await ws.close(code=1008,message=b"Rate limit")
                break
            try:
                data=json.loads(msg.data,parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (ValueError,RecursionError):
                await game.error(ws,"Nieprawidłowy JSON.")
                bad+=1
                if bad>=5:
                    break
                continue
            if isinstance(data,dict) and data.get("type") in ("hello", "hello_google"):
                if len(game.auth_attempts)>1024:
                    game.auth_attempts={k:v for k,v in game.auth_attempts.items() if v and v[-1]>now-60}
                attempts=game.auth_attempts.setdefault(peer,deque())
                while attempts and attempts[0]<now-60:
                    attempts.popleft()
                if len(attempts)>=12:
                    await game.error(ws,"Za dużo prób logowania. Poczekaj minutę.")
                    continue
                attempts.append(now)
            try:
                if isinstance(data,dict) and data.get("type")=="hello_google":
                    await game.hello_google(ws,data,google_auth,
                        request.cookies.get(google_auth.cookie_name,""),request.headers.get("Origin",""))
                else:
                    await game.on_packet(ws,data)
            except (TypeError,ValueError,OverflowError,KeyError):
                await game.error(ws,"Nieprawidłowe dane komendy.")
                bad+=1
                if bad>=5:
                    break
    finally:
        await game.disconnect(ws)
        await ws.close()
    return ws


async def lifecycle(app):
    game=app["game"]
    game.task=asyncio.create_task(game.run())
    yield
    game.task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await game.task
    game.persist()
    for ws in tuple(game.connections):
        await ws.close(code=1001,message=b"Server shutdown")
    game.db.close()


def create_app(db_path="world.sqlite3", clock=None, google_auth_service=None):
    app=web.Application(client_max_size=MAX_MESSAGE)
    app["game"]=Game(db_path, clock=clock)
    app["google_auth"]=google_auth_service if google_auth_service is not None else GoogleAuthService.from_env()
    seo_config=seo.SEOConfig.from_env()
    register_google_routes(app,app["google_auth"],account_info=app["game"].google_account_info)
    app.router.add_get("/ws",websocket)

    async def health(request):
        return web.json_response({"ok":True,"players":len(app["game"].players),"version":content.VERSION,"ui_revision":"UI_29","world_revision":getattr(content,"WORLD_REVISION",20)})

    app.router.add_get("/health",health)
    async def ranking(request):
        return web.json_response(app["game"].ranking(), headers={"Cache-Control":"no-store"})
    app.router.add_get("/ranking",ranking)
    web_dir=Path(__file__).resolve().parents[1]/"web"
    async def index_redirect(request):
        raise web.HTTPMovedPermanently(location=request.rel_url.with_path("/",keep_query=True))
    async def robots(request):
        return web.Response(text=seo.robots_txt(seo_config),content_type="text/plain",
                            headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"})
    async def sitemap(request):
        return web.Response(text=seo.sitemap_xml(seo_config),content_type="application/xml",
                            headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"})
    app.router.add_get("/index.html",index_redirect)
    app.router.add_get("/robots.txt",robots)
    app.router.add_get("/sitemap.xml",sitemap)
    async def landing_css(request):
        path=web_dir/"landing.css"
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path,headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"})
    app.router.add_get("/landing.css",landing_css)
    for route,filename in [("/","index.html"),("/game.js","game.js"),("/runtime.js","runtime.js"),("/atlas_map.js","atlas_map.js"),("/style.css","style.css"),("/spell_vfx.js","spell_vfx.js"),("/character_sheet.js","character_sheet.js"),("/skills_ui.js","skills_ui.js"),("/character_sheet.css","character_sheet.css"),("/level_up.js","level_up.js"),("/level_up.css","level_up.css"),("/loot_ui.js","loot_ui.js"),("/loot_ui.css","loot_ui.css"),("/hud_layout.css","hud_layout.css"),("/windows.css","windows.css"),("/windows.js","windows.js"),("/mobile.js","mobile.js"),("/mobile.css","mobile.css"),("/rest_ui.js","rest_ui.js"),("/rest_ui.css","rest_ui.css"),("/app_shell.js","app_shell.js"),("/app_shell.css","app_shell.css"),("/manifest.webmanifest","manifest.webmanifest"),("/sw.js","sw.js"),("/offline.html","offline.html"),("/inventory_ui.js","inventory_ui.js"),("/fighter_ui.js","fighter_ui.js"),("/martial_ui.js","martial_ui.js"),("/martial.css","martial.css"),("/fighter_vfx.js","fighter_vfx.js"),("/fighter.css","fighter.css"),("/caster_ui.js","caster_ui.js"),("/caster_vfx.js","caster_vfx.js"),("/wizard_vfx.js","wizard_vfx.js"),("/service_ui.js","service_ui.js"),("/hud_icons.js","hud_icons.js"),("/service_ui.css","service_ui.css"),("/caster.css","caster.css"),("/circle_spell_ui.js","circle_spell_ui.js"),("/circle_vfx.js","circle_vfx.js"),("/hotbar_ui.js","hotbar_ui.js"),("/hotbar_ui.css","hotbar_ui.css"),("/world_geometry.js","world_geometry.js"),("/terrain_art.js","terrain_art.js"),("/google_auth.js","google_auth.js"),("/google_auth.css","google_auth.css"),("/adventure_ui.js","adventure_ui.js"),("/adventure_ui.css","adventure_ui.css")]:
        async def asset(request,filename=filename):
            path=web_dir/filename
            if not path.is_file():
                raise web.HTTPNotFound()
            headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"}
            if filename == "index.html":
                headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                return web.Response(text=seo.render_index(path.read_text(encoding="utf-8"),seo_config),
                                    content_type="text/html",headers=headers)
            if filename == "manifest.webmanifest":
                headers["Content-Type"] = "application/manifest+json"
            elif filename == "sw.js":
                headers["Content-Type"] = "application/javascript"
            return web.FileResponse(path,headers=headers)
        app.router.add_get(route,asset)
    app.router.add_static("/assets/",web_dir/"assets",show_index=False)
    app.router.add_static("/icons/",web_dir/"icons",show_index=False)
    app.cleanup_ctx.append(lifecycle)
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8080)
    parser.add_argument("--db",default="world.sqlite3")
    args=parser.parse_args()
    if args.db!=":memory:":
        Path(args.db).resolve().parent.mkdir(parents=True,exist_ok=True)
    web.run_app(create_app(args.db),host=args.host,port=args.port,access_log=None)


if __name__=="__main__":
    main()
