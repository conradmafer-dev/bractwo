# Weryfikacja klas — UI_35

Zmiana dotyczy stylu łowcy na poziomie 2 i Elemental Fury druida na poziomie 7,
ulepszanego na 15. Wybory są niezależne od ASI/atutów i kręgów/specjalizacji.
Obecne kwalifikujące się postacie dostają przypomnienie po zalogowaniu; nowe
awanse mają osobne wiersze i odsyłacze w panelu awansu.

## Zakres działania

Dziesięć stylów ma rzeczywiste warunki sprzętu, rzuty i akcje. Druga lekka broń
zużywa akcję dodatkową po ataku inną lekką bronią w tej turze. Rzucanie przenosi
konkretną instancję z plecaka do zapisanego, prywatnego miejsca odzyskania;
ponowne wczytanie nie wytwarza zastępczej broni. Unarmed Fighting obejmuje
chwyt, ucieczkę, ciągnięcie i obrażenia na początku własnej tury. Protection i
Interception dzielą istniejącą reakcję z innymi zdolnościami i respektują
widoczność, drużynę, odległość, PvP, odporności i osobne komponenty obrażeń.

Druidic Warrior wybiera dwie z **pięciu działających w Bractwie** sztuczek:
Shillelagh, Produce Flame, Thorn Whip, Starry Wisp i Guidance. Pozostałe sztuczki
z pełnego katalogu D&D nie zostały dodane w tym zadaniu. Wybrane sztuczki używają
Mądrości i własnych progów 5/11/17; jedna może zostać wymieniona po nowym poziomie.
Łowca nie otrzymuje przez ten wybór Elemental Fury.

Potent Spellcasting dodaje Mądrość do obrażeń sztuczek druida, w tym sztuczek
uzyskanych z kręgu. Primal Strike dodaje 1k8/2k8 po trafieniu bronią lub atakiem
Dzikiego kształtu, raz we własnej turze, z osobnym typem i odpornością; krytyk
podwaja kości. Gracz wybiera żywioł i może odłożyć użycie na późniejsze trafienie.
Ulepszenie Potent wydłuża o 300 stóp kwalifikujące się sztuczki i widoczność
celów; nie wydłuża zasięgu Self/Touch, w tym Produce Flame.

Bractwo zachowuje własną trzysekundową turę, manę i dotychczasowe podstawowe
zasięgi istniejących broni/czarów. Nowe reakcje/ślepowidzenie/chwyt i rzucanie
stosują przelicznik 6,4 jednostki na stopę. Nie zmieniono bazowej siły klas,
bossów ani innych omawianych zdolności (Roving, Wild Resurgence).

## Testy

```sh
PYTHONPATH=tests:. python -m unittest test_ranger_styles test_elemental_fury test_style_weapon_actions test_style_weapon_game test_class_choice_advancement -q
node --test tests/test_ranger_elemental_ui.cjs tests/test_dnd_levels_ui.cjs tests/test_fighter_0813.cjs tests/test_inventory_windows.cjs
python -m compileall -q server tools/balance_class_choices.py
git diff --check
```

**67/67 testów serwera i 35/35 testów UI zaliczono** (w tym 11 nowych testów UI).

Testy używają rzeczywistego Game, zapisów SQLite, snapshotów właściciela,
serwerowych akcji, rzutów, PvE/PvP, odporności, krytyków i DOM wysyłającego
właściwe pakiety. Obejmują też historyczny kontekst awansów, jednorazowe wybory,
przypomnienie po powrocie i zachowanie limitów po ponownym odczycie.

Wszystkie skrypty Godot przeszły parser gdparse 4.5. Brak silnika Godot
uniemożliwił uruchomienie i zbudowanie APK. Nie wykonano wizualnego testu w
przeglądarce: brak lokalnego Chromium, a pobieranie binariów kończyło się
nieprawidłowym pustym ZIP. Panel i menu sprawdzono testami DOM; CSS przejrzano.

## Starsze testy

Szersze uruchomienie sześciu czytelnych modułów na zmianie i osobnym checkout
`f6e862952e2bb62bcb17681d79b53f8efabdccdf` dało identyczny wynik: **148 testów,
138 zaliczonych, 7 niepowodzeń i 3 błędy**. Dotyczą starych oczekiwań odnowień
Second Wind/Action Surge, dawnego automatycznego wzrostu Siły, starego zakupu
u kupca i dawnych progów mikstur:

- FighterData.test_second_wind_free_and_sixty_seconds
- FighterData.test_surge_is_free_not_a_spell_circle
- FighterGame.test_pvp_graze_resistance_and_protection
- FighterGame.test_second_wind_zero_mana_shared_bonus_and_sixty_cooldown
- FighterGame.test_second_wind_cooldown_survives_save
- FighterGame.test_surge_additional_attack_does_not_reset_other_actions
- FighterGame.test_surge_cooldown_persistent_and_main_attack_still_available
- FighterGame.test_shop_buy_actual_weapon_and_persistent_inventory
- FighterGame.test_surge_extra_attacks_all_levels
- Supplies.test_unowned_or_level_locked_bind_is_rejected

Ich nie poprawiano. Cztery starsze moduły z bajtami NUL pozostawiono bez zmian.
Siedem historycznych niepowodzeń wskazanych w pierwotnym raporcie UI33 również
pozostawiono poza zakresem. Zaktualizowano tylko związane z zadaniem oczekiwanie
karty stylu wojownika, aby uwzględniało kartę łowcy.

Wyniki 320 porównawczych i 1280 dodatkowych walk opisuje README tego katalogu;
raporty zawierają wszystkie pojedyncze walki, ziarna i użycie zasobów.

## Źródła zasad

- [D&D 2024 Basic Rules — klasy](https://www.dndbeyond.com/sources/dnd/br-2024/character-classes)
- [D&D 2024 Basic Rules — atuty](https://www.dndbeyond.com/sources/dnd/br-2024/feats)
- [D&D 2024 Basic Rules — czary](https://www.dndbeyond.com/sources/dnd/br-2024/spell-descriptions)
- Pozostałe style: licencjonowany katalog Player's Handbook 2024 w Roll20
  (Blind Fighting, Interception, Protection, Thrown Weapon Fighting,
  Two-Weapon Fighting, Unarmed Fighting).
