# Raport weryfikacji Bractwa 0.8.5 — 24.09.2026

## Serwer — PASS

`python -m unittest discover -s tests -v`: **334 testy**, pełny końcowy przebieg **29,184 s**, bez błędów i porażek. Log: `qa_0.8.5/server-tests.txt`. W tym **40 nowych metod** w `tests/test_geometry_character_085.py`. Dotychczasowe testy zachowano, aktualizując oczekiwania wersji, rozmiaru paska i krótszego, poprawionego stożka Płonących dłoni. Podprzypadków pętli nie doliczano do liczby testów.

Nowy zakres: granice prostych i obróconych stożków bez starego kołowego marginesu, dalekie rogi, szerokość/długość linii, narożniki kwadratów, koła, dziesięć pól Burzy ognia i cztery obszary meteorów, brak zwielokrotniania jednego trafienia w nakładających się obszarach. Testy wywołują także faktyczne rzucanie czarów i sprawdzają obrażenia wobec celów wewnątrz/poza granicą. Trzy rzuty Magicznego pocisku i jedna pozycja historii, profil promienia mrozu, znikanie efektów pola po końcu koncentracji. Kompletność i zgodność ikon WWW/Godot.

Historia F: domyślny czar przy pustej historii, najczęstszy z ostatnich 100 udanych użyć, remisy, sanitacja kluczy obcych/zablokowanych, brak naliczania nieudanych prób i kolejkowania przed wykonaniem, Tarcza dopiero przy reakcji, utrwalenie w bazie. Pasek: zachowanie wcześniejszych indeksów, 24 pola, przypisanie slotu 23, kompletność czarów. Karta: sześć cech/obron, prawdziwe wyliczenia walki, odporności zgodne z odejmowaniem obrażeń, ich wygaśnięcie, prywatność danych właściciela, pusta lista atutów. Zasoby statyczne sprawdzono również rzeczywistymi żądaniami HTTP aiohttp.

Ponownie przeszły testy istniejącej walki, PvP, kości, rankingu, bezpieczeństwa, koncentracji, towarzyszy, zapisu, migracji, many, kręgów, statusów i pościgu. Nie wykonano nowego benchmarku pojemności świata ani wielogodzinnego playtestu.

## JavaScript i sprawdzenie składni — PASS

`node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs`: **22 testy**, zero porażek. Log: `qa_0.8.5/node-tests.txt`. 14 testów dotychczasowego runtime oraz 8 nowych w `test_spell_vfx.cjs`.

Sprawdzono 1–0, −, =, F1–F12, oddzielenie F od F1, globalne indeksy i strony, zgodność zawierania punktów między geometrią Python i JavaScript, trzy różne krzywe zbiegające w celu, zerowy dystans, rysowanie każdego z 47 profili przy różnych czasach animacji bez NaN i niezrównoważonego save/restore kontekstu oraz fallback dla dawnych efektów. Próbek siatki i faz animacji nie liczono jako osobnych testów.

`python -m compileall -q server tests tools` i `node --check` dla `game.js`, `runtime.js`, `spell_vfx.js`, `character_sheet.js`: PASS. `qa_0.8.5/syntax-tests.txt`. To nie sprawdza GDScript.

## Interfejs WWW — 21 sprawdzeń PASS

`python tools/browser_085_smoke.py`: **21 sprawdzeń**, **0 błędów JavaScript**. Log: `qa_0.8.5/browser-run.txt`; wynik i komendy: `qa_0.8.5/browser-results.json`. Końcowy osobny przebieg zakończył się poprawnie po wcześniejszym przerwaniu zbiorczego wywołania narzędzia limitem czasu.

Weryfikowano rzeczywiste skrypty i style projektu z rzeczywistym serwerem oraz świeżym kontem czarodzieja. Kliknięcia i klawiatura otwierają samodzielną kartę C, cztery zakładki, plecak 5 × 3, statystyki i pusty stan atutów. Przypisano i faktycznie użyto F1 i F12, sprawdzając koszty, efekty oraz historię; oddzielny F rzeczywiście rzuca najczęstszy czar. Wykonano Magiczny pocisk, Promień mrozu, Płonące dłonie, Kulę ognia i Błyskawicę — ich dane geometrii i animacje pochodzą z wykonania na serwerze, nie ze spreparowanych samych zrzutów interfejsu.

Pełny plecak ma kolejne strony bez listy pojedynczych wierszy; wyposażenie pozostaje powyżej. Sprawdzono aktualizację statystyk bez ponownego otwierania karty, drugi zestaw 24 skrótów na wysokim poziomie i wspólne przewijanie dwóch rzędów na małym ekranie. Rozdzielczości: **1440×900, 390×844, 320×700, 844×390**; brak poziomego przepełnienia dokumentu. Zapisano **10 zrzutów** w `qa_0.8.5/`. Obejrzano kartę i efekty wizualnie; końcowe zrzuty zawierają finalne ikony i poprawiony układ powiadomień.

**Ograniczenie metody:** natywna nawigacja Chromium była blokowana przez środowisko. Test używa kontrolowanego mostu WebSocket Python i testowego localStorage w pamięci; zasoby są podawane z rzeczywistych lokalnych plików. Nie jest to end-to-end test natywnych HTTP/WS Chromium, trwałego localStorage, fizycznego dotyku telefonu ani opublikowanego hostingu. Zegar i poziom/zasoby postaci są ustawiane przez fixture, a AI potwora zatrzymane dla czytelnych ujęć; same rzuty, zasady celu i koszty pozostają rzeczywistym kodem serwera. Test nie obejmuje naturalnego awansowania przez całą grę.

## Godot / eksporty — NIE WYKONANO

Zmieniono źródła natywnej karty, geometrii i animacji, ikony, 24 skróty, F, powiadomienia, odświeżanie stanu i metadane projektu (0.8.5, Android code 12). **Silnika nie uruchomiono, projektu nie importowano ani nie skompilowano. GDScript i natywny układ nie zostały zweryfikowane przez wykonanie w Godocie.** Brak APK, AAB i EXE. Przed wydaniem klienta natywnego pozostaje wymagany import, kompilacja i test na urządzeniu.

## Integralność i materiały historyczne

`SOURCE_MANIFEST.json` zawiera rozmiar i SHA-256 każdego dostarczonego pliku poza samym manifestem. Pełny ZIP sprawdzono pod kątem CRC, zgodności każdej sumy i listy plików. Nie dołączono testowych baz danych, cache, silnika, kluczy podpisu, fontów ani eksportów binarnych.

`archive_0.8.4/` i wcześniejsze `archive_*`/`qa_*` zachowują historyczne raporty/zrzuty. Stare scenariusze przeglądarkowe zawierają dawne założenia i nie są bieżącym testem 0.8.5. Aktualny scenariusz to `tools/browser_085_smoke.py`. Wszystkie liczby powyżej dotyczą wykonanych prób tego wydania; nie doliczają historycznych przebiegów.
