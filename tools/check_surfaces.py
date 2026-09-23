"""Cross-check actual world surface classification in Python and pure JS (no renderer)."""
import json, random, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import server as s
rng=random.Random(505)
g=s.Game(':memory:');c=s.content
points=[(rng.randrange(c.WIDTH),rng.randrange(c.HEIGHT),0) for _ in range(1000)]
for p in c.TERRAIN[::11]:
 points.extend([(p['x']+p['w']/2,p['y']+p['h']/2,0),(p['x']+p['w'],p['y'],0)])
for road in c.ROADS:
 for x,y in road[::30]:points.extend([(x,y,0),(x+36,y+36,0),(x,y,-1)])
for area in c.ELEVATIONS:
 for r in area['rooms']:
  points.extend([(r['x']+r['w']/2,r['y']+r['h']/2,area['floor']),(r['x']+20,r['y']+20,area['floor']),(r['x']-20,r['y']-20,0)])
world={key:g.metadata()[key] for key in ['roads','terrain','cities','regions']}
source="const fs=require('node:fs'),{SurfaceMap}=require('./web/runtime.js');const d=JSON.parse(fs.readFileSync(0,'utf8')),m=new SurfaceMap(d.world);process.stdout.write(JSON.stringify(d.points.map(p=>m.at(...p))));"
result=subprocess.run(['node','-e',source],input=json.dumps({'world':world,'points':points}),text=True,capture_output=True,cwd=ROOT,check=True)
actual=json.loads(result.stdout)
for point,got in zip(points,actual):
 expected=c.SURFACE_MAP.at(*point)
 if expected!=got:raise AssertionError((point,expected,got))
print(json.dumps({'matching_points':len(points),'python_js_surface_match':True}))
