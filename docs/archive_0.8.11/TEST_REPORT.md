# Bractwo 0.8.11 — raport weryfikacji

Baza: `BRACTWO_0.8.10_OKNA_EKWIPUNEK_MIKSTURY_FULL_SOURCE.zip`. Testy wykonano lokalnie na zmodyfikowanych źródłach, bez produkcyjnej bazy użytkownika. Starsze raporty w archiwach dotyczą wcześniejszych wersji.

## Python — 560 / 560 PASS

`python -m unittest discover -s tests -v` — **560 testów, 71,181 s, OK**. Log: `qa_0.8.11/python_full.log`.

Dodano 15 przypadków w `tests/test_movement_atlas_0811.py`: kompletność i unikatowość progów czarów dla każdej klasy; rzeczywiste kręgi druida i łowcy; ataki rycerza; cechy i biegłość; bazowa mana; prawidłowe +2k8/+2k4 leczenia przy wyższym kręgu i ręczny wybór niższego; niezależność dx/dy od wyboru, usunięcia i śmierci celu; metadane oryginalnej rzeki i mostu.

Pozostałe 545 regresji zachowano: D&D, mana i skalowanie, PvP, geometria czarów, awanse, łupy i prywatne odkrycia, mikstury, opóźniony powrót potworów, persystencja i uruchamianie. Zmiana istniejących oczekiwań dotyczyła numeru wersji `/health`; nie obniżano oczekiwań balansu. Test trasy statycznej obejmuje nowy `/atlas_map.js`.

## JavaScript — 65 / 65 PASS

`node --test tests/*.cjs` — **65 testów, bez błędów**. Log: `qa_0.8.11/node_full.log`.

Nowych 13 przypadków w `test_atlas_0811.cjs` sprawdza dopasowanie całego świata do kamery, limit 1–64×, przybliżanie do kursora, okolice początku mapy i współrzędne zerowe, ograniczanie przesunięcia, reset widoku, oryginalną rzekę i most, późniejsze drogi wodne, kolejność rysowania mostów, wspólne współrzędne obu map, minimalną grubość małych obiektów i pomijanie niewidocznych segmentów.

`node --check` wszystkich `web/*.js` oraz `python -m compileall -q server run.py tests tools` zakończyły się poprawnie. Nie jest to kompilacja GDScript.

## Chromium — 26 / 26 PASS

`python tools/browser_0811_smoke.py` — wynik `qa_0.8.11/results.json`, log `qa_0.8.11/browser.log`, zrzuty PNG w tym samym katalogu. **Brak błędów JavaScript strony.**

Użyto rzeczywistego HTML, CSS, JavaScript i grafik klienta oraz rzeczywistych handlerów serwera aiohttp. Komunikację WebSocket prowadzi kontrolowany most Python. Zegar i losowania są kontrolowane; AI potworów w tym scenariuszu jest wstrzymane, a odnowienie ataku konta testowego wydłużone. Śmierć celu wywołuje autorytatywne `Game.defeat()`, a kierunek i faktyczne przemieszczenie są sprawdzane na serwerze. AI, rzuty i skalowanie sprawdzono oddzielnie w testach Python. Nie jest to sesja produkcyjna ani fizyczny telefon.

Sprawdzone działania:
- każdy z WASD trzymany przy zaznaczaniu, faktycznej śmierci i automatycznym usunięciu celu; prawidłowe zatrzymanie dopiero po puszczeniu;
- ruch po skosie, ręczne X celu i puszczenie tylko jednego kierunku;
- C, I, K, J, P i H podczas marszu; Escape zamykający okno bez utraty wciśniętego kierunku;
- dwukrotne E dla świata/atlasu oraz kupca; oba przypadki podczas marszu;
- bezpieczne zatrzymanie przy pisaniu czatu oraz utracie aktywności; brak zablokowanego ruchu po powrocie;
- rzeczywiste piksele rzeki i mostu w canvasie minimapy oraz atlasu, nie tylko istnienie metadanych;
- lewy/prawy klik, kółko, przyciski +/−, okolica, przesuwanie mapy i zachowanie kamery przy ruchu oraz zamknięciu/otwarciu;
- przeciąganie okna atlasu uchwytem podczas trzymanego kierunku; bez zmiany kamery i zerowania ruchu;
- osobny wybór celu nawigacji bez zamykania ani przypadkowego zoomu;
- rozwój druida bez obcych odblokowań; jasny opis liczników treningu;
- rozdzielczości **1440×900, 390×844 i 844×390**. Sprawdzono przyciski mapy, brak poziomego przewijania strony, dostępność widocznego fragmentu mapy (nie wąskiego paska), E i ruch przy karcie postaci na obu układach mobilnych.

Księga świata otrzymała wyższą warstwę nad zwykłym HUD-em na małym ekranie i większą wysokość w niskim widoku poziomym. Ręczne przesuwanie nadal pozwala świadomie nakładać okna; ↺ przywraca układ domyślny. Rozmieszczenie wszystkich możliwych kombinacji zapisanych przez użytkownika nie zostało wyczerpująco sprawdzone.

## Rzeczywisty lokalny proces — 15 / 15 PASS

`python tests/smoke_railway.py` — log `qa_0.8.11/local_process.log`. Osobny proces `run.py`, natywne HTTP/WebSocket bez mostu Chromium, dwa konta we wspólnym świecie, zapis i restart przez SIGTERM, kopia bazy, ponowne logowanie i kontrola SQLite.

Dodatkowo sprawdzono start przez **`python server/server.py`**, używany w skryptach Windows/Unix: odpowiedź health 0.8.11 i bajtowo identyczny nowy plik atlasu. Log: `qa_0.8.11/direct_start.log` (2 dodatkowe sprawdzenia startu).

To lokalna weryfikacja konfiguracji, nie wdrożenie na Railway i nie budowa obrazu Docker.

## Weryfikacja reguł leczenia

Sprawdzone oficjalne opisy 25.09.2026:
- https://www.dndbeyond.com/spells/2619079-cure-wounds — 2k8 + cecha; +2k8 za wyższy krąg.
- https://www.dndbeyond.com/spells/2619143-healing-word — 2k4 + cecha; +2k4 za wyższy krąg.

`server/dnd_content.py`, `dnd_game.py`, `combat_rules.py`, `spell_scaling.py`, `monster_ai.py`, `inventory_rules.py`, `loot_content.py`, `loot_tables.py` i `level_up.py` są **bajtowo identyczne** z wejściową wersją 0.8.10. Nie zmieniono kości, HP, many, ekwipunku ani zasad powrotu potworów.

## Ograniczenia

Python **3.13.5**, aiohttp **3.13.3**, Node **22.16.0**, lokalny Chromium/Playwright. Requirements nadal przypina odziedziczone **aiohttp 3.13.5**; nie wykonano osobnego przebiegu z tą wersją biblioteki. Narzędzia QA nie są zależnościami produkcyjnego serwera.

Źródła Godota zmieniono, ale **nie wykonano importu projektu, kompilacji GDScript, uruchomienia w silniku ani eksportu**. Próba pobrania narzędzia była niedostępna w środowisku. Nie ma APK/AAB/EXE. Nie testowano fizycznego Androida, wielogodzinnego balansu ani obciążenia wielu graczy. Nie wdrożono na koncie Railway i nie zbudowano Dockera.

## Pakowanie

Każdy ZIP ma własny `SOURCE_MANIFEST.json` z SHA-256 plików. Integralność ZIP-a, kompletność i skróty manifestu są sprawdzane po zapisie archiwum. Railway ma pliki w głównym katalogu; Full Source ma folder `Bractwo_0.8.11/`. Pliki serwera i WWW w obu paczkach muszą być identyczne. Pomijane są cache, bazy, klucze, eksporty i pliki fontów. Dane kont w QA są wyłącznie lokalnymi danymi testowymi.
