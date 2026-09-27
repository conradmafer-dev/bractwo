# Weryfikacja Bractwa 0.8.7 — 24.09.2026

## Serwer: 437 testów PASS

Pełny przebieg: `python -m unittest discover -s tests -v`. **437 testów, wynik OK, kod wyjścia 0, czas 42,813 s.** Wynik i kod wyjścia: `qa_0.8.7/server-tests.txt` i `qa_0.8.7/server-tests.exit`. Do 369 istniejących testów dodano **68 nowych**, bez doliczania pętli parametrów jako osobnych testów ani ponownego odkrywania importowanej klasy testowej.

Nowe testy `test_spell_scaling_087.py` sprawdzają:

- Przelicznik 1/2/3 poziomów klasy na 5/10/15 poziomów gry, granice i limit poziomu 20 D&D; kręgi czarodzieja/druida oraz opóźnionego łowcy.
- Wszystkie 18 reguł wyższych kręgów: kości, leczenie, stałe wartości, liczba pocisków/promieni/celów, czas. Brak wymyślonego wzrostu dla nieskalowalnych czarów, zerowy koszt sztuczek, niezmienny zimny składnik Lodowej burzy, pojedyncze dodanie cechy do leczenia.
- Rzeczywiste rzucanie: 5 i 11 Magicznych pocisków, osobne rzuty promieni, faktyczna utrata HP, wydatki many na Auto/krąg bazowy, brak samoczynnego słabszego rzutu przy braku many, kolejka oraz skrót F.
- Zamrożenie opłaconych kości/kręgu utrzymywanego czaru i pola przy awansie lub zmianie mocy, zakończenie koncentracji, statusy po skopiowaniu profilu, drużynowe cele Długonogiego oraz Swobody ruchu i blokady PvP. Dodatkowe przypadki Swobody ruchu obejmują progi obu klas, poprawny koszt, niezmienny czas i rzeczywiste usunięcie unieruchomienia u każdego uprawnionego odbiorcy.
- Zapis i sanitację preferencji, prywatność profili właściciela, odrzucanie złej klasy/nieodblokowanych kręgów/błędnych typów, niezmienność katalogu bazowego oraz odświeżanie cache po zmianie poziomu.
- Podsumowania wszystkich pośrednich awansów: oddzielne kości i stały bonus, pociski, cele, czas, koszt; brak dawnych/nowych sum, zerowych wierszy i nieprawdziwych przyrostów. Stare zakresy 0.8.6 bez nowych retroaktywnych wierszy.

Dotychczasowe testy nadal obejmują autorytatywną walkę, geometrię, osady, PvP, pościg bez powrotu, statystyki, wybór celu, manę, hotbar, zapis, konta i kaskadę awansów. Przypadki sprawdzające konkretnie bazowy krąg wybierają teraz ten krąg jawnie. Przypadki sprawdzające automatyczne skalowanie oczekują nowych liczb. Test numeru wersji `/health` sprawdza 0.8.7.

Środowisko: **Python 3.13.5, aiohttp 3.13.3**. Produkcyjny `server/requirements.txt` pozostawia dotychczasowe `aiohttp==3.13.5`; nie zainstalowano osobno tego przypiętego środowiska. Testy nie są pomiarem balansu ani wydajności hostingu pod dużym obciążeniem.

## JavaScript: 36 testów PASS

`node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs tests/test_level_up.cjs`: **36 testów, 36 PASS, zero porażek**. Log: `qa_0.8.7/node-tests.txt`; kod wyjścia 0.

8 dodatkowych testów: nadpisania profilu właściciela i niezmienność katalogu; koszt wybranego kręgu; darmowe powtórzenie tylko aktywnego czaru; brak profilu/zablokowany wpis; scalanie stanów bez przecieku między kontami; 4–11 odrębnych krzywych z właściwymi końcami; brak NaN przy pokrywających się pozycjach; poprawne komendy Canvas dla zwiększonych salw i promieni we wszystkich testowanych fazach. Stare testy 24 skrótów, przyrostów i zgodności geometrycznej pozostają.

Node **v22.16.0**. `python -m compileall -q server tests tools` i `node --check` dla wszystkich skryptów WWW: PASS (osobne pliki `.exit`). To nie jest kompilacja GDScript.

## Interfejs WWW: 14 sprawdzeń PASS, 0 błędów strony JavaScript

`python tools/browser_087_smoke.py`. Wynik: `qa_0.8.7/browser-results.json`; log: `browser-log.txt`; kod wyjścia `browser-tests.exit` = 0. Chromium **144.0.7559.96**.

Sprawdzono podsumowanie poziomu 10 (pocisk, kość, cel i koszt w osobnych wierszach), kaskadę i indywidualne Zamknij, aktualne wartości w księdze, następny próg wzrostu, wysłanie preferencji bazowego kręgu, rzeczywisty rzut z przeglądarki za 20 many z 3 trafieniami, przywrócenie Auto za 30 z 4 trafieniami. Selektor działa przy **390×844, 320×700 i 844×390**, bez poziomego przepełnienia strony. Główny widok sprawdzono przy **1440×900**.

Rzut maksymalnego kręgu tworzy zdarzenie z 11 pociskami. Zrzut `04_eleven_projectile_renderer.png` to **kontrolowany kadr rzeczywistego renderera**, wykorzystujący ten serwerowy pakiet, na dodatkowym płótnie testowym ze stałą fazą animacji i przeskalowanymi pozycjami. Nie jest zrzutem naturalnie zatrzymanej rozgrywki; służy policzeniu i obejrzeniu salwy. Nie dodano tego płótna do gry. Pozostałe zrzuty pokazują zwykłe widoki klienta z kont testowych.

Druid na poziomie 20: odrębne +2k8 i +1 leczenia oraz +1k10 pola; mały ekran zachowuje dostęp do dolnego Zamknij. Istniejący Promień księżyca zachowuje kości po awansie; karta utrzymywanego Wezwania błyskawicy pokazuje opłaconą moc; Zakończ czar usuwa koncentrację i ujawnia nową wersję, której nie można rzucić przy zerowej manie.

**Metoda:** rzeczywiste skrypty WWW, rzeczywisty serwer aiohttp i kontrolowany most WebSocket Python. HTML/JS/CSS/SVG wczytane z plików; testowe localStorage w pamięci; kontrolowany zegar i sztuczne konta; ruch potworów wyłączony, obrażenia/kręgi/PD/stan liczone przez serwer. To nie test natywnego HTTP/WS Chromium, fizycznego telefonu, trwałego localStorage, hostingu ani wielogodzinnej sesji. Zapis preferencji do bazy i migracja są dodatkowo sprawdzone jednostkowo po stronie serwera. W finalnym przebiegu wyciszono transport przed zamknięciem przeglądarki, aby uniknąć błędu sprzątania zamkniętej strony.

## Godot i eksport: NIE WYKONANO

Zmodyfikowano korzystanie z aktualnych profili/kosztów, wybór kręgu w księdze, opis następnego wzrostu, zakończenie koncentracji oraz krzywe i liczbę Magicznych pocisków. Przejrzano zmienione źródła, ale **nie zaimportowano, nie uruchomiono ani nie skompilowano projektu w silniku Godot**. Nie potwierdzono przez silnik typowania GDScript, geometrii natywnego interfejsu ani dotyku. Wyniki Python/JS nie stanowią takiego potwierdzenia.

W środowisku brakowało silnika; próba pobrania docelowego Godota 4.5.1 z oficjalnego wydania nie powiodła się. Nie wykonano APK, AAB ani EXE; ZIP zawiera źródła. Przyszły eksport Androida ma `version/code=14`, ale nie jest tu zbudowany.

## Integralność i historia

`SOURCE_MANIFEST.json` zawiera rozmiary i SHA-256 końcowych plików, z wyłączeniem samego manifestu. Końcowy ZIP jest sprawdzany przez `zipfile.testzip()` i porównanie manifestu. Wykluczono cache, środowiska, pliki podpisu, bazy użytkownika i fonty. Starsze raporty i zrzuty pozostają historyczne; raport 0.8.6 zapisano w `qa_0.8.6/TEST_REPORT.md`. Wcześniejsze nieudane logi robocze 0.8.7 nie są przedstawiane jako końcowe wyniki.
