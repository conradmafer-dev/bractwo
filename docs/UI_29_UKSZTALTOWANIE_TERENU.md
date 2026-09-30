# Bractwo Krain 0.8.18 UI_29 — ukształtowanie terenu

Baza: pełna paczka UI_28 z cechami, umiejętnościami, odrębnymi zakładkami karty postaci i wcześniejszymi poprawkami. Kierunek: przenieść lokalną różnorodność okolic Przystani do dalszych krain.

## Teren

- 167 lokalnych formacji w 20 krainach, 668 nieregularnych płatów podłoża i 666 nowych fizycznych przeszkód. Kompozycje mają zmienne proporcje, przerwy i asymetryczne polany.
- 15 motywów obejmuje doliny leśne, prześwity między drzewami, skalne grzbiety i przesmyki, wydmowe niecki, erodowane wąwozy, suche kępy na bagnach, śnieżne zagłębienia oraz rozpadliny bazaltowe.
- Dobór miejsc korzysta z końcowej sieci dróg i istniejących punktów odkryć. Część miejsc leży przy szlakach, a część w głębi dzikiego terenu. Wszystkie sprawdzono rzeczywistymi kolizjami jako dostępne pieszo.
- Istniejące drogi, brzegi, woda, potwory, schody, odkrycia, usługi i wyzwania umiejętności zachowują położenie. Nowa geografia nie wchodzi w obszar początkowy 7000 × 6600. Nie dodaje przeciwników, nagród ani wymagań poziomu.

## Wygląd w przeglądarce

Dodano większe naturalne wzory podłoża, ściółkę, polne kwiaty, warstwy kamienia, kontury piasku i śniegu, suche trzciny, pobocza oraz wąskie krawędzie wybrzeży. Nowe zagajniki stoją na niskich ziemnych skarpach; formacje skalne mają warstwy i grzbiety dobrane do biomu. Połączone odcinki dróg nie tworzą powtarzających się owalnych śladów.

Podłoże jest przygotowywane przy tworzeniu fragmentu 512 × 512, a gotowy fragment jest używany ponownie. Nowe formacje mają osobną ograniczoną pamięć podręczną do 4 milionów pikseli. Nie wprowadzono generowania całej nowej scenerii w każdej klatce. Zimne tworzenie fragmentu nadal może kosztować kilkanaście–kilkadziesiąt milisekund; nie zmierzono FPS w rzeczywistej przeglądarce ani na telefonie.

Poprawiono zgodność promienia miejskiego bruku w klientach z promieniem przekazywanym przez serwer. Atlas otrzymał czytelniejsze warstwy lokalnych formacji.

## Zapisane postacie

Postać ze starszej wersji zapisana wewnątrz nowej skały lub skarpy trafia na pobliskie dostępne miejsce. Przesunięcie jest odkładane podczas walki i śmierci. Nie odnawia HP ani many i nie przyznaje przedmiotów. Konta i postęp nie są resetowane.

## Wdrożenie

`RAILWAY_GITHUB_READY` zawiera aktualny serwer i przeglądarkę. Wgraj całą zawartość do repozytorium wdrażanego na Railway, zachowując dotychczasowy wolumen, bazę i zmienne środowiska. `/health` oraz ekran wejścia pokazują UI_29; wersja geografii wynosi 29.

`FULL_SOURCE` zawiera również projekt Godota, testy i narzędzia. Natywny klient korzysta z nowych danych terenu i poprawionego promienia bruku, lecz nowa dekoracja Canvas jest przeznaczona dla przeglądarki. Nie zbudowano APK i nie uruchamiano silnika Godota. Paczek nie wdrożono na działający serwer.

## Weryfikacja

- 10 nowych testów Pythona: niezmieniony początek, ochrona istniejących punktów rozgrywki, kolizje, piesza dostępność wszystkich 167 miejsc, deterministyczna generacja i migracja postaci.
- 8 testów integracji kontynentu: wejścia, usługi, przeprawy, granice krain i blokada oceanu. Dawny limit płatów terenu dotyczy teraz osobno oryginalnej warstwy; nowe lokalne formacje są sprawdzane dodatkowym zestawem.
- 3 nowe testy JavaScript: zgodność powierzchni klienta i serwera w ponad 15 tysiącach próbek, rozdzielenie grafik różnych przeszkód oraz ograniczanie pamięci podręcznej.
- 13 testów atlasu i 19 testów istniejących narzędzi klienta zaliczono.
- Sprawdzono lokalny HTTP i WebSocket, w tym dostępność wszystkich 28 skryptów, kolejność ładowania grafiki i przekazywanie nowej geometrii.
- Obrazy `terrain-*.png` to podglądy samego modułu Canvas na rzeczywistych danych świata, z umownym znacznikiem postaci; nie są zrzutami pełnego interfejsu gry.

W środowisku nie było działającego Chromium ani Godota. Nie przeprowadzono pełnego testu przeglądarki, testu na fizycznym Androidzie ani wdrożenia Railway. Raporty i logi: `docs/qa_0.8.18/ui29/`.
