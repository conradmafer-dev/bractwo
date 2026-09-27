# Bractwo 0.8.18 — odpoczynek, pełny ekran i aplikacja

Gra RPG online na komputer i telefon. Aktualizacja bazuje na 0.8.17 z mobilnym układem Mobile01.

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
