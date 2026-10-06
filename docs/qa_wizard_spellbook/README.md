# Księga czarodzieja — regresja balansu

Baza: `41bd67154b341aaf36924e00642ca0f349d74394`. Raport przed zmianą powstał
w oddzielnym worktree tej rewizji; raport po zmianie używa implementacji księgi
i przygotowywania czarów z tego PR.

## Protokół

Każda wersja wykonuje 320 walk: 40 ziaren RNG (0–39), cztery klasy i dwóch
starterowych bossów. Postacie mają poziom 3, czyli odpowiednik dawnego poziomu
10 Bractwa, początkowy ekwipunek, pełne HP/manę, brak specjalizacji i atutów.
Kontroler reaguje na widoczne zapowiedzi po 250 ms, korzysta z rzeczywistych
kolizji areny i używa najwyżej jednej mikstury zdrowia. Krok wynosi 50 ms,
a limit pojedynku 90 s.

Walki przeprowadza serwerowy `Game`: rzuty, koszty, ekonomia akcji, ruch, AI
i obrażenia pochodzą z gry. Benchmark nie implementuje osobnej matematyki
walki ani nie omija walidacji rzucania czarów.

Na bazowej rewizji czarodziej automatycznie zna wszystkie odblokowane czary.
Po zmianie przed walką **uczy się Magicznego pocisku i go przygotowuje** przez
rzeczywiste komendy `wizard_learn` i `wizard_prepare`. Skrypt sprawdza następnie
serwerowe uprawnienie do rzucenia tego czaru. To jedyna zmiana konfiguracji
kontrolera między rewizjami; pozostałe dostępne wybory nauki pozostają niewydane.

Strategia czarodzieja nadal używa Magicznego pocisku z dostępnym wzmocnieniem,
obniża krąg przy niedoborze many, a następnie przechodzi na Ognisty pocisk.
Wojownik walczy bronią i używa Drugiego oddechu, łowca utrzymuje Znak łowcy,
a druid korzysta z Shillelagh i Słowa uzdrawiającego. Pozostałe klasy nie mają
zmienionej konfiguracji ani strategii.

Polecenia uruchomione odpowiednio w bazowym i aktualnym katalogu repozytorium:

```sh
python tools/balance_starter_bosses.py --trials 40 --seed-start 0 --level 3 --output ../bractwo/docs/qa_wizard_spellbook/balance_before.json
python tools/balance_starter_bosses.py --trials 40 --seed-start 0 --level 3 --output docs/qa_wizard_spellbook/balance_after.json
```

Pierwszy raport zapisano z bazowego worktree bezpośrednio do tego katalogu;
skrypt bazy pozostał niezmieniony. Oba raporty zawierają pełne wyniki pojedynczych
walk.

## Wyniki

**320/320 zwycięstw przed zmianą i 320/320 po zmianie; zero przekroczeń czasu.**
Poniższe średnie są identyczne w obu raportach. Każde pole obejmuje 40/40
zwycięstw; czas podano w sekundach.

| Boss | Wojownik | Łowca | Czarodziej | Druid |
|---|---:|---:|---:|---:|
| Szkielet bez głowy | 28,66 | 21,63 | 13,32 | 28,59 |
| Łucznik starej wieży | 26,96 | 20,10 | 12,33 | 26,50 |

Porównanie wszystkich 320 odpowiadających sobie rekordów wykazało **zero
zmienionych walk**: wynik, czas, HP, mana, mikstury i liczba specjalnych ataków
bossów są identyczne. Całe pliki JSON, łącznie z podsumowaniami, mają tę samą
sumę SHA-256:

```text
0ab4b371aaf791809323e7f81c9f5cad9e702649cd28b770ea93fadf76caeace
```

## Zakres wniosku

Nowe zasady nauki i przygotowania zachowują przebieg walk dla tego samego,
legalnie przygotowanego zestawu czarów. Nie zmieniają siły Magicznego pocisku,
Ognistego pocisku ani bazowych mechanik innych klas.

Benchmark obejmuje jeden zestaw czarodzieja i dwa bossy poziomu 3. Nie porównuje
wszystkich możliwych ksiąg, nie ocenia wygody wyborów w interfejsie i nie wykonuje
Memorize Spell, które odblokowuje się dopiero na poziomie 5. Nauka, limity,
przygotowanie, rytuały, migracja zapisu i pomyślne lub przerwane odpoczynki mają
osobne testy regresyjne. Te wyniki nie uzasadniają zmiany parametrów bossów
ani siły całych klas.
