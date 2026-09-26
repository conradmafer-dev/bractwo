# Protokół i reguły wojownika 0.8.13

## Komendy klienta

```json
{"type":"fighting_style","style":"dueling"}
{"type":"fighting_style","style":"defense"}
{"type":"fighting_style","style":"great_weapon"}
{"type":"weapon_grip","grip":"one"}
{"type":"weapon_grip","grip":"two"}
{"type":"cast","spell_id":"action_surge","enemy_id":"world_..."}
```

Zryw obsługuje też `target_id` gracza albo bieżące zaznaczenie. Wciąż obowiązuje wykluczenie jednoczesnego enemy_id i target_id. Zryw kieruje się do wspólnego handlera walki bronią, z odrębnym odnowieniem, nie zeruje zegara głównej akcji. Pierwszy wybór i zmiana stylu wymagają żyjącego wojownika poza walką; zmiana już wybranego stylu wymaga dodatkowo mistrza profesji w osadzie. Malformed/unknown values nie zmieniają stanu. Komendy nie przyjmują premii ani obrażeń wyliczonych przez klienta.

Nowy slot `equipment.shield` przechowuje UID rzeczywistego przedmiotu w inventory. Zwykłe equip/unequip/sell i ograniczenia klas odnoszą się również do tarczy. Sprzęt dwuręczny ją odkłada. Broń wszechstronna ma pole `versatile_dice` oraz per-postaci `weapon_grip`. Usunięta tarcza nadal należy do gracza.

## Dane

W zapisie: `fighting_style`, `weapon_grip`, `fighter_rules_version=1`. Jednorazowa migracja dodaje zestaw obronny, nie kasuje UID, depozytu ani broni, nie powtarza się po relogu. Wspólne `spell_cooldowns` zapisuje bezwzględne terminy drugiego oddechu/Zrywu, jak pozostałe zdolności.

W prywatnej `character_sheet.fighter`: wybory (id/nazwa/opis/ikona/warunek), `pending`, wybrany styl i `style_active`, trzy opanowane mistrzostwa i aktywne z obecną bronią, chwyt i możliwość jego zmiany oraz realna premia tarczy. W publicznym aktorze tylko `weapon_type`, `two_handed`, `shield_equipped` do rysowania, bez UID czy listy ekwipunku.

`action_surge` jest zdolnością z `class_levels.knight=5`, `circle=0`, `feature=true`, `kind=surge`, `action=extra`, mana0/cooldown90. Wlicza się do rzeczywistych użyć pod F. Drugi oddech pozostaje w tej samej bibliotece i ma mana0/cooldown60/actionbonus. Prawidłowe własne skróty nie są przestawiane, nowe zdolności uzupełniają wolne pola.

## Obrażenia i warunki

- GWF: rzeczywiście wyrzucone kości broni zostają w `raw_damage_rolls`, skuteczne wartości w `damage_rolls`. Reguła dotyczy pojedynczych kości, także krytycznych, nie stałych modyfikatorów i nie leczenia/czarów.
- Graze: `hit=false`, `graze=true`, zerowe kości, wyłącznie nieujemny modyfikator cechy ataku. Ma wspólną ścieżkę obrażeń i odporności PvP. Nie uruchamia logiki trafienia. Efekty, log i tekst nad celem ujawniają Draśnięcie zamiast sugerować brak obrażeń.
- Sap: dotyczy pojedynczego następnego rzutu ataku; nie jest konsumowany przez rzut obronny lub obrażenia obszarowe bez rzutu ataku. Do trzech sekund, nie kumuluje utrudnień; ułatwienie i utrudnienie nadal wzajemnie się znoszą.
- Topple: po trafieniu osobny CON save. Przy porażce prone do1,5s; zerowa prędkość ruchu, utrudnienie własnych ataków, ułatwienie trafienia z bliska/utrudnienie z daleka. Nie wymaga koncentracji. Serwer prowadzi również źródło wrogiego efektu PvP.
- Domyślnie opanowane tylko longsword, greatsword, maul. Nie przypisujemy tych właściwości automatycznie każdemu toporowi czy jednoręcznemu młotowi. Warianty mieczy zachowują oryginalne kości/magiczną premię.

Efekty wizualne to `fighter_sap`, `fighter_graze`, `fighter_topple`, `fighter_surge`. Podtrzymywane oznaczenia wynikają ze statusów, nie timerów niezależnych od serwera. Nowe zasoby SVG są identyczne w klientach, generowane z `tools/generate_fighter_art.py`.

## Odniesienia i własne reguły

Zweryfikowane 25.09.2026 oficjalne źródła:
- https://www.dndbeyond.com/sources/dnd/br-2024/character-classes — Fighter: pierwsze cechy, Second Wind, Action Surge.
- https://www.dndbeyond.com/sources/dnd/br-2024/equipment — właściwości broni, długi/dwuręczny miecz, maul, kolczuga i tarcza.
- https://www.dndbeyond.com/sources/dnd/br-2024/feats — Defense, Great Weapon Fighting.

Progi poziomów Bractwa: drugi poziom wzorca daje poziom5 gry. Stałe dodatkowe ataki pozostają20/50/95. W Bractwie odnowienia60/90s zastępują użycia na odpoczynek. Nie dodano dodatkowego ładunku Zrywu na wysokim poziomie ani innych omawianych w podręczniku, lecz niezamówionych cech. Wstawanie automatyczne po1,5s zastępuje ręczne wydanie połowy ruchu. Początkowe trzy typy mistrzostwa są stałym zestawem tej aktualizacji, nie pełnym katalogiem wyborów. Zryw udostępnia akcję ataku, nie nowy interfejs dowolnej akcji. Ceny i pakiet startowy są balansem Bractwa. Nowe polskie streszczenia i grafika są własne; nie kopiowano pełnych opisów podręcznikowych.
