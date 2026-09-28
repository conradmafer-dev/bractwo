# Bractwo 0.8.18 UI_12 — HP zgodne z progami D&D i przyrost na każdy awans

Baza: 0.8.17 z poprawką Mobile01. Zachowano układ telefonu, zasady różdżki i dotychczasowe postacie.

**UI_12 — skalowanie HP:** przyrost z jednego poziomu D&D rozdzielany jest między pojedyncze poziomy gry, z zaokrągleniem łącznej puli. Na poziomach 1, 5, 10, 15…95 całkowite HP odpowiada oficjalnemu wariantowi stałego przyrostu danej klasy i Kondycji. Pierwszy odcinek 1→5 ma cztery awanse; kolejne odcinki mają pięć. Twardy zachowuje +2 HP za efektywny poziom D&D. Bazowy wzrost kończy się na poziomie 95, odpowiadającym 20. poziomowi D&D.

Usunięto autorski bonus Witalności oraz jego zakup w obu panelach. Starsze punkty są zwracane do puli mistrzostwa przy wczytaniu. Jednorazowa migracja zachowuje procent aktualnego zdrowia i stan śmierci; kolejne logowania nie przeliczają zdrowia ponownie. Historyczne komunikaty awansu zachowują dawny wzór, nowe pokazują rzeczywisty przyrost bieżącej wersji. Szczegóły: `docs/HP_0.8.18_UI_12.md`; celowana weryfikacja: `docs/qa_0.8.18/ui_12_results.json`.

**UI_11 — pięć atutów i cztery kręgi druida:** Twardy, Zacięty atak, Rozwój cech, Mistrz ciężkiego pancerza i Mistrz średniego pancerza. Kręgi Ziemi, Księżyca, Morza i Gwiazd odblokowują się na 10. poziomie gry. Bonusy obejmują działające czary, stany, zasoby, przemiany, pływanie, lot i efekty obszarowe; opis mechanik i przeliczeń znajduje się w `docs/DRUID_CIRCLES_0.8.18.md`.

Krótki odpoczynek trwa **10 sekund**, długi **30 sekund**. Odpoczynki odnawiają przypisane im zasoby klasowe zamiast dawnych liczników czasu. Liczby użyć są zapisywane z postacią. Wyłączono pasywną regenerację HP i many; krótki odpoczynek leczy z ograniczonej puli kości zdrowia, a długi przywraca pełne zasoby. Poniższe wpisy UI_10–UI_02 stanowią historię wcześniejszych zmian; bieżące zasady odpoczynku opisano osobno poniżej. Raport bieżącego zakresu: `docs/qa_0.8.18/ui_11_results.json`.

**UI_10 — szerszy widok na telefonie:** skala świata w mobilnym układzie wynosi 85% dotychczasowej skali, czyli obiekty są o 15% mniejsze, a widoczny odcinek mapy w każdej osi jest około 18% większy. Kamera korzysta z tego samego warunku mobilnego co HUD, również po obróceniu telefonu. Rozmiary przycisków, paneli i joysticka pozostają bez zmian; dotychczasowe przeliczanie dotyku oraz prostokąta minimapy uwzględnia skalę kamery. Widok desktopowy zachowuje swoją skalę. To drobna zmiana prezentacji: sprawdzenie ograniczono do składni JavaScript i przeglądu zależności, bez nowych testów ani pełnej regresji. Raport: `docs/qa_0.8.18/ui_10_results.json`.

**UI_09 — ruch i przewijanie paska jednocześnie:** mobilny pasek umiejętności przewija się przez osobny wskaźnik dotyku, niezależnie od palca na joysticku. Przejęcie gestu następuje dopiero po przekroczeniu 12 pikseli poziomego ruchu, więc dotknięcie nadal rzuca czar. Przesuwanie, anulowanie gestu i dodatkowy klik przeglądarki po przesunięciu nie rzucają czaru. Można zacząć przesunięcie również na nieaktywnym slocie lub przerwie między slotami. Zachowano kliknięcia myszy i klawiatury oraz układ desktopowy. Usunięto natywne przewijanie dotykiem i przyciąganie do slotów w mobilnym pasku, ponieważ kolidowały z niezależną obsługą drugiego palca. Weryfikacja jest ograniczona do celowanych testów gestów oraz składni; raport: `docs/qa_0.8.18/ui_09_results.json`.

**UI_08 — odkrycia, Atlas i wybór atutu:**

- Nazwane łowiska oraz wejścia i przejścia są powiązane z tym samym katalogiem odkryć co młyn. Zachowano historyczne identyfikatory, a pobliskie schody współdzielą odkrycie tylko wtedy, gdy leżą w jego promieniu na tym samym piętrze. Anonimowe dekoracje pozostają dekoracjami.
- Wszystkie wpisy katalogu dają dodatnie PD przy pierwszym odkryciu. Nagroda uwzględnia poziom biomu/miejsca, najsilniejszego pobliskiego przeciwnika na tym samym piętrze (z premią za bossa) i odległość od najbliższego miasta. Uwzględniono też pierwotne potwory wokół Przystani; dla starszych przeciwników bez poziomu próg trudności wynika z HP. Nagrody za złoto i wcześniej zapisane odkrycia są zachowane; nie ma ponownego wypłacania ani wyrównań za już odkryte miejsca.
- Znaczki ◇/✓ działają także na nazwanych łowiskach, miejscach interakcji i schodach. Dziennik i listy Atlasu pokazują stan odkrycia, a dla nieodkrytego miejsca również PD. Nowe odkrycie wyświetla komunikat z nagrodą.
- Kliknięcie minimapy, górny przycisk ⌖ oraz N otwierają bezpośrednio Atlas. M nadal przełącza widoczność minimapy. Skrót N nie działa podczas pisania w polach formularzy i czacie.
- Krokodyl bagienny korzysta z osobnego czteroklatkowego sprite'a z płaskim pyskiem, krótkimi nogami, łuskami i długim ogonem. Nie zmienia to jego statystyk.
- Usunięto dolną instrukcję sugerującą, że zaznaczanie zawsze uruchamia autoatak, i doprecyzowano pomoc.
- Naprawiono wybór atutu na telefonie: fokus na liście cech nie zatrzymuje już odświeżania dostępności przycisku po zakończeniu walki. Wybór i fokus pozostają zachowane; wysyłanie korzysta z aktualnego stanu gracza. Blokady walki, śmierci, przemiany i braku punktu nadal obowiązują.

Weryfikacja UI_08 jest celowana: testy odkryć i formularza atutów, jednorazowa kontrola katalogu świata, składnia oraz render samej grafiki krokodyla. Bez sesji przeglądarki, telefonu ani pełnej regresji. Raport: `docs/qa_0.8.18/ui_08_results.json`.

**UI_07 — śledzenie z dziennika:** pod tytułem dostępnego, aktywnego lub gotowego do oddania zadania znajduje się przycisk Śledź zadanie. Wybór zastępuje ręczny cel atlasu i zamyka dziennik, aby od razu było widać kierunek. Śledzone zadanie pozostaje wybrane przy zmianach pozostałych zadań; cel jest wyliczany z bieżącego postępu. Po wykonaniu wszystkich etapów prowadzi do zleceniodawcy, a po odebraniu nagrody śledzenie wybranego zadania kończy się. Można je również wyłączyć tym samym przyciskiem. Kliknięcie panelu śledzonego zadania otwiera dziennik przy tym zadaniu. Wybór i wyłączenie są zapamiętywane na urządzeniu dla danej postaci. Bez zapisanego wyboru zachowano dotychczasową automatyczną podpowiedź. Dla celu na innym piętrze pozostaje wskazówka o szukaniu schodów; gra nie wyznacza nowej trasy przez podziemia. Wpisy UI_06–UI_02 poniżej opisują wcześniejsze poprawki.

**UI_06 — wygodniejsze zakładanie przedmiotów:** przyciski Załóż, Zdejmij oraz pozostałe akcje przeniesiono pod nazwę przedmiotu, przed jego statystyki i opis. Wybór przedmiotu w plecaku lub założonym wyposażeniu przewija panel do jego przycisków akcji; zwykłe odświeżenie danych nie zmienia pozycji przewijania. Dotyczy to wspólnego widoku szczegółów na telefonie i komputerze. Zasady zakładania oraz ograniczenia przedmiotów pozostają bez zmian. Wpisy UI_05–UI_02 poniżej opisują wcześniejsze poprawki.

**UI_05 — pełna regeneracja i cooldown:** dotychczasowy krótki odpoczynek trwa teraz 15 sekund i przywraca całe HP oraz manę. Po udanym ukończeniu zaczyna się wspólny cooldown 60 sekund, zapisany przy postaci i widoczny na przycisku. Ponowne logowanie ani starsze polecenie długiego odpoczynku nie omijają blokady. Przerwanie nie przyznaje regeneracji ani nie uruchamia cooldownu. Nadal wystarcza jedno kliknięcie, a pasek i animacja pozostają nad postacią. Wpisy UI_04–UI_02 poniżej są historią wcześniejszych poprawek.

**Mikstury i skróty w UI_05:** usunięto mikstury many ze sklepu, łupów, nagród i wyposażenia. Pozostaje jeden slot mikstury zdrowia **Q**; klawisz **R** rozpoczyna lub przerywa odpoczynek. Starsze mikstury many są usuwane przy odczycie plecaka i depozytu, bez zmiany pozostałych przedmiotów. Poprawne przypisanie mikstury zdrowia do Q zostaje zachowane; jeśli Q wskazywało dawną miksturę many, wraca do mikstury zdrowia. Stare polecenia przypisania lub użycia mikstury pod R są odrzucane.

**UI_04 — odpoczynek jednym kliknięciem:** przycisk Odpoczynek natychmiast wysyła polecenie krótkiego odpoczynku. Usunięto okno wyboru krótkiego i długiego odpoczynku. Dotyczy to również przycisku u kupca. Ponowne kliknięcie przerywa aktywny odpoczynek. Serwer nadal sprawdza blokadę po walce i informuje o pozostałym czasie. Animacja i pasek nad postacią są bez zmian. Poniższe wpisy UI_03 i UI_02 opisują wcześniejsze poprawki.

**UI_03 — joystick, czary i medytacja:** czar z paska oraz najczęściej używany czar reagują na niezależne dotknięcie drugim palcem, gdy pierwszy obsługuje joystick. Przesunięcie paska lub anulowanie gestu nie rzuca czaru; dodatkowe zdarzenie kliknięcia nie powtarza akcji. Po wyborze rodzaju odpoczynku okno zamyka się od razu. Postęp jest nad własną postacią, z animacją medytacji, niebieskim kręgiem i unoszącymi się kroplami many. Efekt kończy się zgodnie ze stanem serwera. Zachowano układ UI_02 i dotychczasowe czasy oraz zasady regeneracji. Sprawdzenie tej poprawki ograniczono do celowanych testów Node i składni; raport: `docs/qa_0.8.18/ui_03_results.json`.

**UI_02 — korekta rozmieszczenia przycisków:** odpoczynek przeniesiono nad Rozmawiaj na telefonie, na wysokość Czary i ulubionego czaru, oraz nad K Czary na komputerze. Na wąskim ekranie pionowym przycisk przechodzi wyżej, gdy ten sam rząd jest zajęty; nie zasłania istniejących przycisków. Ikona ekwipunku z górnego menu jest ukryta, a skrót I działa jak wcześniej. Reszta gry jest bez zmian. Zgodnie z prośbą użytkownika tę korektę sprawdzono tylko pod kątem składni JavaScript i zachowania powiązań przycisków; poniższe rozbudowane wyniki testów dotyczą poprzedniego wydania 0.8.18.

## Odpoczynek

Przycisk z księżycem **Odpoczynek** znajduje się nad K Czary na komputerze i nad Rozmawiaj na telefonie. Ta sama opcja jest dostępna w oknie kupca. Samo rozpoczęcie rozmowy z kupcem nie uruchamia już leczenia.

| Rodzaj | Czas | Efekt po ukończeniu | Miejsce |
| --- | --- | --- | --- |
| Krótki | 10 sekund | Leczenie z kości zdrowia i zasoby odnawiane krótkim odpoczynkiem | Także w terenie |
| Długi | 30 sekund | Całe HP, mana, kości zdrowia i zasoby odnawiane długim odpoczynkiem | Także w terenie |

- Przycisk **Odpoczynek** pozwala wybrać krótki albo długi odpoczynek i zamyka wybór zaraz po rozpoczęciu. **R** rozpoczyna krótki, **Shift+R** długi; podczas odpoczynku R przerywa go.
- Oddzielne blokady po ukończeniu trwają **15 sekund dla krótkiego** i **60 sekund dla długiego**. Serwer zapisuje je przy postaci; obowiązują również po ponownym zalogowaniu i upływają poza grą.
- Po starciu z potworem można zacząć po **3 sekundach**. Przy wcześniejszym kliknięciu komunikat pokazuje pozostały czas blokady.
- Walka z graczem nadal wymaga odczekania pełnej dotychczasowej blokady **20 sekund**.
- Odpoczynek jest bezpłatny. Ruch, walka i rozpoczęcie innej wykonywanej czynności przerywają go. Można też ponownie nacisnąć przycisk **Odpoczynek** lub **R**, aby przerwać regenerację.
- Pasek i pozostały czas widać nad własną postacią. Niebieski krąg i krople many towarzyszą medytacji. Długi odpoczynek kończy przemiany, koncentrację i aktywne efekty.
- Regeneracja i zwrot użyć następują dopiero po ukończeniu. Przerwany odpoczynek nie zużywa kości zdrowia, nie odnawia zasobów i nie uruchamia cooldownu.
- Odpoczynek odnawia konkretne zasoby zgodnie z ich opisem: m.in. Dziki kształt, Drugi oddech, Zryw akcji, Odzyskanie mocy, omeny i zdolności kręgów. Zwykłe tempo akcji w walce pozostaje bez zmian. Nie ma pasywnego odnawiania HP i many.

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

Wyniki znajdują się w `docs/qa_0.8.18/`. Raport `ui_12_results.json` dotyczy bieżącej zmiany HP. Raport `ui_11_results.json` zachowuje wyniki wcześniejszych sprawdzeń kręgów i odpoczynków. Poniższe szersze kontrole przeprowadzono dla wcześniejszego wydania 0.8.18; nie powtarzano ich w UI_12.

Przeszło wtedy 296 unikalnych testów serwera, 56 testów JavaScript oraz 4 testy tras HTTP i plików aplikacji. Dwa scenariusze WebSocket przekroczyły limit czasu przy równoległym obciążeniu komputera; powtórzone osobno przeszły bez zmiany testów lub ich limitów. Raporty zachowują oba wyniki.

Testy obejmują logikę odpoczynku i przerwań, zachowanie many oraz PvP, interfejs odpoczynku, blokadę paneli, API pełnego ekranu, instalację PWA i zakres pamięci service workera. Raport `browser_results.json` osobno opisuje zakres kontroli w przeglądarce i jej ograniczenia. Emulacja przeglądarki nie zastępuje testu na fizycznym telefonie.

Chrome potwierdził logowanie, dostępność panelu odpoczynku w rozmiarach 734 × 260 i 390 × 844 oraz rzeczywiste wejście i wyjście z pełnego ekranu przed logowaniem i podczas gry. Dalszy test rozgrywki zatrzymano, gdy mostek testowy zaczął dostarczać stany serwera z opóźnieniem. Nie jest to zaliczony pełny test rozgrywki w przeglądarce. Instalację PWA i service worker sprawdzono testami jednostkowymi i HTTP; nie przeprowadzono instalacji na fizycznym telefonie.

Osobny test przeglądarkowy rzeczywistego DOM i CSS zaliczył 4 kontrole: środek joysticka z widocznym zadaniem, dotykowe przeciąganie po odblokowaniu, ponowne zablokowanie i reset oraz przeciąganie myszą na komputerze. Podczas tej kontroli poprawiono uchwyt zasłaniający zamknięcie menu; ponowny przebieg sprawdził końcową wersję CSS. Test działał bez serwera i nie zastępuje testu całej rozgrywki.

Źródła możliwości przeglądarek: [MDN: instalowanie PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable), [MDN: Fullscreen API](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API), [Apple: aplikacja ze strony w Safari](https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios).
