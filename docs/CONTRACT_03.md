# Wspólny kontrakt aktualizacji 0.3 — Wyprawy

Wersja 0.3 zachowuje konta, cztery klasy, nieograniczone poziomy, loot, drużyny i karane PvP z 0.2. Własna kolorowa oprawa klasycznego RPG 2D, bez reliktów. Zachowujemy wymiary świata i dotychczasowe kolizje: 3200 × 2304, most otwarty. Dodajemy trzy domy z rzeczywistą kolizją w mieście: (340,1030,100,76), (420,1300,108,80), (710,990,110,84). Przy młynie dodajemy rzeczywistą podstawę budynku (235,1510,90,86); punkt odkrycia pozostaje na dostępnym gruncie (340,1640).

## Ruch i efekty

Publiczne pole `speed`: prędkość serwera `100 + 90*(level-1)/(level+79)` px/s. Poziom 1: 100, 10: 109.1, 50: 134.2, 100: 149.7. Poziomy bez limitu; przyrost ruchu maleje, asymptota 190. Znormalizowane przekątne, żadnego przyjmowania prędkości od klienta.

Publiczne `attack_facing` jest kierunkiem ostatniego faktycznego ataku i nie zmienia się od chodzenia. `facing` pozostaje kierunkiem ruchu. Efekty wyłącznie kosmetyczne, obrażenia oblicza serwer natychmiast.

Każdy state zawiera `effects`: zdarzenia ostatnich 1.5 s, deduplikowane po `id`. Efekt: `{id,kind,source_id,target_id,x,y,target_x,target_y,time,duration,radius}`; time to czas symulacji. `kind`: sword, arrow, magic_bolt, nature_bolt, fire_ring, piercing_arrow, bulwark, heal. Początek i koniec zapisane przy trafieniu, niezależne od późniejszego ruchu. Promień fire_ring 320, duration 0.9. Zwykły pocisk duration 0.32. Przeglądarkowy i natywny klient animują te zdarzenia. Żaden klient nie może zgłaszać efektów/obrażeń.

## Czat

Komenda `chat {text}` zostaje. Serwer wysyła `{type:'chat',id,name,text}`. Publiczny gracz ma `speech_text` i `speech_until` (czas symulacji; 6 s). Własne i cudze wypowiedzi widoczne nad głową (zawijanie, maks. 160 znaków) i w dzienniku czatu. Enter otwiera i ustawia fokus; drugi Enter wysyła; Escape anuluje; litery podczas pisania nie poruszają postaci i nie rzucają zaklęć. Nowo zalogowany klient nie odtwarza przeterminowanego dymka.

## Świat i cele

Nowe metadata `npcs`, `landmarks`, `quests`. Serwer jest źródłem prawdy dla współrzędnych, postępów i nagród. Każdy npc: `{id,name,x,y,role,radius:150}`. Każdy landmark: `{id,name,x,y,radius:90,description,biome}`. Klienci rysują obiekty i znaczniki na minimapie. Odkrycie w zasięgu automatyczne, jednorazowe i trwałe, przyznaje drobną nagrodę; nazwy i opisy pokazane w dzienniku. Świat: kolorowe miasto z dachami, brukowane drogi, łąki, gęsty las, obóz goblinów, mokradła, kamienne ruiny, twierdza. Dekoracje nie udają przechodnich ścian. Co najmniej 5 odkryć, nowe szczury, dziki, gobliny, pająki i szkielety obok istniejących wilków/ogników/strażników/bossa. Pierwsze szczury blisko poza granicą bezpiecznego miasta.

Nowe owner-only pola stanu: `quests` (lista wpisów), `discoveries` (lista id). Wpis zadania: `{id,title,description,npc_id,status,objectives,reward,requires}`. status: locked, available, active, ready, claimed. objectives: `[{type:'kill'|'discover',target,label,count,required}]`. reward: `{xp,gold,item?}`. Nagroda za zadanie może używać `class_weapon_2`, rozwijanej do odpowiedniej klasy. Quest tracker pokazuje pierwszy aktywny/ready/available cel, listę postępów oraz nazwę i odległość do zleceniodawcy/celu. Dziennik pod J i przyciskiem, osobny od ekwipunku. NPC interakcja E otwiera dziennik, można przyjąć/odebrać zadanie przy właściwym NPC.

Komendy `quest_accept {quest_id}`, `quest_claim {quest_id}`. Zasięg 150, żywa postać, odpowiedni NPC, serwer weryfikuje zależności/progres. Nagrody dokładnie raz, zapis SQLite; pełny plecak nie gubi gwarantowanej nagrody (odmowa odebrania do zwolnienia miejsca). Zabójstwa liczone tylko od przyjęcia, również dla kwalifikujących się członków party. Odkrycia zrobione wcześniej mogą zaliczyć cel.

Minimalna ścieżka: zadanie w mieście na 3 szczury; wizyta przy Starym Młynie; 3 gobliny i odkrycie obozu; odkrycie ruin i 3 szkielety; opcjonalna wyprawa drużynowa na Władcę Twierdzy. Wczesne zadania dają mikstury/złoto i gwarantowaną broń klasy tier 2, a dziennik pokazuje kolejne cele. Dokładny katalog i pozycje ustala implementacja serwera; oba klienty renderują metadane, bez duplikowania logiki nagród.

## Weryfikacja

Testy serwera: prędkość i przekątna, stałe celowanie przy ruchu, faktyczne eventy kręgu, speech, zadania/persistencja/podwójna nagroda/zasięg/pełny plecak, odkrycia raz. Regresja walki/PvP/migracji. Browser: Enter od razu po loginie, Enter po kliknięciu HUD, tekst bez ruchu, dymek u drugiego gracza, zadania/NPC i pierwszy cel normalnymi wejściami, efekt maga podczas ruchu i krąg ognia, desktop i touch screenshots. Godot: parser + przegląd; bez silnika nie deklarujemy testu uruchomienia.
