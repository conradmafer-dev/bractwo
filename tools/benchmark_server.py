"""Synthetic stationary-player server benchmark. This does not measure client FPS.
Run: python tools/benchmark_server.py [path-to-another-project]
"""
import cProfile, io, pstats, sys, time, tempfile, json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1] if len(sys.argv)>1 else str(Path(__file__).resolve().parents[1]))
from server import server as s
from server import world_content as c
result={}
for count in (1,24):
 with tempfile.TemporaryDirectory() as directory:
  game=s.Game(str(Path(directory)/'bench.sqlite3'))
  for i in range(count):
   camp=c.HUNTING_GROUNDS[(i*59)%len(c.HUNTING_GROUNDS)]
   p=s.Player(str(i+1),'Bench'+str(i),ws=SimpleNamespace(closed=False),level=100,x=camp['x']+550,y=camp['y'],discoveries=[d['id'] for d in s.LANDMARKS])
   game.starter(p);p.hp=p.max_hp;p.mana=p.max_mana;game.players[p.id]=p
  pr=cProfile.Profile();pr.enable()
  for _ in range(20):game.step(.05)
  pr.disable()
  start=time.perf_counter()
  for _ in range(240):game.step(.05)
  step_ms=(time.perf_counter()-start)*1000/240
  start=time.perf_counter()
  states=[game.snapshot(p) for p in game.players.values()]
  snapshot_ms=(time.perf_counter()-start)*1000
  if hasattr(game, "wire_snapshot"):
   game.compact_clients.update(game.players)
   for p in game.players.values():game.wire_snapshot(p)
   states=[game.wire_snapshot(p) for p in game.players.values()]
  result[str(count)]={'step_ms':round(step_ms,3),'snapshot_batch_ms':round(snapshot_ms,3),'mean_packet_bytes':round(sum(len(json.dumps(q)) for q in states)/count),'monsters':len(game.enemies)}
  stream=io.StringIO();pstats.Stats(pr,stream=stream).sort_stats('cumulative').print_stats(9)
  print(str(count)+' players\n'+stream.getvalue(),file=sys.stderr)
  game.db.close()
print(json.dumps(result,indent=2))
