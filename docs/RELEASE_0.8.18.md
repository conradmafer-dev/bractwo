# Bractwo 0.8.18 — odpoczynek, pełny ekran i aplikacja

Baza: 0.8.17 z poprawką Mobile01. Zachowano układ telefonu, zasady różdżki i dotychczasowe postacie.

## Odpoczynek

Przycisk z księżycem **Odpoczynek** znajduje się w górnym menu gry. Na telefonie otwórz najpierw menu ☰. Ta sama opcja jest dostępna w oknie kupca. Samo rozpoczęcie rozmowy z kupcem nie uruchamia już leczenia.

| Rodzaj | Czas | Efekt po ukończeniu | Miejsce |
| --- | --- | --- | --- |
| Krótki | 6 sekund | +25% maksymalnego zdrowia i +25% maksymalnej many, do ich limitów | Także w terenie |
| Długi | 15 sekund | Pełne zdrowie i mana | Bezpieczna osada |

- Po starciu z potworem można zacząć po **3 sekundach**. Panel pokazuje pozostały czas blokady.
- Walka z graczem nadal wymaga odczekania pełnej dotychczasowej blokady **20 sekund**.
- Odpoczynek jest bezpłatny. Ruch, walka i rozpoczęcie innej wykonywanej czynności przerywają go. Jest też przycisk **Przerwij odpoczynek**.
- Nagroda jest przyznawana dopiero po ukończeniu. Zamknięcie panelu nie przerywa odpoczynku; ruch po powrocie do gry już tak.
- Odpoczynek nie zeruje odnowień czarów i zdolności. Pasywna regeneracja many, ochrona PvP, handel i zasady bezpiecznego wylogowania zachowują własne warunki.

## Blokada paneli i joystick

Obok przycisku przywracania układu **↺** znajduje się przełącznik blokady przesuwania. Domyślnie blokada jest włączona. Po jej wyłączeniu można przesuwać panele za uchwyty na komputerze i telefonie; ponowne włączenie blokady zabezpiecza ich aktualne położenie. Ustawienie jest zapamiętywane razem z profilem układu, osobno dla telefonu i komputera oraz orientacji ekranu.

Domyślny joystick w widoku poziomym znajduje się w środku wolnego obszaru po lewej: poziomo między krawędzią ekranu a paskiem czarów, pionowo między dolną krawędzią paneli zadań a dołem ekranu. Gdy zadanie jest ukryte, górną granicą jest ostatni widoczny panel po lewej. W pionie joystick jest wyśrodkowany w dolnym lewym obszarze pod paskiem czarów. Ręczne przesunięcie po odblokowaniu ma pierwszeństwo przed automatycznym centrowaniem.

## Pełny ekran

Przycisk **⛶ Pełny ekran** działa na stronie logowania i podczas gry. Na komputerze jest w górnym menu, a na telefonie pod przyciskiem czatu, bez otwierania menu. Ponowne naciśnięcie opuszcza pełny ekran. Przeglądarka może również umożliwiać wyjście klawiszem Escape.

Jeśli przeglądarka nie obsługuje tej funkcji albo odmówi, gra wyświetli instrukcję. Nie przełącza ekranu automatycznie ani nie wymusza orientacji urządzenia.

## Instalowanie gry ze strony

**Zainstaluj grę** jest dostępne na stronie logowania i w menu gry. Obsługująca tę funkcję przeglądarka pokaże własne okno instalacji. Przy braku tej możliwości pojawi się instrukcja odpowiednia dla urządzenia.

- Chrome/Edge: wybierz **Zainstaluj grę** lub opcję instalacji w menu przeglądarki.
- iPhone/iPad: w Safari wybierz **Udostępnij → Dodaj do ekranu początkowego**. Jeśli dostępna jest opcja otwierania jako aplikacji internetowej, pozostaw ją włączoną.
- Następne uruchomienia odbywają się z ikony **Bractwo**, bez wpisywania adresu strony.

To aplikacja internetowa PWA, nie instalator APK/EXE. Publiczna strona musi działać przez HTTPS; localhost nadaje się do testów. Rozgrywka wieloosobowa nadal wymaga internetu i dostępnego serwera.

Przy braku połączenia aplikacja pokazuje osobną stronę z możliwością ponowienia. Service worker zapisuje tylko tę stronę i ikony. Nie przechowuje gry offline, danych kont, odpowiedzi API ani starych plików kodu gry.

## Aktualizacja na Railway / GitHub

1. Rozpakuj paczkę **RAILWAY_GITHUB_READY**. `Dockerfile`, `run.py`, `server` i `web` muszą znajdować się bezpośrednio w głównym katalogu repozytorium.
2. Podmień pliki projektu, zachowując katalog `.git` oraz dotychczasowy wolumen i bazę graczy. Do repozytorium trafiają rozpakowane pliki, nie sam ZIP.
3. Zatwierdź i wyślij zmiany z GitHub Desktop. Jeśli Railway śledzi tę gałąź, wdroży nową wersję zgodnie z konfiguracją projektu.
4. Po wdrożeniu odśwież stronę. Przycisk instalacji może wymagać ponownego wejścia na stronę, zanim przeglądarka udostępni własne okno instalacji.

Reset postaci nie jest potrzebny. Ta paczka nie zawiera bazy graczy. Przygotowanie paczki i lokalne testy nie oznaczają wdrożenia na działający serwer.

Pełna paczka źródłowa dodatkowo zawiera testy, narzędzia, historyczną dokumentację i źródła Godota. Nowy panel odpoczynku, pełny ekran i instalacja dotyczą klienta przeglądarkowego. Silnik Godot nie był uruchamiany ani przebudowywany.

## Weryfikacja

Wyniki tej aktualizacji znajdują się w `docs/qa_0.8.18/`. Przeszło 296 unikalnych testów serwera, 56 testów JavaScript oraz 4 testy tras HTTP i plików aplikacji. Dwa scenariusze WebSocket przekroczyły limit czasu przy równoległym obciążeniu komputera; powtórzone osobno przeszły bez zmiany testów lub ich limitów. Raporty zachowują oba wyniki.

Testy obejmują logikę odpoczynku i przerwań, zachowanie many oraz PvP, interfejs odpoczynku, blokadę paneli, API pełnego ekranu, instalację PWA i zakres pamięci service workera. Raport `browser_results.json` osobno opisuje zakres kontroli w przeglądarce i jej ograniczenia. Emulacja przeglądarki nie zastępuje testu na fizycznym telefonie.

Chrome potwierdził logowanie, dostępność panelu odpoczynku w rozmiarach 734 × 260 i 390 × 844 oraz rzeczywiste wejście i wyjście z pełnego ekranu przed logowaniem i podczas gry. Dalszy test rozgrywki zatrzymano, gdy mostek testowy zaczął dostarczać stany serwera z opóźnieniem. Nie jest to zaliczony pełny test rozgrywki w przeglądarce. Instalację PWA i service worker sprawdzono testami jednostkowymi i HTTP; nie przeprowadzono instalacji na fizycznym telefonie.

Osobny test przeglądarkowy rzeczywistego DOM i CSS zaliczył 4 kontrole: środek joysticka z widocznym zadaniem, dotykowe przeciąganie po odblokowaniu, ponowne zablokowanie i reset oraz przeciąganie myszą na komputerze. Podczas tej kontroli poprawiono uchwyt zasłaniający zamknięcie menu; ponowny przebieg sprawdził końcową wersję CSS. Test działał bez serwera i nie zastępuje testu całej rozgrywki.

Źródła możliwości przeglądarek: [MDN: instalowanie PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable), [MDN: Fullscreen API](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API), [Apple: aplikacja ze strony w Safari](https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios).
