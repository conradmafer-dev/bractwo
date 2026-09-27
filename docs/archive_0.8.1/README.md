# Bractwo — Pogranicze 0.8.1 · Czary i zdolności w PvP

Pełny projekt na bazie `BRACTWO_0.8.0_DND_KREGI_TOWARZYSZE_FULL_SOURCE.zip`: serwer Python, klient WWW i klient Godot. Bez APK, AAB i EXE. Mapa, miasta, piętra, drogi, grafika, przedmioty, zadania, zapisy i zasady ochrony PvP pozostają z poprzedniej paczki.

## Nowe w 0.8.1: cały obecny katalog działa w PvP

Po wyłączeniu blokady PvP zaznaczony gracz może być celem ofensywnych czarów, sztuczek, efektów obszarowych i towarzysza łowcy. Działają również spowolnienia, unieruchomienie, oślepienie, przyciąganie, Znak łowcy, ataki przemienionego druida, Tarcza, odporności, tymczasowe HP i koncentracja. Nie zmieniono kosztów many, kości ani progów odblokowań z 0.8.0.

Leczenie i wspierające czary działają na siebie lub wskazanego członka drużyny zgodnie z opisem; zdolności osobiste pozostają osobiste. Przy zaznaczonym przeciwniku leczenie z paska domyślnie leczy własną postać, nie wymaga czyszczenia celu. Wspieranie towarzysza podczas PvP wymaga odblokowania PvP u rzucającego i włącza go do walki. Wsparcie gracza oznaczonego czaszką może nadać wspierającemu białą czaszkę.

**Uwaga: po odblokowaniu PvP obszar może trafić innych uprawnionych do walki graczy spoza drużyny, również gdy głównym celem jest potwór.** Własna postać i drużyna nie otrzymują obrażeń od własnych obszarów. Nadal chronione są poziomy poniżej 8 i bezpieczne osady; obowiązują piętra, zasięgi i ściany. Blokada chroni przed wykonaniem własnego ataku, nie zapewnia nietykalności przed cudzą agresją. Ponowne zablokowanie PvP zatrzymuje własne ataki i szkodliwe efekty na graczach, ale nie kasuje czasu walki ani kar.

Pełne zasady i przypadki brzegowe: `docs/PVP_0.8.1.md`. Lista zmian: `docs/CHANGELOG_0.8.1.md`.

## Mechaniki zachowane z 0.8.0

Obrażenia są naprawdę losowane z kości, np. `1k8+3`, a nie wyświetlane jako kości przy dawnych wysokich wartościach. Zmniejszono HP postaci i potworów, ograniczono premie sprzętu, dodano sześć cech, biegłość, rzuty obronne zależne od czaru, koncentrację, osobne akcje dodatkowe i reakcję Tarcza. Krytyk podwaja kości, nie stały dodatek.

| Klasa | HP na starcie | Broń / podstawowy atak | Ważne odblokowania |
|---|---:|---|---|
| Rycerz | 12 | Miecz `1k8+3` | 2/3/4 ataki na poziomach 20/50/95; Drugi oddech |
| Łowca | 12 | Łuk `1k8+3` | Wilk od 10.; 2 ataki od 20.; kręgi I–V na 20/40/60/80/100 |
| Druid | 10 | Laska wręcz `1k6+2`, Shillelagh `1k8+3` | Kręgi od 10. co 10; wilk od 20.; niedźwiedź z dwoma atakami od 40. |
| Czarodziej | 8 | Ognisty pocisk `1k10` | Darmowe sztuczki; kręgi I–IX na 10/20/…/90 |

Paczka zawiera **43 czary/sztuczki oraz 4 wpisy zdolności klasowych**. To wybrany, działający katalog, nie wszystkie czary z podręczników. Mana zostaje, sztuczki kosztują zero many. Opisy polskie zawierają również angielską nazwę, kości, warunki i krąg. Pełny katalog: `docs/SPELLS_0.8.md`.

Pasek **1–8** przypisujesz w księdze **K**. Czary rzucone w czasie odnowienia głównej akcji mają pojedynczą kolejkę przed kolejnym autoatakiem. Rzucenie czaru dodatkowego nie odbiera zwykłego ataku. Kliknięcie żywego potwora albo jego wiersza na liście włącza autoatak w zasięgu i linii widzenia. Postać nie goni ani nie zmienia celu. **Esc / × celu** zatrzymuje autoatak. Utrata aktywności okna wstrzymuje go.

**Ranking TOP 20** jest na ekranie logowania, także telefonu: poziom, następnie PD i liczba pokonanych potworów. Nie publikuje kont, haseł ani danych ekwipunku. Mały panel sterowania zamykasz **×**; wybór zapisuje się na urządzeniu. Stare stałe podpowiedzi na dole zastąpiono panelem. Napisy na przyciskach oraz kontekst rozmowy pozostają.

## Uruchomienie

Rozpakuj cały folder. Na Windows uruchom `start_windows.bat`, pozostaw okno serwera otwarte i wejdź w przeglądarce na `http://127.0.0.1:8080`. Wymagany Python 3.11+; pierwszy start instaluje zależność z `server/requirements.txt`.

Linux/macOS: `bash start_unix.sh`. Wspólna sieć Wi-Fi: `start_windows.bat lan` albo `bash start_unix.sh lan`; drugi gracz otwiera `http://IP_KOMPUTERA:8080`. Dla dostępu publicznego używaj HTTPS/WSS. Nie wystawiaj lokalnego trybu HTTP z hasłami bez szyfrowania w internecie.

Ręcznie:
```bash
python -m pip install -r server/requirements.txt
python server/server.py --host 127.0.0.1 --port 8080 --db data/world.sqlite3
```

Godot: importuj `client/project.godot` do Godot 4.5.x Standard i uruchom projekt przy działającym serwerze. Natywny klient jest zmodyfikowany, ale **w tej paczce nie został skompilowany ani uruchomiony w silniku**. Instrukcje eksportu pozostają w `docs/BUILD.md`.

## Aktualizacja i zapisy

Zatrzymaj stary serwer. Zrób kopię `data/world.sqlite3`; dopiero potem skopiuj bazę do identycznego katalogu nowej paczki. Aktualizuj **serwer i klienta razem**. Nie uruchamiaj obu serwerów na tej samej bazie. Przy kopiowaniu aktywnej bazy mogą istnieć pliki WAL, dlatego bazę przenoś po poprawnym zatrzymaniu serwera.

Aktualizacja **0.8.0 → 0.8.1 nie wymaga resetu postaci ani nowej migracji schematu bazy**. Po wejściu blokada PvP jest domyślnie włączona, jak wcześniej. W kliencie WWW odśwież stronę; natywny klient wymaga źródeł nowej wersji.

Przy aktualizacji z 0.7: przy pierwszym wejściu dawny paladyn zostaje łowcą; numery UID przedmiotów, poziom, PD, złoto, zadania i odkrycia są zachowane. HP przelicza się w przybliżeniu proporcjonalnie do starego maksimum. Usunięte stare runy dają jednorazowy zwrot 25 złota za sztukę. Ekwipunek otrzymuje nowe statystyki z tych samych szablonów. Przemiany i koncentracja nie wracają po wylogowaniu. Pasek czarów zapisuje serwer. Cofnięcie do 0.7 wymaga oryginalnej kopii bazy.

## Zakres adaptacji

Podstawą wybranych czarów jest SRD 5.2.1. **Mana, runda 3 s, dostęp do kręgów, część efektów i towarzysz są zasadami Bractwa**, nie wiernym przeniesieniem wszystkich zasad stołowych. Nie ma slotów czarów, inicjatywy, pełnej listy atutów/podklas, dowolnego przygotowywania zaklęć ani rzucania z wyższego kręgu. Szczegółowe różnice: `docs/RULES_0.8.md`; atrybucja: `LICENSE-SRD.txt`.

W 0.8.1 usunięto ograniczenie czarów klasowych i wilka do PvE. Zakres odbiorców każdego wpisu katalogu opisuje `docs/SPELLS_0.8.md`; reguły PvP mają zastosowanie po stronie serwera, także przy bezpośrednim wysyłaniu pakietów.

## Weryfikacja

**187 testów Python, 10 testów Node i 10 sprawdzeń interfejsu Chromium: PASS.** Raport i wyniki: `docs/TEST_REPORT.md`, `docs/qa_0.8.1/`. Testy obejmują cały katalog, działania na graczach, blokadę, bezpieczne strefy, drużynę, niskie poziomy, kolejkę, koncentrację, zabójstwa i prawdziwe połączenia dwóch klientów WebSocket. UI sprawdzono przez kontrolowany most transportowy do serwera; nie jest to test natywnej nawigacji sieciowej przeglądarki. Godot nie został uruchomiony ani wyeksportowany; nie ma APK/AAB/EXE ani potwierdzenia działania na fizycznym telefonie.

```bash
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs
node --check web/game.js
node --check web/runtime.js
# Opcjonalny test UI: wymaga Playwright i dostępnego Chromium.
python tools/browser_pvp_smoke.py
```

Dokumenty `archive_*`, poprzednie `qa_*` i `tests/legacy_0_7/` są historyczne. Reguły 0.8 wraz z uzupełnieniem PvP 0.8.1 mają pierwszeństwo.
