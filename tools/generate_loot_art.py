"""Original offline artwork: item SVG icons and four-frame pixel monster atlases.
Pillow is a developer-only dependency. No external art, fonts or runtime downloads.
"""
from pathlib import Path
import sys, hashlib
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.hunt_content import PALETTES


def item_icon(key,item):
    kind=item.get('art_kind','trophy')
    if key.startswith('loot_trophy_'):
        creature=key.removeprefix('loot_trophy_')
        kind={'rat':'tail','boar':'tusk','wolf':'fur','bear':'fur','frost_wolf':'fur',
              'crocodile':'scale','nightmare':'mane','spider':'silk','spitting_spider':'venom',
              'scorpion':'stinger','scarab':'scarab','harpy':'feather','ghoul':'claw',
              'dragon':'scale','dragon_lord':'scale'}.get(creature,kind)
    themes={'mummy':('#d4b578','#4fe4ca'),'hierophant':('#e4c77d','#5af0d5'),
      'crypt':('#a8bab0','#73d4d1'),'grave':('#b8acbd','#b295e6'),'acolyte':('#a995bc','#8dbbdd'),
      'frost':('#c6e0eb','#77d8ff'),'winter':('#bcd9eb','#73cfff'),'thorn':('#9cb66a','#c7e876'),
      'root':('#b39c69','#71dd91'),'obsidian':('#aaa0c3','#ed9571'),'abyss':('#b1a2d1','#c193ee'),
      'dragon':('#c5a25e','#ffbd69'),'ember':('#c8986a','#ff8c55'),'skeleton':('#d6d0b3','#a1d8ce'),
      'orc':('#a7b989','#e2c46b'),'captain':('#ccc0a0','#ce7f57'),'elven':('#b2c092','#84daa1'),
      'lich':('#b6a7cd','#b38cdd'),'night':('#aaa6bd','#dc9ed0')}
    metal,gem=next((v for k,v in themes.items() if k in key),('#c9c8b2','#e8b469'))
    edge={'common':'#627b70','uncommon':'#6ea383','rare':'#749fcf','epic':'#b296cd','legendary':'#eac377'}.get(item.get('rarity'),'#627b70')
    out=f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><defs>
      <linearGradient id="bg" x2=".9" y2="1"><stop stop-color="#304448"/><stop offset="1" stop-color="#111f27"/></linearGradient>
      <linearGradient id="metal" x2="1" y2=".7"><stop stop-color="#faf0d4"/><stop offset=".42" stop-color="{metal}"/><stop offset="1" stop-color="#5e737b"/></linearGradient></defs>
      <rect x="2" y="2" width="60" height="60" rx="10" fill="url(#bg)" stroke="{edge}" stroke-width="2"/>
      <ellipse cx="32" cy="52" rx="20" ry="5" fill="#071318" opacity=".6"/>
      <g stroke="#17262e" stroke-width="1.8" stroke-linejoin="round">'''
    if kind in ('sword','greatsword','sabre','axe','hammer'):
        shape='<path d="M30 42V14L34 7L38 14V42Z" fill="url(#metal)"/><path d="M34 13V38" stroke="#f7eccb"/>'
        if kind=='sabre':shape='<path d="M30 42Q29 22 43 8Q39 31 36 42Z" fill="url(#metal)"/><path d="M34 37Q34 22 41 13" stroke="#f8eccb"/>'
        if kind=='greatsword':shape='<path d="M28 42V16L34 6L40 16V42Z" fill="url(#metal)"/><path d="M34 13V40" stroke="#f5edda"/>'
        if kind=='axe':shape='<path d="M31 45L33 12L37 12L35 45Z" fill="#a78354"/><path d="M32 14L20 11L16 28L31 26L38 26L49 32L50 10L38 14Z" fill="url(#metal)"/><path d="M21 14L18 25M48 13V28" stroke="#f7ecd2"/>'
        if kind=='hammer':shape='<path d="M31 48V19H37V48Z" fill="#ac8458"/><path d="M18 10H46L49 25H16Z" fill="url(#metal)"/><path d="M21 13H42V20H21Z" fill="#93a6a4"/>'
        out+=f'<g transform="rotate(32 32 32)">{shape}<path d="M23 41Q34 38 45 41L43 46H24Z" fill="{metal}"/><path d="M31 44H37V55H31Z" fill="#92603d"/><path d="M29 54H39V58H29Z" fill="{gem}"/><path d="M31 48H37M31 51H37" stroke="#d0a576"/></g>'
    elif kind=='bow':
        out+=f'<path d="M23 8Q53 31 24 56L30 47Q43 31 29 18Z" fill="#ac895a"/><path d="M23 8L18 31L24 56" fill="none" stroke="#e7d9b6"/><path d="M9 35L49 26" stroke="#d6bf81"/><path d="M48 22L57 24L50 30Z" fill="url(#metal)"/><path d="M10 32L17 31M11 37L18 36" stroke="{gem}"/><path d="M34 28L38 34L33 37L30 32Z" fill="{gem}"/>'
    elif kind in ('wand','nature_staff'):
        out+=f'<path d="M17 55L39 15L44 18L22 57Z" fill="#9b7a4f"/><path d="M21 51L25 53M24 45L28 47M29 36L34 38" stroke="{metal}"/>'
        if kind=='wand':out+=f'<path d="M34 17L34 8L44 6L52 13L47 24L39 25Z" fill="{metal}"/><path d="M38 14L43 9L49 14L44 21L40 20Z" fill="{gem}"/><path d="M39 13L43 11" stroke="#f4f8e7"/>'
        else:out+=f'<path d="M35 24Q20 8 38 7Q52 4 49 19L40 24" fill="none" stroke="#a9a575" stroke-width="6"/><path d="M31 11Q18 8 23 23Q30 24 33 17M44 25Q55 26 55 13Q45 13 44 25" fill="{gem}"/><circle cx="39" cy="17" r="4" fill="{gem}"/>'
    elif kind in ('light','medium','heavy','robe'):
        out+=f'<path d="M23 11L14 16L7 30L17 35L20 51Q32 56 46 51L48 35L58 30L50 16L41 11Q33 17 23 11Z" fill="{metal}"/><path d="M25 12L28 22H37L41 12" fill="#344d50"/>'
        if kind=='light':
            out+='<path d="M21 19L27 24L29 43L20 45L17 29ZM43 19L37 24L35 43L45 45L48 29Z" fill="#806246"/><path d="M21 43H45V49H21Z" fill="#594534"/>'
            for y in (27,34):
                for x in (23,39):out+=f'<circle cx="{x}" cy="{y}" r="1.3" fill="{gem}" stroke="none"/>'
        elif kind=='medium':
            out+='<path d="M22 21L42 21L46 43L33 49L19 43Z" fill="url(#metal)"/>'
            for y in (25,32,39):
                for x in (24,32,40):out+=f'<path d="M{x-3} {y}L{x} {y+5}L{x+3} {y}" fill="none" stroke="#637575" stroke-width="1"/>'
        elif kind=='heavy':
            out+='<path d="M11 18L20 15L23 26L16 31L8 27ZM43 15L53 18L58 27L49 31L42 26Z" fill="url(#metal)"/><path d="M23 21L33 25L43 21L45 40L33 47L20 40Z" fill="url(#metal)"/><path d="M33 25V42M20 47H46" fill="none" stroke="#e3decd"/>'
        else:out+=f'<path d="M24 18L30 26L22 53L17 50L22 25ZM42 18L35 26L44 53L48 50L45 25Z" fill="#524f72"/><path d="M31 23V48M28 45L33 48L38 45" stroke="{gem}"/><path d="M23 14L32 26L42 14" fill="none" stroke="{gem}"/>'
        out+=f'<path d="M29 37L33 33L37 37L33 41Z" fill="{gem}"/>'
    elif kind=='fur':
        fur='#d7e5e9' if 'frost' in key else '#8b745d' if 'bear' in key else '#9caeac'
        out+=f'<path d="M22 9L32 15L42 9L46 19L56 26L49 36L51 50L39 47L32 56L25 47L13 50L15 36L8 26L18 19Z" fill="{fur}"/><path d="M31 18L27 30L32 44L37 30Z" fill="#5b6e73"/><path d="M19 25L21 32M43 25L41 32M22 39L25 44M42 39L39 44" stroke="#e0d7be"/>'
    elif kind=='tail':out+='<path d="M18 14Q38 10 42 26Q48 43 31 46Q16 48 21 35Q25 27 31 32" fill="none" stroke="#b98981" stroke-width="7"/><path d="M20 11L19 18M28 13L26 19M36 18L31 22M41 26L36 28M42 36L36 35M36 43L33 38M26 44L26 38" stroke="#d9b6a3"/>'
    elif kind in ('tusk','claw','stinger'):
        shade='#bfbaa1' if kind!='stinger' else '#927959'
        out+=f'<path d="M15 46Q18 34 32 34Q48 30 45 8Q59 39 38 52Q24 62 15 46Z" fill="{shade}"/><path d="M22 45Q37 43 43 32" stroke="#ece3c6"/>'
        if kind=='claw':out+='<path d="M11 38Q15 27 25 29Q36 22 32 10Q48 30 28 42Z" fill="#d1c7ad"/>'
        if kind=='stinger':out+=f'<path d="M16 49L24 40M22 54L30 44M32 53L36 43" stroke="#594c40"/><circle cx="48" cy="12" r="3" fill="{gem}"/>'
    elif kind=='scale':
        for x,y in ((20,16),(34,12),(42,24),(19,32),(31,29)):
            out+=f'<path d="M{x-7} {y}Q{x} {y-7} {x+7} {y}L{x+5} {y+13}L{x} {y+20}L{x-5} {y+13}Z" fill="{metal}"/><path d="M{x} {y-2}V{y+15}" stroke="{gem}"/>'
    elif kind=='feather':out+=f'<path d="M14 48Q4 21 32 8Q47 6 49 14Q58 40 14 48Z" fill="{gem}"/><path d="M12 54L42 16M22 42L18 26M28 33L26 20M33 25L33 15M20 43L33 42M27 34L42 30" stroke="{metal}"/>'
    elif kind=='mane':out+=f'<path d="M14 46Q12 19 32 9L46 14Q42 30 53 47L39 41L42 55L30 47L24 56L21 44Z" fill="#61566e"/><path d="M30 17Q19 38 24 46M37 20Q33 34 39 43M42 22Q38 31 44 38" fill="none" stroke="{gem}"/>'
    elif kind=='silk':
        out+='<ellipse cx="31" cy="33" rx="20" ry="17" fill="#b4c9c0"/>'
        for y in (21,26,31,36,41):out+=f'<path d="M15 {y+3}Q29 {y-7} 47 {y+3}" fill="none" stroke="#eef0dc"/>'
        out+='<path d="M45 38Q59 47 41 53Q29 60 27 53" fill="none" stroke="#dfe8d8"/>'
    elif kind=='venom':out+='<path d="M25 12H38V24Q55 34 48 47Q32 60 17 46Q11 34 25 24Z" fill="#618c67"/><path d="M20 34Q32 42 46 32L47 45Q33 55 19 43Z" fill="#b5d85d"/><path d="M24 9H39V17H24Z" fill="#ba9a61"/><path d="M22 28L18 35M26 23L23 27" stroke="#e9ecbf"/>'
    elif kind=='scarab':
        out+=f'<ellipse cx="32" cy="33" rx="15" ry="20" fill="{metal}"/><path d="M32 15V52M19 27H45M16 21L9 16M17 34L8 36M19 46L12 54M48 21L55 16M47 34L56 36M45 46L52 54" fill="none" stroke="{gem}"/><path d="M25 17Q22 8 32 7Q42 8 39 17Z" fill="{gem}"/>'
    elif kind=='ring':out+=f'<ellipse cx="32" cy="38" rx="16" ry="16" fill="none" stroke="{metal}" stroke-width="7"/><path d="M21 24L27 13H39L45 24L32 34Z" fill="{metal}"/><path d="M26 23L30 16H36L40 23L32 29Z" fill="{gem}"/>'
    elif kind=='essence':out+=f'<path d="M15 42L18 25L26 13L33 25L42 9L50 36L41 53L25 56Z" fill="{gem}"/><path d="M26 16L27 45L33 28M42 12L39 45L47 36" fill="none" stroke="#eef6dc"/><path d="M18 40L27 47L39 44L45 51L25 56Z" fill="{metal}"/>'
    else:out+=f'<path d="M18 16Q24 11 29 19L34 27L47 22Q54 25 48 31L36 37L29 48Q23 57 18 51L19 44L24 35L15 30Q10 23 18 16Z" fill="{metal}"/><path d="M24 22L31 31L25 44" fill="none" stroke="#f3e3bb"/><path d="M41 30L46 27" stroke="{gem}"/>'
    out+=f'<circle cx="52" cy="51" r="6" fill="#1c3037" stroke="{edge}"/><path d="M49 51L52 47L55 51L52 55Z" fill="{gem}"/>'
    # Unique stamped marks, plus enchantment notches.
    seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
    for i in range(4):
        if seed&(1<<i):out+=f'<path d="M{8+i*4} 55V{52-i%2}" stroke="{edge}" stroke-width="1"/>'
    for i in range(item.get('enchantment',0)):out+=f'<path d="M{8+i*4} 9V12" stroke="{edge}" stroke-width="2"/>'
    return out+'</g></svg>'


def col(hex,factor=1):
    return tuple(max(0,min(255,round(int(hex[i:i+2],16)*factor))) for i in (1,3,5))+(255,)


def monster_frame(kind,palette,frame):
    im=Image.new('RGBA',(80,80));d=ImageDraw.Draw(im)
    coat,skin,accent=palette;C=col(coat);S=col(skin);A=col(accent);ink=(22,33,38,255);metal=(160,183,189,255)
    step=(0,2,0,-2)[frame];arm=-step;bob=abs(step)//2
    mummy=kind in ('mummy','mummy_hierophant');skeleton=kind in ('skeleton_sentinel','crypt_guard','skeleton_archer')
    caster=kind in ('grave_acolyte','thorn_shaman','mummy_hierophant','mummy')
    archer=kind in ('skeleton_archer','frost_ranger');heavy=kind in ('skeleton_sentinel','crypt_guard','obsidian_knight','bandit_captain')
    def rect(box,fill,outline=None):d.rectangle(box,fill=fill,outline=outline)
    def poly(points,fill,outline=ink):d.polygon(points,fill=fill,outline=outline)
    for x,offset in ((27,step),(43,-step)):
        rect((x,54+offset,x+7,68+offset),col(coat,.6),ink);rect((x-2,66+offset,x+9,71+offset),C,ink)
    if caster:
        poly([(26,29),(48,28),(55+step,65),(44,70),(37,66),(22-step,70)],C)
        d.line([(28,32),(24-step,64),(33,61)],fill=col(coat,1.25),width=3)
        d.line([(44,33),(48+step,63),(40,61)],fill=col(coat,.65),width=3)
    else:
        poly([(27,28+bob),(48,28+bob),(52,54),(46,63),(26,61),(23,47)],C)
        rect((28,32+bob,36,50),col(coat,1.3));rect((27,51,49,55),col(coat,.55),ink);rect((37,51,41,55),A)
    rect((20,31+bob,26,47+arm),C,ink);rect((21,45+arm,27,51+arm),S,ink)
    rect((48,32+bob,55,48-arm),C,ink);rect((50,45-arm,56,51-arm),S,ink)
    if heavy:
        poly([(25,30),(37,34),(48,29),(50,47),(37,52),(26,48)],metal if skeleton else col(coat,1.35))
        poly([(25,27),(30,32),(24,39),(16,37),(17,30)],col(coat,1.5))
        poly([(46,29),(55,28),(60,37),(53,41),(46,34)],col(coat,1.3));d.line([(37,35),(37,46)],fill=A,width=2)
    if skeleton:
        rect((28,33,46,49),ink);rect((36,33,39,49),S)
        for yy in (35,40,45):rect((29,yy,46,yy+1),S)
        if heavy:rect((32,43,43,47),metal)
    rect((27,10+bob,49,31+bob),ink);rect((29,11+bob,47,29+bob),S);rect((30,12+bob,36,16+bob),col(skin,1.15))
    if skeleton or mummy:
        rect((31,20+bob,35,24+bob),ink);rect((41,20+bob,45,24+bob),ink);rect((37,25+bob,39,28+bob),col(skin,.55))
        if skeleton:
            for xx in (33,37,41):rect((xx,29+bob,xx+1,31+bob),S)
    else:rect((31,20+bob,34,22+bob),ink);rect((42,20+bob,45,22+bob),ink);rect((35,26+bob,43,27+bob),col(skin,.6))
    if heavy:
        poly([(25,13+bob),(28,6+bob),(45,5+bob),(52,14+bob),(47,18+bob),(29,16+bob)],C)
        d.line([(30,9+bob),(44,8+bob)],fill=metal,width=2);rect((26,16+bob,29,31+bob),C);rect((47,17+bob,50,30+bob),C)
        if kind in ('bandit_captain','obsidian_knight'):poly([(34,6+bob),(38,0),(43,4+bob),(46,8+bob)],A)
    elif not mummy:
        poly([(25,14+bob),(27,7+bob),(42,4+bob),(50,11+bob),(49,16+bob),(38,11+bob)],C)
        if caster:rect((25,16+bob,29,30+bob),C);rect((47,16+bob,50,30+bob),C)
    if mummy:
        for yy in (14,18,27):d.line([(29,yy+bob),(47,yy+bob-2)],fill=col(skin,.68),width=2)
        for yy in range(35,57,5):d.line([(28,yy),(48,yy-2)],fill=S,width=3)
        if kind=='mummy_hierophant':
            poly([(24,19),(24,7),(30,4),(34,9),(38,1),(43,8),(47,4),(52,7),(52,19)],col('#b79b55'))
            rect((27,10,50,13),A);rect((25,21,29,36),col('#c1a159'));rect((48,21,52,36),col('#c1a159'))
    if archer:
        d.line([(58,23-arm),(67,32-arm),(69,45-arm),(65,57-arm),(56,65-arm)],fill=ink,width=5)
        d.line([(58,23-arm),(65,33-arm),(67,45-arm),(63,57-arm),(56,65-arm)],fill=A,width=3)
        d.line([(58,23-arm),(56,65-arm)],fill=(222,225,191),width=1)
        d.line([(47,46-arm),(73,42-arm)],fill=metal,width=2);poly([(70,38-arm),(78,41-arm),(71,45-arm)],metal)
        rect((15,31,20,52),col(coat,.6),ink)
        for xx in (16,20):d.line([(xx,36),(xx-3,20)],fill=A,width=2)
    elif caster:
        d.line([(57,63),(63,15+arm)],fill=ink,width=6);d.line([(57,63),(63,15+arm)],fill=col('#a79465'),width=4)
        if kind=='thorn_shaman':
            poly([(62,25+arm),(54,18+arm),(53,10+arm),(62,14+arm),(70,7+arm),(70,18+arm)],A)
            for yy in (37,48):poly([(58,yy),(52,yy-3),(54,yy+5)],A)
        else:
            d.ellipse((56,8+arm,70,21+arm),fill=col(coat,.6),outline=A,width=2)
            poly([(62,8+arm),(67,14+arm),(62,19+arm),(58,14+arm)],A);rect((61,11+arm,63,14+arm),(234,253,235,255))
    else:
        d.line([(56,56-arm),(65,19-arm)],fill=ink,width=7)
        poly([(59,40-arm),(62,20-arm),(66,13-arm),(69,21-arm),(64,42-arm)],metal if kind!='obsidian_knight' else col('#a497c5'))
        d.line([(65,20-arm),(62,38-arm)],fill=A,width=2);d.line([(55,42-arm),(68,44-arm)],fill=A,width=4)
        if heavy:
            poly([(15,42),(23,38),(29,42),(27,55),(21,62),(14,55)],C);d.line([(20,43),(21,55)],fill=A,width=3)
    return im


def main():
    from server.server import ITEMS
    for base in [ROOT/'web/assets',ROOT/'client/assets']:
        (base/'equipment').mkdir(parents=True,exist_ok=True);(base/'monsters').mkdir(exist_ok=True)
        for key,item in ITEMS.items():
            if item.get('content_version')=='0.8.8':(base/'equipment'/f'{key}.svg').write_text(item_icon(key,item))
        palettes={**PALETTES,'mummy':('#9e925f','#daccad','#91d7ca'),'skeleton_archer':('#786753','#d7d0b3','#adbc85')}
        for kind,palette in palettes.items():
            atlas=Image.new('RGBA',(320,80))
            for frame in range(4):atlas.paste(monster_frame(kind,palette,frame),(frame*80,0))
            atlas.save(base/'monsters'/f'{kind}.png',optimize=True)
    print('79 item icons and 11 four-frame monster atlases generated for both clients.')
if __name__=='__main__':main()
