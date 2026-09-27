# Raport weryfikacji Bractwa 0.8.3 — 24.09.2026

## Testy serwera — PASS

`python -m unittest discover -s tests -v`: **247 testów**, pełny przebieg 20,783 s. Wynik w `qa_0.8.3/server-tests.txt`. Zestaw zawiera 224 dotychczasowe testy z aktualizacją oczekiwanego progu I kręgu i wersji oraz **23 nowe metody testowe** z `tests/test_first_circle.py`. Podprzypadków nie doliczono do liczby testów.

Nowe sprawdzenia: cały I krąg obu klas od poziomu 1; zgodność `spell_circle` z rzeczywistym dostępem do każdego czaru na poziomach 1–105; niezmienione progi II–IX; późniejszy I krąg łowcy także dla dzielonych czarów; brak przesunięcia cech klasowych i skalowania sztuczek; domyślne sloty 4/5; każdy czar I kręgu wykonany faktycznie na poziomie 1, w tym koszty, rzuty, reakcja Tarczy i koncentracja; odrzucenie czarów przy zbyt małej manie; darmowe sztuczki przy zerze many; kolejka przed autoatakiem; niezmieniona ochrona niskich poziomów w PvP; istniejące zapisy poziomów 1/5/9 z zachowaniem własnych skrótów, poziomu, XP i złota; rejestracja po WebSocket; katalog dostarczany klientowi i pomoc.

W pełnym zestawie ponownie wykonano wcześniejsze testy PvP, pościgu, różdżek, sztuczek, migracji, rankingu, endpointów HTTP i rzeczywistych połączeń WebSocket. Nie oznacza to wielogodzinnego testu gry ani pełnego testu wydajności świata.

## JavaScript i składnia — PASS

**10 testów Node**: `node --test tests/test_client_runtime.cjs`, wynik w `qa_0.8.3/client-runtime-tests.txt`. `node --check web/game.js`, `node --check web/runtime.js` i `python -m compileall -q server tests tools`: PASS. Wynik składni w `qa_0.8.3/syntax-tests.txt`.

## Interfejs WWW — PASS w opisanym zakresie

`python tools/browser_083_smoke.py`: **13 sprawdzeń UI**, zero błędów JavaScript. Wyniki: `qa_0.8.3/browser-results.json`, log: `browser-console.txt`. Trzy nowo zarejestrowane postacie: czarodziej, druid i łowca, wszystkie poziomu 1. Księga, pasek, blokady wyższych kręgów, opisy, wykonywanie czarów i kolejka były sprawdzane przez kliknięcia w rzeczywistym interfejsie oraz odczyt rzeczywistego stanu serwera. Widoki: 1440×900 i 390×844. Zrzuty `01`–`04` dokumentują I krąg na poziomie 1; desktop czarodzieja i mobile druida dodatkowo przejrzano wizualnie.

Ograniczenie środowiska: bezpośrednie wejście Chromium na lokalny adres HTTP zostało zablokowane (`net::ERR_BLOCKED_BY_ADMINISTRATOR`). Dlatego użyto kontrolowanego mostu WebSocket Python, prawdziwych skryptów klienta i serwera oraz testowego localStorage w pamięci. To nie jest test natywnych połączeń HTTP/WS przeglądarki, trwałego localStorage ani telefonu fizycznego. Szczegóły: `qa_0.8.3/browser-network-note.txt`. Nie ponawiano wcześniejszych scenariuszy UI 0.8.2; ich historyczne wyniki nie są doliczane do bieżących 13 sprawdzeń.

## Godot i eksporty

Źródła Godota pokazują nowe opisy i korzystają z katalogu przesyłanego przez serwer. Zmieniono wersję projektu i metadane eksportu Androida. **Silnika Godot nie uruchomiono; projektu nie importowano ani nie kompilowano w silniku. Nie przygotowano APK, AAB ani EXE.** Statyczna poprawka tekstów nie stanowi testu działającej aplikacji natywnej.

## Archiwum i integralność

Aktualne wyniki są wyłącznie w `qa_0.8.3/`. Wcześniejsze `qa_*`, `archive_*` i `tests/legacy_0_7/` są historią. Nie wykonywano nowego benchmarku wydajności. Manifest źródeł zawiera rozmiary i sumy SHA-256 wszystkich dołączonych plików poza samym manifestem. Archiwum jest pełnym projektem, bez testowej bazy danych, pamięci podręcznej Pythona i binarnych eksportów.
