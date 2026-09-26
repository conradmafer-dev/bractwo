# Bractwo 0.8.14 — protokół i odniesienia

## Autorytatywne moduły

`equipment_rules.py`: 2 kategorie broni, konkretne rodzaje, dynamiczne wyszkolenia, cztery ogólne atuty, prywatne podglądy. `caster_rules.py`: katalog i progi. `caster_game.py`: kanały rzucania, ścieżka, atuty, formy, chowańce, Alarm i interakcje przyrodnicze. Kontrolę obrażeń wykonują istniejące wspólne moduły walki. Klient nie przesyła własnych kości, bonusów, ceny ani liczby punktów.

Komendy:
```json
{"type":"primal_order","order":"warden"}
{"type":"primal_order","order":"magician"}
{"type":"training_feat","feat":"moderately_armored","ability":"dexterity"}
{"type":"cast","spell_id":"arcane_recovery"}
{"type":"ritual","spell_id":"alarm"}
{"type":"channel_cancel"}
{"type":"cast","spell_id":"wild_shape_cat"}
{"type":"familiar_command","mode":"help"}
{"type":"nature_interact","id":"fox_trail"}
{"type":"weapon_grip","grip":"two"}
```

`training_feat` id: lightly_armored, moderately_armored, heavily_armored, martial_weapon_training. Sprawdź definicję przed generowaniem wyboru: dostępne cechy i wymagania zwraca serwer. Polecenia sowy: follow/help/scout/dismiss. Rytuały mają zamkniętą listę: alarm/find_familiar/speak_with_animals. Koszt składników pobiera dopiero ukończenie kanału. Płatny tryb wybierany przez cast, rytualny przez ritual. Tylko konkretna ścieżka jest ręcznym wyborem na starcie; jej uprawnienia i zdolności klasowe są automatyczne.

## Dane / prywatność / zapis

Prywatne `character_sheet.training`: granted(name/icon/sources), chosen(name/ability/active), points, options(tylko brakujące), levels, armor_penalty, grip/can_change_grip. `character_sheet.caster`: order/order_pending/orders/features/forms/familiar/channel/legacy_medium_grace/recovery_amount. Klasa/wybrana ścieżka dają wyłącznie wyszkolenie; +1 cechy istnieje tylko w aktywnym, faktycznie wybranym ogólnym atucie.

Przedmiot publiczny dla właściciela: `preview.attack`, `dice`, `damage_type`, `two_hand_dice`, `spell_bonus`, `proficient/proficiency`, `mastery_active`, `ac`, wymagania i ostrzeżenia. `item_previews` zawiera podglądy katalogu sklepu dla właściciela; nie ma w nim nieodkrytych źródeł loot. Publiczny sprzęt widoczny innym pokazuje tylko typ/wygląd/tarczę, nie listę plecaka.

Zapisane: primal_order, training_feats, caster_rules_version=1, legacy_medium_grace, weapon_grip oraz dotychczasowe cooldowny/ekwipunek. Kanał, sowa i Alarm są sesyjne. Ładowanie usuwa kanał, nie zwraca wcześniej opłaconego odnowienia. Migracja nie przyznaje przedmiotu za wybór Strażnika. Zmiana ścieżki nie usuwa zapisanych atutów; zależne nieaktywne atuty przestają dawać także swój punkt cechy. Ponowne spełnienie warunku włącza je bez duplikacji.

## Uczciwe granice zgodności

Wyjściowe zasady to D&D 2024/SRD5.2.1. Wyszkolenie z klasy nie jest zakupem ogólnego atutu. Dwie kategorie broni to simple/martial; fokus nie jest kategorią exotic. Brak biegłości usuwa PB z ataku, nie obrażenia; niewyszkolony pancerz blokuje czary i utrudnia STR/DEX; tarcza bez wyszkolenia nie dodaje AC.

Własne reguły: +1 spell attack/DC Mistyka zamiast testów wiedzy/dodatkowej sztuczki; 180s odnowienia odzyskania, wspólne60s przemian; czasy kanałów3/4/10/30/40s zamiast czasów podręcznikowych; jedno Alarm pole przy rzucającym i reakcja na nie-party; cztery konkretne automatycznie znane formy, brak swobodnego wyboru całego bestiariusza, brak latania/wspinania/szpar; sowa pomaga wyłącznie właścicielowi; powalenie i wstawanie wykorzystuje istniejące1,5s rozwiązanie czasu rzeczywistego; złoto gry za składnik. Chowaniec ma uproszczone3HP, nie jest dosłownym pełnym blokiem statystyk sowy.

Odzyskanie many liczy najlepszą równowartość dozwolonej sumy kręgów (ceil(poziom_klasy/2), kręgi≤5, liczba komórek według tabeli). Wspólna pula nie śledzi konkretnych zużytych komórek, więc jest to równowartość, nie odbudowa wybranych slotów. Efekty form używają własnej fizycznej charakterystyki i ataków; dodatki wyposażenia nie przechodzą na pazury. Czas efektów godzinowych jest przeliczony z6s na3s, czas wyraźnie pokazany w UI.

Ogólne atuty wyposażenia to cztery pozycje przygotowane w tej wersji, nie wszystkie atuty. Progi15/35/55/75 odpowiadają poziomom4/8/12/16 ogólnego rozwoju. Nie usunięto wcześniejszych automatycznych przyrostów cech ani nie przenoszono całego podręcznikowego ASI. Rozszerzenie pełnej puli atutów wymaga późniejszego balansu. Mistrzostwa wojownika pozostają oddzielne i nie są nadawane przez biegłość żołnierską.

## Oficjalne źródła

Sprawdzono podczas pracy, 26.09.2026. Polskie opisy i grafiki są własne; nie przepisano pełnych tekstów książek. Przypisanie SRD w LICENSE-SRD.txt.

- https://www.dndbeyond.com/sources/dnd/br-2024/character-classes — Wizard, Druid, Wild Shape, Arcane Recovery, Primal Order, klasy i wyszkolenia.
- https://www.dndbeyond.com/sources/dnd/br-2024/equipment — kategorie, właściwości, armor training, shield training.
- https://www.dndbeyond.com/sources/dnd/br-2024/spell-descriptions — Alarm, Find Familiar, Speak with Animals, Shillelagh.
- https://www.dndbeyond.com/feats — oficjalny katalog i krótkie streszczenia ogólnych atutów wyposażenia; nie uzyskano pełnych opisów za logowaniem.
- https://www.dndbeyond.com/monsters/4775804-black-bear — czarny niedźwiedź2024.
- https://www.dndbeyond.com/monsters/4775806-brown-bear — brunatny niedźwiedź2024.

## Ponowne testy

```text
python -m unittest discover -s tests
node --test tests/*.cjs
python tools/browser_0814_smoke.py
python tools/browser_0814_fighter_regression.py
python tests/smoke_railway.py
```

Scenariusze przeglądarkowe wymagają Playwright i Chromium pod /usr/bin/chromium; nie są zależnościami serwera produkcyjnego. Używają kontrolowanego mostu WebSocket, opisanego w TEST_REPORT. Lokalny smoke Railwaye uruchamia prawdziwy run.py i natywne połączenia HTTP/WS. Nie jest to test wdrożenia zewnętrznego ani test obrazu Docker.
