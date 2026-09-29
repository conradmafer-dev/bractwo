"""Generate code-native UI19 magic equipment icons, matching existing 64px assets."""
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.magic_items import CATALOG

ROOT=Path(__file__).resolve().parents[1]
COLORS={'fire':'#ff9162','cold':'#8eddf3','poison':'#afd166','lightning':'#e7ce77','necrotic':'#bd94dc'}


def icon(key,spec):
    color=next((v for k,v in COLORS.items() if key.endswith('_'+k)), '#c8b8ed' if key=='ring_free_action' else '#87dbdf' if key=='ring_swimming' else '#ffbb71' if key=='ring_warmth' else '#e1c180')
    kind=spec['slot']
    if kind=='ring':
        art='<circle cx="32" cy="38" r="14" fill="none" stroke="url(#gold)" stroke-width="6"/>'
        if key=='ring_protection':art+='<path d="M21 12L32 8L43 12V22Q40 30 32 34Q24 30 21 22Z" fill="#3a7771" stroke="#fff1ba" stroke-width="2"/><path d="M26 20l4 4 8-9" fill="none" stroke="#fff1ba" stroke-width="2"/>'
        elif key=='ring_swimming':art+='<path d="M17 17q7-8 15 0t15 0M17 25q7-8 15 0t15 0" fill="none" stroke="'+color+'" stroke-width="3"/>'
        elif key=='ring_warmth':art+='<path d="M33 7q-3 10 5 12l2-7q12 20-6 22Q16 33 22 19l5 4q-3-8 6-16Z" fill="'+color+'" stroke="#fff1ba"/><path d="M32 22q8 9 1 11q-8-2-1-11" fill="#fff1ba"/>'
        elif key=='ring_free_action':art+='<path d="M25 9l-7 7 8 8M39 9l7 7-8 8M28 12l8 8M26 27l12-12" fill="none" stroke="'+color+'" stroke-width="3" stroke-linecap="round"/>'
        else:art+='<path d="M22 14L32 7L42 14L38 26L26 26Z" fill="'+color+'" stroke="#fff1ba" stroke-width="1.5"/><path d="M22 14h20M32 7l-5 7 5 12 5-12Z" fill="none" stroke="#fff1ba" stroke-opacity=".65"/>'
    elif kind=='shield':art='<path d="M14 13L32 7L50 13V33Q48 46 32 56Q16 46 14 33Z" fill="#326666" stroke="url(#gold)" stroke-width="4"/><path d="M32 17v26M23 30h18" stroke="#fff1ba" stroke-width="3"/>'
    elif kind=='armor':
        color='#c6eaf0' if 'mithral' in key else '#7d809c' if 'adamantine' in key else '#bdba9b'
        art='<path d="M22 9L14 14L9 29L18 34L20 53H44L46 34L55 29L50 14L42 9Q32 19 22 9Z" fill="'+color+'" stroke="#e1c180" stroke-width="2"/>'
        art+=''.join(f'<path d="M{x} {y}q3 6 6 0" fill="none" stroke="#243e49" stroke-width="1.4"/>' for y in (22,29,36,43) for x in (23,30,37))
        if 'adamantine' in key:art+='<path d="M30 18l-4 10h7l-4 11 11-15h-7l5-6" fill="#202739" stroke="#d1d8e6"/>'
    elif 'longbow' in key:art='<path d="M21 8Q60 32 21 56M21 8L29 32L21 56" fill="none" stroke="url(#gold)" stroke-width="4"/><path d="M10 32h41l-8-6m8 6-8 6" fill="none" stroke="#c3e7de" stroke-width="2"/>'
    elif 'quarterstaff' in key:art='<path d="M18 54L43 10" stroke="#a77b48" stroke-width="7" stroke-linecap="round"/><path d="M18 54L43 10" stroke="#edcf91" stroke-width="2"/><path d="M35 16l9 5M27 30l9 5M21 42l9 5" stroke="#74dcd7" stroke-width="3"/>'
    else:art='<path d="M25 38L41 8L47 9L49 15L30 42Z" fill="#b6d8df" stroke="#eff9eb"/><path d="M18 33l17 11M25 40L15 54" stroke="url(#gold)" stroke-width="6" stroke-linecap="round"/>'
    return '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><defs><linearGradient id="gold" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#a77b48"/><stop offset="1" stop-color="#e1c180"/></linearGradient></defs><rect x="1" y="1" width="62" height="62" rx="10" fill="#122b29" stroke="#a77b48" stroke-opacity=".65"/><circle cx="32" cy="32" r="26" fill="none" stroke="#a77b48" stroke-opacity=".2"/>'+art+'<path d="M52 7v8M48 11h8" stroke="'+color+'" stroke-width="1.5"/></svg>\n'


if __name__=='__main__':
    for key,spec in CATALOG.items():
        svg=icon(key,spec);ET.fromstring(svg)
        for folder in ('web','client'):
            path=ROOT/folder/'assets'/'equipment'/(key+'.svg')
            with path.open('w',encoding='utf-8',newline='\n') as handle:
                handle.write(svg);handle.flush();os.fsync(handle.fileno())
    print(f'{len(CATALOG)} magic icons generated and XML-validated in web and client.')
