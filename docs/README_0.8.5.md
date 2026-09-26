# Bractwo 0.8.5 — grafika czarów, karta postaci i 24 skróty

Pełny projekt na bazie `BRACTWO_0.8.4_MANA_PASEK_STATUSY_KREGI_FULL_SOURCE.zip`: serwer Python, klient WWW i źródła klienta Godot. **Nie zawiera APK, AAB ani EXE.** Zachowano świat, zadania, ekwipunek, klasy, kręgi, manę, PvP, towarzysza, przemiany oraz pościg bez powrotu do spawnu.

## Czary: widoczny obszar i trafienia

Obszar na serwerze i grafika klienta korzystają z tej samej geometrii. Stożki nie są już wycinkami koła z dodatkowym zapasem trafienia, a linie są prostokątami o określonej długości i szerokości. Koła, kwadrat Oplątania, dziesięć przylegających pól Burzy ognia i cztery obszary Roju meteorów mają własne kształty. Płonące dłonie obejmują stożek długości 15 stóp; Stożek zimna 60 stóp; Błyskawica linię 100 × 5 stóp, Promień słońca 60 × 5 stóp. Kula ognia ma promień 20 stóp. Pięć stóp odpowiada 32 jednostkom mapy.

**Magiczny pocisk:** trzy widoczne pociski po różnych łukach, każdy ze smugą i błyskiem. Mechanicznie nadal trzy rzuty 1k4+1. **Promień mrozu:** niebiesko-biały rdzeń, poświata i lodowy rozprysk przy trafieniu. Pozostałe czary otrzymały przypisane motywy: promienie, płomienie, łańcuchy błyskawic, korzenie, lodowe kryształy, meteory, leczenie, tarcze, przyzwanie i przemiany. Długotrwałe pola pozostają widoczne do końca działania i znikają po przerwaniu koncentracji.

Dodano **47 różnych ikon czarów i zdolności oraz 7 ikon wyposażenia**, w obu klientach. Ich źródłowy generator jest w `tools/generate_spell_icons.py`; efekty walki rysują `web/spell_vfx.js` i `client/scripts/spell_vfx.gd`.

Obowiązują wcześniejsze zasady PvP, osad, drużyny, niskich poziomów, pięter i przeszkód. Trafienie wymaga położenia środka stworzenia w obszarze oraz przejścia pozostałych kontroli serwera. Dekoracyjna poświata nie powiększa obszaru. Wybrany przeciwnik nadal określa kierunek lub środek czaru: nie dodano dowolnego wskazywania ziemi, rozdzielania Magicznego pocisku między kilka celów ani swobodnego układania pól Burzy ognia i meteorów. Ich układy są stałe. Animacje pocisków są oprawą rozstrzygnięcia serwera, nie nową symulacją kolizji pocisków w czasie lotu.

## Osobna karta postaci

**C** lub przycisk w prawym górnym rogu otwiera kartę, bez dziennika i atlasu. Skrót **I** prowadzi prosto do ekwipunku, **K** do czarów. Mapa, dziennik, drużyna i usługi świata pozostają w swoich osobnych oknach.

Karta ma cztery zakładki:

- **Ekwipunek:** założona broń, pancerz i pierścień u góry; niżej plecak w trzech rzędach po pięć pól. Kolejne strony mieszczą resztę przedmiotów. Kliknięcie przedmiotu pokazuje opis i dostępne działania zamiast długiej listy pojedynczych pozycji.
- **Statystyki:** zdrowie, mana, poziom i doświadczenie, KP, kości i premie ataku/obrażeń, liczba ataków, atak czarem, ST czarów, cechy, rzuty obronne, szybkość, odporności, aktualne efekty i pozostałe istniejące dane postaci. Wartości pochodzą z obliczeń walki i odświeżają się podczas otwartego okna.
- **Atuty:** osobna, na razie pusta zakładka. Ta aktualizacja nie dodaje ani nie sprzedaje jeszcze atutów.
- **Czary:** dostępne i przyszłe czary klasy, ikony, koszty, wymagane poziomy, używanie i przypisywanie skrótów. Zablokowane czary są widoczne w księdze, ale nie zajmują paska.

## Dwa paski i adaptacyjny F

Pierwszy rząd: **1 2 3 4 5 6 7 8 9 0 − =**. Drugi: **F1–F12**. Razem **24 pola**. Wszystkie odblokowane czary i zdolności są automatycznie umieszczane; po przekroczeniu 24 wpisów strzałki lub Page Up / Page Down zmieniają cały zestaw obu rzędów. Przypisania zmieniasz w zakładce Czary. Na małym ekranie oba rzędy przewijają się poziomo razem, aby przyciski pozostały dotykowe.

**F to oddzielny, adaptacyjny skrót**, nie F1: wybiera najczęstszy czar/zdolność z **ostatnich 100 skutecznych użyć postaci**. Przy remisie wybiera ostatnio użyty. Nie liczy nieudanych prób, braku many, zablokowanych czarów ani samego zakolejkowania. Trzy pociski liczą się jako jeden czar, impulsy pola nie zwiększają licznika, a Tarcza liczy się przy rzeczywistym uruchomieniu reakcji, nie podczas włączania gotowości. Nowa postać lub stary zapis bez historii zaczyna od domyślnej zdolności klasy. Historia zapisuje się razem z postacią. Skrót zmienia wybór, nie uruchamia ciągłego rzucania.

## Uruchomienie i aktualizacja

Windows: uruchom `start_windows.bat`, otwórz `http://127.0.0.1:8080` i pozostaw serwer włączony. Wymagany Python 3.11+; pierwszy start instaluje zależności. `start_windows.bat lan` udostępnia serwer w sieci lokalnej. Linux/macOS: `./start_unix.sh`. Internet nadal wymaga własnego hostingu i TLS/wss.

Godot: import `client/project.godot` w Godot 4.5.x Standard; eksport opisuje `docs/BUILD.md`. **Źródła Godota zmieniono, ale silnika nie uruchomiono, projektu nie importowano ani nie skompilowano.** Metadane Androida: 0.8.5, kod 12; brak podpisanego APK/AAB.

Zatrzymaj stary serwer i zrób kopię `data/world.sqlite3` przed przeniesieniem bazy do nowej paczki. Nie kopiuj starych folderów kodu na nową wersję. **Zaktualizuj serwer i klienta razem**, a w WWW odśwież stronę z pominięciem cache.

**Reset postaci nie jest potrzebny.** Poziomy, przedmioty, zadania i poprawne przypisania pozostają. Pasek jest powiększany i uzupełniany; nie następuje ponowne przeliczenie many już przeniesionej do zasad 0.8.4. Historia F startuje pusta wyłącznie wtedy, gdy nie było jej jeszcze w zapisie. Aktywne czasowe efekty, tak jak wcześniej, nie są przenoszone przez restart serwera.

## Weryfikacja

**334 testy Python, 22 testy JavaScript i 21 sprawdzeń interfejsu Chromium**. WWW sprawdzono z rzeczywistym serwerem przez kontrolowany most WebSocket, z testowym localStorage i kontrolowanymi postaciami. Nie jest to test natywnej sieci Chromium, fizycznego telefonu, Godota ani hostingu. Polecenia i ograniczenia: `docs/TEST_REPORT.md`; logi i dziesięć zrzutów: `docs/qa_0.8.5/`.

```sh
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs
python tools/browser_085_smoke.py
```

Ostatnie polecenie wymaga Playwright i Chromium; nie są zależnościami produkcyjnego serwera.

## Dokumentacja i zasady

`docs/CHANGELOG_0.8.5.md`, `docs/PROTOCOL.md`, `docs/RULES_0.8.md`, `docs/SPELLS_0.8.md`, `docs/TEST_REPORT.md`. Poprzednie raporty i zrzuty w `archive_*`/`qa_*` są historyczne. Manifest obejmuje każdy dostarczony plik poza samym manifestem.

Bractwo pozostaje adaptacją, nie pełnym symulatorem D&D: zachowuje wspólną manę, własne poziomy, rundy po 3 s i część skróconych czasów/zakresów. Ta wersja poprawia kształty, lecz nie dodaje wszystkich zaklęć SRD, pełnego 3D, przygotowania czarów, rytuałów ani upcastingu. Atrybucja: `LICENSE-SRD.txt`. Źródła odniesienia: oficjalny [słownik zasad](https://www.dndbeyond.com/sources/dnd/free-rules/rules-glossary) i [opisy czarów](https://www.dndbeyond.com/sources/dnd/free-rules/spell-descriptions).
