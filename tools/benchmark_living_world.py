"""Synthetic active-combat load, not FPS or a graphical playtest.
24 players at separated encounters, high fixture HP prevents workload disappearing.
"""
import json, math, statistics, sys, time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import server as s
result={'version':s.content.VERSION,'monsters':len(s.content.SPAWNS)+28,'rendering_measured':False}
for count in (1,24):
 game=s.Game(':memory:')
 players=[]
 for i in range(count):
  camp=s.content.HUNTING_GROUNDS[(i*157)%len(s.content.HUNTING_GROUNDS)]
  x,y=camp['x']+310,camp['y']
  while game.blocked(x,y):y+=30
  p=s.Player(str(i+1),'Bench',ws=SimpleNamespace(closed=False),x=x,y=y,level=100,discoveries=[l['id'] for l in s.LANDMARKS])
  game.starter(p);p.hp=1_000_000;game.players[p.id]=p;players.append(p)
 for _ in range(30):game.step(.05)
 times=[]
 for _ in range(300):
  start=time.perf_counter();game.step(.05);times.append((time.perf_counter()-start)*1000)
 game.compact_clients.update(game.players)
 for p in players:game.wire_snapshot(p)
 start=time.perf_counter()
 packets=[game.wire_snapshot(p) for p in players]
 snapshot_ms=(time.perf_counter()-start)*1000
 result[str(count)]={'mean_step_ms':round(statistics.mean(times),3),'p95_step_ms':round(sorted(times)[int(len(times)*.95)],3),'max_step_ms':round(max(times),3),'snapshot_batch_ms':round(snapshot_ms,3),'mean_packet_bytes':round(statistics.mean(len(json.dumps(p)) for p in packets)),'damaged_players':sum(p.hp<1_000_000 for p in players),'alive_players':sum(p.alive for p in players)}
 game.db.close()
print(json.dumps(result,indent=2))
