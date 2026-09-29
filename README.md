# Bractwo 0.8.18 UI_14 — Strzała, powrót do druida i mniejszy pełny ekran

Aktywny Łucznik ma na mobilnym pasku przycisk **Strzała**, własną ikonę i licznik
odnowienia. **▾ → Powrót do druida** jest na górze menu, zawsze poza przewijaną
listą. Działa także przy 0/2 użyć. Kielich i Smok pozwalają wrócić również głównym
przyciskiem. Serwer przekazuje aktualny stan przemiany w każdym pakiecie właściciela.

Mobilny HUD i oddalenie świata pozostają kompaktowe również po wejściu w pełny
ekran. Nie zmieniono układu desktopowego, zasad walki ani interpolacji ruchu.
Zachowano grupy przemian, księgę K, dodatkowe zestawy i przewijanie drugim palcem.

[Obsługa, wdrożenie, szczegóły i ograniczenia testów UI_14](docs/UI_14_DRUID_FULLSCREEN.md).
Przeszło 56 celowanych testów serwera, 63 testy JavaScript i 28 kontroli Chromium.
Pełny ekran sprawdzono w przeglądarce testowej z kontrolowaną zmianą viewportu,
nie na fizycznym Androidzie. To nie jest pełna regresja wszystkich historycznych testów.

Wgrywaj razem **server + web**. Reset postaci nie jest potrzebny. Na ekranie
logowania sprawdź **UI_14**. Paczka nie została wdrożona automatycznie na Railway.
Natywny interfejs Godota jest niezmieniony. Archiwalny opis UI_13 zachowano
w `docs/HOTBAR_0.8.18_UI_13.md`.

## Historia wcześniejszych zmian

Poniższe wpisy UI_10 i starsze zachowano jako historię. Aktualne zasady odpoczynku po UI_11 są w `docs/RELEASE_0.8.18.md`; dawne 15 sekund pełnej regeneracji i pasywna regeneracja nie opisują obecnej wersji.


Gra RPG online na komputer i telefon. Aktualizacja bazuje na 0.8.17 z mobilnym układem Mobile01.

Poprawka **UI_10**: kamera w mobilnym układzie jest nieco oddalona — postać i świat są o 15% mniejsze, dzięki czemu widać około 18% więcej mapy w każdej osi. Dotyczy pionu i poziomu. Przyciski, panele, joystick oraz widok desktopowy zachowują dotychczasową wielkość.

Poprawka **UI_09**: na telefonie można przewijać pasek umiejętności drugim palcem podczas chodzenia joystickiem. Przesunięcie paska nie rzuca czaru ani nie przerywa ruchu. Zwykłe dotknięcie czaru nadal działa; pasek można przesuwać również od nieaktywnego slotu.

Poprawka **UI_08**: Atlas otwiera się po kliknięciu minimapy, przyciskiem **⌖** u góry lub klawiszem **N**. Nazwane miejsca, łowiska i przejścia mają wspólne oznaczenia odkrycia oraz jednorazowe PD zależne od poziomu okolicy, przeciwników i odległości od najbliższego miasta. Krokodyl bagienny otrzymał własną animowaną grafikę. Usunięto nieaktualną podpowiedź „kliknij cel: autoatak”. Naprawiono też przycisk wyboru atutu: po zakończeniu walki odblokowuje się nawet wtedy, gdy lista statystyk na telefonie nadal ma fokus, bez ponownego logowania i utraty wyboru.

Poprawka **UI_07**: w **Dzienniku (J)** przy zadaniu jest przycisk **Śledź zadanie**. Wybór zamyka dziennik i zastępuje cel z atlasu. Wskazówka prowadzi do bieżącego etapu, a po wykonaniu zadania do zleceniodawcy. Przycisk **Śledzone · wyłącz** kończy śledzenie. Wybór jest zapamiętany na tym urządzeniu osobno dla każdej postaci.

Poprawka **UI_06**: przyciski **Załóż**, **Zdejmij** i pozostałe akcje przedmiotu są pod jego nazwą, przed statystykami i opisem. Wybór przedmiotu przewija panel do tych przycisków. Nie trzeba przewijać całego opisu, aby zmienić wyposażenie.

Poprawka **UI_05**: kliknięcie **Odpoczynek** lub klawisz **R** rozpoczyna pełną regenerację, bez okna wyboru. Trwa ona **15 sekund** i odnawia całe HP oraz manę. Po ukończeniu obowiązuje **60 sekund cooldownu**, widocznego na przycisku. Postęp jest nad własną postacią, która medytuje w niebieskim kręgu z unoszącymi się kroplami many. Ponowne kliknięcie lub R przerywa odpoczynek bez nagrody i bez cooldownu. Zachowano obsługę joysticka i czaru dotykanego drugim palcem z UI_03.

Mikstury many usunięto ze sklepu, łupów i wyposażenia. Pozostaje jeden slot mikstury zdrowia pod **Q**. Przy odczycie starszej postaci stare mikstury many są usuwane z plecaka i depozytu; pozostałe przedmioty są zachowane.

Zachowano układ **UI_02**: odpoczynek nad Rozmawiaj na telefonie i nad K Czary na komputerze. Skrót I nadal otwiera ekwipunek; jego dodatkowa ikona w górnym menu jest ukryta.

- **Pełny odpoczynek:** 15 sekund, całe HP i mana, także w terenie. Cooldown po ukończeniu: 60 sekund, zachowany po ponownym zalogowaniu.
- Po walce z potworami odpoczynek jest dostępny po **3 sekundach**. Blokada po PvP nadal trwa 20 sekund.
- **Pełny ekran:** przycisk na stronie logowania i podczas gry, także bezpośrednio na telefonie.
- **Zainstaluj grę:** aplikacja PWA uruchamiana z ikony. Rozgrywka wymaga internetu.
- **Blokada paneli:** domyślnie włączona, z przełącznikiem obok przywracania układu. Joystick jest wyśrodkowany w wolnej przestrzeni po lewej.

[Dokładny opis zmian, instalacja i weryfikacja](docs/RELEASE_0.8.18.md)

## Uruchomienie lokalne

Uruchom `start_windows.bat` w Windows lub `./start_unix.sh` w Linux/macOS. Otwórz `http://127.0.0.1:8080`. Nie uruchamiaj gry przez bezpośrednie otwarcie pliku HTML.

## Aktualizacja na GitHub / Railway

Rozpakuj paczkę **RAILWAY_GITHUB_READY** i skopiuj jej zawartość do katalogu repozytorium: `Dockerfile`, `run.py`, `server` i `web` muszą być bezpośrednio w jego głównym katalogu. Zachowaj `.git`, bazę graczy i wolumen danych. Do GitHub wysyłaj rozpakowane pliki, nie sam ZIP. W GitHub Desktop zatwierdź zmiany i użyj **Push origin**.

Jeżeli Railway śledzi tę gałąź, uruchomi wdrożenie zgodnie z konfiguracją projektu. Reset postaci nie jest potrzebny. W publicznym internecie instalowanie PWA wymaga HTTPS.

Paczka **FULL_SOURCE** dodatkowo zawiera źródła Godota, testy, narzędzia i historyczną dokumentację. Nowe przyciski oraz instalacja dotyczą klienta przeglądarkowego. Bieżące wyniki testów są w `docs/qa_0.8.18/`.
