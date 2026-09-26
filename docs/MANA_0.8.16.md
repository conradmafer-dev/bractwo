# Rozkład many 0.8.16

Tylko bazowe pule i ilość Odzyskania mocy. Skupienie dodaje osobno 4 many za punkt
(do 20 punktów); nie zwiększa Odzyskania mocy. Rycerz ma 30 podstawowej many,
bez sztucznych przyrostów. Druid nie otrzymuje zdolności Odzyskanie mocy.

## Punkty odniesienia

Zachowane wartości 0.8.15 z poziomów 1 / 10 / 20 / 30 / 40 / 50 / 60 / 70 /
80 / 90 / 95. Między nimi liniowy wzrost zaokrąglany do najbliższej liczby całkowitej
(połowy w górę). Liczenie od poziomu, nie przez sumowanie zaokrąglonych kroków.
Czarodziej/druid osiągają dawny limit 1330 na poziomie 95. Łowca ma dawny limit 640
na 90., a Odzyskanie mocy 180 na 90. Dalej te bazowe wartości nie rosną.

Koszty, kręgi, czary, 180 s odnowienia i proporcjonalna regeneracja niezmienione.
Odzyskanie mocy zawsze zwraca najwyżej brakującą część puli. Nie resetuje odnowienia
przy awansie ani logowaniu. Większe pule pośrednie nie oznaczają osobnych komórek
ani darmowego rzucania; to adaptacja progresji Bractwa.

## Wszystkie poziomy

| Poziom | Czarodziej / druid: pula | Łowca: pula | Odzyskanie mocy czarodzieja |
| ---: | ---: | ---: | ---: |
| 1 | 40 | 40 | 20 |
| 2 | 51 | 42 | 22 |
| 3 | 62 | 44 | 24 |
| 4 | 73 | 47 | 27 |
| 5 | 84 | 49 | 29 |
| 6 | 96 | 51 | 31 |
| 7 | 107 | 53 | 33 |
| 8 | 118 | 56 | 36 |
| 9 | 129 | 58 | 38 |
| 10 | 140 | 60 | 40 |
| 11 | 153 | 68 | 42 |
| 12 | 166 | 76 | 44 |
| 13 | 179 | 84 | 46 |
| 14 | 192 | 92 | 48 |
| 15 | 205 | 100 | 50 |
| 16 | 218 | 108 | 52 |
| 17 | 231 | 116 | 54 |
| 18 | 244 | 124 | 56 |
| 19 | 257 | 132 | 58 |
| 20 | 270 | 140 | 60 |
| 21 | 281 | 143 | 62 |
| 22 | 292 | 146 | 64 |
| 23 | 303 | 149 | 66 |
| 24 | 314 | 152 | 68 |
| 25 | 325 | 155 | 70 |
| 26 | 336 | 158 | 72 |
| 27 | 347 | 161 | 74 |
| 28 | 358 | 164 | 76 |
| 29 | 369 | 167 | 78 |
| 30 | 380 | 170 | 80 |
| 31 | 399 | 180 | 81 |
| 32 | 418 | 190 | 82 |
| 33 | 437 | 200 | 83 |
| 34 | 456 | 210 | 84 |
| 35 | 475 | 220 | 85 |
| 36 | 494 | 230 | 86 |
| 37 | 513 | 240 | 87 |
| 38 | 532 | 250 | 88 |
| 39 | 551 | 260 | 89 |
| 40 | 570 | 270 | 90 |
| 41 | 586 | 275 | 92 |
| 42 | 602 | 280 | 94 |
| 43 | 618 | 285 | 96 |
| 44 | 634 | 290 | 98 |
| 45 | 650 | 295 | 100 |
| 46 | 666 | 300 | 102 |
| 47 | 682 | 305 | 104 |
| 48 | 698 | 310 | 106 |
| 49 | 714 | 315 | 108 |
| 50 | 730 | 320 | 110 |
| 51 | 740 | 326 | 112 |
| 52 | 750 | 332 | 114 |
| 53 | 760 | 338 | 116 |
| 54 | 770 | 344 | 118 |
| 55 | 780 | 350 | 120 |
| 56 | 790 | 356 | 122 |
| 57 | 800 | 362 | 124 |
| 58 | 810 | 368 | 126 |
| 59 | 820 | 374 | 128 |
| 60 | 830 | 380 | 130 |
| 61 | 841 | 386 | 131 |
| 62 | 852 | 392 | 132 |
| 63 | 863 | 398 | 133 |
| 64 | 874 | 404 | 134 |
| 65 | 885 | 410 | 135 |
| 66 | 896 | 416 | 136 |
| 67 | 907 | 422 | 137 |
| 68 | 918 | 428 | 138 |
| 69 | 929 | 434 | 139 |
| 70 | 940 | 440 | 140 |
| 71 | 953 | 453 | 142 |
| 72 | 966 | 466 | 144 |
| 73 | 979 | 479 | 146 |
| 74 | 992 | 492 | 148 |
| 75 | 1005 | 505 | 150 |
| 76 | 1018 | 518 | 152 |
| 77 | 1031 | 531 | 154 |
| 78 | 1044 | 544 | 156 |
| 79 | 1057 | 557 | 158 |
| 80 | 1070 | 570 | 160 |
| 81 | 1086 | 577 | 162 |
| 82 | 1102 | 584 | 164 |
| 83 | 1118 | 591 | 166 |
| 84 | 1134 | 598 | 168 |
| 85 | 1150 | 605 | 170 |
| 86 | 1166 | 612 | 172 |
| 87 | 1182 | 619 | 174 |
| 88 | 1198 | 626 | 176 |
| 89 | 1214 | 633 | 178 |
| 90 | 1230 | 640 | 180 |
| 91 | 1250 | 640 | 180 |
| 92 | 1270 | 640 | 180 |
| 93 | 1290 | 640 | 180 |
| 94 | 1310 | 640 | 180 |
| 95 | 1330 | 640 | 180 |
| 96 | 1330 | 640 | 180 |
| 97 | 1330 | 640 | 180 |
| 98 | 1330 | 640 | 180 |
| 99 | 1330 | 640 | 180 |
| 100 | 1330 | 640 | 180 |
