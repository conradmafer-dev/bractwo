# Balans bossów początkowych — 4 października 2026

Baza: `cf1e946c7885b478b2d324ddb096557033756216` (`podziemia`).
Pod koniec prac `main` przesunął się na `b8e18bb5e2a04a8e9f58c0f514fa1ec22447992d`
(wyłącznie dodanie tagu Google Ads w `web/index.html`). Gałąź zmian zawiera
ten commit; kod walki i pomiary bazowe pozostają zgodne z `cf1e946`.
Jedyny zmieniony plik wykonywalnej gry: `server/starter_adventures.py`.
Klasy, czary, ekwipunek, nagrody, dostęp do skrzyń i pozostałe potwory zachowują swoje reguły.

## Przyczyna i zmiana

Magiczny pocisk trafia automatycznie, więc omija KP. Przy 32–36 HP czarodziej
może zakończyć spotkanie, zanim trzeba ponownie odpowiedzieć na specjalny atak.
Ataki bronią wymagają rzutu, a łuk w zwarciu ma utrudnienie. Szkielet stale
skracał dystans, również w 0,8 s przerwy od atakowania po zamachu.
Wojownik i druid dodatkowo tracą czas na odejście z koła i powrót do zwarcia.

| Parametr | Szkielet: przed → po | Łucznik: przed → po |
| --- | --- | --- |
| HP | 36 → 64 | 32 → 60 |
| KP | 12 → 8 | 12 → 8 |
| Zwykły atak: odstęp | 3,6 → 4,2 s | bez zmian |
| Prędkość | 76 → 68 | bez zmian |
| Zapowiedź specjalnego ataku | 1,45 → 1,65 s | 1,65 s, bez zmian |
| Promień zamachu | 110 → 80 | nie dotyczy |
| Przerwa po specjalnym ataku | 0,8 s tylko ataki → 1,8 s ataki i ruch | 0,8 s tylko ataki → 1,5 s ataki i ruch |

Większa pula HP ogranicza pomijanie mechanik serią czarów. Niższa KP pomaga
postaciom opartym na rzutach ataku, bez odporności wymierzonych w konkretny
czar lub klasę. Szkielet daje więcej czasu na odzyskanie dystansu. Mniejsze
koło skraca drogę powrotną do walki wręcz. Łucznik zachowuje stałą linię
strzału, osłony filarami i brak automatycznej ucieczki przed wojownikiem.

Obrażenia specjalnego ataku nadal rozstrzygają się na końcu zapowiedzi.
Dopiero potem trwa przerwa; nie wydłużamy niewidocznie czasu do trafienia.
Dotychczasowe dłuższe terminy gotowości nie są skracane.

## Powtarzalny pomiar

Oryginalny raport UI33 pozostał niezmieniony. Repozytorium nie zawierało jego
kontrolera ani listy ziaren. **Poniższe wyniki przed/po pochodzą z nowego,
jednakowego kontrolera na obu wersjach**, a nie z zestawienia starego raportu
z nową symulacją. Nowa próba bazowa daje inne liczby niż historyczne 9,2/8,6 s
czarodzieja i 36/40 łowcy; nie twierdzimy, że odtworzono tamten eksperyment.

`tools/balance_starter_bosses.py` uruchamia prawdziwe akcje, obrażenia, AI,
kolizje i `Game.step(0.05)` oraz `process_player_actions`. Każda próba tworzy
nowy Game z bazą SQLite w pamięci i osobnymi generatorami losowymi walki/łupu.
W arenie pozostaje jeden boss na oryginalnej pozycji; geometria nie jest zmieniana.

- 40 prób na parę boss/klasa, ziarna 0–39, poziom 10, pełne HP/mana.
- Początkowy ekwipunek, bez nagród bossów, wybranych atutów, specjalizacji i towarzyszy.
- Start 180 jednostek na południe od szkieleta, 230 od łucznika, te same miejsca dla klas.
- Wojownik: broń i Drugi oddech poniżej 65% HP. Łowca: łuk i Znak łowcy.
- Druid: Shillelagh, broń, Leczące słowo poniżej 60% HP.
- Czarodziej: Magiczny pocisk z domyślnym automatycznym kręgiem, niższy krąg
  przy braku many, potem Ognisty pocisk. To kosztowna strategia szybkich obrażeń.
- Każdy używa najwyżej jednej mikstury poniżej 45% HP.
- Reakcja na zapowiedzi po 0,25 s; ruch przez kolizje serwera, bez teleportów.
  Postacie dystansowe utrzymują pozycję między zapowiedziami, bez idealnego kitingu.
- Limit 90 s; wyniki obejmują zwycięstwa, porażki i przekroczenia limitu.
  `mean_seconds` dotyczy wszystkich prób, `mean_win_seconds` tylko zwycięstw.
  Pozostałe HP/mana to wartości bezwzględne. `potion_used` to liczba walk z miksturą.
  `mean_specials` liczy zaobserwowane rozpoczęte zapowiedzi, także przerwane śmiercią.

| Boss | Klasa | Zwycięstwa przed → po | Średni czas przed → po | Walki z miksturą przed → po |
| --- | --- | --- | --- | --- |
| Szkielet bez głowy | Wojownik | 40/40 → 40/40 | 20,33 → 28,66 s | 0 → 0 |
| Szkielet bez głowy | Łowca | 40/40 → 40/40 | 21,02 → 21,63 s | 14 → 4 |
| Szkielet bez głowy | Czarodziej | 40/40 → 40/40 | 6,15 → 13,32 s | 0 → 0 |
| Szkielet bez głowy | Druid | 40/40 → 40/40 | 21,85 → 28,59 s | 7 → 4 |
| Łucznik starej wieży | Wojownik | 40/40 → 40/40 | 18,96 → 26,96 s | 0 → 0 |
| Łucznik starej wieży | Łowca | 40/40 → 40/40 | 15,15 → 20,10 s | 2 → 2 |
| Łucznik starej wieży | Czarodziej | 40/40 → 40/40 | 5,85 → 12,33 s | 0 → 1 |
| Łucznik starej wieży | Druid | 40/40 → 40/40 | 17,58 → 26,50 s | 0 → 4 |

Stosunek najdłuższego do najkrótszego średniego czasu spada **3,55 → 2,15**
w krypcie i **3,24 → 2,19** w wieży. Czarodziej pozostaje najszybszy, ale
kończy średnio z 0,5/140 i 2/140 many; wojownik zachowuje wytrzymałość,
łowca korzysta z okien na strzelanie, druid z leczenia. Czasy nie są równe:
to łatwe spotkania solo z różnymi kosztami zasobów, a nie jednakowy DPS klas.

Pełny rejestr głównej próby: `before_level10.json`, `after_level10.json`.
Dodatkowe serie kontrolne opisuje `sensitivity.json` (parametry każdej serii
i podsumowanie wszystkich ośmiu par): niezależne ziarna 1000–1039 na poziomie
10 dały 320/320 zwycięstw; poziomy 8 i 12 po 160/160. Próba bez reakcji na
zapowiedzi na poziomie 10 dała 155/160, z większym zużyciem mikstur.
To pomiary tej strategii, a nie prognoza
wszystkich graczy. Nie obejmują przemian druida, wyspecjalizowanych buildów,
gry grupowej, opóźnień sieci ani ręcznego testu na telefonie.

## Odtwarzanie

```bash
python tools/balance_starter_bosses.py --trials 40 --output /tmp/after.json
git worktree add --detach /tmp/bractwo-base cf1e946c7885b478b2d324ddb096557033756216
cp tools/balance_starter_bosses.py /tmp/bractwo-base/tools/
cd /tmp/bractwo-base
python tools/balance_starter_bosses.py --trials 40 --output /tmp/before.json
```

Dalsze próby na poprawionej wersji:

```bash
python tools/balance_starter_bosses.py --trials 40 --seed-start 1000 --output /tmp/holdout.json
python tools/balance_starter_bosses.py --trials 20 --seed-start 2000 --level 8 --output /tmp/level8.json
python tools/balance_starter_bosses.py --trials 20 --seed-start 2000 --level 12 --output /tmp/level12.json
python tools/balance_starter_bosses.py --trials 20 --seed-start 2000 --no-dodge --output /tmp/no-dodge.json
```

## Regresje

Nowy `tests/test_starter_boss_balance.py` sprawdza koniec zapowiedzi i pojedyncze
rozliczenie obrażeń, zatrzymanie ruchu i ataków w przerwie, wznowienie po niej,
zachowanie dłuższych cooldownów oraz brak dodatkowej przerwy zwykłej strzały.
Osiem deterministycznych ziaren na parę pilnuje zwycięstw, czasu do 35 s,
średnio co najmniej 1,5 zapowiedzi i stosunku czasów klas najwyżej 2,5.
Skopiowanie tych testów na bazowy commit daje oczekiwane niepowodzenia
przerwy/rozstrzygnięcia i balansu obu bossów (6 nieudanych podprzypadków).

```bash
python -m unittest discover -s tests -p 'test_starter_boss_balance.py' -v
python -m unittest discover -s tests -p 'test_starter_adventures_ui33.py' -v
node --test tests/test_starter_adventures_ui33.cjs
```

Szersze porównanie obejmuje ponadto całe moduły `test_magic_items_ui19`,
`test_general_feats_0818`, `test_health_potions_0818`, `test_ui19_core_integration`.
Siedem historycznych niepowodzeń odtworzono przed i po; nie modyfikowano
tych testów ani powiązanych z nimi reguł:

1. `test_mithral_removes_strength_and_stealth_penalties`
2. `test_passives_require_a_point_and_cannot_be_repeated`
3. `test_repeatable_asi_is_serializable_and_caps_each_allocation`
4. `test_catalog_rewards_and_authored_loot_only_expose_health`
5. `test_01_local_boat_payment_destination_home_and_remote_rejection`
6. `test_02_nearest_merchant_stock_is_authoritative`
7. `test_05_ocean_migration_only_moves_legacy_revision`

Łącznie: **67 testów Pythona, 60 PASS i te same 7 FAIL**. W tym wszystkie
34 testy bossów/UI33 przechodzą. Test JavaScript UI33: PASS. Kontrola składni
zmienionych plików Pythona i `git diff --check`: PASS. Zapis: `validation.json`.

Nie uruchamiano pełnego historycznego zestawu projektu ani nie wdrażano na Railway.
