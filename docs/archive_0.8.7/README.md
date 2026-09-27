# Bractwo 0.8.7 — skalowanie czarów i przyrosty po awansie

Pełny projekt rozwijający `BRACTWO_0.8.6_AWANSE_PRZYROSTY_KASKADA_FULL_SOURCE.zip`: serwer Python, klient WWW i źródła Godota. Zachowano świat, potwory bez odwrotu do patrolu, PvP, grafikę, manę, kartę postaci, 24 skróty, F, zapis i kaskadę podsumowań. **Nie jest to APK, AAB ani EXE.**

## Co się zmieniło

Skalowalne czary rzeczywiście otrzymują dodatkowe kości obrażeń/leczenia, pociski, promienie, odbiorców albo czas działania według reguł danego wpisu SRD 5.2.1. Nie ma uniwersalnego mnożnika wszystkich czarów. Wyższy krąg rzucania kosztuje więcej many. Czary, które nie mają takiego skalowania, zachowują swój koszt i działanie.

Czarodziej i druid odblokowują kręgi na poziomach **1, 10, 20, 30, 40, 50, 60, 70, 80**. Łowca nadal później: **20, 40, 60, 80, 100**. Przyrost zależny od jednego poziomu klasy D&D przypada co 5 poziomów gry, od dwóch co 10, od trzech co 15. Sztuczki pozostają darmowe i zwiększają liczbę kości na **20., 50. i 80. poziomie**. Nie dopisano zaklęciom nieistniejących reguł wzrostu z dawnych edycji.

Magiczny pocisk ma 3 pociski na początku, 4 od poziomu 10, 5 od 20 i maksymalnie 11 od 80 w najwyższej mocy. Każdy zadaje 1k4+1 i leci osobnym łukiem. Płonące dłonie zyskują +1k6 za wyższy krąg, Leczenie ran +2k8, Uzdrawiające słowo +2k4. Palący promień zwiększa liczbę promieni; Łańcuch błyskawic liczbę odbiorców. Pełna tabela 18 czarów: `docs/SPELL_SCALING_0.8.7.md`.

## Wybieranie mocy

Otwórz **C → Czary** lub **K**. Przy czarze z dostępnym wzmocnieniem wybierz **Auto · najwyższa moc** albo konkretny niższy krąg. Wybór zapisuje się z postacią i działa na obu paskach oraz pod F. Nie tworzy osobnych kopii czaru na pasku. Księga pokazuje aktualne kości/liczbę pocisków/cele/czas, koszt oraz pierwszy następny próg wzrostu.

Na przykład na poziomie 10 czarodziej może rzucać Magiczny pocisk kręgu II: 4 pociski za 30 many, albo wybrać I: 3 pociski za 20. Gdy brakuje many, gra nie zmienia potajemnie wybranej mocy. Sztuczki nadal są alternatywą bez kosztu.

Długotrwałe pola i kolejne bezpłatne wywołania utrzymywanego czaru zachowują krąg/kości opłacone na początku. Awans nie wzmacnia ich za darmo. Przycisk **Zakończ czar** w księdze pozwala przerwać koncentrację przed opłaceniem nowej wersji. Zmiana selektora nie przerywa istniejącego zaklęcia sama z siebie.

Długonogi nie zyskuje dłuższego czasu ani większej szybkości: wyższy krąg daje dodatkowego członka drużyny w zasięgu dotyku. Nadal 600 rund, +10 stóp, bez koncentracji i bez przerywania atakiem. Znak łowcy zwiększa czas na kręgach III i V, nie premię 1k6. Utrzymano zegar Bractwa: 3 sekundy na rundę.

## Panel awansu

Każda zmiana ma własny wiersz z samym przyrostem, np.:

```
Magiczny pocisk +1 pocisk
Płonące dłonie +1k6 do obrażeń
Leczenie ran +2k8 do leczenia
Leczenie ran +1 do leczenia
Długonogi +1 cel
```

Wzrost kosztu maksymalnej mocy ma osobny wiersz. Nie ma wartości przed/po ani wierszy bez zmiany. Nowo poznany czar ma osobny wpis z ikoną. Podsumowanie mówi o nowo dostępnej maksymalnej mocy również przy ręcznie wybranym tańszym kręgu; nie nadpisuje tego wyboru.

Każdy poziom tworzy oddzielne podsumowanie. Kaskada przy lewej krawędzi i dolny **Zamknij** pozostają. Zamknięcie usuwa tylko wybrany panel. Niezamknięte podsumowania zapisują się z postacią. Historyczne awanse 0.8.6 nie otrzymują retroaktywnych wierszy skalowania. Nie dodano nowych atutów ani punktów cech.

## Uruchomienie i aktualizacja

Windows: rozpakuj ZIP, uruchom `start_windows.bat` i otwórz `http://127.0.0.1:8080`. Wymagany Python 3.11+. Sieć lokalna: `start_windows.bat lan`. Linux/macOS: `./start_unix.sh`. Godot: import `client/project.godot`.

**Reset postaci nie jest potrzebny.** Zatrzymaj stary serwer, zrób kopię `data/world.sqlite3` i przenieś bazę do nowej paczki. Podmień serwer oraz klienta razem. W WWW odśwież stronę z pominięciem pamięci podręcznej. Nie nadpisuj nowego kodu starymi plikami. Istniejące postacie od razu uzyskają skalowanie właściwe dla swojego poziomu; domyślnie będą korzystać z Auto. Pula many i poziomy postaci nie są resetowane.

## Weryfikacja

**437 testów Python, 36 testów JavaScript i 14 sprawdzeń interfejsu Chromium — PASS.** Skontrolowano rzeczywiste kości, liczbę trafień, koszty, zmiany preferencji, koncentrację, pola, PvP, zapis, migrację, prywatność i podsumowania awansów. Logi i zrzuty: `docs/qa_0.8.7/`. Raport: `docs/TEST_REPORT.md`.

WWW uruchamiano z rzeczywistym serwerem przez kontrolowany most WebSocket Python, z testowym localStorage i kontrolowanym zegarem. Nie jest to test natywnej sieci Chromium, fizycznego telefonu ani hostingu. **Godot został zmodyfikowany, ale nie uruchomiony, zaimportowany, skompilowany ani wyeksportowany w silniku.**

```sh
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs tests/test_level_up.cjs
python tools/browser_087_smoke.py
```

Atrybucja: `LICENSE-SRD.txt`. Zmiany: `docs/CHANGELOG_0.8.7.md`. Pełne reguły tej adaptacji: `docs/SPELL_SCALING_0.8.7.md`. Protokół: `docs/PROTOCOL.md`. Eksport: `docs/BUILD.md`. Starsze raporty i zrzuty są historyczne, a nie nowymi wynikami testów.
