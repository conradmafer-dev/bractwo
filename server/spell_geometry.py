"""2D projections of spell areas. One payload drives authoritative hits and VFX.
Distances use 32 world units per 5 ft. Targets use their ground-position centre.
Fire Storm defaults to ten adjacent cubes; Meteor Swarm uses four chosen-by-layout
centres until free ground targeting is added. Neither deals overlap damage twice.
"""
import math


def build(spec, source, target):
    shape = spec.get('shape', 'circle')
    dx, dy = target.x-source.x, target.y-source.y
    length = math.hypot(dx, dy)
    if length < 1e-6:
        dx, dy = getattr(source, 'facing', (0, 1)); length = math.hypot(dx, dy) or 1
    ux, uy = dx/length, dy/length
    area = dict(shape=shape, origin=[source.x, source.y], center=[target.x, target.y],
                direction=[ux,uy], length=spec['range'], width=spec.get('width',32),
                radius=spec.get('radius',0), polygons=[], circles=[])
    def oriented(x, y):
        return [source.x+ux*x-uy*y, source.y+uy*x+ux*y]
    if shape=='cone':
        r=spec['range']; area['width']=r
        area['polygons']=[[oriented(0,0),oriented(r,-r/2),oriented(r,r/2)]]
    elif shape=='line':
        r=spec['range'];w=spec.get('width',32)/2
        area['polygons']=[[oriented(0,-w),oriented(r,-w),oriented(r,w),oriented(0,w)]]
    elif shape=='square':
        w=spec.get('width',128)/2;x,y=target.x,target.y
        area['polygons']=[[[x-w,y-w],[x+w,y-w],[x+w,y+w],[x-w,y+w]]]
    elif shape=='cubes':
        side=spec.get('cube_size',64)
        for row in range(2):
            for col in range(5):
                x=target.x+(col-2.5)*side;y=target.y+(row-1)*side
                area['polygons'].append([[x,y],[x+side,y],[x+side,y+side],[x,y+side]])
    elif shape=='meteors':
        offset=spec.get('meteor_offset',160)
        area['circles']=[[target.x+dx,target.y+dy,spec['radius']] for dx,dy in ((-offset,0),(offset,0),(0,-offset),(0,offset))]
    elif shape not in ('chain','single'):
        area['circles']=[[target.x,target.y,spec.get('radius',0)]]
    points=[p for polygon in area['polygons'] for p in polygon]
    for x,y,r in area['circles']:points.extend([[x-r,y-r],[x+r,y+r]])
    if not points:points=[[target.x,target.y]]
    area['bounds']=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
    return area


def point_in_polygon(x,y,polygon):
    """Convex polygon, inclusive edges. Areas above are triangles or rectangles."""
    signs=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        cross=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])
        if abs(cross)>1e-7:signs.append(cross>0)
    return not signs or all(v==signs[0] for v in signs)


def contains(area,x,y):
    return (any((x-cx)**2+(y-cy)**2<=r*r+1e-7 for cx,cy,r in area.get('circles',[]))
        or any(point_in_polygon(x,y,p) for p in area.get('polygons',[])))


def query_radius(area,source):
    x0,y0,x1,y1=area['bounds']
    return max(math.hypot(x-source.x,y-source.y) for x,y in ((x0,y0),(x0,y1),(x1,y0),(x1,y1)))+1
