# Bractwo 0.8.4 — mana, pełny pasek, statusy i kręgi

Pełny projekt na bazie `BRACTWO_0.8.3_PIERWSZY_KRAG_OD_1_POZIOMU_FULL_SOURCE.zip`. Zawiera serwer Python, klient WWW i źródła klienta Godot. Nie zawiera APK, AAB ani EXE. Zachowano świat, przedmioty, zapisy, PvP, towarzysza, przemiany, autoatak oraz pościg bez powrotu do spawnu.

## Zmiany 0.8.4

**Kręgi czarodzieja i druida:** I od 1, II od 10, III od 20, IV od 30, V od 40, VI od 50, VII od 60, VIII od 70, IX od 80. Łowca bez przesunięcia: I–V na 20/40/60/80/100. Przemiany, dodatkowe ataki i skalowanie sztuczek zachowują dotychczasowe progi.

**Mana:** I–IX kosztują odpowiednio 20/30/50/60/70/90/100/110/130. Sztuczki kosztują 0. Nowy czarodziej i druid mają 40 many — dwa czary I kręgu przed odnowieniem, użyciem mikstury lub odpoczynkiem. Tarcza pobiera 20 dopiero przy uruchomieniu reakcji. Koszty zdolności klasowych nie zmieniły się.

Pula odpowiada ważonej sumie komórek czarów SRD dla poziomu bojowego `min(20,1+poziom_gry//5)`. Na poziomie 5 jest 60 MP (3×I), na 10: 140 MP (4×I + 2×II), na 20: 270 MP (4×I + 3×II + 2×III). Mana pozostaje **wspólna**, więc można zmieniać proporcje używanych kręgów; nie są to oddzielne ograniczenia liczby użyć każdego kręgu. Pełne liczby bez premii Skupienia, mikstur i odpoczynku.

**Brak pasywnej regeneracji many w walce PvE i PvP.** Poza walką i co najmniej 12 s od płatnego użycia wraca 1/240 puli na sekundę w terenie lub 1/20 w osadzie. Promocja zachowuje premię +25% do tego tempa. Mikstury i usługi odpoczynku nadal działają na dotychczasowych zasadach.

**Pasek:** zawiera wszystkie odblokowane czary i zdolności na stronach po osiem. Klawisze 1–8 dotyczą bieżącej strony; strzałki obok paska lub Page Up / Page Down zmieniają stronę. Czarodziej od początku ma dziewięć wpisów (dwie strony), druid osiem (jedna). Księga K pozwala zamieniać pozycje. Nowe czary trafiają na pasek automatycznie przy awansie; zablokowane i obce wpisy są usuwane, poprawne własne pozycje pozostają.

**Statusy:** WWW pokazuje pasek efektów postaci i zaznaczonego celu nad czarami, z nazwą, czasem i liczbą pozostałych rund. Kliknięcie / dotknięcie otwiera opis. Koncentracja ma nazwę utrzymywanego czaru; Tarcza w gotowości jest odróżniona od aktywnego +5 KP. Obejmują także osłabienia PvP, przemiany i tymczasowe HP. W menu pasek efektów jest ukryty, aby nie blokował przycisków. Źródło Godot zawiera odpowiadające etykiety przy górnym HUD i opisy po najechaniu.

**Długonogi:** I krąg, dotyk siebie lub członka drużyny, +10 stóp szybkości, bez koncentracji. W D&D trwa godzinę = 600 rund po 6 s. W Bractwie zachowano **600 rund po 3 s = 30 minut czasu rzeczywistego**. Atak, obrażenia ani rzucenie innego czaru nie kończą efektu. Ponowne rzucenie odnawia czas, nie kumuluje premii. Dodatek szybkości wynosi `10 × (32/5) / 3` jednostek mapy na sekundę, przed zwykłymi modyfikatorami terenu. Nie skraca odnowienia ataku. Wylogowanie/restart nadal nie przenosi aktywnych buffów, tak jak w poprzednim systemie; nie dodano upcastingu.

**Potwory:** niebossowie o bazowym HP do 18 wykrywają nowy cel z promienia mniejszego o 25%, a HP 19–34 o 12%. Silniejsze i bossowie bez zmiany. To wyłącznie początek agresji — nie zasięg ciosów/pocisków ani dystans trwającego pościgu. Atak spoza małego promienia nadal prowokuje. Po utracie celu potwór zostaje w miejscu; nie wraca do spawnu.

## Uruchomienie i aktualizacja

Windows: uruchom `start_windows.bat`, następnie otwórz `http://127.0.0.1:8080`. Pozostaw okno serwera otwarte. Wymagany Python 3.11+; pierwszy start instaluje zależności. `start_windows.bat lan` wystawia serwer w sieci lokalnej. Internet nadal wymaga własnego hostingu oraz TLS/wss.

Godot: importuj `client/project.godot` do Godot 4.5.x Standard. Instrukcje eksportu: `docs/BUILD.md`. **Źródła zmieniono, ale w tej aktualizacji nie uruchomiono silnika, nie importowano projektu i nie zbudowano klienta natywnego.** Metadane Androida: wersja 0.8.4, kod 11; brak podpisanego pliku APK/AAB.

Przed aktualizacją zatrzymaj stary serwer i zabezpiecz `data/world.sqlite3` (oraz pliki WAL/SHM, jeśli nadal istnieją). Do nowej paczki przenieś bazę dopiero po prawidłowym zamknięciu serwera. Nie kopiuj starego `server/`, `web/` ani `client/` na nowe źródła. Uruchom serwer i zaktualizowanego klienta razem; w WWW odśwież stronę z pominięciem pamięci podręcznej.

**Reset postaci nie jest wymagany.** Poziom, XP, złoto, ekwipunek i zadania pozostają. Jednorazowa migracja zachowuje procent wypełnienia starej puli many, a nie jej starą wartość liczbową. Zerowa mana zostaje zerowa. Normalizacja paska usuwa zablokowane wpisy i dodaje brakujące dostępne czary. Zamknięta wcześniej wskazówka sterowania pozostaje zamknięta na tym samym urządzeniu.

## Weryfikacja

Pełny zestaw: **294 testy Python**, w tym 47 nowych metod dotyczących tej aktualizacji; **14 testów Node**; **20 sprawdzeń interfejsu Chromium** z prawdziwym serwerem przez kontrolowany most WebSocket i testowy localStorage. To nie jest test fizycznego telefonu, natywnej sieci przeglądarki ani aplikacji Godot. Szczegóły i polecenia: `docs/TEST_REPORT.md`; wyniki i zrzuty: `docs/qa_0.8.4/`.

```sh
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs
python tools/browser_084_smoke.py
```

Ostatnie polecenie wymaga Playwright oraz Chromium; narzędzia QA nie są zależnością serwera produkcyjnego.

## Dokumentacja i SRD

Aktualne: `docs/RULES_0.8.md`, `docs/SPELLS_0.8.md`, `docs/BESTIARY_0.8.md`, `docs/PROTOCOL.md`, `docs/CHANGELOG_0.8.4.md`. Wyniki starszych wersji w `archive_*` i wcześniejszych `qa_*` są historyczne. Nowy manifest obejmuje każdy plik paczki poza samym manifestem.

Bractwo jest adaptacją, nie pełnym symulatorem podręcznika: wspólna mana, progi, szybkość rund, część innych czasów i zakresów efektów pozostają autorskie. Nie dodano wszystkich czarów SRD, przygotowania czarów, slotów per krąg, rytuałów ani rzucania z wyższego kręgu. Źródła zasad i wymagana atrybucja znajdują się w `LICENSE-SRD.txt` i dokumentacji.
