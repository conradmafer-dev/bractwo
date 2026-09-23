"""Accelerated introductory expeditions using normal commands, without teleports.

Run: python tools/check_expedition.py
A fresh knight and a fresh mage each accept a town quest, hunt three rats,
claim the reward, explore the Old Mill, earn and equip their class weapon,
and buy a potion. All travel and combat use the same commands as a client;
only wall/simulation time is accelerated. No character statistics are edited.
The real WebSocket integration suite lives in tests/test_server.py.
"""
import asyncio
import importlib.util
import math
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    "route_server", Path(__file__).resolve().parents[1] / "server" / "server.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class Clock:
    def __init__(self):
        self.value = 1_800_000_000.0

    def __call__(self):
        return self.value


class Socket:
    closed = False

    def __init__(self):
        self.messages = []

    async def send_json(self, data):
        self.messages.append(data)

    async def close(self, *args, **kwargs):
        self.closed = True


async def expedition(class_id):
    clock, ws = Clock(), Socket()
    game = mod.Game(":memory:", clock=clock)
    try:
        await game.on_packet(ws, {"type": "hello", "name": "Explorer"+class_id.title(),
                                 "password": "Route-pass-123", "create": True,
                                 "class_id": class_id})
        player = next(iter(game.players.values()))
        metadata = game.metadata()
        min_hp = player.hp
        health_used = 0
        starting_speed = player.speed

        def own_state():
            return next(p for p in game.snapshot(for_player=player)["players"] if p["id"] == player.id)

        def quest(quest_id):
            return next(q for q in own_state()["quests"] if q["id"] == quest_id)

        def catalogue(key):
            entries = metadata[key]
            return list(entries.values()) if isinstance(entries, dict) else entries

        def npc_for(quest_id):
            return next(n for n in catalogue("npcs") if n["id"] == quest(quest_id)["npc_id"])

        async def command(kind, **data):
            await game.on_packet(ws, {"type": kind, **data})

        async def tick():
            nonlocal min_hp, health_used
            if game.tick % 4 == 0:
                await command("attack")
                if player.hp < player.max_hp*.4:
                    before = player.potions["health_potion"]
                    await command("potion", item="health_potion")
                    health_used += before-player.potions["health_potion"]
            clock.value += .05
            game.step(.05)
            min_hp = min(min_hp, player.hp)
            if not player.alive:
                raise AssertionError(f"{class_id} died at {(round(player.x), round(player.y))}; "
                                     f"level={player.level}, kills={player.kills}")

        async def walk(x, y, limit=1800):
            for _ in range(limit):
                distance = math.hypot(x-player.x, y-player.y)
                if distance < 9:
                    await command("input", x=0, y=0)
                    return
                await command("input", x=(x-player.x)/distance, y=(y-player.y)/distance)
                await tick()
            raise AssertionError(f"{class_id} stuck approaching {(x, y)} at {(player.x, player.y)}; "
                                 f"combat={player.combat_until-game.now():.1f}s")

        async def visit_npc(quest_id):
            npc = npc_for(quest_id)
            await walk(npc["x"], npc["y"])

        await visit_npc("q_rats")
        await command("quest_accept", quest_id="q_rats")
        assert quest("q_rats")["status"] == "active", "The first objective must be available immediately"
        for point in ((700, 1340), (810, 1460), (700, 1580), (910, 1660)):
            if quest("q_rats")["status"] == "ready":
                break
            await walk(*point)
            if point != (700, 1340):
                for _ in range(100):
                    if quest("q_rats")["status"] == "ready":
                        break
                    await tick()
        assert quest("q_rats")["status"] == "ready", "Three starter rats must be reachable and survivable"
        for point in ((810, 1400), (680, 1260)):
            await walk(*point)
        await visit_npc("q_rats")
        before_gold = player.gold
        await command("quest_claim", quest_id="q_rats")
        assert quest("q_rats")["status"] == "claimed" and player.gold > before_gold
        await visit_npc("q_mill")
        await command("quest_accept", quest_id="q_mill")
        assert quest("q_mill")["status"] == "active"
        mill = next(m for m in catalogue("landmarks") if m["id"] == "old_mill")
        for point in ((600, 1250), (600, 1450), (mill["x"], mill["y"])):
            await walk(*point)
        assert "old_mill" in own_state()["discoveries"]
        assert quest("q_mill")["status"] == "ready"
        discovered_gold = player.gold
        for _ in range(20):
            await tick()
        assert player.gold == discovered_gold, "Standing at a landmark must not repeat its reward"
        await walk(600, 1450)
        await walk(600, 1250)
        await visit_npc("q_mill")
        await command("quest_claim", quest_id="q_mill")
        assert quest("q_mill")["status"] == "claimed"
        assert quest("q_goblins")["status"] == "available", "The next expedition should be visible"
        weapon = next(i for i in player.inventory if i["template"] == class_id+"_weapon_2")
        assert player.level >= weapon["min_level"], "The introductory reward must already be usable"
        await command("equip", uid=weapon["uid"])
        assert player.equipment["weapon"] == weapon["uid"]
        merchant = metadata["merchant"]
        await walk(merchant["x"], merchant["y"])
        for _ in range(420):
            if player.combat_until <= game.now():
                break
            await tick()
        gold, potions = player.gold, player.potions["health_potion"]
        await command("buy", item="health_potion")
        assert player.gold < gold and player.potions["health_potion"] == potions+1
        assert player.speed > starting_speed
        result = {"class": class_id, "seconds": round(game.time, 1), "level": player.level,
                  "kills": player.kills, "gold": player.gold, "hp": round(player.hp),
                  "lowest_hp": round(min_hp), "potions_used": health_used,
                  "items": len(player.inventory), "speed": round(player.speed, 2),
                  "claimed": [q["id"] for q in own_state()["quests"] if q["status"] == "claimed"],
                  "discoveries": own_state()["discoveries"], "equipped_reward": weapon["template"]}
        print("Introductory expedition passed:", result)
        return result
    finally:
        game.db.close()


async def main():
    for class_id in ("knight", "mage"):
        await expedition(class_id)


if __name__ == "__main__":
    asyncio.run(main())
