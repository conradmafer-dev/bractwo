"""Focused UI19 integration: real collision, local approaches and transport graph.

Run this file directly; it writes docs/qa_0.8.18/ui19/continent_results.json.
No browser or live server is started, and SQLite stays in memory.
"""
import json
import math
import sys
import time
import unittest
from collections import deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEPS=ROOT.parent/'Bractwo_0.8.17'/'.qa-python'
sys.path[:0]=[str(ROOT),str(DEPS)]
REPORT={'suite':'UI19 continent integration','checks':{}}


class ContinentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server import server as s
        from server import continent_world as geography
        cls.s=s;cls.c=s.content;cls.geo=geography;cls.game=s.Game(':memory:')

    @classmethod
    def tearDownClass(cls):
        cls.game.db.close()

    def blocked(self,p):
        return self.game.blocked(p['x'],p['y'],radius=18,floor=p.get('floor',0))

    def test_01_all_gameplay_points_use_real_unblocked_tiles(self):
        groups={'npcs':[dict(p) for p in self.s.NPCS]+[dict(self.s.MERCHANT,id='starter_merchant')],
                'stair_origins':self.c.STAIRS,
                'stair_destinations':[dict(id=p['id'],x=p['to_x'],y=p['to_y'],floor=p['to_floor']) for p in self.c.STAIRS],
                'ports':self.c.PORTS,
                'new_discoveries':[p for p in self.s.LANDMARKS if p['id'].startswith(('adv_','landing_')) or p['id'] in {'city_'+r[0] for r in self.geo.NEW_CITIES}],
                'spawns':[dict(id=e.id,kind=e.kind,x=e.x,y=e.y,floor=e.floor) for e in self.game.enemies.values()]}
        failures=[];counts={}
        for group,points in groups.items():
            counts[group]=len(points)
            for p in points:
                if self.blocked(p):failures.append(dict(group=group,id=p['id'],x=p['x'],y=p['y'],floor=p.get('floor',0)))
        REPORT['checks']['collision']={'counts':counts,'failures':failures}
        self.assertFalse(failures,json.dumps(failures[:30],ensure_ascii=False))

    def _local_road(self,point):
        """Four-way walking BFS; short segments are collision sampled too.

        A lone decorative stub does not qualify: the reached road must extend
        at least 900 units away from the service/entrance being checked.
        """
        x,y=point['x'],point['y'];step=32;limit=1152
        if self.blocked(point):return False,0,'blocked_start'
        segments={}
        for path in self.c.ROADS:
            if not any(math.hypot(q[0]-x,q[1]-y)>900 for q in path):continue
            for a,b in zip(path,path[1:]):
                if max(a[0],b[0])<x-limit-40 or min(a[0],b[0])>x+limit+40 or max(a[1],b[1])<y-limit-40 or min(a[1],b[1])>y+limit+40:continue
                for cx in range(math.floor((min(a[0],b[0])-34)/128),math.floor((max(a[0],b[0])+34)/128)+1):
                    for cy in range(math.floor((min(a[1],b[1])-34)/128),math.floor((max(a[1],b[1])+34)/128)+1):segments.setdefault((cx,cy),[]).append((a,b))
        if not segments:return False,0,'no_regional_road_nearby'
        pending=deque([(0,0)]);seen={(0,0)};free={}
        def clear(px,py):
            key=(px,py)
            if key not in free:free[key]=not self.game.blocked(px,py,radius=18,floor=0)
            return free[key]
        while pending:
            ix,iy=pending.popleft();px,py=x+ix*step,y+iy*step
            if any(self.geo.segment_distance(px,py,a,b)<=30 for a,b in segments.get((int(px//128),int(py//128)),())):return True,len(seen),''
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                key=ix+dx,iy+dy
                if key in seen or abs(key[0]*step)>limit or abs(key[1]*step)>limit:continue
                seen.add(key)
                if all(clear(px+dx*step*t,py+dy*step*t) for t in (.25,.5,.75,1)):pending.append(key)
        return False,len(seen),'no_walkable_approach'

    def test_02_local_services_ports_and_entrances_reach_regional_roads(self):
        groups={'npcs':[p for p in self.s.NPCS if p.get('floor',0)==0]+[dict(self.s.MERCHANT,id='starter_merchant')],
                'surface_stairs':[p for p in self.c.STAIRS if p.get('floor',0)==0],
                'ports':self.c.PORTS,'adventure_anchors':list(self.c.ADVENTURE_ANCHORS.values())}
        failures=[];counts={};visited=0;cache={}
        for group,points in groups.items():
            counts[group]=len(points)
            for p in points:
                key=(p['x'],p['y'])
                if key not in cache:cache[key]=self._local_road(p)
                passed,nodes,reason=cache[key];visited+=nodes
                if not passed:failures.append(dict(group=group,id=p['id'],x=p['x'],y=p['y'],reason=reason))
        REPORT['checks']['local_approaches']={'counts':counts,'visited_nodes':visited,'failures':failures}
        self.assertFalse(failures,json.dumps(failures,ensure_ascii=False))

    def test_03_port_network_and_authored_region_plans(self):
        ports={p['id']:p for p in self.c.PORTS};edges={(r['from_id'],r['to_id']) for r in self.c.SEA_ROUTES}
        failures=[]
        if len(ports)!=len(self.c.PORTS):failures.append('duplicate port ID')
        for route in self.c.SEA_ROUTES:
            if route['from_id'] not in ports or route['to_id'] not in ports:failures.append('unknown port: '+route['id'])
            if (route['to_id'],route['from_id']) not in edges:failures.append('missing return: '+route['id'])
            if route['cost']<0 or route['min_level']<1:failures.append('invalid route terms: '+route['id'])
        pending=list(ports)[:1];seen=set(pending)
        while pending:
            node=pending.pop()
            for a,b in edges:
                if a==node and b not in seen:seen.add(b);pending.append(b)
        if seen!=set(ports):failures.append('disconnected ports: '+','.join(sorted(set(ports)-seen)))
        plans={json.dumps(p,separators=(',',':')) for p in self.geo.REGIONAL_ROUTES}
        if len(plans)!=20:failures.append('regional route plans are repeated')
        # Verify that distinct plans survived construction, rather than merely
        # existing as unused metadata: compare the actual normalized road cells.
        signatures=[]
        for r in self.c.REGIONS:
            cells={(int((x-r['x'])/r['w']*32),int((y-r['y'])/r['h']*32)) for path in self.c.ROADS for x,y in path
                   if r['x']<=x<r['x']+r['w'] and r['y']<=y<r['y']+r['h']}
            signatures.append(tuple(sorted(cells)))
            if len(cells)<10:failures.append('missing road layout: '+r['id'])
        if len(set(signatures))!=20:failures.append('actual road footprints repeat')
        REPORT['checks']['transport_and_variety']={'ports':len(ports),'directed_routes':len(edges),'reachable_ports':len(seen),
            'authored_plans':len(plans),'distinct_actual_road_footprints':len(set(signatures)),'failures':failures}
        self.assertFalse(failures,'; '.join(failures))


if __name__=='__main__':
    start=time.perf_counter()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContinentIntegration))
    REPORT.update(passed=result.wasSuccessful(),tests=result.testsRun,seconds=round(time.perf_counter()-start,3),
                  errors=[str(error) for _,error in result.errors],failures=len(result.failures))
    output=ROOT/'docs'/'qa_0.8.18'/'ui19'/'continent_results.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    print(output)
    raise SystemExit(0 if result.wasSuccessful() else 1)
