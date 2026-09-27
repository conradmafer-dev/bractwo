"""Reproducible original vector icons, bundled with both clients. No font dependency."""
from pathlib import Path
from html import escape
import sys,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.dnd_content import SPELLS
# Hand-authored silhouettes; spell-specific rays, motes and rune ticks make variants legible.
MOTIFS={
'fire':'<path d="M33 9C41 23 47 25 45 38C44 51 18 54 18 36C18 26 27 24 27 16C32 19 29 27 32 30C37 25 34 18 33 9Z" fill="url(#ink)"/><path d="M32 30C43 43 33 52 27 44C22 39 30 35 32 30Z" fill="{light}"/>',
'cold':'<g stroke="{light}" stroke-width="2.5" stroke-linecap="round"><path d="M32 10V54M13 21L51 43M13 43L51 21M26 14L32 20L38 14M26 50L32 44L38 50M14 28L22 27L20 19M44 45L42 37L50 36M14 36L22 37L20 45M44 19L42 27L50 28"/></g>',
'lightning':'<path d="M36 9L16 35H29L24 55L49 25H35L42 9Z" fill="url(#ink)" stroke="{light}" stroke-width="1.2"/>',
'force':'<g fill="{light}"><path d="M44 12L49 17L44 22L39 17Z"/><path d="M45 29L50 34L45 39L40 34Z"/><path d="M37 43L42 48L37 53L32 48Z"/></g><g fill="none" stroke="url(#ink)" stroke-width="3" stroke-linecap="round"><path d="M14 47Q4 12 40 17M14 47Q15 28 41 34M14 47Q22 57 34 48"/></g>',
'acid':'<path d="M32 9C30 18 16 32 16 39A16 16 0 0 0 48 39C48 31 34 17 32 9Z" fill="url(#ink)"/><circle cx="28" cy="38" r="4" fill="{light}"/><circle cx="37" cy="44" r="2" fill="{light}"/>',
'radiant':'<circle cx="32" cy="32" r="11" fill="url(#ink)" stroke="{light}" stroke-width="2"/><g stroke="{light}" stroke-width="2"><path d="M32 7V17M32 47V57M7 32H17M47 32H57M14 14L21 21M43 43L50 50M14 50L21 43M43 21L50 14"/></g>',
'necrotic':'<path d="M18 31C12 5 52 5 46 31L41 37V47H23V37Z" fill="url(#ink)"/><path d="M24 25L29 29L24 32M40 25L35 29L40 32M30 36H34M29 41V48M35 41V48" fill="none" stroke="#15202a" stroke-width="3"/>',
'nature':'<path d="M48 11C14 8 9 38 23 46C42 57 53 35 48 11Z" fill="url(#ink)"/><path d="M16 55L43 19M23 45L21 31M29 36L44 34M34 29L34 17" fill="none" stroke="{light}" stroke-width="2"/>',
'arcane':'<path d="M32 9L38 23L54 25L42 36L46 52L32 43L18 52L22 36L10 25L26 23Z" fill="url(#ink)" stroke="{light}" stroke-width="1.5"/>',
'shield':'<path d="M32 9L50 17L46 40L32 54L18 40L14 17Z" fill="url(#ink)" stroke="{light}" stroke-width="2"/><path d="M32 15V45M21 24L43 24" stroke="{light}" stroke-width="2"/>',
'heal':'<path d="M25 12H39V25H52V39H39V52H25V39H12V25H25Z" fill="url(#ink)" stroke="{light}" stroke-width="1.5"/>',
'boot':'<path d="M22 11H36L35 34L47 41L49 51H15V43L23 35Z" fill="url(#ink)" stroke="{light}" stroke-width="2"/><path d="M40 16H54M42 23H51M13 27H4" stroke="{light}" stroke-width="2"/>',
'paw':'<ellipse cx="32" cy="41" rx="13" ry="11" fill="url(#ink)"/><g fill="{light}"><ellipse cx="14" cy="26" rx="5" ry="7" transform="rotate(-30 14 26)"/><ellipse cx="25" cy="17" rx="5" ry="7"/><ellipse cx="39" cy="17" rx="5" ry="7"/><ellipse cx="50" cy="26" rx="5" ry="7" transform="rotate(30 50 26)"/></g>',
'beam':'<path d="M9 51L49 11" stroke="{color}" stroke-width="10"/><path d="M9 51L49 11" stroke="{light}" stroke-width="3"/><path d="M39 10L50 10L50 21M43 3L45 8M57 14L52 13M41 20L45 16" stroke="{light}" stroke-width="2" fill="none"/>',
'roots':'<path d="M15 52L26 28L25 12M49 52L37 27L42 12M32 52V30M12 25L23 30M50 28L39 32M13 46L24 38M49 44L40 38" stroke="{light}" stroke-width="3" fill="none"/><path d="M14 13Q32 4 26 23M42 12Q56 11 44 25" fill="url(#ink)"/>',
'mark':'<circle cx="32" cy="32" r="15" fill="none" stroke="{color}" stroke-width="3"/><path d="M32 8V23M32 41V56M8 32H23M41 32H56" stroke="{light}" stroke-width="3"/><circle cx="32" cy="32" r="3" fill="{light}"/>',
'armor':'<path d="M21 11L13 16L9 29L18 34L18 51H46V34L55 29L51 16L43 11L38 19H26Z" fill="url(#ink)" stroke="{light}" stroke-width="2"/><path d="M32 20V49M23 36H41" stroke="{light}" stroke-width="1.5"/>',
'sword':'<path d="M43 9L51 12L32 40L25 35Z" fill="url(#ink)" stroke="{light}" stroke-width="2"/><path d="M19 31L37 43M26 39L18 52" stroke="{light}" stroke-width="5"/>',
'ring':'<circle cx="32" cy="37" r="15" fill="none" stroke="{color}" stroke-width="6"/><path d="M23 16L32 8L41 16L32 25Z" fill="{light}"/>',
}
MOTIFS['bow']='<path d="M21 10Q55 32 21 54M21 10L28 32L21 54" fill="none" stroke="{light}" stroke-width="3"/><path d="M9 32H54M48 27L55 32L48 37" fill="none" stroke="{color}" stroke-width="3"/>'
MOTIFS['staff']='<path d="M24 54L35 18" stroke="{color}" stroke-width="5"/><path d="M32 26Q19 18 28 11Q47 3 46 18Q45 27 36 22" fill="none" stroke="{light}" stroke-width="3"/><circle cx="36" cy="14" r="4" fill="{light}"/>'
MOTIFS['nature_staff']='<path d="M23 54L37 11M31 32L20 24" fill="none" stroke="{color}" stroke-width="5"/><path d="M35 20Q30 5 46 8Q53 23 35 20M25 31Q9 29 13 17Q26 15 25 31" fill="{light}"/>'
MOTIFS['cone']='<path d="M10 32L53 10V54Z" fill="url(#ink)" stroke="{light}" stroke-width="2"/><g stroke="{light}" stroke-width="1.5"><path d="M11 32L46 20M11 32H48M11 32L46 44"/></g>'
MOTIFS['sphere']='<circle cx="34" cy="34" r="18" fill="url(#ink)" stroke="{light}" stroke-width="2"/><path d="M8 11L20 23M10 28L18 30M27 6L30 17" stroke="{color}" stroke-width="4"/><path d="M34 24C29 35 28 42 35 45C47 37 36 35 39 26" fill="{light}"/>'
MOTIFS['meteors']='<g fill="url(#ink)" stroke="{light}" stroke-width="1.2"><circle cx="22" cy="25" r="7"/><circle cx="43" cy="24" r="7"/><circle cx="22" cy="47" r="7"/><circle cx="44" cy="46" r="7"/></g><g stroke="{color}" stroke-width="3"><path d="M8 8L19 21M31 7L40 20M8 30L19 42M31 30L41 41"/></g>'
MOTIFS['chain']='<path d="M9 32L25 22L32 32L24 39L33 45M32 32L44 14M32 32L52 33M32 32L47 51" fill="none" stroke="url(#ink)" stroke-width="4"/><g fill="{light}"><circle cx="44" cy="14" r="4"/><circle cx="52" cy="33" r="4"/><circle cx="47" cy="51" r="4"/></g>'
MOTIFS['sunburst']='<circle cx="32" cy="32" r="19" fill="none" stroke="{color}" stroke-width="3"/><path d="M32 8L36 24L51 13L41 28L57 32L41 36L51 51L36 41L32 57L28 41L13 51L24 36L8 32L24 28L13 13L28 24Z" fill="url(#ink)"/><circle cx="32" cy="32" r="7" fill="{light}"/>'
MOTIFS['piercing']=MOTIFS['nature']
MOTIFS['ensnare']='<path d="M16 50L46 13M35 13H47V26" fill="none" stroke="{light}" stroke-width="4"/><path d="M12 53Q6 34 24 33Q50 29 30 18Q18 11 22 8M45 55Q58 37 40 35Q21 32 40 22" fill="none" stroke="{color}" stroke-width="3"/><path d="M17 41Q3 30 13 25Q25 30 17 41M42 37Q60 23 58 38Q48 46 42 37" fill="{color}"/>'
SPECIAL={'ensnaring_strike':'ensnare','burning_hands':'cone','cone_of_cold':'cone','fireball':'sphere','meteor_swarm':'meteors','chain_lightning':'chain','sunburst':'sunburst','ray_of_frost':'beam','scorching_ray':'beam','sunbeam':'beam','shocking_grasp':'lightning','shield':'shield','mage_armor':'armor','barkskin':'armor','stoneskin':'armor','longstrider':'boot','misty_step':'boot','entangle':'roots','spike_growth':'roots','plant_growth':'roots','thorn_whip':'roots','hunters_mark':'mark','animal_companion':'paw','wild_shape_wolf':'paw','wild_shape_bear':'paw','foresight':'mark'}
def svg(motif,colors,variant=0):
 color,bright,light=colors
 # Distinct edge ticks maintain an individual mark without unreadable text.
 ticks=''.join(f'<circle cx="{32+26*math.cos((i+variant*.25)*math.pi/4):.2f}" cy="{32+26*math.sin((i+variant*.25)*math.pi/4):.2f}" r="1" fill="{bright}"/>' for i in range(variant%4+1))
 art=MOTIFS[motif].replace('{color}',bright).replace('{light}',light)
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><defs><linearGradient id="ink" x1="0" y1="1" x2="1" y2="0"><stop stop-color="{color}"/><stop offset="1" stop-color="{bright}"/></linearGradient></defs><rect x="1" y="1" width="62" height="62" rx="10" fill="#122b29" stroke="{color}" stroke-opacity=".65"/><circle cx="32" cy="32" r="26" fill="none" stroke="{color}" stroke-opacity=".2"/>{art}{ticks}</svg>'
def main():
 for base in [ROOT/'web/assets',ROOT/'client/assets']:
  (base/'spells').mkdir(parents=True,exist_ok=True);(base/'equipment').mkdir(parents=True,exist_ok=True)
  for i,(key,s) in enumerate(SPELLS.items()):
   motif=SPECIAL.get(key,'heal' if s['kind']=='heal' else s['visual']['theme'])
   (base/'spells'/f'{key}.svg').write_text(svg(motif,s['visual']['colors'],i))
  for key,motif in [('weapon','sword'),('bow','bow'),('staff','staff'),('nature_staff','nature_staff'),('armor','armor'),('ring','ring'),('empty','arcane')]:
   (base/'equipment'/f'{key}.svg').write_text(svg(motif,['#a77b48','#e1c180','#fff1ba']))
if __name__=='__main__':main()
