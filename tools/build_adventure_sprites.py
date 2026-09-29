"""Build the original code-drawn, four-frame UI_19 creature sprites."""
from pathlib import Path

DEST=Path(__file__).resolve().parents[1]/'web/assets/monsters/adventure'
DEST.mkdir(parents=True,exist_ok=True)

def rect(x,y,w,h,c):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>'
def poly(points,c):return f'<polygon points="{points}" fill="{c}"/>'
def path(d,c,stroke=None,width=1):return f'<path d="{d}" fill="{c}"'+(f' stroke="{stroke}" stroke-width="{width}"' if stroke else '')+'/>'

def bat(n):
    lift=[0,-5,0,5][n];s=''
    for mirror in (False,True):
        s+=f'<g transform="'+('translate(80 0) scale(-1 1)' if mirror else '')+'">'
        s+=poly(f'36,40 26,{23+lift} 8,{14+lift} 3,{44+lift} 12,43 18,50 26,48 35,57','#312c3d')
        s+=poly(f'34,43 24,{29+lift} 11,{22+lift} 9,{37+lift} 17,39 21,45 28,43','#76647d')
        s+=path(f'M34 45 L12 {22+lift} M28 45 L24 {29+lift}','none','#b192a6',2)+'</g>'
    s+=poly('29,21 36,29 44,29 51,21 49,37 48,55 44,62 36,62 32,55 30,38','#52485d')
    s+=rect(35,36,11,17,'#ad93b0')+rect(32,33,5,4,'#edb892')+rect(44,33,5,4,'#edb892')
    s+=rect(34,34,2,3,'#241f29')+rect(45,34,2,3,'#241f29')+poly('38,42 42,42 40,45','#dfb2a5')
    s+=rect(34,60,4,5,'#b49294')+rect(44,60,4,5,'#b49294');return s

def sword(n):
    b=[0,-2,0,2][n]
    s=f'<g transform="translate(0 {b})">'+path('M17 56 Q7 27 37 18 M61 21 Q77 49 45 67','none','#406866',2)
    s+=poly('25,62 34,51 28,45 31,41 39,46 58,14 64,9 65,19 45,50 53,57 49,61 41,55 33,67','#253941')
    s+=poly('38,46 58,15 62,12 62,19 43,49','#bddde3')+poly('41,46 61,16 61,21 44,48','#779ba9')
    s+=poly('29,45 32,43 50,57 49,59','#dac78a')+poly('29,60 36,51 40,55 33,64','#785d47')
    s+=poly('25,63 29,60 33,64 30,68','#a9e7df')+rect(14,36,3,3,'#82b7ac')+rect(61,50,3,3,'#82b7ac')+'</g>';return s

def armor(n):
    step=[0,2,0,-2][n];s=''
    s+=rect(28,51+step,10,17-step,'#34434d')+rect(44,51-step,10,17+step,'#34434d')
    s+=rect(26,64,13,6,'#879da3')+rect(43,64,13,6,'#879da3')
    s+=poly('27,29 36,25 47,25 57,31 53,51 44,58 32,53','#394d58')
    s+=poly('29,31 39,29 41,50 34,51 29,44','#a3b8ba')+poly('42,29 52,32 50,48 44,51','#748b94')
    s+=rect(22,31+step,10,10,'#a3b8ba')+rect(52,31-step,10,10,'#a3b8ba')
    s+=rect(20,41+step,9,13,'#617983')+rect(55,41-step,9,13,'#617983')
    s+=rect(19,51+step,11,8,'#a3b8ba')+rect(54,51-step,11,8,'#a3b8ba')
    s+=poly('32,15 46,15 51,22 48,30 34,30 29,23','#a3b8ba')+rect(31,23,18,5,'#182b32')
    s+=rect(37,23,6,2,'#68d1bd')+rect(37,15,5,6,'#ced5ca')+rect(29,51,24,5,'#6d6650');return s

def gargoyle(n):
    lift=[0,-3,0,3][n];s=''
    for mirror in (False,True):
        s+=f'<g transform="'+('translate(80 0) scale(-1 1)' if mirror else '')+'">'
        s+=poly(f'34,43 27,{24+lift} 10,{17+lift} 7,{45+lift} 15,41 20,49 30,49','#414d4d')
        s+=poly(f'31,41 24,{29+lift} 14,{24+lift} 12,{38+lift} 22,42','#7c8b81')+'</g>'
    s+=poly('33,32 49,32 56,51 51,61 56,69 44,69 41,56 36,68 23,68 29,59 25,48','#5b6665')
    s+=poly('36,34 45,34 49,50 42,57 33,50','#abb3a6')
    s+=rect(22,44,7,18,'#7c8b81')+rect(51,44,7,18,'#7c8b81')
    s+=poly('29,22 27,13 36,21 46,21 53,13 51,31 45,37 35,35','#abb3a6')
    s+=rect(32,27,5,3,'#cae6ac')+rect(44,27,5,3,'#cae6ac')+poly('36,32 47,32 45,37 39,37','#384345')
    s+=rect(22,66,15,5,'#abb3a6')+rect(44,66,14,5,'#abb3a6')
    return s

def grick(n):
    b=[0,2,0,-2][n]
    s=path('M15 64 Q8 55 15 52 Q18 67 33 54 L36 37 L49 33 Q65 53 54 65 Q40 78 22 71Z','#514f43','#303a32',2)
    s+=path('M22 67 Q43 73 48 55 L45 42 L38 45 L35 61Z','#96927b')
    s+=path('M37 35 Q18 31 21 15 Q13 23 21 35 L30 42 M48 35 Q64 26 58 14 Q71 24 64 38 L55 44', 'none','#a7aa8c',6)
    s+=path(f'M34 40 Q14 {44+b} 13 {57+b} M53 41 Q71 {43-b} 70 {55-b}','none','#96927b',7)
    s+=path(f'M34 40 Q14 {44+b} 13 {57+b} M53 41 Q71 {43-b} 70 {55-b}','none','#5e6856',2)
    s+=poly('37,26 49,26 55,36 50,45 38,46 30,36','#747c63')+poly('40,30 48,33 47,40 39,43 42,37','#d5b477')
    s+=poly('42,32 45,35 44,38 41,37','#4c4336');return s

def ogre(n):
    step=[0,2,0,-2][n]
    s=rect(25,50+step,13,19-step,'#56623e')+rect(44,51-step,14,18+step,'#6d7951')
    s+=rect(21,65,18,7,'#92966e')+rect(44,65,18,7,'#92966e')
    s+=poly('25,25 50,22 61,39 57,57 47,61 26,57 20,42','#718157')
    s+=poly('31,27 46,28 51,48 41,52 29,46','#a4ad7e')
    s+=rect(15,31+step,13,22,'#596949')+rect(12,48+step,13,11,'#929c6c')
    s+=rect(55,30-step,11,22,'#a4ad7e')+rect(60,48-step,11,11,'#79895c')
    s+=poly('59,35 65,33 73,65 65,67','#795e44')+poly('62,36 58,19 65,15 72,18 71,37','#665948')
    s+=poly('27,11 46,10 51,18 47,33 34,36 26,25','#a4ad7e')+poly('28,12 35,9 48,12 47,19 43,15 31,17','#48543f')
    s+=rect(29,21,6,3,'#e5b482')+rect(40,20,6,4,'#283b32')+poly('30,29 44,27 43,35 34,36','#4a4c39')
    s+=rect(32,29,4,5,'#dac2a0')+rect(40,28,3,4,'#dac2a0')+poly('24,51 58,51 55,63 45,60 38,63 25,59','#655546')
    s+=rect(30,39,14,3,'#d2c399')+rect(31,44,14,3,'#d2c399');return s

for name,draw in [('giant_bat',bat),('flying_sword',sword),('animated_armor',armor),('gargoyle',gargoyle),('grick',grick),('ogre_zombie',ogre)]:
    frames=''.join(f'<g transform="translate({80*n} 0)">{draw(n)}</g>' for n in range(4))
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80" viewBox="0 0 320 80" shape-rendering="crispEdges">'+frames+'</svg>\n'
    (DEST/f'adv_{name}.svg').write_text(svg,encoding='utf-8')
print('Built six original four-frame creature sprites.')
