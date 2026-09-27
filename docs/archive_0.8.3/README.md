# Bractwo — Pogranicze 0.8.3 · Pierwszy krąg od początku

Pełny projekt na bazie `BRACTWO_0.8.1_DND_PVP_PELNE_CZARY_FULL_SOURCE.zip`: serwer Python, klient WWW i klient Godot. Bez APK, AAB i EXE. Mapa, miasta, piętra, drogi, grafika, przedmioty, zadania, zapisy i zasady ochrony PvP pozostają z poprzedniej paczki.

## Nowe w 0.8.3

**Czarodziej i druid otrzymują cały obecny katalog I kręgu już na poziomie 1.** Czarodziej: Magiczny pocisk, Płonące dłonie, Tarcza, Zbroja maga i Długonogi. Druid: Leczenie ran, Uzdrawiające słowo, Oplątanie i Długonogi. Sztuczki nadal są dostępne i darmowe; I krąg kosztuje jak wcześniej 6 many (Tarcza pobiera ją dopiero przy reakcji).

Pozostałe kręgi nie przyspieszają: **II na 20, III na 30, IV na 40, V na 50, VI na 60, VII na 70, VIII na 80, IX na 90.** Łowca nadal dostaje I krąg na 20, następne co 20 poziomów. Przemiany i dodatkowe ataki bez zmian.

Zmiana obejmuje serwer, księgę, pasek, opisy klas, pomoc i listę odblokowań WWW/Godot. Domyślne sloty 4/5 od razu udostępniają Magiczny pocisk/Tarczę lub Leczenie ran/Oplątanie. Nie nadpisuje się ustawień paska zapisanych przez gracza. Pełny opis: `docs/CHANGELOG_0.8.3.md`.

## Zachowane zmiany 0.8.2

**Potwory po zgubieniu celu zostają dokładnie tam, gdzie zakończyły pościg.** Żywy, sprowokowany potwór nie wraca do spawnu ani starej trasy patrolu. Pościg ogranicza aktualny dystans do celu, nie odległość od punktu odrodzenia. Po ponownym zbliżeniu potwór podejmuje walkę z nowej pozycji. Dotyczy to zwykłych stworzeń, strzelców i bossów. Nie ma szybkiego leczenia za odwrót: zwykła regeneracja 0,25 HP/s zaczyna się dopiero po 12 s bez celu/ataków, w aktywnie symulowanej okolicy. Ochrona miast pozostaje.

Po zasłonięciu się ścianą potwór przez maks. 12 s szuka przy ostatniej widzianej pozycji, zamiast znać bieżące współrzędne gracza przez ścianę. Po śmierci odradza się w pierwotnym miejscu. Nowe, jeszcze niesprowokowane potwory zachowują patrol. Położenia potworów pozostają stanem działającego serwera, nie nowym zapisem w bazie: restart, jak wcześniej, odtwarza świat potworów.

**Zwykły autoatak czarodzieja to teraz Iskra różdżki: 1k4 ognia, bez skalowania.** Ognisty pocisk z paska nadal jest darmową sztuczką: 1k10 / 2k10 / 3k10 / 4k10 na poziomach 1/20/50/80. Promień mrozu zachowuje 1k8 → 4k8 i spowolnienie, inne sztuczki zachowują swoje efekty. Silniejsze różdżki nadal poprawiają trafienie czarami, ale nie dodają fikcyjnej premii do obrażeń iskry. Przeliczono też opisy zwykłych i unikatowych różdżek.

Atak różdżki i główny czar dzielą odnowienie 3 s. **Naciśnij sztuczkę na pasku 1–8 podczas odnowienia: zostanie wykonana przed następnym autoatakiem.** To nadal kolejka jednego użycia, nie stałe automatyczne powtarzanie wybranego czaru. Brak nowego kosztu many sztuczek. Te same kości obowiązują w PvE i odblokowanym PvP.

Naprawiono indeksowanie potworów po ich bieżącej pozycji, w tym przy przemieszczeniu czarem. Dzięki temu odciągnięty przeciwnik nie znika z wykrywania i listy celów daleko od swojego spawnu. Zmiany i szczegóły: `docs/CHANGELOG_0.8.2.md`.

## Zachowane z 0.8.1: cały obecny katalog działa w PvP

Po wyłączeniu blokady PvP zaznaczony gracz może być celem ofensywnych czarów, sztuczek, efektów obszarowych i towarzysza łowcy. Działają również spowolnienia, unieruchomienie, oślepienie, przyciąganie, Znak łowcy, ataki przemienionego druida, Tarcza, odporności, tymczasowe HP i koncentracja. Koszty many i progi odblokowań pozostają; w 0.8.2 zmieniono wyłącznie kości podstawowego strzału czarodzieja.

Leczenie i wspierające czary działają na siebie lub wskazanego członka drużyny zgodnie z opisem; zdolności osobiste pozostają osobiste. Przy zaznaczonym przeciwniku leczenie z paska domyślnie leczy własną postać, nie wymaga czyszczenia celu. Wspieranie towarzysza podczas PvP wymaga odblokowania PvP u rzucającego i włącza go do walki. Wsparcie gracza oznaczonego czaszką może nadać wspierającemu białą czaszkę.

**Uwaga: po odblokowaniu PvP obszar może trafić innych uprawnionych do walki graczy spoza drużyny, również gdy głównym celem jest potwór.** Własna postać i drużyna nie otrzymują obrażeń od własnych obszarów. Nadal chronione są poziomy poniżej 8 i bezpieczne osady; obowiązują piętra, zasięgi i ściany. Blokada chroni przed wykonaniem własnego ataku, nie zapewnia nietykalności przed cudzą agresją. Ponowne zablokowanie PvP zatrzymuje własne ataki i szkodliwe efekty na graczach, ale nie kasuje czasu walki ani kar.

Pełne zasady i przypadki brzegowe: `docs/PVP_0.8.1.md`. Lista zmian: `docs/CHANGELOG_0.8.1.md`.

## Mechaniki zachowane z 0.8.0

Obrażenia są naprawdę losowane z kości, np. `1k8+3`, a nie wyświetlane jako kości przy dawnych wysokich wartościach. Zmniejszono HP postaci i potworów, ograniczono premie sprzętu, dodano sześć cech, biegłość, rzuty obronne zależne od czaru, koncentrację, osobne akcje dodatkowe i reakcję Tarcza. Krytyk podwaja kości, nie stały dodatek.

| Klasa | HP na starcie | Broń / podstawowy atak | Ważne odblokowania |
|---|---:|---|---|
| Rycerz | 12 | Miecz `1k8+3` | 2/3/4 ataki na poziomach 20/50/95; Drugi oddech |
| Łowca | 12 | Łuk `1k8+3` | Wilk od 10.; 2 ataki od 20.; kręgi I–V na 20/40/60/80/100 |
| Druid | 10 | Laska wręcz `1k6+2`, Shillelagh `1k8+3` | I krąg od 1.; II od 20., kolejne co 10; wilk od 20.; niedźwiedź z dwoma atakami od 40. |
| Czarodziej | 8 | Iskra różdżki `1k4`; sztuczka Ognisty pocisk `1k10` | Sztuczki rosną na 20/50/80; kręgi I–IX na 1/20/30/…/90 |

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

Aktualizacja **0.8.0 / 0.8.1 / 0.8.2 → 0.8.3 nie wymaga resetu postaci ani nowej migracji schematu bazy**. Po wejściu blokada PvP jest domyślnie włączona, jak wcześniej. W kliencie WWW odśwież stronę; natywny klient wymaga źródeł nowej wersji.

Przy aktualizacji z 0.7: przy pierwszym wejściu dawny paladyn zostaje łowcą; numery UID przedmiotów, poziom, PD, złoto, zadania i odkrycia są zachowane. HP przelicza się w przybliżeniu proporcjonalnie do starego maksimum. Usunięte stare runy dają jednorazowy zwrot 25 złota za sztukę. Ekwipunek otrzymuje nowe statystyki z tych samych szablonów. Przemiany i koncentracja nie wracają po wylogowaniu. Pasek czarów zapisuje serwer. Cofnięcie do 0.7 wymaga oryginalnej kopii bazy.

## Zakres adaptacji

Podstawą wybranych czarów jest SRD 5.2.1. **Mana, runda 3 s, dostęp do kręgów, część efektów i towarzysz są zasadami Bractwa**, nie wiernym przeniesieniem wszystkich zasad stołowych. Nie ma slotów czarów, inicjatywy, pełnej listy atutów/podklas, dowolnego przygotowywania zaklęć ani rzucania z wyższego kręgu. Szczegółowe różnice: `docs/RULES_0.8.md`; atrybucja: `LICENSE-SRD.txt`.

W 0.8.1 usunięto ograniczenie czarów klasowych i wilka do PvE. Zakres odbiorców każdego wpisu katalogu opisuje `docs/SPELLS_0.8.md`; reguły PvP mają zastosowanie po stronie serwera, także przy bezpośrednim wysyłaniu pakietów.

## Weryfikacja

**247 testów Python, 10 testów Node i 13 sprawdzeń interfejsu Chromium: PASS.** W tym 23 nowe testy pierwszego kręgu na poziomie 1, późniejszych progów, many, zapisów i katalogu sieciowego. Dotychczasowe testy PvP, pościgu i sztuczek pozostają w zestawie.

Interfejs sprawdzono z rzeczywistym serwerem poprzez kontrolowany most WebSocket i testowy localStorage; to nie jest test natywnej nawigacji HTTP przeglądarki ani fizycznego telefonu. Bezpośrednia nawigacja lokalna była blokowana przez środowisko. Raport i wyniki: `docs/TEST_REPORT.md`, `docs/qa_0.8.3/`. **Godot nie został uruchomiony ani wyeksportowany. ZIP zawiera źródła, nie APK/AAB/EXE.**

```bash
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs
node --check web/game.js
node --check web/runtime.js
# Opcjonalny test UI: wymaga Playwright i Chromium.
python tools/browser_083_smoke.py
```

Dokumenty `archive_*`, wcześniejsze `qa_*` i `tests/legacy_0_7/` są historyczne. Reguły 0.8 oraz uzupełnienia PvP 0.8.1, pościgu/balansu 0.8.2 i pierwszego kręgu 0.8.3 mają pierwszeństwo.
