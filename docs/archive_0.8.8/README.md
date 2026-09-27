# Bractwo 0.8.8 — łupy, pancerze i nowe potwory

**59 nowych elementów wyposażenia:** 30 broni, 23 pancerze/szaty i 6 pierścieni. Do tego **20 trofeów**, **9 nowych rodzajów potworów** (w tym 2 bossy) i **126 nowych odrodzeń** w istniejącym świecie. Każdy z 57 gatunków ma przypisane przedmioty z jawną szansą procentową, niezależnie od klasy zabijającego gracza.

Pełne tabele i parametry są w `docs/LOOT_0.8.8.md` oraz maszynowo w `docs/LOOT_0.8.8.json`. Są generowane z rzeczywistego katalogu serwera, a nie ręcznie powielane. Wykresy i zrzuty starszych wersji w dokumentacji to archiwum, nie dowód nowego testu.

## Przykładowe łupy

| Przeciwnik | Przedmiot | Szansa na jedną nagrodę |
|---|---|---:|
| Mumia | Różdżka mumii +1 | 5% |
| Szkielet łucznik | Łuk kościanego wartownika / Łuk z krypty +1 | 7% / 1,5% |
| Bandyta | Miecz rozbójnika / Szabla rabusia +1 | 6% / 3% |
| Grobowy akolita | Różdżka grobowego akolity +1 | 4% |
| Szaman Ciernistego Kręgu | Kostur Ciernistego Kręgu +1 | 5% |
| Herszt Czarnego Traktu | Rozkaz Herszta +1 / zbroja paskowa | 18% / 12% |
| Mumia Hierofanta | Berło Hierofanty +2 / szata | 15% / 12% |
| Obsydianowy rycerz | Obsydianowy miecz +2 / płyta +2 | 3% / 2% |

Każdy przedmiot losowany osobno. Rzut na broń nie blokuje rzutu na pancerz. 5% nie daje gwarancji po dwudziestym pokonaniu przeciwnika. Zwierzęta i elementale zostawiają głównie własne trofea lub esencje, nie miecze dobrane do gracza. Smoki i odpowiedni bossowie mają skarbce/zdobycze. Stare skrzynie i nagrody zadań nie zostały wymienione na nowe tabele.

## Nowy sprzęt naprawdę działa

Nowe bronie używają swoich kości: np. miecz dwuręczny `2k6`, młot `1k8` obuchowych, topór króla `1k12`, krótki łuk `1k6`, długi `1k8`. Premia magiczna jest doliczana raz, osobno od modyfikatora cechy. Krytyk podwaja kości, nie stałą premię. Kostury współpracują z Shillelagh. **Różdżki nie przywracają silnego autoataku:** Iskra nadal zadaje `1k4`; poprawa trafienia/ST wzmacnia sens używania czarów.

Pancerze lekkie korzystają z pełnej Zręczności, średnie najwyżej z +2, ciężkie nie doliczają Zręczności. Ciężki nowy sprzęt nosi rycerz, lekki i średni rycerz/łowca/druid, czarodziej ma szaty. Nowe pierścienie i wybrane pancerze zapewniają odporności; działają przy otrzymywaniu obrażeń, także PvP, i są widoczne w statystykach. Odporności tego samego typu się nie kumulują. Szaty pozostają zgodne ze Zbroją maga.

## Wygląd i obsługa

79 nowych ikon przedmiotów oraz 11 oryginalnych atlasów animowanych potworów (po cztery klatki): dziewięć nowych gatunków i poprawiony wygląd mumii oraz szkieleta łucznika. Grafiki są dołączone do obu klientów, nie pobierają się z zewnętrznych serwisów. Nowi przeciwnicy nie są tylko dawnymi figurami z inną nazwą.

Zaznacz przeciwnika i naciśnij **Łup** obok nazwy celu. Podgląd zawiera konkretne przedmioty i ich procenty. W **C → Ekwipunek** wybierz przedmiot, a następnie **Skąd zdobyć**. Oba podglądy korzystają z tej samej tabeli co faktyczne losowanie. W Godocie podgląd celu jest prostszym oknem tekstowym z nazwami i procentami; ikony są w karcie ekwipunku, animacje w świecie.

Przedmioty trafiają do plecaka; sprzęt innej klasy można sprzedać lub przechować. **Plecak nadal ma 40 miejsc, a nadmiar łupu przepada z ostrzeżeniem.** Zdejmowanie/zakładanie nie dubluje przedmiotów. C, I, K, oba paski skrótów, adaptacyjne F i kaskada awansów pozostają bez zmian. Potwory nadal nie wracają po zakończeniu pościgu.

## Uruchomienie

Windows: `start_windows.bat`, następnie `http://127.0.0.1:8080`. Do lokalnego testu w sieci: `start_windows.bat lan`.

Na pozostałych systemach: `python -m pip install -r requirements.txt`, potem `python run.py`. Launcher używa `data/world.sqlite3` lokalnie lub wskazanej zmiennej `BRACTWO_DB_PATH`.

Godot: import `client/project.godot`. W tej paczce nie ma APK, AAB ani EXE. Dostarczone źródła Godot nie zostały uruchomione w silniku ani wyeksportowane.

## Aktualizacja istniejącej gry / Railway

**Nie wymaga resetu postaci.** Zachowaj bazę, konta i wolumen. Aktualizacja odświeża definicje przedmiotów podczas wczytywania ekwipunku i depozytu, nie zmienia ich identyfikatorów ani własności. Nowi przeciwnicy pojawią się po starcie nowego serwera; stare miejsca odrodzenia nie są przenoszone. Nie dopisuje się łupów za potwory pokonane wcześniej.

Przed lokalną podmianą zatrzymaj serwer i zrób kopię `data/world.sqlite3`. Na Railway zachowaj istniejącą usługę, jej Volume `/data` i `BRACTWO_DB_PATH=/data/world.sqlite3`. Nie przesyłaj bazy do GitHuba. Podmień serwer **oraz cały katalog web wraz z assets**. Pełna paczka także zawiera Dockerfile/run.py; osobna paczka Railway ma płaski układ katalogów bez źródeł klienta Godot. Instrukcja: `docs/RAILWAY.md`.

Po aktualizacji odśwież stronę; w razie starego wyglądu wymuś pełne odświeżenie Ctrl+F5. Zdrowie serwera `/health` podaje wersję `0.8.8`.

## Sprawdzenie

Pełny raport i rzeczywiste logi: `docs/TEST_REPORT.md` oraz `docs/qa_0.8.8/`. Testy obejmują losowanie, granice procentów, rzeczywiste wyposażanie/obrażenia/KP/odporności, zapis, nowy świat i interfejs. To nie zastępuje testu balansu na długiej sesji lub hostingu z wieloma graczami. Wdrożenie na koncie Railway ani budowa obrazu Docker nie zostały wykonane.

Atrybucja materiału SRD: `LICENSE-SRD.txt`. Poziomy, progi i tabele łupu są autorskim balansem Bractwa. Źródła wszystkich nowych grafik: `tools/generate_loot_art.py` (Pillow potrzebny tylko do ponownego generowania, nie do gry).
