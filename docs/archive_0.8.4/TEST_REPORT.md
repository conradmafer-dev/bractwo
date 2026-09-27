# Raport weryfikacji Bractwa 0.8.4 — 24.09.2026

## Serwer — PASS

`python -m unittest discover -s tests -v`: **294 testy**, pełny przebieg 26,165 s, zero błędów/porażek. Log: `qa_0.8.4/server-tests.txt`.

Zestaw zawiera 247 dotychczasowych testów, których oczekiwania dotyczące zmienionych progów, kosztów, wersji i kompletności paska zostały zaktualizowane, oraz **47 nowych metod** w `tests/test_mana_hotbar_statuses.py`. Podprzypadki pętli nie są doliczane do liczby testów.

Nowy zakres: początkowe 40 MP i dwa płatne czary; ważone budżety komórek i ich zgodność z najwyższym dostępnym kręgiem na poziomach 1–149; zmienione koszty wszystkich nieklasowych czarów; darmowe sztuczki przy pustej puli; brak regeneracji w PvE/PvP; opóźnienie po rzucaniu, reakcja Tarczy, tempo poza walką, limit maksymalnej many; jednorazowa migracja procentu starej puli i trwałość opóźnienia; kompletny pasek każdej klasy, brak zablokowanych wpisów, czyszczenie duplikatów/nieprawidłowych wpisów, zachowanie poprawnych pozycji, zamiana miejsc, automatyczne uzupełnienie po awansie, zapis/odczyt.

Długonogi: 600 rund/1800 sekund gry, brak koncentracji, zachowanie po ataku/obrażeniach/innym czarze koncentracyjnym, brak kumulowania premii, odświeżenie czasu, stały dodatek szybkości, dotyk do członka drużyny i odrzucenie dalszego celu. Statusy: publiczne/prywatne sekundy/rundy/opisy, brak ujawniania właściciela efektu, osłabienia potworów i graczy, wygaśnięcie, nazwa koncentracji, odróżnienie gotowości Tarczy, postać zwierzęca i tymczasowe HP. Aggro: obniżenie odpowiednich promieni, brak zmiany silniejszych/bossów, niesprowokowany potwór nie podchodzi ze starego promienia, odwet i trwający pościg działają dalej.

Ponownie wykonano dotychczasowe testy PvP (w tym rzeczywiste połączenia WebSocket), rankingów, migracji, kręgów, koncentracji, pól, towarzyszy, bezpieczeństwa, kości, pościgu i różdżek. Nie jest to wielogodzinny playtest ani nowy benchmark wydajności świata.

## JavaScript i składnia — PASS

`node --test tests/test_client_runtime.cjs`: **14 testów**, zero porażek. Nowe sprawdzenia: osiem klawiszy na bieżącej stronie i dodatkowe strony, pusta lista i granice wielokrotności ośmiu, czytelny licznik 600 rund/30 minut i statusów bez końca, opis mieszanej puli many. Log: `qa_0.8.4/node-tests.txt`.

`node --check web/game.js`, `node --check web/runtime.js`, `python -m compileall -q server tests tools`: PASS. Log: `qa_0.8.4/syntax-tests.txt`. Te polecenia nie sprawdzają składni ani działania GDScript.

## Interfejs WWW — PASS w opisanym zakresie

`python tools/browser_084_smoke.py`: **20 sprawdzeń**, zero błędów JavaScript. Log: `qa_0.8.4/browser-run.txt`; strukturalny wynik i wysłane polecenia: `qa_0.8.4/browser-results.json`.

Dwie świeżo zarejestrowane postacie (czarodziej/druid), rzeczywiste skrypty i style projektu, rzeczywisty serwer. Test wykonuje kliknięcia/klawisze, zmiany stron, rzucanie czarów, wyczerpanie many, zamianę slotów z księgi, awanse, wyświetlanie/wygaśnięcie statusów postaci i celu, koncentrację i debuff PvP. Sprawdza brak zablokowanych pól na początkowym pasku oraz automatyczne dodanie II/III kręgu na 10/20.

Rozdzielczości: **1440×900, 390×844, 320×700, 844×390**. Strony i opisy efektów mają klikalne kontrolki na małych ekranach; sprawdzono brak poziomego przewijania dokumentu. Księga ukrywa nakładkę statusów, aby ta nie zakrywała czarów. Zrzuty `01`–`05` zapisano przy użyciu tego testu. Widoki desktop, mały portrait i landscape dodatkowo obejrzano wizualnie. Podczas pracy wykryto i poprawiono nakładanie statusów na mobilny przycisk księgi oraz listę czarów; końcowy przebieg jest po tych poprawkach.

**Ograniczenie metody:** użyto kontrolowanego mostu WebSocket Python i testowego localStorage w pamięci, zamiast natywnej nawigacji i połączenia sieciowego przeglądarki. To nie jest end-to-end test natywnych HTTP/WS Chromium, trwałego localStorage, dotyku fizycznego telefonu ani opublikowanego hostingu. Zegar i niektóre wartości postaci są kontrolowane przez fixture QA; nie jest to test naturalnego zdobywania poziomów. Historycznych wyników innych `browser_*` nie doliczono do bieżących 20.

## Godot i binarne eksporty — NIE WYKONANO

Źródła Godota zmieniono: strony paska, klawisze i wybór slotów, opisy budżetu, poprawne kręgi i etykiety aktywnych efektów postaci/celu. Zmieniono metadane projektu i eksportów na 0.8.4 (Android code 11). **Silnika nie uruchomiono; projektu nie importowano ani nie skompilowano. GDScript i natywnego układu nie zweryfikowano wykonaniem.** Brak APK, AAB i EXE. To pozostaje istotnym zakresem testu przed wydaniem natywnego klienta.

## Archiwum i integralność

Aktualny raport dotyczy wyłącznie 0.8.4. `archive_0.8.3/`, wcześniejsze `archive_*`/`qa_*` i `tests/legacy_0_7/` to materiały historyczne. Stare narzędzia browser QA zawierają stare oczekiwania i nie są alternatywą bieżącego `browser_084_smoke.py`.

Końcowy ZIP jest pełnym projektem, bez testowej bazy, cache Pythona, silnika Godot, kluczy podpisu i eksportów. `SOURCE_MANIFEST.json` podaje rozmiar i SHA-256 każdego pliku oprócz samego manifestu. Integralność ZIP i zgodność manifestu sprawdzono po utworzeniu archiwum.
