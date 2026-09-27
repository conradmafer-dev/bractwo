"""Generate player-facing tables from the same canonical catalog the server uses."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import ITEMS,POTIONS,ENEMY_TYPES,content,CLASSES
from server import hunt_content as hunts

def pct(x):return f'{x*100:g}'.replace('.',',')+'%'
def main():
    rows=['# Bractwo 0.8.8 — przedmioty i łowiska','',
      '## Zasady łupu','',
      'Procent oznacza niezależną szansę na dany przedmiot po pokonaniu potwora, dla każdego gracza uprawnionego do nagrody. Nie zależy od klasy postaci. Jeden potwór może oddać kilka przedmiotów albo żaden. 5% nie gwarantuje łupu co 20 zabójstw. W drużynie nadal obowiązują dotychczasowe warunki udziału, odległości i różnicy poziomów.',
      '', 'Sprzęt trafia do plecaka. Przedmioty innych klas można sprzedać lub przechować w depozycie. Trofea są na sprzedaż; nie jest to zapowiedź systemu craftingu. Przy pełnym plecaku (40 sztuk, razem z założonymi) nadmiar przepada z komunikatem — zwalniaj miejsce przed polowaniem. Mikstury mają osobne liczniki.',
      '', 'Każdy gatunek ma jawną tabelę. W grze wybierz potwora i naciśnij **Łup** przy jego nazwie. W szczegółach przedmiotu **C → Ekwipunek → Skąd zdobyć** widać źródła z tymi samymi procentami. Stare skrzynie, nagrody zadań i posiadany sprzęt zachowują wcześniejszą zawartość.',
      '', 'Jakość to nowy, autorski balans Bractwa, nie tabela losowania z podręcznika D&D. Małe premie +1/+2/+3 są rozłożone po poziomach; rzadszy przedmiot nie zawsze zastąpi broń odpowiadającą innemu stylowi gry. Różdżki poprawiają trafienie czarami i ST, nie zmieniają darmowej Iskry w skalującą się sztuczkę.',
      '', '## Nowi przeciwnicy','', '| Przeciwnik | Poziom | HP / KP | Najbliższe nowe łowisko | Liczba nowych odrodzeń |', '|---|---:|---:|---|---:|']
    for h in content.LOOT_HUNTS:
        e=ENEMY_TYPES[h['kind']]
        rows.append(f"| {e['name']}{' — boss' if e.get('boss') else ''} | {e['level']} | {e['hp']} / {e['armor_class']} | {h['region']} ({h['x']}, {h['y']}) | {h['count']} |")
    rows+=['','Współrzędne służą orientacji na rozległej mapie. W atlasie są także nowe znaczniki łowisk. Pozostałe osobniki zwykłych gatunków są rozproszone po odpowiednich siedliskach. Miejsca wcześniejszych potworów pozostają bez zmian.',
      '', '## Wszystkie tabele potworów','']
    for kind,s in sorted(ENEMY_TYPES.items(),key=lambda kv:(kv[1].get('level',1),kv[1]['name'])):
        rows += [f"### {s['name']} — poziom {s.get('level',1)}{' · boss' if s.get('boss') else ''}",'', s['loot_origin']+'.','', '| Przedmiot | Szansa |', '|---|---:|']
        for e in s['loot']['entries']:
            item=(POTIONS if e['kind']=='potion' else ITEMS)[e['template']]
            rows.append(f"| {item['name']} | {pct(e['chance'])} |")
        rows.append('')
    rows+=['## Nowe wyposażenie — parametry','',
      'Kości niżej są kośćmi broni; stała premia magiczna jest wyszczególniona osobno. Do ataku i obrażeń dochodzą odpowiednie cechy postaci oraz istniejące zdolności. Różdżka zawsze zadaje Iskrą 1k4 bez premii do obrażeń, a zaklęcia korzystają z własnych kości.',
      '', 'Lekki pancerz: pełny modyfikator Zręczności. Średni: najwyżej +2 Zręczności (ujemny modyfikator pozostaje). Ciężki: bez Zręczności. Szaty nie są pancerzem i współpracują ze Zbroją maga. Suma magicznych premii KP z wyposażenia pozostaje ograniczona do +3. Nowe ciężkie pancerze są dla rycerza; lekkie i średnie dla rycerza, łowcy i druida. Stare, już istniejące wyposażenie zachowuje wcześniejsze ograniczenia klas.',
      '', 'Odporność oznacza połowę obrażeń danego typu. Dwie takie same odporności nie zmniejszają ich do ćwierci. Podczas przemiany wyposażenie nie zapewnia odporności postaci zwierzęcej. Obliczenia są wspólne dla PvE i PvP.',
      '', '| Przedmiot | Poziom | Dla | Parametry |', '|---|---:|---|---|']
    for k,i in ITEMS.items():
        if i.get('content_version')!='0.8.8' or i['slot']=='trophy':continue
        stat=i.get('armor_summary',i.get('damage_dice',i.get('description','')))
        if i['slot']=='weapon':
            if i.get('attack'):stat+=f" · obrażenia +{i['attack']}"
            if i.get('attack_bonus'):stat+=f" · trafienie +{i['attack_bonus']}"
        if i.get('resistances'):stat+=' · '+i['description']
        names=', '.join(CLASSES[c]['name'] for c in i['class_ids'])
        rows.append(f"| {i['name']} | {i['min_level']} | {names} | {stat} |")
    rows+=['','## Źródła reguł','',
      'Kości broni, bazy pancerzy i rozróżnienie premii cechy nawiązują do SRD 5.2.1: https://www.dndbeyond.com/srd oraz https://www.dndbeyond.com/sources/dnd/br-2024/equipment . Progi gry, nazwy nowych przedmiotów, wymagania klas, szanse łupu i statystyki nowych potworów są autorską adaptacją, a nie kompletnym odtworzeniem zasad stołowych. Atrybucja w LICENSE-SRD.txt. Wszystkie nowe grafiki wygenerowano lokalnym, oryginalnym kodem tools/generate_loot_art.py.']
    (ROOT/'docs/LOOT_0.8.8.md').write_text('\n'.join(rows)+'\n')
    export=dict(version='0.8.8',items={k:i for k,i in ITEMS.items() if i.get('content_version')=='0.8.8'},
        monsters={k:dict(name=s['name'],level=s['level'],hp=s['hp'],armor_class=s['armor_class'],boss=s.get('boss',False),loot=s['loot'],loot_origin=s['loot_origin']) for k,s in ENEMY_TYPES.items()},hunts=content.LOOT_HUNTS)
    (ROOT/'docs/LOOT_0.8.8.json').write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
    print(f"Generated {len(export['items'])} items and {len(export['monsters'])} drop tables.")
if __name__=='__main__':main()
