# Bractwo — Pogranicze 0.8.0 · Kości, kręgi i towarzysze

Pełny projekt na bazie przesłanego `Bractwo_0.7.0_RUNDY_K20_FULL`: serwer Python, klient WWW i klient Godot. Bez APK, AAB i EXE. Mapa, miasta, piętra, drogi, grafika, przedmioty, zadania, zapisy i zasady ochrony PvP pozostają z poprzedniej paczki.

## Najważniejsze zmiany

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

Przy pierwszym wejściu dawny paladyn zostaje łowcą; numery UID przedmiotów, poziom, PD, złoto, zadania i odkrycia są zachowane. HP przelicza się w przybliżeniu proporcjonalnie do starego maksimum. Usunięte stare runy dają jednorazowy zwrot 25 złota za sztukę. Ekwipunek otrzymuje nowe statystyki z tych samych szablonów. Przemiany i koncentracja nie wracają po wylogowaniu. Pasek czarów zapisuje serwer. Cofnięcie do 0.7 wymaga oryginalnej kopii bazy.

## Zakres adaptacji

Podstawą wybranych czarów jest SRD 5.2.1. **Mana, runda 3 s, dostęp do kręgów, część efektów i towarzysz są zasadami Bractwa**, nie wiernym przeniesieniem wszystkich zasad stołowych. Nie ma slotów czarów, inicjatywy, pełnej listy atutów/podklas, dowolnego przygotowywania zaklęć ani rzucania z wyższego kręgu. Szczegółowe różnice: `docs/RULES_0.8.md`; atrybucja: `LICENSE-SRD.txt`.

Ofensywne czary z księgi i wilk są obecnie **PvE**. PvP zachowuje ataki podstawowe (w tym Ognisty pocisk czarodzieja), ochronę osad i niskich poziomów, blokadę ataku oraz kary. Leczenie innego gracza wymaga wspólnej drużyny, zasięgu i braku walki PvP u odbiorcy. Pełna magia PvP nie jest deklarowana w tej wersji.

## Weryfikacja

Raport i surowe wyniki: `docs/TEST_REPORT.md`, `docs/qa_0.8/`. Testy automatyczne obejmują reguły, wszystkie wpisy katalogu, migrację, autoatak, czary, towarzysza i HTTP/WebSocket. Test wizualny WWW wykorzystał Chromium z kontrolowanym mostem transportowym; ograniczenia są opisane w raporcie. Nie przeprowadzono wielogodzinnego testu balansu, testu na fizycznym telefonie ani eksportu Godot.

```bash
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs
node --check web/game.js
node --check web/runtime.js
```

Pliki `tests/legacy_0_7/` i starsze dokumenty wersjonowane są historyczne, a nie zestawem potwierdzającym działanie nowych zasad. Aktualne reguły 0.8 mają pierwszeństwo.
