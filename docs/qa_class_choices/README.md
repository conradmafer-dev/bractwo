# Style łowcy i Furia żywiołów druida — walidacja balansu

Baza: `f6e862952e2bb62bcb17681d79b53f8efabdccdf`.

## Protokół

Symulacje używają rzeczywistego `Game`: serwerowych rzutów, AI, kolizji,
przeciwników, kosztów, odnowień i ekonomii akcji. Nie kopiują matematyki walki.
Każda walka ma początkowy ekwipunek, pełne HP/manę, brak specjalizacji i atutów,
reakcję na zapowiedź ataku po 250 ms i najwyżej jedną miksturę zdrowia.
Ziarna RNG to 0–39, krok symulacji 50 ms, limit walki 90 s.
Bazowe cechy nie są zmieniane: łowca ma Zręczność 16 i Mądrość 14, druid
Mądrość 16. Benchmark nie wydaje punktów ASI ani nie optymalizuje ekwipunku.

`before_starter_level3.json` to 320 walk wykonanych w osobnym worktree na bazie.
Powtórzenie tego samego benchmarku po zmianach sprawdza, czy niewybrane nowe
zdolności zachowują wcześniejszy przebieg istniejących postaci.

```sh
python tools/balance_starter_bosses.py --trials 40 --level 3 --output docs/qa_class_choices/after_starter_level3.json
python tools/balance_class_choices.py --trials 40 --output docs/qa_class_choices/choices.json
```

Nowy benchmark porównuje 16 profili na obu bossach (1280 walk):

- Łowca, poziom 3: łuk bez stylu, Łucznictwo, Druidic Warrior z Gwiaździstym
  ognikiem, Druidic Warrior z Ciernistym biczem. Każdy utrzymuje Znak łowcy.
  Wybrane sztuczki to Ognik i Bicz; każdy profil czarujący używa jednego z nich.
- Druid, poziomy 7 i 15: Ognik bez wyboru / Potężne sztuczki; laska z Shillelagh
  bez wyboru / Pierwotne uderzenie; Dziki kształt wilka bez wyboru / Pierwotne
  uderzenie. Druid poza przemianą leczy się Słowem uzdrawiającym poniżej 60% HP.
  Typ dodatkowych obrażeń Pierwotnego uderzenia to zimno.

Pary druida mają identyczną strategię i te same początkowe ziarna RNG. Porównanie
sztuczek łowcy z łukiem obejmuje również zmianę sposobu atakowania, nie samą
premię stylu. Dodanie kości lub inne zakończenie walki zmienia kolejne pobrania
z RNG, dlatego porównanie nie oznacza identycznych poszczególnych rzutów.

## Ograniczenia

Starterowi bossowie są przeznaczeni dla poziomu 3. Walki druida na 7 i 15
potwierdzają działanie nowych opcji na znanym przeciwniku, a nie docelową
trudność późniejszych lokacji. Nie uzasadniają osłabienia całej klasy.

Kontroler trzyma dystans do 170 jednostek i nie stosuje idealnego kite'owania.
Zwiększony zasięg Potężnych sztuczek na 15 jest sprawdzany testami regresyjnymi;
benchmark nie wykorzystuje go do ostrzału przeciwnika spoza jego zasięgu.
Benchmark nie zastępuje testów wyboru, zapisu, odporności, krytyków, PvP,
dodatkowego ataku dwiema broniami ani reakcji obronnych.

## Baza przed zmianą

Wszystkie 320 walk zakończyły się zwycięstwem. Średni czas w sekundach:

| Boss | Wojownik | Łowca | Czarodziej | Druid |
|---|---:|---:|---:|---:|
| Szkielet bez głowy | 28,66 | 21,63 | 13,32 | 28,59 |
| Łucznik starej wieży | 26,96 | 20,10 | 12,33 | 26,50 |

## Niezmienione postaci po zmianie

`after_starter_level3.json` zawiera kolejne 320 walk. **Całe raporty są
identyczne**: nie zmienił się żaden wynik pojedynczej walki, czas, HP, mana,
użycie mikstury, liczba specjalnych ataków ani podsumowanie. Zestawienie
`baseline_comparison.json` potwierdza 0 zmienionych walk.

Oznacza to, że nowe wybory nie wzmacniają automatycznie postaci, które jeszcze
ich nie wybrały.

## Wyniki nowych wyborów

`choices.json`: **1280 walk, 1279 zwycięstw, 0 przekroczeń czasu**. Każdy wiersz
poniżej obejmuje po 40 walk na bossa. Średnia uwzględnia wszystkie próby.

### Łowca, poziom 3

| Strategia | Szkielet: wygrane / czas | Łucznik: wygrane / czas |
|---|---:|---:|
| Łuk, bez stylu | 40/40 · 21,63 s | 40/40 · 20,10 s |
| Łuk, Łucznictwo | 40/40 · 19,65 s | 40/40 · 17,82 s |
| Druidic Warrior, Gwiaździsty ognik | 39/40 · 34,64 s | 40/40 · 34,74 s |
| Druidic Warrior, Ciernisty bicz | 40/40 · 36,73 s | 40/40 · 33,79 s |

Łucznictwo poprawia celność bez zmiany kości obrażeń ani zużycia many.
Sztuczki są darmową alternatywą: zachowują pełne 60 many, lecz na poziomie 3
przy bazowej Mądrości 14 mają niższą skuteczność niż łuk korzystający ze
Zręczności 16 i płaskiej premii do obrażeń. Nie otrzymują Elemental Fury druida.
Przy niezmienionej strategii wymagały 15/20 mikstur przeciw Szkieletowi i 18/12
przeciw Łucznikowi (Ognik/Bicz), wobec 2/1 dla Łucznictwa. Jedyna porażka to
Ognik przeciw Szkieletowi, ziarno 33. To jawny koszt wyboru magii na tym buildzie,
nie przesłanka do zmiany bazowej siły łowcy ani dopisania premii spoza zasad.

### Druid: identyczna strategia przed wyborem i po wyborze

| Poziom | Strategia / wybór | Szkielet: bez → z Furią | Łucznik: bez → z Furią |
|---|---|---:|---:|
| 7 | Ognik / Potężne sztuczki | 22,09 → 15,99 s | 20,26 → 15,22 s |
| 7 | Shillelagh / Pierwotne uderzenie | 22,95 → 15,55 s | 22,67 → 15,04 s |
| 7 | Wilk / Pierwotne uderzenie | 38,45 → 20,15 s | 35,74 → 19,73 s |
| 15 | Ognik / Potężne sztuczki | 14,38 → 11,33 s | 13,39 → 10,72 s |
| 15 | Shillelagh / Pierwotne uderzenie | 19,28 → 9,52 s | 19,80 → 10,80 s |
| 15 | Wilk / Pierwotne uderzenie | 35,20 → 12,86 s | 33,43 → 11,78 s |

Wszystkie warianty druida wygrały 40/40 walk na każdym bossie bez mikstur.
Wzmocnienie działa dla wybranej ścieżki: Potężne sztuczki zwiększają obrażenia
sztuczki, a Pierwotne uderzenie wzmacnia broń i Dzikie kształty. Różnice między
poziomami 7 i 15 obejmują także zwykły rozwój postaci i kości sztuczek.
Szybkie zwycięstwa na 15 są oczekiwane przeciw bossom poziomu 3; nie użyto ich
do osłabiania klas ani zmiany bossów.
