from pathlib import Path
root=Path(__file__).resolve().parents[1]
shapes={
'feats/dueling': '<path d="M18 48L41 12L47 8L46 17L25 52Z" fill="url(#metal)"/><path d="M17 38L31 47M15 50L20 54" stroke="#eac475" stroke-width="4"/><path d="M39 31L54 34V44Q50 52 44 55Q36 51 34 44V34Z" fill="#497b68" stroke="#eac475" stroke-width="2"/>',
'feats/defense': '<path d="M10 15L32 7L54 15V32Q52 47 32 57Q12 47 10 32Z" fill="url(#metal)" stroke="#e9cc85" stroke-width="2"/><path d="M16 19L32 13L48 19V32Q46 43 32 50Q18 43 16 32Z" fill="#305c58"/><path d="M24 29L30 35L42 22" fill="none" stroke="#f4d790" stroke-width="4"/>',
'feats/great_weapon':'<path d="M26 12L32 4L38 12L37 39H27Z" fill="url(#metal)" stroke="#e4eedf"/><path d="M17 40Q32 34 47 40M32 40V55M26 57H38" stroke="#e5ba69" stroke-width="4"/><path d="M11 22L6 29L12 30M53 22L58 29L52 30" fill="none" stroke="#d89c58" stroke-width="2"/>',
'feats/sap':'<path d="M22 18Q32 7 42 18V28Q32 40 22 28Z" fill="#aab9ab"/><path d="M18 52V40Q32 32 46 40V52" fill="#58786f"/><path d="M12 13L18 8M46 8L52 13M11 30H5M53 30H59" stroke="#ffda80" stroke-width="3"/><path d="M35 10L27 22H35L29 33" fill="none" stroke="#ffe2a6" stroke-width="3"/>',
'feats/graze':'<path d="M8 44Q25 10 57 19Q29 24 17 49Z" fill="#dceadd"/><path d="M14 52Q28 27 53 30" fill="none" stroke="#e1b869" stroke-width="2"/><path d="M44 40L54 50M53 38L43 52M55 28L61 27" stroke="#ffe1a0" stroke-width="2"/>',
'feats/topple':'<path d="M14 21L46 43" stroke="#b58b54" stroke-width="6"/><path d="M7 16L17 7L33 23L23 34Z" fill="url(#metal)" stroke="#e5c17d" stroke-width="2"/><path d="M9 51H55M35 15L50 24V35M45 30L50 36L57 30" fill="none" stroke="#f6d691" stroke-width="3"/><path d="M31 51L26 58M42 52L47 58" stroke="#a88951" stroke-width="2"/>',
'spells/action_surge':'<path d="M31 7L16 35H29L25 57L50 25H35L43 7Z" fill="#ffe3a2" stroke="#c18b3c" stroke-width="2"/><path d="M12 15Q3 29 11 43M52 12Q64 31 54 48" fill="none" stroke="#e3b854" stroke-width="3"/>',
'equipment/fighter_chain_mail':'<path d="M17 10L26 7Q32 15 38 7L47 10L59 27L47 33L44 25V56H20V25L17 33L5 27Z" fill="#77958e" stroke="#e2d1a2" stroke-width="2"/>' + ''.join(f'<path d="M{x} {y}q3 5 6 0" fill="none" stroke="{col}" stroke-width="1.4"/>' for y in range(20,53,6) for x in range(23 if (y//6)%2 else 20,41,7) for col in ['#dbe6d7'])+'<path d="M19 43H45" stroke="#ab8b53" stroke-width="5"/><rect x="30" y="40" width="6" height="6" fill="#e5c17d"/>',
'equipment/fighter_shield':'<path d="M10 14L32 6L54 14V32Q52 48 32 58Q12 48 10 32Z" fill="#678884" stroke="#e4c68e" stroke-width="3"/><path d="M15 18L31 12V50Q17 42 15 32Z" fill="#375b56"/><path d="M32 15V48M18 29H46" stroke="#e1bc71" stroke-width="3"/><circle cx="32" cy="30" r="7" fill="url(#metal)" stroke="#e4cf9d"/>',
'equipment/training_greatsword':'<path d="M19 44L41 9L50 5L50 16L28 51Z" fill="url(#metal)" stroke="#dce8de"/><path d="M19 44L48 8" stroke="#ffffff" stroke-opacity=".7"/><path d="M13 38L35 52M9 53L17 58" stroke="#c7a260" stroke-width="4"/><path d="M15 46L11 54" stroke="#755e43" stroke-width="5"/>',
'equipment/training_maul':'<path d="M17 12L50 55" stroke="#aa8250" stroke-width="6"/><path d="M4 20L20 6L40 26L24 41Z" fill="url(#metal)" stroke="#dbc694" stroke-width="2"/><path d="M11 15L31 35M18 9L37 28" stroke="#69847d" stroke-width="3"/><path d="M39 46L44 42" stroke="#edc578" stroke-width="3"/>'
}
for name,shape in shapes.items():
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><defs><linearGradient id="metal" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#edf4e6"/><stop offset=".5" stop-color="#a3bab1"/><stop offset="1" stop-color="#627d76"/></linearGradient></defs><rect x="1" y="1" width="62" height="62" rx="10" fill="#142e2b" stroke="#b49a60"/><circle cx="32" cy="32" r="27" fill="none" stroke="#d8bf7f" stroke-opacity=".16"/>{shape}</svg>'
 for base in ('web','client'):
  out=root/base/'assets'/f'{name}.svg';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(svg)
for base in ('web','client'):
 (root/base/'assets/equipment/shield.svg').write_bytes((root/base/'assets/equipment/fighter_shield.svg').read_bytes())
print('Original SVG assets generated for both clients:',len(shapes)+1)
