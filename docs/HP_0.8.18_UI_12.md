# HP — zgodne sumy D&D, przyrost na każdy poziom gry

UI_12 zachowuje oficjalne wartości stałego przyrostu HP D&D 2024. Rozłożenie tego przyrostu między poziomami gry jest przeliczeniem tempa Bractwa, a nie dodatkową zasadą podręcznikową.

Przy początkowej Kondycji 14 (+2), bez atutów:

| Klasa | Poziom gry 1 | 5 | 10 | 15 | 20 | 95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rycerz / Łowca | 12 | 20 | 28 | 36 | 44 | 164 |
| Druid | 10 | 17 | 24 | 31 | 38 | 143 |
| Czarodziej | 8 | 14 | 20 | 26 | 32 | 122 |

Wzrost między poziomami gry 5 a 10:

| Klasa | Awans na 6 | na 7 | na 8 | na 9 | na 10 | Razem |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rycerz / Łowca | +1 | +2 | +1 | +2 | +2 | +8 |
| Druid | +1 | +1 | +2 | +1 | +2 | +7 |
| Czarodziej | +1 | +1 | +1 | +1 | +2 | +6 |

## Obliczenia

Pierwszy poziom daje maksymalny wynik kości klasy + modyfikator Kondycji. Każdy następny poziom D&D daje `max(1, połowa kości + 1 + modyfikator Kondycji)`: podstawą jest 6 dla rycerza/łowcy, 5 dla druida i 4 dla czarodzieja.

Progi gry to 1, 5, 10, 15…95. Między sąsiednimi progami rośnie część całego przyrostu. Zaokrąglenie w dół następuje raz, po wyliczeniu łącznego przyrostu od początku rozwoju. Ułamki nie są tracone przy poszczególnych awansach; obliczenia używają liczb całkowitych, bez błędów arytmetyki zmiennoprzecinkowej. Nie jest potrzebne zapisywanie osobnego licznika ułamków.

Odcinek 1→5 ma cztery awanse. Pozostałe odcinki mają pięć. Przy obecnych początkowych cechach każda klasa dostaje co najmniej 1 HP przy każdym awansie aż do 95. poziomu. Przy hipotetycznej bardzo niskiej Kondycji nie można gwarantować całego HP przy każdym awansie gry i jednocześnie zachować minimalnego przyrostu 1 HP na poziom D&D. Poziomy powyżej 95 nie zwiększają bazowego HP, bo odpowiadają już limitowi 20. poziomu D&D.

Kondycja jest uwzględniana w całym wzorze również wstecz. Na progach +1 modyfikatora daje dokładnie +1 HP za osiągnięty poziom D&D; między progami zaokrąglenie interpolacji może dodać jeszcze 1 HP z części następnego przyrostu. Nieparzysty wzrost cechy bez zmiany modyfikatora nie zmienia HP.

Twardy pozostaje osobnym dodatkiem `2 × efektywny poziom D&D`, zgodnie z wcześniejszym ustaleniem; jego bonus nie jest rozdrabniany. Dziki kształt zachowuje własne maksymalne HP i własną Kondycję druida do tego obliczenia. Tymczasowe HP bestii/Polimorfii nie są częścią tego wzoru.

## Starsze postacie

Autorski bonus Witalności +2 HP za punkt został usunięty. Przy wczytaniu znika wyłącznie wydanie punktów na tę gałąź; punkty ponownie są wolne. Pozostałe przydziały zostają zachowane.

Nowe maksymalne HP nalicza się automatycznie bez resetowania postaci. Aktualne HP zachowuje dawny procent maksimum, także po usunięciu Witalności lub ograniczeniu rozwoju do 20. poziomu D&D. Martwa postać pozostaje martwa. Zapisany znacznik wersji zapobiega ponownej migracji przy kolejnych logowaniach.

Historyczne komunikaty awansu zachowują wzór obowiązujący podczas jego zdobycia. Nowe komunikaty pokazują faktyczną różnicę nowego maksimum między danymi poziomami.

Źródło: [D&D 2024 — tworzenie postaci i awanse](https://www.dndbeyond.com/sources/dnd/br-2024/creating-a-character#LevelAdvancement). Raport sprawdzeń: `docs/qa_0.8.18/ui_12_results.json`.
