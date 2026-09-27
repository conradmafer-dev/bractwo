# Bractwo 0.8.18 — odpoczynek, pełny ekran i aplikacja

Baza: 0.8.17 z poprawką Mobile01. Zachowano układ telefonu, zasady różdżki i dotychczasowe postacie.

**UI_05 — pełna regeneracja i cooldown:** dotychczasowy krótki odpoczynek trwa teraz 15 sekund i przywraca całe HP oraz manę. Po udanym ukończeniu zaczyna się wspólny cooldown 60 sekund, zapisany przy postaci i widoczny na przycisku. Ponowne logowanie ani starsze polecenie długiego odpoczynku nie omijają blokady. Przerwanie nie przyznaje regeneracji ani nie uruchamia cooldownu. Nadal wystarcza jedno kliknięcie, a pasek i animacja pozostają nad postacią. Wpisy UI_04–UI_02 poniżej są historią wcześniejszych poprawek.

**Mikstury i skróty w UI_05:** usunięto mikstury many ze sklepu, łupów, nagród i wyposażenia. Pozostaje jeden slot mikstury zdrowia **Q**; klawisz **R** rozpoczyna lub przerywa odpoczynek. Starsze mikstury many są usuwane przy odczycie plecaka i depozytu, bez zmiany pozostałych przedmiotów. Poprawne przypisanie mikstury zdrowia do Q zostaje zachowane; jeśli Q wskazywało dawną miksturę many, wraca do mikstury zdrowia. Stare polecenia przypisania lub użycia mikstury pod R są odrzucane.

**UI_04 — odpoczynek jednym kliknięciem:** przycisk Odpoczynek natychmiast wysyła polecenie krótkiego odpoczynku. Usunięto okno wyboru krótkiego i długiego odpoczynku. Dotyczy to również przycisku u kupca. Ponowne kliknięcie przerywa aktywny odpoczynek. Serwer nadal sprawdza blokadę po walce i informuje o pozostałym czasie. Animacja i pasek nad postacią są bez zmian. Poniższe wpisy UI_03 i UI_02 opisują wcześniejsze poprawki.

**UI_03 — joystick, czary i medytacja:** czar z paska oraz najczęściej używany czar reagują na niezależne dotknięcie drugim palcem, gdy pierwszy obsługuje joystick. Przesunięcie paska lub anulowanie gestu nie rzuca czaru; dodatkowe zdarzenie kliknięcia nie powtarza akcji. Po wyborze rodzaju odpoczynku okno zamyka się od razu. Postęp jest nad własną postacią, z animacją medytacji, niebieskim kręgiem i unoszącymi się kroplami many. Efekt kończy się zgodnie ze stanem serwera. Zachowano układ UI_02 i dotychczasowe czasy oraz zasady regeneracji. Sprawdzenie tej poprawki ograniczono do celowanych testów Node i składni; raport: `docs/qa_0.8.18/ui_03_results.json`.

**UI_02 — korekta rozmieszczenia przycisków:** odpoczynek przeniesiono nad Rozmawiaj na telefonie, na wysokość Czary i ulubionego czaru, oraz nad K Czary na komputerze. Na wąskim ekranie pionowym przycisk przechodzi wyżej, gdy ten sam rząd jest zajęty; nie zasłania istniejących przycisków. Ikona ekwipunku z górnego menu jest ukryta, a skrót I działa jak wcześniej. Reszta gry jest bez zmian. Zgodnie z prośbą użytkownika tę korektę sprawdzono tylko pod kątem składni JavaScript i zachowania powiązań przycisków; poniższe rozbudowane wyniki testów dotyczą poprzedniego wydania 0.8.18.

## Odpoczynek

Przycisk z księżycem **Odpoczynek** znajduje się nad K Czary na komputerze i nad Rozmawiaj na telefonie. Ta sama opcja jest dostępna w oknie kupca. Samo rozpoczęcie rozmowy z kupcem nie uruchamia już leczenia.

| Rodzaj | Czas | Efekt po ukończeniu | Miejsce |
| --- | --- | --- | --- |
| Pełny | 15 sekund | Całe HP i mana; następnie 60 sekund cooldownu | Także w terenie |

- Jedno kliknięcie **Odpoczynek** lub naciśnięcie **R** rozpoczyna pełny odpoczynek bez wyboru rodzaju i bez dodatkowego panelu.
- Cooldown trwa **60 sekund od ukończenia**. Licznik jest widoczny na przycisku, który w tym czasie nie rozpoczyna kolejnego odpoczynku. Serwer zapisuje blokadę przy postaci, więc obowiązuje ona także po ponownym zalogowaniu i restarcie serwera; upływa również poza grą.
- Po starciu z potworem można zacząć po **3 sekundach**. Przy wcześniejszym kliknięciu komunikat pokazuje pozostały czas blokady.
- Walka z graczem nadal wymaga odczekania pełnej dotychczasowej blokady **20 sekund**.
- Odpoczynek jest bezpłatny. Ruch, walka i rozpoczęcie innej wykonywanej czynności przerywają go. Można też ponownie nacisnąć przycisk **Odpoczynek** lub **R**, aby przerwać regenerację.
- Pasek i pozostały czas widać nad własną postacią. Niebieski krąg i krople many towarzyszą medytacji; przemieniony druid zachowuje formę zwierzęcia i otrzymuje ten sam efekt regeneracji.
- Całe zdrowie i mana są przyznawane dopiero po ukończeniu. Przerwany odpoczynek nie przyznaje nagrody i nie uruchamia cooldownu.
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

Wyniki znajdują się w `docs/qa_0.8.18/`. Raport `ui_05_results.json` dotyczy bieżącej poprawki. Poniższe szersze kontrole przeprowadzono dla wcześniejszego wydania 0.8.18; nie powtarzano ich dla UI_03–UI_05.

Przeszło wtedy 296 unikalnych testów serwera, 56 testów JavaScript oraz 4 testy tras HTTP i plików aplikacji. Dwa scenariusze WebSocket przekroczyły limit czasu przy równoległym obciążeniu komputera; powtórzone osobno przeszły bez zmiany testów lub ich limitów. Raporty zachowują oba wyniki.

Testy obejmują logikę odpoczynku i przerwań, zachowanie many oraz PvP, interfejs odpoczynku, blokadę paneli, API pełnego ekranu, instalację PWA i zakres pamięci service workera. Raport `browser_results.json` osobno opisuje zakres kontroli w przeglądarce i jej ograniczenia. Emulacja przeglądarki nie zastępuje testu na fizycznym telefonie.

Chrome potwierdził logowanie, dostępność panelu odpoczynku w rozmiarach 734 × 260 i 390 × 844 oraz rzeczywiste wejście i wyjście z pełnego ekranu przed logowaniem i podczas gry. Dalszy test rozgrywki zatrzymano, gdy mostek testowy zaczął dostarczać stany serwera z opóźnieniem. Nie jest to zaliczony pełny test rozgrywki w przeglądarce. Instalację PWA i service worker sprawdzono testami jednostkowymi i HTTP; nie przeprowadzono instalacji na fizycznym telefonie.

Osobny test przeglądarkowy rzeczywistego DOM i CSS zaliczył 4 kontrole: środek joysticka z widocznym zadaniem, dotykowe przeciąganie po odblokowaniu, ponowne zablokowanie i reset oraz przeciąganie myszą na komputerze. Podczas tej kontroli poprawiono uchwyt zasłaniający zamknięcie menu; ponowny przebieg sprawdził końcową wersję CSS. Test działał bez serwera i nie zastępuje testu całej rozgrywki.

Źródła możliwości przeglądarek: [MDN: instalowanie PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable), [MDN: Fullscreen API](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API), [Apple: aplikacja ze strony w Safari](https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios).
