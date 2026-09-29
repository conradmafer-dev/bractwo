# Bractwo 0.8.18 UI_13 — pogrupowany pasek druida

Baza: dostarczone paczki UI_12. Nowy interfejs dotyczy wersji przeglądarkowej na komputerze i telefonie. Nie przebudowano natywnego klienta Godota.

## Pasek, który nie zużywa slotu na każdy wariant

Dziki kształt zajmuje jeden slot. Przycisk otwiera wybór dostępnych zwierząt; podczas przemiany główne pole pozwala wrócić do druida. Zdolność stratowania, gdy jest dostępna dla danej formy, znajduje się w tej samej grupie.

Gwiezdna postać zajmuje drugi slot. Otwiera wybór Łucznika, Kielicha lub Smoka wraz z krótkim opisem rzeczywistego efektu i kosztem. Po aktywowaniu Łucznika główny przycisk staje się Gwiezdną strzałą. Przycisk ▾ nadal otwiera warianty i zakończenie postaci. Strzelanie nie aktywuje postaci ponownie ani nie zabiera kolejnego użycia Dzikiego kształtu.

Druid Kręgu Gwiazd na 15. poziomie, przy standardowym zestawie odblokowanych czarów, ma teraz 17 zajętych slotów zamiast 21. Włączenie Łucznika nie dodaje nowego slotu na strzałę i nie przesuwa pozostałych przycisków. Nie zmniejszono przycisków ani tekstu, nie dodano trzeciego rzędu.

Pozostałe czary nadal automatycznie trafiają na pasek po odblokowaniu. K otwiera pełną księgę i przypisywanie skrótów. Przypisanie jednego wariantu przemiany przenosi całą jego grupę. Kolejne zestawy po 24 miejsca pozostają dostępne przyciskami strzałek oraz Page Up / Page Down. Na telefonie pasek przewija się poziomo, również drugim palcem podczas chodzenia joystickiem. Nie ukryto bezpowrotnie wyuczonych czarów; grupowanie nie zastępuje stronicowania na wyższych poziomach.

## Użycia i gwiezdne postacie

Menu pokazuje wspólną pulę Dzikiego kształtu i koszt wybranej zdolności. Brak użyć blokuje nowe przemiany, ale nie darmową Gwiezdną strzałę aktywnego Łucznika ani zmianę konstelacji, która zgodnie z dotychczasowymi regułami jest darmowa od 45. poziomu. Aktywna konstelacja nie może zostać ponownie włączona. Dodatkowa blokada po stronie serwera chroni pulę także przed podwójnym kliknięciem lub starszym klientem.

Menu odróżnia dodatkowe obrażenia Łucznika od leczenia Kielicha po czarze leczącym i od wzmocnienia testów Smoka. Opisy podają wartości dla bieżącej postaci. Nie zmieniono progów kręgów, mocy czarów ani reguł odpoczynku.

## Wskazywanie terenu

Zwykłe kliknięcie pustego terenu nie uruchamia celownika i nie usuwa zaznaczonego przeciwnika. Nowe czary wymagające miejsca, np. Mgła, Pajęczyna i Kamienny mur, działają w kolejności: wybór czaru, wskazanie miejsca, potwierdzenie kliknięciem. Do potwierdzenia nie jest wysyłane polecenie rzucenia. Escape, prawy przycisk myszy lub × w podpowiedzi anulują wskazywanie.

Podgląd i znacznik są widoczne wyłącznie podczas celowania. Polecenia przenoszenia odpowiednich efektów również najpierw włączają wskazywanie. Nie przebudowano tu celowania każdego starszego czaru — pozostałe zachowują dotychczasowe zasady.

## Zapisy i zgodność

Serwer nadal zapisuje prawdziwe identyfikatory czarów w dotychczasowym `hotbar`; nowa lista `grouped_hotbar` jest projekcją dla przeglądarki. Nie ma nowej tabeli ani resetu postaci. Stare klienty nie dostają identyfikatorów grup zamiast czarów w swoim dawnym polu. Wstępne pogrupowanie usuwa z widocznego paska powtórzone warianty, więc miejsca późniejszych skrótów mogą przesunąć się w lewo; w K można ustawić nowy układ.

Ważne: aktualizuj jednocześnie serwer i katalog `web`. Serwer ma jawne trasy dla nowego `hotbar_ui.js` oraz `hotbar_ui.css`. Wersja na ekranie logowania powinna kończyć się `UI_13`.

## Weryfikacja tej poprawki

Celowany zestaw serwerowy: **47 testów zakończonych powodzeniem**, w tym grupowanie i przypisywanie, brak zgubionych odblokowań poziomów 1–100, ochrona puli, wcześniejsze testy kręgów druida i czarów kręgów oraz pobranie wszystkich plików JS/CSS z HTML przez rzeczywiste trasy HTTP aplikacji.

JavaScript: **54 testy zakończone powodzeniem**, obejmujące nowy pasek i dotychczasowe testy skrótów, dotyku, przewijania, statusów, czarujących i pierwszeństwa czarów nad różdżką.

Chromium: **12 kontroli zakończonych powodzeniem**. Sprawdzono 17 zajętych pól, aktywację Łucznika i darmową strzałę, blokady przy 0/2, zwykłe kliknięcie terenu, przypisanie grupy z księgi, kolejne zestawy na wysokim poziomie, jawne celowanie, menu przy 844×390, 390×844 i 734×260, drugi palec przewijający pasek podczas ruchu joystickiem oraz brak błędów JavaScript.

Ograniczenia: środowisko blokowało natywną nawigację przeglądarki do serwera. Klient produkcyjny wyrenderowano z osadzonymi JS/CSS i zasobami w Chromium, używając istniejącego mostka Python WebSocket do izolowanego serwera z bazą w pamięci. Pamięć localStorage była zastąpiona testową pamięcią. Osobny test HTTP sprawdził rzeczywiste trasy. Nie oznacza to testu zainstalowanej PWA, trwałości przeglądarkowego localStorage, fizycznego telefonu, APK ani produkcyjnego wdrożenia Railway.

Nie deklarujemy zielonego wyniku całego historycznego zestawu. Próba szerszej regresji przekroczyła limit czasu; 14 zaobserwowanych wcześniej nieprzechodzących testów uruchomiono potem osobno zarówno na nietkniętym UI_12, jak i UI_13. W obu wersjach te same testy zwracają 11 niezgodności asercji i 3 błędy wykonania. Dotyczą m.in. dawnych zasad regeneracji, natychmiastowego odzyskania mocy i starego cooldownu przemian. Ich naprawa nie należała do tej poprawki. Porównanie: `docs/qa_0.8.18/ui13/legacy_comparison.json`.

Raporty tej wersji: `docs/qa_0.8.18/ui13/`. Starsze raporty w nadrzędnym katalogu dokumentują wcześniejsze rewizje, a nie bieżące testy. Obrazy i źródła nowych testów są w paczce FULL_SOURCE.

Polecenia odtworzenia testów z katalogu projektu:

```sh
PYTHONPATH=tests python -m unittest test_hotbar_ui13 test_mana_hotbar_statuses.CompleteHotbars test_druid_circles_0818 test_druid_circle_spells_0818 -v
node --test tests/test_hotbar_ui13.cjs tests/test_client_runtime.cjs tests/test_hotbar_scroll_ui09.cjs tests/test_multitouch_ui03.cjs tests/test_status_actions_0818.cjs tests/test_casters_0814.cjs tests/test_wand_casting_0817.cjs
python tools/browser_hotbar_ui13.py
```

Test przeglądarkowy dodatkowo wymaga Playwright i Chromium; ścieżka do Chromium w skrypcie odpowiada środowisku QA.

## Wgranie

Paczka RAILWAY_GITHUB_READY ma `Dockerfile`, `run.py`, `server/` i `web/` bezpośrednio w katalogu głównym. Zastąp nimi pliki repozytorium, zachowując `.git`, własną bazę graczy i wolumen danych. Nie podmieniaj bazy plikiem testowym. Wyślij rozpakowane pliki, nie ZIP. Po wdrożeniu odśwież klienta. Ta paczka nie została automatycznie wdrożona do działającego serwera.
