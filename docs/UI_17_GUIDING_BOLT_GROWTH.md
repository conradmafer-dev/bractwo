# Bractwo 0.8.18 UI_17 — prawidłowy przyrost Wiodącego pocisku

Baza: `BRACTWO_0.8.18_UI_16_FULL_SOURCE.zip`.

## Co było błędne

Na niezmienionej UI_16 odtworzono dokładnie zgłoszone wpisy na awansie 19 → 20:
**Wiodący pocisk −1k6 do obrażeń** i **−10 do kosztu many**.
Nie była to kreska oddzielająca nazwę od wartości. Serwer rzeczywiście wysyłał
ujemne różnice, ponieważ porównanie rozwoju używało chwilowego stanu darmowych użyć.

Przypadek odtworzenia: druid Kręgu Gwiazd wydał trzy darmowe użycia pocisku.
Na 19. poziomie modyfikator Mądrości wynosi +3, więc pula jest pusta; tryb Auto
wybiera płatny pocisk II kręgu, 5k6 za 30 many. Na 20. poziomie Mądrość daje +4,
a więc pojawia się dodatkowe darmowe użycie. Tryb Auto ponownie wybiera wersję
podstawową I kręgu, 4k6. Błędna prognoza traktowała tę zmianę wyboru wersji jako
utraconą kość obrażeń; dla kosztu porównywała przy tym katalogowe 30 i 20 many,
zamiast rzeczywistego kosztu darmowego rzucenia.

To odtworzenie na osobnej postaci testowej, nie odczyt konta użytkownika z Railway.
Dane przed zmianą: `docs/qa_0.8.18/ui17/reproduction_ui16.json`.

## Poprawka

Projekcja stałego rozwoju (`automatic=True` w `spell_scaling.resolve`) porównuje
teraz najwyższą dostępną, użyteczną wersję płatną, niezależnie od chwilowej puli
bezpłatnych użyć, aktywowanej darmowej magii Kręgu Ziemi i ręcznego wyboru mocy.
Zwykły wybór **Auto podczas rzucania** nadal korzysta z dotychczasowych zasad.

Dla Wiodącego pocisku przy awansie 19 → 20 porównanie wynosi:

| Poziom | Najmocniejsza wersja płatna | Obrażenia | Koszt |
| --- | --- | --- | --- |
| 19 | II krąg | 5k6 | 30 many |
| 20 | III krąg | 6k6 | 50 many |

Panel prawidłowo pokazuje **+1k6 do obrażeń** oraz **+20 do kosztu many**.
Wzrost kosztu dotyczy mocniejszej wersji, nie podwyżki cen wszystkich wersji.
Darmowy pocisk I kręgu pozostaje 4k6 za 0 many w ramach dostępnych użyć.
Wciąż można ręcznie wybrać niższy krąg w księdze czarów.

Ta sama poprawka usuwa fałszywy minus w zapowiedzi kolejnego ulepszenia w księdze.
Nie zastosowano wartości bezwzględnej ani ukrywania ujemnych liczb: prawdziwe
ujemne różnice nadal zachowują znak. Zmieniono źródło porównania.

## Zakres

Jedyną zmianą działania jest warunek w `server/spell_scaling.py` (oraz jego komentarz).
`web/index.html` otrzymał etykietę **UI_17**. Dodano testy, raporty i dokumentację.
Porównano bajty wszystkich plików `server/` i `web/` z UI_16: poza wskazanymi dwoma
plikami pozostały identyczne.

Nie zmieniono obrażeń, kosztów rzucania, balansu Kolczastego wzrostu, grafik,
porządku księgi, paska skrótów, wielkości interfejsu, kamery ani ruchu.
Nie przebudowywano natywnego klienta Godota. Grafiki Wskazówek i Wiodącego pocisku
pozostają w paczce takie jak w UI_16; obie paczki zawierają `web/assets/spells/`.

## Wdrożenie i zapis gry

Wgraj rozpakowane pliki paczki Railway do głównego katalogu repozytorium: pliki
startowe, `server/` i `web/`. Zachowaj bazę graczy, wolumen oraz konfigurację.
Wymagane jest ponowne uruchomienie serwera z nowym kodem; sam nowy `index.html`
nie poprawia obliczeń. Po wdrożeniu odśwież stronę — logowanie ma pokazywać UI_17.

Reset postaci nie jest potrzebny. Po ponownym wczytaniu na nowym serwerze
niezamknięte wcześniej panele UI_16 zostaną obliczone poprawnie z zachowanego
kontekstu awansu, z tymi samymi identyfikatorami. Zamknięte panele nie wracają.
Archiwalne panele sprzed wprowadzenia skalowania zachowują dotychczasową obsługę.
Nie wdrażano paczek na produkcyjne Railway.

## Faktycznie wykonane testy

- **16 nowych testów serwera — 16 zaliczonych.** Dokładny przypadek 19 → 20,
  prognoza w księdze, różne stany użyć i wybory mocy, progi do 100. poziomu,
  otwarty i zamknięty panel, stabilność historii, brak mutacji katalogu oraz realne
  rzucenie pocisku za 0, 30 i 50 many na serwerze testowym.
- **184 starsze testy serwera — 181 zaliczonych, 2 niepowodzenia i 1 błąd.**
  Dla porównania uruchomiono dokładnie ten sam zestaw na niezmienionej UI_16:
  identyczne trzy problemy w `test_mana_growth_0816.LiveGrowth` dotyczące
  historycznych oczekiwań odzyskiwania many. Nie zmieniano tych testów ani reguł
  odzyskiwania, by uzyskać zielony raport. Szczegóły w `summary.json` i obu logach.
- **124 istniejące testy JavaScript — wszystkie zaliczone.** Panel awansu,
  obsługa danych klienta, grupy paska, mobilne formy i porządek księgi UI_16.
- **8 kontroli w Chromium — wszystkie zaliczone, bez wyjątków JavaScript.**
  Rzeczywisty panel po awansie, dodatnia zapowiedź ulepszenia, niezmieniony
  darmowy pocisk, zamykanie panelu i zachowany pasek/kręgi, osobno na pulpicie
  oraz w emulowanym dotykowym układzie poziomym. Ikona pocisku się wczytała.

Raporty oraz zrzuty: `docs/qa_0.8.18/ui17/`.
Sprawdzono też składnię Pythona i plików JavaScript.

## Ograniczenia

Nie testowano na fizycznym Androidzie ani na produkcyjnym serwerze. Test przeglądarki
osadza rzeczywiste HTML/CSS/JS, korzystając z istniejącego mostu Python–WebSocket
do osobnego serwera i bazy w pamięci. Nie jest to pełna regresja gry. Nie badano
w tym zadaniu balansu innych czarów, przytrzymania paska ani cache na telefonie.
