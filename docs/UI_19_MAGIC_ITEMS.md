# UI 19: magiczne wyposażenie

Podstawa: [SRD 5.2.1](https://www.dndbeyond.com/srd), [aktualny PDF SRD](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf), [katalog przedmiotów 2024](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items-a-z), [zestrojenie](https://www.dndbeyond.com/sources/dnd/br-2024/equipment#Attunement), [reguły przedmiotów i mikstur](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items).

Moduł `server/magic_items.py` dodaje 16 szablonów bez wymyślonych premii zależnych od poziomu. Wartości SRD to 400 szt. złota za Uncommon i 4000 za Rare, powiększone o koszt zwykłej broni, zbroi lub tarczy. Dokładna wartość znajduje się w `srd_value_gp`. Ponieważ gra obsługuje całkowite sztuki złota, kupiec zaokrągla zakup w górę, a skup w dół; kostur +1 ma wartość SRD 400,2, cenę zakupu 401 i skupu 400. Szablony nie mają bram poziomu D&D. Wszystkie nowe ikony są odrębnymi SVG w `web/assets/equipment` i `client/assets/equipment`.

| ID | Efekt | Zestrojenie |
| --- | --- | --- |
| `ring_protection` | +1 KP i do wszystkich rzutów obronnych | Tak |
| `ring_swimming` | Szybkość pływania 40 stóp; bez oddychania pod wodą | Nie |
| `ring_free_action` | Brak dodatkowego kosztu trudnego terenu; magia nie obniża szybkości ani nie powoduje paraliżu lub spętania | Tak |
| `ring_warmth` | Redukcja obrażeń Cold o 2k8; ochrona przed skrajnym zimnem | Tak |
| `ring_resistance_fire`, `_cold`, `_poison`, `_lightning`, `_necrotic` | Odporność na jeden określony typ obrażeń | Nie |
| `magic_longsword_1`, `magic_longbow_1`, `magic_quarterstaff_1` | +1 do ataku i obrażeń tej broni | Nie |
| `magic_shield_1` | +3 KP łącznie ze zwykłą premią tarczy | Nie |
| `magic_chain_mail_1` | Kolczuga KP 17 | Nie |
| `adamantine_chain_mail` | Trafienia krytyczne przeciw noszącemu stają się zwykłymi trafieniami | Nie |
| `mithral_chain_mail` | Kolczuga bez wymogu Siły 13 i bez utrudnienia Skradania od materiału zbroi | Nie |

Premie do obrażeń broni nie zwiększają obrażeń czarów ani naturalnych ataków przemiany. Pierścień swobody odróżnia magiczne efekty od fizycznego chwytu i niemagicznego paraliżu. Pierścień pływania zachowuje wymagania oddechu. Naturalne 20 nadal trafia noszącego adamantyn; usuwa się dodatkowe kości krytyka przed obrażeniami dodatkowymi. Mithral nie nadaje wyszkolenia w ciężkich pancerzach. Przedmioty scalone z postacią podczas przemiany nie dają premii.

Przeliczenie szybkości pływania korzysta z istniejącej skali ruchu świata, tak jak szybkości form: 40/30 bieżącej szybkości bazowej. Nie zmienia poziomowego wzrostu szybkości poruszania się Bractwa. Jest to jawna adaptacja świata, nie dodatkowa cecha przedmiotu D&D.

## Zestrojenie i integracja

Zestrojenie wymaga pełnego krótkiego odpoczynku z konkretnym przedmiotem w plecaku. Obowiązuje limit trzech więzi i zakaz zestrojenia dwóch kopii tego samego przedmiotu. Zdjęcie pierścienia nie usuwa więzi. Śmierć ją kończy. Przedmiot oddalony o ponad 100 stóp przez 24 godziny również traci więź; śledzone są ostatnia pozycja i początek oddalenia. Przerwanie odpoczynku nie przyznaje zestrojenia. Żądanie zakończenia więzi także wymaga krótkiego odpoczynku.

SRD zabrania identyfikacji przedmiotu i zestrojenia z nim podczas tego samego odpoczynku; nie zabrania zwykłych korzyści odpoczynku. Katalog gry już ujawnia właściwości przedmiotów. Rozpoczęcie zestrojenia nie wydaje automatycznie kości wytrzymałości (`recover=False`). Krótki odpoczynek trwa istniejące 10 sekund gry. Czas 24 godzin jest odwzorowany jako 43 200 sekund według istniejącej skali czasu. Jedno miejsce na pierścień pozostaje jawną regułą ekwipunku Bractwa, a nie limitem D&D.

Pola trwałe postaci: `magic_items_version` i `magic_attunements`, lista rekordów `{uid, template, away_since, last_position}`. Cel odpoczynku mieści się w nietrwałym `rest_state.magic_item`.

- `configure(ITEMS)` wywołać po wszystkich wcześniejszych konfiguratorach przedmiotów.
- `migrate(player, ITEMS)` odświeża stare egzemplarze, zachowując UID, template i wyposażenie; `maintain(player, now)` aktualizuje więzi przy zapisie, wczytaniu i kroku świata.
- Komenda `{"type":"magic_item","action":"attune" lub "unattune","uid":"..."}` trafia do `await magic_items.command(game, player, data)`.
- Po ukończonym odpoczynku: `magic_items.finish_rest(player, rest)` przed zapisem; zwrócony tekst pokazuje rezultat.
- Po śmierci: `magic_items.on_death(player)`.
- Redukcja Cold: `magic_items.reduce_damage(player, amount, kind, rng)` po redukcjach stałych, przed odpornością. Składniki Cold jednego źródła obrażeń należy zsumować przed jednym rzutem 2k8.
- `metadata()` udostępnia katalog. `character_sheet.magic_items` zawiera limit, użycie limitu, stan każdego UID, wymaganie zestrojenia, przyczynę blokady i bieżący cel odpoczynku.

Migracja dawnych pierścieni zachowuje ich identyfikatory dla wcześniejszych nagród i tabel łupów: miedziany otrzymuje właściwości pływania, dotychczasowe odporności zachowują swój typ, pozostałe stają się pierścieniem ochrony wymagającym zestrojenia. Migracja nie przyznaje automatycznie więzi. Dawne szanse łupu wymagają oceny razem z nową ekonomią; wartość Rare nie powinna być traktowana jak cena starej zwykłej ozdoby.

## Mikstury i weryfikacja

W aktualnym SRD picie **każdej** mikstury lub podanie jej drugiej istocie wymaga akcji dodatkowej. Oleje mogą mieć inne czasy zastosowania wskazane w ich opisie. Rozróżnienie „tylko lecznicza jako akcja dodatkowa” nie opisuje pełnych obecnych zasad DMG 2024. Rdzeń mikstur, interfejs i handel należą do integracji głównej aktualizacji.

`tests/test_magic_items_ui19.py`: **13/13 sprawdzonych** w dwóch uruchomieniach: pierwsze 12 testów (3,740 s) oraz dodatkowy test kwot całkowitych i utraty kontaktu z przedmiotem (0,244 s). Testy sprawdzają efekty, krytyki, przemiany, naturalny lot potworów, magiczne i fizyczne ograniczenia ruchu, przerwanie zestrojenia, limit, duplikaty, oddalenie, śmierć i migrację. W przeglądzie rdzenia potwierdzono grupowanie obrażeń jednego typu przed redukcją ciepła oraz wywołania migracji, zapisu, utrzymania więzi, śmierci i zakończenia odpoczynku. Końcową integrację interfejsu i świata weryfikuje główny zestaw UI 19.

Dodatkowe podłączenie Nieumarłej Wytrwałości przekazuje znacznik `critical` z broni, ataków czarów i towarzyszy do `AdventureGame.environment_damage_enemy`. Bazowy `EnvironmentGame` przyjmuje ten parametr również bez domieszki przygodowej.

W `continent_world.refresh_shops` wszystkie **16/16** nowych identyfikatorów ma bezpośrednią drogę zakupu. Sprzęt łowiecki i natury trafia do Brzeziny, broń i pancerze do Złotego Portu i Bazaltowej Strażnicy, akcesoria wodne do Solnej Przystani i Przełomu Rzeki, ochrona przed zimnem do Mroźnej Przystani, a przed ogniem do Żarowego Nabrzeża i Popielnego Portu. Przystań Cieni sprzedaje pierścienie związane z trucizną, energią nekrotyczną i swobodą. Dodatki nakładane są po `SHOP_REQUESTS` przy każdym odświeżeniu, więc ponowne zbudowanie świata ich nie usuwa. Niezależnie część przedmiotów pozostaje nagrodami nowych zadań.

Krótka kontrola dodatkowej integracji: poprawna składnia pięciu zmienionych modułów, komplet 16 identyfikatorów w asortymencie oraz stabilność powtórnego `refresh_shops` w izolowanym modelu kupców. Nie uruchamiano szerokiej regresji ani kolejnej inicjalizacji pełnego świata. Szczegóły: `docs/qa_0.8.18/ui19/magic_items_integration.json`.
