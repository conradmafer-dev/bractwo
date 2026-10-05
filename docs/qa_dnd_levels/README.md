# UI34 — poziomy i doświadczenie D&D

Podstawa: `88d24b5f9614e5c53829a7501f6465c310445063`. Nowe poziomy zastępują dawną skalę: 1 → 1, 5 → 2, 10 → 3, 15 → 4, 20 → 5, 95 → 20. Rozwój pozostaje nieograniczony zgodnie z decyzją użytkownika.

## Doświadczenie

Poziomy 1–20 używają skumulowanych progów z [oficjalnych D&D Free Rules 2024 — Character Advancement](https://www.dndbeyond.com/sources/dnd/br-2024/creating-a-character#LevelAdvancement), zgodnych z SRD 5.2.1:

`0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000`.

Powyżej 20. poziomu obowiązuje rozszerzenie Bractwa: 50 000 XP za kolejny poziom (21: 405 000; 22: 455 000). Zdolności klasowe, biegłość i HP zachowują dotychczasowy limit mocy odpowiadający poziomowi D&D 20. Mistrzostwa i dalszy rozwój Bractwa pozostają dostępne.

Interfejs pokazuje skumulowane XP. Pole zapisu/protokołu `xp` nadal oznacza postęp wewnątrz poziomu, a `xp_next` koszt tego przedziału; nowe `xp_total`, `xp_level_start`, `xp_next_total` zapewniają prawidłowe etykiety bez zmiany procentowego paska. Nagrody XP potworów i zadań pozostają bez zmian, więc czas zdobywania poziomów wynika teraz z tabeli D&D.

## Migracja istniejących postaci

`level_rules_version=1` zabezpiecza przed ponowną konwersją. Przy starcie serwera wszystkie konta, także offline, są konwertowane w jednej transakcji SQLite. Pierwotny JSON każdego konta trafia do `level_migration_backups`; ranking jest odbudowywany z nowych zapisów. Błąd migracji wycofuje transakcję.

Postęp pomiędzy dawnymi progami jest przeliczany proporcjonalnie na nowy przedział XP (zaokrąglenie w dół mniejsze niż 1 XP). Przykład: połowa starego przedziału 1→5 daje 150/300 XP na nowym poziomie 1. Postać 23. poziomu staje się postacią 5. poziomu z postępem w kierunku 6.

`legacy_growth_level` zachowuje już zdobyte częściowe HP, manę, odzyskanie many i szybkość. Zwykły rozwój przejmuje te wartości po osiągnięciu kolejnego progu; premia nie nalicza się podwójnie. Ekwipunek, jego UID, wybory atutów, mistrzostwa, zasoby i postęp zadań pozostają zachowane. Stare powiadomienia o pośrednich awansach są archiwizowane w `legacy_level_up_batches`, a gracz otrzymuje jedno powiadomienie o przeliczeniu. Dostępne wybory rozwoju nadal wynikają z osiągniętego poziomu.

Wymagania świata i przedmiotów używają tej samej funkcji `1 + old_level // 5`, minimum 1; przykładowo dawne minimum 8 oznacza nowe minimum 2. Statystyki i nagrody świata powstają przed końcową normalizacją etykiet, dzięki czemu wszystkie 77 typów przeciwników zachowuje parametry walki i łupów. Źródłowe tabele generatorów świata pozostają w dawnych jednostkach; publiczne katalogi i porównania z poziomem gracza korzystają z nowych.

## Weryfikacja

- Końcowy zestaw regresji Python: 71/71 zaliczonych, obejmujący poniższe nowe testy oraz istniejące testy HP, progów klas, ataków i UI33.
- 9 nowych testów progów XP, wielopoziomowych nagród, zachowania częściowych przyrostów, idempotencji, atomowości, kopii zapisów, restartu i rankingu.
- 3 regresje normalizacji świata i aliasów obiektów.
- 48 000 porównań HP, biegłości, sztuczek i dodatkowych ataków z bazową wersją.
- 5791 profili czarów w 252 kombinacjach klas, specjalizacji i poziomów: brak różnic w parametrach walki, HP, manie i odzyskaniu mocy.
- 320 symulacji bossów na nowym poziomie 3: wszystkie wyniki identyczne z wcześniejszym raportem poziomu 10, również czas, HP, mana, mikstury i ataki specjalne. Zobacz `after_level3.json` oraz `balance_comparison.json`.
- 44/44 testy interfejsu Node, w tym 6 nowych regresji XP i poziomów. Historyczny zestaw spellbook ma te same 14 błędów na bazie i po zmianie.
- Lokalne HTTP: `/health`, `/`, `/runtime.js`, `/game.js`, `/sw.js`, `/ranking`; rewizja UI_34 i `level_rules_version: 1`.

Szczegóły porównania zestawów Python i znanych błędów zawiera `validation.json`. Nie naprawiano siedmiu wcześniej wymienionych błędów ani innych historycznych problemów, w tym plików testowych wypełnionych bajtami NUL już na bazowej gałęzi. Klient Godot został zaktualizowany w źródłach; w tym środowisku nie budowano APK/AAB.

Przy ewentualnym wycofaniu wdrożenia nie wystarczy uruchomić starego kodu na nowych numerach poziomów. Należy odtworzyć zgodny zapis z kopii SQLite lub kontrolowanie użyć zachowanych rekordów sprzed migracji, uwzględniając późniejszy postęp graczy.
