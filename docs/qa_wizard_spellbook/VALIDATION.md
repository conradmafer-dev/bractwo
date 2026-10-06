# Własna księga czarodzieja — UI_36

## Działanie

Nowy czarodziej wybiera sześć czarów I kręgu do księgi i cztery przygotowane.
Na kolejnych poziomach do 20 otrzymuje po dwa wybory nauki; każdy zachowuje
najwyższy krąg z poziomu zdobycia. Limit przygotowania pochodzi z tabeli
czarodzieja D&D 2024 (np. 4 na 1. poziomie, 9 na 5., 25 na 20.), niezależnie
od Inteligencji. Sztuczki i zdolności klasy/szkoły nie zajmują tych miejsc.

Znany czar wymaga przygotowania do normalnego rzucania. Znane rytuały można
rzucać bez przygotowania; serwer sprawdza księgę przy rozpoczęciu i ukończeniu
rytuału. Zapisany wybór mocy czaru pozostaje przy nim także po zmianie listy.

Całą listę przygotowuje się po długim odpoczynku. Memorize Spell od poziomu 5
wymienia jeden przygotowany czar na jeden inny znany po krótkim odpoczynku.
Gracz wybiera zestaw lub parę przed odpoczynkiem; zatwierdza je wyłącznie serwer
po pomyślnym ukończeniu. Ruch, akcja, obrażenia, śmierć i rozłączenie przerywają
odpoczynek bez zmiany listy. Bractwo zachowuje obecne 10/30 sekund odpoczynku,
trzysekundową turę i zasób many. Wolne miejsca przyznane przy tworzeniu postaci
lub wzroście limitu można uzupełnić poza walką, bez wymiany już przygotowanych.

Księga zawiera rzeczywiście wdrożony katalog Bractwa. Przydziały Savant czterech
szkół dotyczą odpowiedniej szkoły i kręgu; brakujących czarów iluzji czy wróżb
nie zastępuje się czarami z innych szkół. Niewydane wybory są zachowane, a
przypomnienie nie wymusza wyborów niemożliwych w obecnym katalogu. To wdrożenie
obejmuje naukę na poziomach i przygotowanie; nie dodaje źródeł znalezionych
zwojów, przepisywania za złoto ani utraty/odtwarzania fizycznego przedmiotu księgi.

## Zapis i migracja

Dotychczasowa postać bez pola księgi zachowuje wszystkie wcześniej odblokowane
czary jako znane. Przygotowany zestaw mieści się w nowym limicie i preferuje
stary hotbar. Migracja nie odnawia zasobów ani minionych wyborów nauki. Dane
księgi są trwałe i prywatne dla właściciela. Ponowne połączenie nie odnawia
wykorzystanych przydziałów; nieprawidłowe znaczniki poziomu nie tworzą nowych.
Pusta/niepoprawna księga nie daje prawa do rzucania wszystkich czarów.

Panele awansu zawierają osobne odnośniki do nauki, przygotowania i Memorize.
Historyczne podsumowania zachowują własny kontekst. Web: K/C → Czary →
Nauka/Księga/Przygotuj. Godot: karta postaci → Księga. Oba klienty pokazują
liczbę wyborów, ograniczenia kręgów, migrację i dostępne rytuały.

## Weryfikacja

```sh
PYTHONPATH=tests:. python -m unittest test_wizard_spellbook test_wizard_book_advancement test_wizard_spellbook_game test_ranger_styles test_elemental_fury test_style_weapon_actions test_style_weapon_game test_class_choice_advancement test_rest_0818 -q
node --test tests/test_wizard_spellbook_ui.cjs tests/test_rest_ui_0818.cjs tests/test_ranger_elemental_ui.cjs tests/test_dnd_levels_ui.cjs
python -m compileall -q server tools/balance_starter_bosses.py
git diff --check
```

**131/131 testów serwera i 34/34 testy interfejsu zaliczone.** W tym 44 nowe
testy serwera (18 reguł, 19 integracyjnych, 7 awansów) i 11 nowych testów DOM.

Nowe testy pokrywają przydziały i kręgi, Savant, przygotowania, całą obsługę
pakietów w Game, odczyt/zapis i wybór klasy, przerwane/udane odpoczynki,
nieprawidłowe żądania, automatyczną Tarczę, kanały rytuałów, upcasting,
prywatność i unieważnianie pamięci podręcznej. Testy DOM wykonują kontrolki
wysyłające pakiety, zmieniają stan w trakcie otwarcia panelu i sprawdzają
odnośniki podsumowania awansu.

Dwa istniejące testy odpoczynku otrzymały legalny wybór nauki/przygotowania
przed użyciem czaru; ich dotychczasowe asercje pozostają. Siedmiu historycznych
niepowodzeń z UI33 nie poprawiano. Starszy test_spellbook_ui16.cjs daje ten sam
wynik na bazie 41bd671 i na zmianie: 86 testów, 72 zaliczone i 14 niepowodzeń
związanych z oczekiwaniem zdolności niewybranych szkół/specjalizacji. Historyczne
pliki testowe z bajtami NUL pozostały niezmienione. Nie deklarujemy pełnej starej
suity jako zielonej.

Wszystkie 19 skryptów Godot przeszło parser gdtoolkit 4.5. W środowisku brak
silnika Godot i Chromium; nie wykonano natywnego uruchomienia/APK ani wizualnego
testu przeglądarki. Interfejs przetestowano przez DOM i przegląd kodu.

Porównanie symulacji bossów i pełne wyniki znajdują się w README tego katalogu.

## Źródło zasad

[D&D 2024 Basic Rules — Wizard](https://www.dndbeyond.com/sources/dnd/br-2024/character-classes).
Zasady opisano własnymi słowami; katalog czarów i wcześniejsze adaptacje czasu,
many oraz zasięgów pozostają częścią Bractwa.
