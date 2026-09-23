"""Pogranicze: authoritative shared-world RPG prototype, version 0.6.0.

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
import os
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
    from . import living_world, vertical_world, loot_tables
    from .monster_ai import MonsterAI
    from .progression import ExpansionGame, same_floor, near, train, skill_level, private_state
except ImportError:
    import world_content as content
    import living_world, vertical_world, loot_tables
    from monster_ai import MonsterAI
    from progression import ExpansionGame, same_floor, near, train, skill_level, private_state

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
            "prices": {"health_potion": 15, "mana_potion": 12}}
INVENTORY_CAP, PARTY_CAP, PARTY_RANGE = 40, 4, 650
PVP_RULES = {"min_level": 8, "white_seconds": 120, "combat_seconds": 20,
             "red_kills": 3, "crime_window_seconds": 86400, "red_seconds": 86400,
             "normal_gold_loss": .05, "normal_xp_loss": .10,
             "red_gold_loss": .20, "red_xp_loss": .20,
             "red_item_loss": "one_unequipped; transferred_to_killer_if_space_else_destroyed"}
POTIONS = {"health_potion": {"name": "Mikstura zdrowia", "price": 15, "restore": 65},
           "mana_potion": {"name": "Mikstura many", "price": 12, "restore": 55}}
CLASSES = {
    "knight": {"name": "Rycerz", "description": "Dużo zdrowia i pancerza; walka mieczem.",
               "weapon": "sword", "hp": 150, "hp_growth": 18, "mana": 45, "mana_growth": 4,
               "damage": 22, "armor": 3, "ability_name": "Bastion", "ability_cost": 15, "ability_cooldown": 12},
    "paladin": {"name": "Paladyn", "description": "Łuk i mocny strzał z dystansu.",
                "weapon": "bow", "hp": 115, "hp_growth": 13, "mana": 70, "mana_growth": 7,
                "damage": 18, "armor": 1, "ability_name": "Przeszywający strzał", "ability_cost": 18, "ability_cooldown": 7},
    "mage": {"name": "Mag", "description": "Mało zdrowia, dużo many i obrażenia obszarowe.",
             "weapon": "staff", "hp": 85, "hp_growth": 9, "mana": 120, "mana_growth": 12,
             "damage": 21, "armor": 0, "ability_name": "Krąg ognia", "ability_cost": 30, "ability_cooldown": 9},
    "druid": {"name": "Druid", "description": "Leczenie siebie i drużyny podczas wypraw.",
              "weapon": "staff", "hp": 100, "hp_growth": 11, "mana": 105, "mana_growth": 10,
              "damage": 16, "armor": 1, "ability_name": "Odnowa", "ability_cost": 25, "ability_cooldown": 9},
}
WEAPONS = {"sword": {"range": 108, "cooldown": .55}, "bow": {"range": 310, "cooldown": .8},
           "staff": {"range": 285, "cooldown": .85}}
ITEMS = {}
for class_id, weapon, noun in [("knight", "sword", "Miecz"), ("paladin", "bow", "Łuk"),
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
     "reward": {"xp": 55, "gold": 25, "potions": {"health_potion": 2, "mana_potion": 1}}},
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


content.configure(ITEMS, ZONES, NPCS, LANDMARKS, QUESTS, ENEMY_TYPES, OBSTACLES, MERCHANT)
content.QUESTS_REF = QUESTS
content.expand_wilderness(ZONES, NPCS, LANDMARKS, OBSTACLES)
living_world.configure(content, OBSTACLES, LANDMARKS, QUESTS, ENEMY_TYPES)
vertical_world.configure(content, OBSTACLES, LANDMARKS, ZONES, ENEMY_TYPES)
loot_tables.configure(ITEMS, ENEMY_TYPES, content.TIER_LEVELS)
WIDTH, HEIGHT = content.WIDTH, content.HEIGHT
for prefix, label in (("health", "zdrowia"), ("mana", "many")):
    for tier, level, amount, cost in ((2, 20, 220, 45), (3, 50, 520, 95), (4, 80, 950, 165)):
        POTIONS[f"{prefix}_potion_{tier}"] = {"name": f"Mikstura {label} {tier}", "price": cost, "restore": amount, "min_level": level}

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
    blessed: bool = False
    mastery: dict = field(default_factory=dict)
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
    hp: float = 150
    mana: float = 45
    level: int = 1
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
    equipment: dict = field(default_factory=lambda: {"weapon": "", "armor": "", "ring": ""})
    potions: dict = field(default_factory=lambda: {"health_potion": 3, "mana_potion": 3})
    facing: list = field(default_factory=lambda: [0, 1])
    attack_facing: list = field(default_factory=lambda: [0, 1])
    speech_text: str = ""
    speech_until: float = 0
    quest_progress: dict = field(default_factory=dict)
    discoveries: list = field(default_factory=list)
    attack_until: float = 0
    attack_ready: float = 0  # compatibility: simulation animation only; cooldown uses wall time
    attack_cooldown_until: float = 0
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

    @property
    def spec(self):
        return CLASSES[self.class_id]

    @property
    def speed(self):
        return player_speed(self.level)*(1.3 if self.haste_until > self.current_wall_time else 1)*(1.2 if self.premium_demo_until > self.current_wall_time else 1)*(1.15 if self.wind_until > self.current_wall_time else 1)*living_world.SURFACES[content.SURFACE_MAP.at(self.x,self.y,self.floor)]["speed"]

    @property
    def max_hp(self):
        return self.spec["hp"] + (self.level - 1) * self.spec["hp_growth"] + self.mastery.get("vitality", 0)*12

    @property
    def max_mana(self):
        return self.spec["mana"] + (self.level - 1) * self.spec["mana_growth"] + self.mastery.get("focus", 0)*8

    def gear_bonus(self, stat):
        equipped = set(self.equipment.values())
        return sum(ITEMS[i["template"]].get(stat, 0) for i in self.inventory if i["uid"] in equipped)

    @property
    def attack(self):
        skill = "melee" if self.class_id == "knight" else "distance" if self.class_id == "paladin" else "magic"
        bonus = skill_level(self, skill)-(1 if skill == "magic" else 10)
        return self.spec["damage"] + (self.level - 1) * 2 + self.gear_bonus("attack") + bonus*2 + self.mastery.get("power", 0)*3 + self.mastery.get("focus", 0)

    @property
    def armor(self):
        return self.spec["armor"] + (self.level - 1) // 4 + self.gear_bonus("armor") + (skill_level(self, "shielding")-10)//2

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
                  "hp": round(max(0, self.hp), 1), "max_hp": self.max_hp, "mana": round(self.mana, 1),
                  "max_mana": self.max_mana, "level": self.level, "weapon": self.spec["weapon"],
                  "floor": self.floor, "promoted": self.promoted, "class_id": self.class_id, "class_chosen": self.class_chosen,
                  "attack": self.attack, "armor": self.armor, "kills": self.kills, "boss_kills": self.boss_kills,
                  "ability_name": self.spec["ability_name"], "ability_cooldown": max(0, self.ability_cooldown_until-now),
                  "facing": list(self.facing), "attack_facing": list(self.attack_facing),
                  "speech_text": self.speech_text if self.speech_until > simulation_time else "",
                  "speech_until": self.speech_until, "speed": round(self.speed, 3),
                  "attack_until": self.attack_until, "alive": self.alive,
                  "respawn_in": max(0, self.respawn_until-now) if not self.alive else 0,
                  "skull": skull, "skull_remaining": max(0, (self.red_until if skull == "red" else self.white_until)-now),
                  "combat_remaining": max(0, self.combat_until-now),
                  "pvp_combat_remaining": max(0, self.pvp_combat_until-now), "disconnected": self.disconnected,
                  "party_id": self.party_id, "party_members": party_members or []}
        if private:
            result.update(private_state(self, now))
            result.update({"xp": self.xp, "xp_next": xp_next(self.level), "gold": self.gold,
                           "pvp_safety": self.pvp_safety, "unjust_kills": len([t for t in self.unjust_kills if t > now-86400]),
                           "inventory": [dict(i) for i in self.inventory], "equipment": dict(self.equipment),
                           "potions": dict(self.potions), "potion_cooldown": max(0, self.potion_cooldown_until-now),
                           "quests": self.quest_entries(), "discoveries": list(self.discoveries)})
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
            "site_cooldowns", "wind_until", "ward_until", "premium_demo_until", "floor", "skill_tries", "promoted", "soul", "runes", "bank_gold", "depot", "home_city", "blessed", "mastery", "spell_cooldowns", "spell_ready", "rune_ready", "haste_until", "transition_ready",
            "x", "y", "hp", "mana", "level", "xp", "gold", "class_id", "class_chosen", "weapon", "kills", "boss_kills",
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

    @property
    def max_hp(self):
        return ENEMY_TYPES[self.kind]["hp"]

    def public(self):
        return {"id": self.id, "kind": self.kind, "name": ENEMY_TYPES[self.kind]["name"], "x": round(self.x, 2),
                "y": round(self.y, 2), "floor": self.floor, "hp": round(self.hp, 1), "max_hp": self.max_hp, "alive": self.alive,
                "attack_until": self.attack_until, "facing": self.facing, "size": ENEMY_TYPES[self.kind].get("size", 1)}


class Game(ExpansionGame, MonsterAI):
    def __init__(self, db_path, clock=None):
        self.clock = clock or time.time
        self.rng = random.Random()
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            name_key TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, password_hash BLOB NOT NULL, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS shared(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS boss_rewards(player_id INTEGER PRIMARY KEY);
        """)
        # Old relic flags and boss claims never gate the new game.
        self.flags = {"bridge_open": True, "trail_open": True, "event_active": True, "boss_defeated": False}
        self.players, self.enemies, self.parties, self.invites = {}, {}, {}, {}
        self.connections, self.auth_attempts = set(), {}
        self.compact_clients, self.owner_cache = set(), {}
        self.time, self.tick, self.last_save, self.task = 0.0, 0, 0, None
        self.effects, self.effect_serial = [], 0
        self.hazards = []
        for i, (kind, x, y) in enumerate([
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
        ]):
            e = Enemy("boss" if kind == "boss" else f"e{i}", kind, x, y, ENEMY_TYPES[kind]["hp"], x, y)
            e.aoe_ready = 7
            self.enemies[e.id] = e
        for i, (kind, x, y, floor) in enumerate(content.SPAWNS):
            e = Enemy(f"world_{i}", kind, x, y, ENEMY_TYPES[kind]["hp"], x, y, floor=floor)
            self.enemies[e.id] = e
        self.legacy_enemies = [e for e in self.enemies.values() if not e.id.startswith("world_")]
        self.enemy_cells = {}
        for e in self.enemies.values():
            if e.id.startswith("world_"):
                self.enemy_cells.setdefault((e.floor, int(e.home_x//1024), int(e.home_y//1024)), []).append(e)
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
        return {"version": content.VERSION, "regions": content.REGIONS, "cities": content.CITIES, "stairs": content.STAIRS,
                "terrain": content.TERRAIN, "surfaces": content.SURFACES, "premium": content.PREMIUM,
                "elevations": content.ELEVATIONS, "waterways": content.WATERWAYS, "bridges": content.BRIDGES,
                "pois": content.POIS, "canyons": content.CANYONS, "rarities": loot_tables.RARITIES,
                "dungeons": content.DUNGEONS, "hunting_grounds": content.HUNTING_GROUNDS, "roads": content.ROADS, "safe_zones": content.CITIES,
                "spells": content.SPELLS, "runes": content.RUNES, "milestones": [{"level":v[0], "name":v[1], "description":v[2]} for v in content.MILESTONES],
                "width": WIDTH, "height": HEIGHT, "sites": [], "chests": [], "obstacles": OBSTACLES,
                "zones": ZONES, "npcs": NPCS, "landmarks": LANDMARKS, "quests": QUESTS,
                "enemy_types": ENEMY_TYPES, "spawn": SPAWN, "river": RIVER, "trail_gate": TRAIL_GATE, "weapons": WEAPONS,
                "classes": CLASSES, "items": ITEMS, "merchant": MERCHANT, "safe_zone": SAFE_ZONE,
                "pvp_rules": PVP_RULES, "potions": POTIONS, "inventory_cap": INVENTORY_CAP,
                "party_rules": {"max_members": PARTY_CAP, "range": PARTY_RANGE, "bonus_per_extra_member": .10,
                                "participation_seconds": 30, "max_level_ratio": 3},
                "abilities": {"offense": "PvE_only", "druid_party_heal": "no_other_player_in_PvP_combat"}}

    def snapshot(self, for_player=None, public_players=None):
        pid = for_player.id if isinstance(for_player, Player) else str(for_player or "")
        now = self.now()
        viewer = self.players.get(pid)
        def visible(obj):
            return viewer is None or (same_floor(viewer, obj) and distance(viewer, obj) <= 1800)
        return {"type": "state", "tick": self.tick, "time": self.time,
                "players": [self.players[pid].public(now, self.time, True, self.parties.get(self.players[pid].party_id, [])) if entry["id"] == pid else entry for entry in public_players] if public_players is not None else
                           [p.public(now, self.time, p.id == pid, self.parties.get(p.party_id, [])) for p in self.players.values()],
                "enemies": [e.public() for e in (self.nearby_enemies(viewer, 1800) if viewer else self.enemies.values()) if visible(e)], "world": dict(self.flags),
                "effects": [dict(effect) for effect in self.effects if self.time-effect["time"] <= max(1.5,effect.get("duration",0)) and (viewer is None or (same_floor(viewer, effect) and point_distance(viewer, effect) <= 1800))]}

    def persist(self, extra_players=()):
        with self.db:
            for p in (*self.players.values(), *extra_players):
                self.save_player(p)
            self.db.execute("INSERT OR REPLACE INTO shared VALUES(1,?)", (json.dumps(self.flags),))

    def save_player(self, p):
        self.db.execute("UPDATE accounts SET data=? WHERE id=?", (json.dumps(p.save_data()), p.id))

    def starter(self, p):
        p.inventory = [make_item(f"{p.class_id}_weapon_1"), make_item("cloth")]
        p.equipment = {"weapon": p.inventory[0]["uid"], "armor": p.inventory[1]["uid"], "ring": ""}
        p.weapon = p.spec["weapon"]

    def load_player(self, pid, name, ws, saved):
        p = Player(pid, name, ws)
        for attr in p.save_data():
            if attr in saved:
                setattr(p, attr, saved[attr])
        if "class_id" not in saved:
            p.class_chosen = False
            p.class_id = "knight"
        if "inventory" not in saved:
            self.starter(p)
        p.weapon = p.spec["weapon"]
        if "mana" not in saved:
            p.mana = p.max_mana
        p.hp, p.mana = min(p.hp, p.max_hp), min(p.mana, p.max_mana)
        # Existing dead characters retain death; v0.1 had no persistent timer.
        if p.hp <= 0 and not p.respawn_until:
            p.respawn_until = self.now() + 4
        # Old relic progression may have saved a character in an invalid tile.
        if self.blocked(p.x, p.y, floor=p.floor) and p.combat_until <= self.now():
            p.x, p.y, p.floor = SPAWN["x"], SPAWN["y"], 0
        p.unjust_kills = [t for t in p.unjust_kills if t > self.now()-86400]
        p.aggressors = {k: t for k, t in p.aggressors.items() if t > self.now()}
        return p

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
        private_keys = ("quests", "discoveries", "inventory", "equipment", "depot", "skills", "runes", "mastery", "potions")
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
        if any(p.ws is ws for p in self.players.values()):
            return await self.error(ws, "Jesteś już zalogowany.")
        name, password, create = data.get("name"), data.get("password"), data.get("create")
        class_id = data.get("class_id", "knight")
        if (not isinstance(name, str) or not re.fullmatch(r"[\w -]{3,20}", name, re.UNICODE)
                or name != name.strip() or not isinstance(password, str) or not 8 <= len(password) <= 128
                or type(create) is not bool):
            return await self.error(ws, "Nazwa: 3–20 liter/cyfr. Hasło: 8–128 znaków.")
        if create and (not isinstance(class_id, str) or class_id not in CLASSES):
            return await self.error(ws, "Wybierz jedną z czterech klas.")
        row = self.db.execute("SELECT id,name,salt,password_hash FROM accounts WHERE name_key=?", (name.casefold(),)).fetchone()
        salt = secrets.token_bytes(16) if create else (row[2] if row else bytes(16))
        hashed = await asyncio.to_thread(self.password_hash, password, salt)
        if ws.closed:
            return
        if create:
            if len(self.players) >= MAX_PLAYERS:
                return await self.error(ws, "Świat jest pełny. Spróbuj za chwilę.")
            p = Player("", name, ws, class_id=class_id)
            p.hp, p.mana = p.max_hp, p.max_mana
            self.starter(p)
            try:
                with self.db:
                    cur = self.db.execute("INSERT INTO accounts(name,name_key,salt,password_hash,data) VALUES(?,?,?,?,?)",
                                          (name, name.casefold(), salt, hashed, json.dumps(p.save_data())))
                pid = str(cur.lastrowid)
                p.id = pid
            except sqlite3.IntegrityError:
                return await self.error(ws, "Ta nazwa jest zajęta. Wybierz Zaloguj lub inną nazwę.")
        else:
            if not row or not hmac.compare_digest(hashed, row[3]):
                return await self.error(ws, "Nieprawidłowa nazwa lub hasło.")
            pid = str(row[0])
            p = self.players.get(pid)
            if p and not p.disconnected:
                return await self.error(ws, "To konto jest już w grze. Wyloguj je na drugim urządzeniu.")
            if p is None:
                if len(self.players) >= MAX_PLAYERS:
                    return await self.error(ws, "Świat jest pełny. Spróbuj za chwilę.")
                # Hash work yielded; always read fresh save after the active-session check.
                saved = json.loads(self.db.execute("SELECT data FROM accounts WHERE id=?", (pid,)).fetchone()[0])
                p = self.load_player(pid, row[1], ws, saved)
            p.ws = ws
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
        return any(near(p, zone) for zone in content.CITIES)

    def blocked(self, x, y, radius=RADIUS, floor=0):
        if x < radius or y < radius or x > WIDTH-radius or y > HEIGHT-radius:
            return True
        if floor != 0:
            for px, py in [(x-radius,y-radius),(x+radius,y-radius),(x-radius,y+radius),(x+radius,y+radius)]:
                rooms = self.room_cells.get((floor, int(px//512), int(py//512)), ())
                if not any(r["x"] <= px <= r["x"]+r["w"] and r["y"] <= py <= r["y"]+r["h"] for r in rooms):
                    return True
        for cx in range(int((x-radius)//256), int((x+radius)//256)+1):
            for cy in range(int((y-radius)//256), int((y+radius)//256)+1):
                if any(intersects(x, y, r, radius) for r in self.obstacle_cells.get((floor,cx,cy), [])):
                    return True
        if floor != 0:
            return False
        if content.WATER_MAP.blocked(x, y, radius):
            return True
        if y-radius < RIVER["h"] and x+radius > RIVER["x"] and x-radius < RIVER["x"]+RIVER["w"]:
            if y-radius < RIVER["bridge_y"] or y+radius > RIVER["bridge_y"]+RIVER["bridge_h"]:
                return True
        return False

    def move(self, obj, dx, dy):
        parts = max(1, math.ceil(max(abs(dx), abs(dy))/10))
        def allowed(x, y):
            if self.blocked(x, y, floor=obj.floor):
                return False
            if isinstance(obj, Player) and obj.pvp_combat_until > self.now():
                for zone in content.CITIES:
                    new_distance = math.hypot(x-zone["x"], y-zone["y"])
                    if obj.floor == 0 and new_distance <= zone["radius"] and new_distance < point_distance(obj, zone):
                        return False
            if isinstance(obj, Enemy) and obj.floor == 0 and any(math.hypot(x-zone["x"],y-zone["y"]) < zone["radius"] for zone in content.CITIES):
                return False
            return True
        for _ in range(parts):
            if allowed(obj.x+dx/parts, obj.y):
                obj.x += dx/parts
            if allowed(obj.x, obj.y+dy/parts):
                obj.y += dy/parts

    def line_clear(self, a, b):
        if not same_floor(a, b):
            return False
        steps = max(1, math.ceil(distance(a, b)/12))
        return all(not self.blocked(a.x+(b.x-a.x)*i/steps, a.y+(b.y-a.y)*i/steps, 2, floor=a.floor) for i in range(1, steps))

    def award(self, p, xp, gold):
        p.xp += int(xp)
        p.gold += int(gold)
        # Solve total XP cost algebraically with integer sqrt. No loop or level cap.
        # Cost of k levels: k * current_cost + 35*k*(k-1)/2.
        b = 2*xp_next(p.level)-35
        levels = max(0, (math.isqrt(b*b+280*p.xp)-b)//70)
        if levels:
            p.xp -= levels*xp_next(p.level)+35*levels*(levels-1)//2
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
        if template and len(p.inventory) >= INVENTORY_CAP:
            return await self.notice(p, "Zwolnij miejsce w plecaku. Gwarantowana nagroda pozostaje u zleceniodawcy.")
        if any(p.potions.get(key, 0)+amount > 99 for key, amount in reward.get("potions", {}).items()):
            return await self.notice(p, "Zrób miejsce na mikstury przed odebraniem nagrody (limit 99 każdego rodzaju).")
        # Validate everything before mutation. One SQLite commit includes claim, XP, gold and item.
        with self.db:
            p.quest_progress[quest_id]["claimed"] = True
            self.award(p, reward["xp"], reward["gold"])
            if template:
                p.inventory.append(make_item(template))
            for key, amount in reward.get("potions", {}).items():
                p.potions[key] = p.potions.get(key, 0)+amount
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
        kind = {"knight": "sword", "paladin": "arrow", "mage": "magic_bolt", "druid": "nature_bolt"}[p.class_id]
        return self.combat_effect(p, kind, target, duration=.22 if kind == "sword" else .32)

    def tag(self, p, pvp=False):
        p.combat_until = max(p.combat_until, self.now()+PVP_RULES["combat_seconds"])
        if pvp:
            p.pvp_combat_until = max(p.pvp_combat_until, p.combat_until)

    def grant_loot(self, p, drops):
        names, overflow = [], False
        for kind, template in drops:
            if kind == "potion":
                if p.potions.get(template, 0) >= 99:
                    overflow = True
                else:
                    p.potions[template] = p.potions.get(template, 0)+1
                    names.append(POTIONS[template]["name"])
            elif len(p.inventory) >= INVENTORY_CAP:
                overflow = True
            else:
                item = make_item(template)
                p.inventory.append(item)
                names.append(item["name"]+" ["+loot_tables.RARITIES[item["rarity"]]+"]")
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
                    detail += self.grant_loot(p, loot_tables.roll(p.class_id, spec, self.rng))
                    self.save_player(p)
                    notices.append((p, detail))
            self.db.execute("INSERT OR REPLACE INTO shared VALUES(1,?)", (json.dumps(self.flags),))
        enemy.contributors.clear()
        for p, text in notices:
            await self.notice(p, text)

    def pvp_error(self, p, target):
        if target is None or target.id == p.id or not target.alive:
            return "Wskaż żywą postać przeciwnika."
        if p.pvp_safety:
            return "Najpierw świadomie wyłącz ochronę przed atakowaniem graczy."
        if p.level < 8 or target.level < 8:
            return "PvP jest dostępne od poziomu 8; początkujący są chronieni."
        if self.in_safe(p) or self.in_safe(target):
            return "Przystań jest bezpieczna: nie można tu walczyć."
        if p.party_id and p.party_id == target.party_id:
            return "Nie można atakować członków drużyny."
        return ""

    def remember_attacker(self, enemy, p):
        enemy.contributors[p.id] = self.time
        enemy.attacker_id, enemy.attacker_until = p.id, self.time+20

    def selected_enemy(self, p, enemy_id, attack_range):
        enemy = self.enemies.get(enemy_id) if isinstance(enemy_id, str) else None
        if enemy and enemy.alive and same_floor(p, enemy) and distance(p, enemy) <= attack_range and self.line_clear(p, enemy):
            return enemy
        return None

    async def attack(self, p, target_id=None, enemy_id=None):
        now = self.now()
        if not p.alive or now < p.attack_cooldown_until:
            return
        spec = WEAPONS[p.spec["weapon"]]
        if target_id is not None and enemy_id is not None:
            return await self.notice(p, "Wybierz jeden cel ataku.")
        if target_id is not None:
            target = self.players.get(str(target_id)) if isinstance(target_id, (str, int)) else None
            reason = self.pvp_error(p, target)
            if reason:
                return await self.notice(p, reason)
            if distance(p, target) > spec["range"] or not self.line_clear(p, target):
                return await self.notice(p, "Przeciwnik jest poza zasięgiem lub za ścianą.")
            unjust = target.skull(now) == "none" and p.aggressors.get(target.id, 0) <= now
            if unjust:
                p.white_until = max(p.white_until, now+120)
                target.aggressors[p.id] = now+120
            self.tag(p, True)
            self.tag(target, True)
            p.attack_cooldown_until, p.attack_until = now+spec["cooldown"], self.time+.22
            self.basic_effect(p, target)
            self.damage_player(target, p.attack*.65, killer=p, unjust=unjust)
            self.persist()
            return
        if self.in_safe(p):
            return
        if enemy_id is not None:
            enemy = self.selected_enemy(p, enemy_id, spec["range"])
            if enemy is None:
                return await self.notice(p, "Wybrany potwór jest poza zasięgiem, za ścianą lub na innym piętrze.")
            targets = [enemy]
        else:
            targets = [e for e in self.nearby_enemies(p, 360) if e.alive and distance(p, e) <= spec["range"] and self.line_clear(p, e)]
        p.attack_cooldown_until, p.attack_until = now+spec["cooldown"], self.time+.22
        if not targets:
            return
        enemy = min(targets, key=lambda e: distance(p, e))
        self.basic_effect(p, enemy)
        self.tag(p)
        train(p, "melee" if p.class_id=="knight" else "distance" if p.class_id=="paladin" else "magic", 1 if p.class_id in ("knight", "paladin") else 2)
        enemy.hp = max(0, enemy.hp-p.attack)
        self.remember_attacker(enemy, p)
        if enemy.hp <= 0:
            await self.defeat(enemy)

    async def ability(self, p, enemy_id=None):
        now = self.now()
        if not p.alive or now < p.ability_cooldown_until:
            return
        if p.mana < p.spec["ability_cost"]:
            return await self.notice(p, "Za mało many.")
        targets = [e for e in self.nearby_enemies(p, 360) if e.alive and distance(p, e) <= 320 and self.line_clear(p, e)]
        if p.class_id == "paladin" and enemy_id is not None:
            selected = self.selected_enemy(p, enemy_id, 320)
            if selected is None:
                return await self.notice(p, "Wybrany potwór jest poza zasięgiem lub za ścianą.")
            targets = [selected]
        if p.class_id in ("mage", "paladin", "knight") and (self.in_safe(p) or not targets):
            return await self.notice(p, "Umiejętność wymaga potwora w zasięgu poza Przystanią.")
        if p.class_id == "druid":
            friends = [q for q in self.players.values() if q.alive and not q.disconnected
                       and distance(p, q) <= 300 and self.line_clear(p, q)
                       and (q.id == p.id or (p.party_id and p.party_id == q.party_id and q.pvp_combat_until <= now))
                       and q.hp < q.max_hp]
            if not friends:
                return await self.notice(p, "Brak rannych sojuszników w zasięgu; leczenie innych graczy podczas PvP jest wyłączone.")
        p.mana -= p.spec["ability_cost"]
        train(p, "magic", p.spec["ability_cost"])
        p.ability_cooldown_until = now+p.spec["ability_cooldown"]
        p.attack_until = self.time+.35
        if p.class_id == "knight":
            self.combat_effect(p, "bulwark", radius=100, duration=.9)
            p.bulwark_until = now+6
            self.tag(p)
            for e in targets:
                e.taunt_id, e.taunt_until = p.id, self.time+6
                self.remember_attacker(e, p)
        elif p.class_id in ("mage", "paladin"):
            self.tag(p)
            if p.class_id == "paladin":
                targets = [min(targets, key=lambda e: distance(p, e))]
                self.combat_effect(p, "piercing_arrow", targets[0], duration=.4)
            else:
                self.combat_effect(p, "fire_ring", min(targets, key=lambda e: distance(p, e)), radius=320, duration=.9)
            for e in targets:
                e.hp = max(0, e.hp-p.attack*(2.2 if p.class_id == "paladin" else 1.6))
                self.remember_attacker(e, p)
            # Mark all hits before any await; repeat packets cannot reuse this skill.
            for e in targets:
                if e.hp <= 0:
                    await self.defeat(e)
        else:
            for q in friends:
                self.combat_effect(p, "heal", q, radius=65, duration=.9)
                q.hp = min(q.max_hp, q.hp+45+p.level*4)
                if q.combat_until > now:
                    self.tag(p, q.pvp_combat_until > now)
        self.persist()

    async def interact(self, p):
        if not p.alive:
            return
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
        if p.alive and self.merchant_near(p) and p.combat_until <= self.now():
            p.hp, p.mana = p.max_hp, p.max_mana
            self.persist()
            return await self.notice(p, "Kupiec: odpocząłeś. Sprzedaj niezałożony sprzęt lub kup mikstury zdrowia (15) i many (12).")
        await self.notice(p, "Kupiec w Przystani sprzedaje mikstury, skupuje sprzęt i pozwala odpocząć.")

    async def inventory_command(self, p, kind, data):
        if not p.alive:
            return
        uid = data.get("uid")
        item = next((i for i in p.inventory if i["uid"] == uid), None)
        if kind == "equip":
            if item is None:
                return await self.notice(p, "Nie masz tego przedmiotu.")
            spec = ITEMS[item["template"]]
            if spec["slot"] not in ("weapon", "armor", "ring"):
                return await self.notice(p, "Trofeum można sprzedać lub przechować; nie jest wyposażeniem.")
            if p.class_id not in spec["class_ids"] or p.level < spec["min_level"]:
                return await self.notice(p, "Niewłaściwa klasa lub za niski poziom.")
            p.equipment[spec["slot"]] = item["uid"]
        elif kind == "unequip":
            slot = data.get("slot")
            if slot not in ("weapon", "armor", "ring"):
                return await self.notice(p, "Nieznane miejsce wyposażenia.")
            p.equipment[slot] = ""
        elif kind == "sell":
            if not self.merchant_near(p) or p.combat_until > self.now():
                return await self.notice(p, "Sprzedaż jest dostępna przy kupcu, poza walką.")
            if item is None or uid in p.equipment.values():
                return await self.notice(p, "Sprzedawać można tylko posiadany, niezałożony sprzęt.")
            p.inventory.remove(item)
            p.gold += ITEMS[item["template"]]["value"]
        elif kind == "buy":
            if not self.merchant_near(p) or p.combat_until > self.now():
                return await self.notice(p, "Podejdź do kupca poza walką.")
            kind_id = data.get("item")
            spec = POTIONS.get(kind_id) if isinstance(kind_id, str) else None
            if spec is None or p.level < spec.get("min_level", 1) or p.gold < spec["price"]:
                return await self.notice(p, "Nieznana mikstura lub za mało złota.")
            if p.potions.get(kind_id, 0) >= 99:
                return await self.notice(p, "Możesz nosić do 99 mikstur każdego rodzaju.")
            p.gold -= spec["price"]
            p.potions[kind_id] = p.potions.get(kind_id, 0)+1
        elif kind == "potion":
            kind_id = data.get("item")
            spec = POTIONS.get(kind_id) if isinstance(kind_id, str) else None
            if spec is None or p.level < spec.get("min_level", 1) or not p.potions.get(kind_id) or self.now() < p.potion_cooldown_until:
                return
            attr, maximum = ("hp", p.max_hp) if kind_id.startswith("health_potion") else ("mana", p.max_mana)
            if getattr(p, attr) >= maximum:
                return
            p.potions[kind_id] -= 1
            setattr(p, attr, min(maximum, getattr(p, attr)+spec["restore"]))
            p.potion_cooldown_until = self.now()+3
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
        if kind == "ping":
            return await self.send(ws, {"type": "pong"})
        p = next((p for p in self.players.values() if p.ws is ws), None)
        if p is None:
            return await self.error(ws, "Najpierw zaloguj postać.")
        if kind == "input":
            x, y = data.get("x"), data.get("y")
            if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e6 for v in (x, y)):
                return await self.error(ws, "Nieprawidłowy kierunek ruchu.")
            norm = max(1, math.hypot(x, y))
            p.dx, p.dy, p.input_time = x/norm, y/norm, self.time
            if x or y:
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
            if data.get("target_id") is not None:
                return await self.notice(p, "Ofensywne umiejętności klas działają tylko na potwory.")
            if "enemy_id" in data and (not isinstance(data["enemy_id"], str) or not data["enemy_id"]):
                return await self.notice(p, "Nieprawidłowy cel potwora.")
            await self.ability(p, data.get("enemy_id"))
        elif kind in ("cast", "rune_use", "rune_craft", "rune_buy", "descend", "travel", "promote", "bless", "mastery", "mastery_reset", "bank_deposit", "bank_withdraw", "depot_store", "depot_take", "bind_city"):
            await self.expansion_command(p, kind, data)
        elif kind in ("quest_accept", "quest_claim"):
            await self.quest_command(p, kind, data)
        elif kind in ("equip", "unequip", "sell", "buy", "potion"):
            await self.inventory_command(p, kind, data)
        elif kind == "pvp_safety":
            if type(data.get("enabled")) is not bool:
                return await self.error(ws, "Ochrona wymaga true albo false.")
            p.pvp_safety = data["enabled"]
            await self.notice(p, "Atakowanie graczy zablokowane." if p.pvp_safety else "Możesz wskazać cel PvP. Nieuzasadniony atak i zabójstwo mają kary.")
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
            p.chat_at = self.time
            p.speech_text, p.speech_until = text, self.time+6
            await self.broadcast({"type": "chat", "id": p.id, "name": p.name, "text": text})
        else:
            await self.error(ws, "Nieznana komenda.")

    def damage_player(self, p, damage, killer=None, unjust=False):
        if not p.alive:
            return
        now = self.now()
        actual = max(1, damage-p.armor)
        if p.bulwark_until > now:
            actual *= .5
        if killer is None and p.ward_until > now:
            actual *= .88
        self.tag(p, killer is not None)
        if killer is not None:
            p.last_pvp_attacker = killer.id
            p.last_pvp_unjust = bool(unjust)
            p.last_pvp_hit_until = now+PVP_RULES["combat_seconds"]
        train(p, "shielding")
        p.hp = max(0, p.hp-actual)
        if p.alive:
            return
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
        for p in tuple(self.players.values()):
            p.current_wall_time = now
            if not p.alive:
                if now >= p.respawn_until:
                    home = next((c for c in content.CITIES if c["id"] == p.home_city), content.CITIES[0])
                    p.x, p.y, p.floor, p.hp, p.mana = home["x"], home["y"], 0, p.max_hp, p.max_mana
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
            if not p.disconnected and self.time-p.input_time <= .35:
                self.move(p, p.dx*p.speed*dt, p.dy*p.speed*dt)
            if p.combat_until <= now:
                p.mana = min(p.max_mana, p.mana+(3 if p.promoted else 1.5)*dt)
                if self.in_safe(p):
                    p.hp = min(p.max_hp, p.hp+10*dt)
                    p.mana = min(p.max_mana, p.mana+6*dt)
            if p.promoted and p.combat_until <= now:
                p.hp = min(p.max_hp, p.hp+dt*2)
            if not p.disconnected:
                self.discover_landmarks(p)
            p.unjust_kills = [t for t in p.unjust_kills if t > now-86400]
            p.aggressors = {pid: until for pid, until in p.aggressors.items() if until > now}
        self.invites = {key: value for key, value in self.invites.items() if value[1] > now}
        player_cells, unsafe_ids = {}, set()
        for p in self.players.values():
            if p.alive:
                player_cells.setdefault((p.floor, int(p.x//1024), int(p.y//1024)), []).append(p)
                if not self.in_safe(p):
                    unsafe_ids.add(p.id)
        self.step_monsters(dt, player_cells, unsafe_ids)

    async def run(self):
        loop = asyncio.get_running_loop()
        next_tick = loop.time()
        while True:
            self.step(.05)
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
        with self.db:
            self.save_player(p)
        self.leave_party(p)
        self.players.pop(p.id, None)
        self.compact_clients.discard(p.id)
        self.owner_cache.pop(p.id, None)

    async def disconnect(self, ws):
        p = next((p for p in self.players.values() if p.ws is ws), None)
        if p:
            p.ws, p.dx, p.dy, p.input_time = None, 0, 0, -10
            if p.alive and p.combat_until > self.now():
                self.persist()
            else:
                self.remove_player(p)
        self.connections.discard(ws)


async def websocket(request):
    game = request.app["game"]
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
            if isinstance(data,dict) and data.get("type")=="hello":
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


def create_app(db_path="world.sqlite3", clock=None):
    app=web.Application(client_max_size=MAX_MESSAGE)
    app["game"]=Game(db_path, clock=clock)
    app.router.add_get("/ws",websocket)

    async def health(request):
        return web.json_response({"ok":True,"players":len(app["game"].players),"version":"0.6.0"})

    app.router.add_get("/health",health)
    web_dir=Path(__file__).resolve().parents[1]/"web"
    for route,filename in [("/","index.html"),("/game.js","game.js"),("/runtime.js","runtime.js"),("/style.css","style.css")]:
        async def asset(request,filename=filename):
            path=web_dir/filename
            if not path.is_file():
                raise web.HTTPNotFound()
            return web.FileResponse(path,headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"})
        app.router.add_get(route,asset)
    app.cleanup_ctx.append(lifecycle)
    return app


def _runtime_defaults():
    """Resolve local defaults plus Railway-provided runtime variables."""
    host = os.environ.get("GAME_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "8080"))
    except ValueError:
        port = 8080

    db_path = os.environ.get("BRACTWO_DB")
    if not db_path:
        volume_path = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
        db_path = str(Path(volume_path) / "world.sqlite3") if volume_path else "world.sqlite3"
    return host, port, db_path


def main():
    default_host, default_port, default_db = _runtime_defaults()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host",default=default_host)
    parser.add_argument("--port",type=int,default=default_port)
    parser.add_argument("--db",default=default_db)
    args=parser.parse_args()
    if args.db!=":memory:":
        Path(args.db).resolve().parent.mkdir(parents=True,exist_ok=True)
    web.run_app(create_app(args.db),host=args.host,port=args.port,access_log=None)


if __name__=="__main__":
    main()
