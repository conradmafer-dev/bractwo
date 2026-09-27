from pathlib import Path
R=Path(__file__).resolve().parents[1]
art={
'arcane_recovery':('spells','#5d65b8','<path d="M17 37 A18 18 0 1 1 26 49" fill="none"/><path d="M14 30 L17 40 27 35" fill="none"/><path d="M34 14 L25 34 H34 L30 49 44 28 H35Z" fill="#d0e8ff"/>'),
'alarm':('spells','#8e7599','<path d="M20 41V28 Q20 12 32 12 Q44 12 44 28 V41 L49 46 H15Z" fill="#c4a1e1"/><circle cx="32" cy="50" r="4" fill="#ffe7b0"/><path d="M11 17L7 25 M53 17L57 25 M26 8H38" fill="none"/>'),
'find_familiar':('spells','#657aa0','<path d="M15 16 L22 19 Q32 13 42 19 L49 16 46 35 Q42 54 32 54 Q20 52 17 35Z" fill="#aab8c9"/><circle cx="25" cy="30" r="9" fill="#eee5bc"/><circle cx="39" cy="30" r="9" fill="#eee5bc"/><circle cx="25" cy="30" r="3" fill="#141d29"/><circle cx="39" cy="30" r="3" fill="#141d29"/><path d="M29 39 L32 44 35 39Z" fill="#e6b365"/>'),
'speak_with_animals':('spells','#537a57','<path d="M11 19 L23 24 32 12 40 24 52 19 46 42 32 51 18 42Z" fill="#d6a76c"/><path d="M20 31L25 33 M39 33L44 31" fill="none"/><path d="M28 41 H36 L32 46Z" fill="#1b2b29"/><path d="M50 8Q62 17 52 28 M48 13Q55 17 50 23" fill="none"/>'),
'wild_shape_wolf':('spells','#536e7a','<path d="M13 10 L28 19 35 16 49 8 46 33 53 42 36 55 20 45 15 30Z" fill="#afc9cc"/><path d="M20 27L28 30 M37 28L44 25" stroke="#203938"/><path d="M30 43 L40 41 35 49Z" fill="#253946"/>'),
'wild_shape_cat':('spells','#737785','<path d="M14 11 L26 21 38 21 50 11 46 40 Q32 58 18 40Z" fill="#c8bb9f"/><path d="M21 33L27 34 M38 34L44 33" stroke="#214933"/><path d="M28 41H36L32 45Z" fill="#c77d89"/><path d="M7 38L23 41 M7 45L23 44 M41 41L57 38 M41 44L57 45" fill="none"/>'),
'wild_shape_black_bear':('spells','#536766','<circle cx="17" cy="18" r="8" fill="#374740"/><circle cx="47" cy="18" r="8" fill="#374740"/><path d="M14 26 Q32 8 50 26 L48 43 Q33 59 16 43Z" fill="#3e454b"/><ellipse cx="32" cy="40" rx="13" ry="10" fill="#bca67e"/><path d="M28 37H36L32 42Z" fill="#1b2127"/><circle cx="22" cy="29" r="2" fill="#f9d175"/><circle cx="42" cy="29" r="2" fill="#f9d175"/>'),
'wild_shape_bear':('spells','#755b45','<circle cx="17" cy="18" r="8" fill="#654937"/><circle cx="47" cy="18" r="8" fill="#654937"/><path d="M14 26 Q32 8 50 26 L48 43 Q33 59 16 43Z" fill="#aa7850"/><ellipse cx="32" cy="40" rx="13" ry="10" fill="#d2b28b"/><path d="M28 37H36L32 42Z" fill="#1b2127"/><circle cx="22" cy="29" r="2" fill="#f9d175"/><circle cx="42" cy="29" r="2" fill="#f9d175"/>'),
'warden':('feats','#516f55','<path d="M13 15 L32 8 51 15 V34 Q48 49 32 56 Q16 49 13 34Z" fill="#648760"/><path d="M32 15V47 M21 24L32 34 43 24 M22 35L32 44 42 35" fill="none"/>'),
'magician':('feats','#56736d','<path d="M32 7 Q57 26 36 51 Q9 55 14 31 Q16 17 32 7Z" fill="#86c7a1"/><path d="M24 52Q27 34 42 22" fill="none"/><path d="M45 8L48 16 56 19 48 22 45 30 42 22 34 19 42 16Z" fill="#e6d9ae"/>'),
'simple_weapons':('feats','#7a6047','<path d="M21 53L43 11" stroke="#d2b68a" stroke-width="8"/><path d="M37 10L48 16 M19 42L30 48" fill="none"/>'),
'martial_weapons':('feats','#716268','<path d="M15 51L44 15 53 8 50 21 23 54Z" fill="#c1d3d7"/><path d="M13 39L29 53" stroke="#dfba65" stroke-width="5"/><path d="M45 52L20 14 11 8 12 21 39 55Z" fill="#adb9c7"/><path d="M37 52L51 41" stroke="#dfba65" stroke-width="5"/>'),
'light_armor':('feats','#927353','<path d="M22 12L28 18H36L42 12 54 23 45 32 43 54H21L19 32 10 23Z" fill="#ac895b"/><path d="M28 18L32 30 36 18 M32 30V53 M22 42H43" fill="none"/>'),
'medium_armor':('feats','#637768','<path d="M22 12L28 18H36L42 12 54 23 45 32 43 54H21L19 32 10 23Z" fill="#8b9c84"/><path d="M22 28H43 M22 35H43 M22 43H43 M22 50H43 M29 25V51 M37 25V51" stroke="#d7cfad" stroke-width="2"/>'),
'heavy_armor':('feats','#5b6e83','<path d="M20 11L29 18H35L44 11 57 26 44 33 44 53H20L20 33 7 26Z" fill="#9cb2bf"/><path d="M32 20V54 M20 35L32 41 44 35 M15 20L21 28 M49 20L43 28" fill="none"/>'),
'shields':('feats','#677675','<path d="M13 14L32 7 51 14V32 Q49 48 32 57 Q15 48 13 32Z" fill="#98a3a1"/><path d="M32 10V52 M17 24H47" stroke="#d7bc6c" stroke-width="6"/>'),
'druid_leather':('equipment','#927353','<path d="M22 12L28 18H36L42 12 54 23 45 32 43 54H21L19 32 10 23Z" fill="#91744d"/><path d="M28 18L32 30 36 18 M32 30V53 M22 42H43" fill="none"/><path d="M38 32Q50 35 38 43Z" fill="#88ba6d"/>'),
'wooden_shield':('equipment','#776544','<path d="M14 14L32 7 50 14V32 Q48 48 32 56 Q16 48 14 32Z" fill="#987546"/><path d="M24 13V48 M40 13V48 M14 26H50 M19 42H45" stroke="#594e36"/><circle cx="32" cy="30" r="8" fill="#a4b0a0"/>'),
'hide_armor':('equipment','#745d45','<path d="M21 10L29 18H35L44 10 55 23 46 33 43 55H21L18 33 9 23Z" fill="#a38258"/><path d="M19 12L25 27 32 22 40 27 46 12" fill="#dec9a0"/><path d="M24 40H42 M32 24V55" fill="none"/>'),
}
art['wild_companion']=('spells','#477566',art['find_familiar'][2])
for key,(folder,bg,paths) in art.items():
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><defs><linearGradient id="g" x2="0.7" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="#152526"/></linearGradient></defs><rect x="1" y="1" width="62" height="62" rx="11" fill="url(#g)" stroke="#b0ba9f" stroke-width="2"/><g stroke="#e4dfb9" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">{paths}</g></svg>'
 for base in [R/'web/assets',R/'client/assets']:
  dst=base/folder/(key+'.svg');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(svg)
print('Generated',len(art),'original icons, mirrored in both clients.')
