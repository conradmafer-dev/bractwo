# Bractwo Krain 0.8.18 UI_26 — specjalizacje wojownika i łowcy

## Jak wybrać

Po osiągnięciu poziomu 10 kup promocję u mistrza profesji za 2000 złota.
Otwórz **C → Atuty**. Wybór specjalizacji i początkowych zdolności jest
bezpłatny po promocji, trwały i wymaga potwierdzenia. Dokonujesz go poza
walką, odpoczynkiem i rzucaniem czarów, żywą postacią poza przemianą.

Wojownik wybiera Mistrza Bitewnego albo Czempiona. Łowca wybiera Huntera
i jedną z trzech technik. Dotychczasowe style, mistrzostwa broni, Drugi
oddech, Zryw akcji, czary i wilczy towarzysz zachowują działanie.
Istniejące postacie nie otrzymują automatycznie przypisanej podklasy.

## Mistrz Bitewny

Wybierz trzy różne manewry z pięciu:

| Manewr | Zasada |
| --- | --- |
| Precyzyjny atak | Przygotowanie czeka na pudło bronią inne niż naturalna 1. Kość przewagi zwiększa rzut trafienia przed zadaniem obrażeń; nie zwiększa obrażeń. |
| Riposta | Po chybieniu przeciwnika atakiem wręcz: reakcja i kość na własny atak bronią wręcz, z dodatkową kością obrażeń przy trafieniu. |
| Parowanie | Po obrażeniach ataku wręcz: reakcja i kość; obrażenia zmniejszają się o wynik kości i modyfikator Zręczności. |
| Powalający atak | Po trafieniu: dodatkowa kość obrażeń; cel Duży lub mniejszy wykonuje obronę Siły, przy porażce upada. |
| Zastraszający atak | Po trafieniu: dodatkowa kość obrażeń; obrona Mądrości albo przerażenie do końca następnej tury wojownika. |

ST manewrów wynosi 8 + biegłość + wyższy modyfikator Siły/Zręczności.
Jednego ataku nie wzmacnia kilka manewrów. Naturalna 1 pozostaje pudłem;
krytyki podwajają dodatkowe kości obrażeń, a nie płacony koszt zasobu.

Poznane manewry trafiają na pasek umiejętności i do karty postaci.
Jednocześnie przygotowujesz jeden manewr ofensywny i jedną reakcję.
Riposta i Parowanie działają automatycznie po włączeniu, jeśli spełnione
są warunki i dostępna jest reakcja. Przygotowanie/anulowanie nic nie
kosztuje; zasób zużywa dopiero wykonanie. Nie wymaga many ani wolnej
akcji głównej. Rozbrojenie przygotowania działa także przy wyczerpanej puli.

| Poziom gry | Pula po odpoczynku |
| --- | --- |
| 10–29 | 4 kości k8 |
| 30–44 | 5 kości k8 |
| 45–69 | 5 kości k10 |
| 70–84 | 6 kości k10 |
| 85+ | 6 kości k12 |

Krótki i długi odpoczynek odnawiają wszystkie kości. Przerwany odpoczynek,
śmierć, ponowne logowanie i ponowny komunikat wyboru nie odnawiają zasobu.
Przygotowania wyłączają się po zalogowaniu, śmierci i zakończeniu odpoczynku.

## Czempion

Ataki bronią trafiają krytycznie na naturalnym 19 lub 20, od poziomu 70
również na 18. Premia nie dotyczy ataków czarami, Iskry różdżki, bestialnych
przemian i towarzyszy. Karta postaci pokazuje aktualny próg krytyka.

## Hunter

Wybierz jedną technikę, bez dodatkowych opłat i punktów atutów:

| Technika | Zasada |
| --- | --- |
| Pogromca kolosów | +1k8 obrażeń trafienia bronią, jeżeli cel był już ranny przed trafieniem. Najwyżej raz na 3-sekundową turę. Każdy rozmiar celu. |
| Rozbijacz hord | Raz w swojej turze po ataku bronią: dodatkowy atak tą samą bronią na innego przeciwnika do 5 stóp od pierwszego i w zasięgu broni. |
| Zabójca olbrzymów | Reakcja po ataku widocznego Dużego lub większego przeciwnika w odległości do 5 stóp, niezależnie od jego trafienia. |

Rozbijacz hord automatycznie wybiera najbliższego legalnego drugiego
przeciwnika. Dodatkowy strzał nie rozpoczyna walki z postronnym graczem:
gracz może zostać dodatkowym celem, gdy uczestniczy już w walce PvP.
Nie powstaje łańcuch kolejnych ataków Rozbijacza hord.

## Zasady adaptacji

Źródłem nowych zdolności bojowych jest D&D 5e 2014. Ta aktualizacja obejmuje
początkowy zestaw bojowy archetypów, pięć zaimplementowanych manewrów oraz
skalowanie kości przewagi i progu krytyka. Nie dodaje całej późniejszej
listy zdolności podklas z podręcznika ani nie zmienia wcześniejszych klas.

Warunek promocji, stałe wybory w tej wersji, automatyczne przygotowane reakcje,
wybór drugiego celu i czas rzeczywisty są zasadami Bractwa. Efektywny poziom
D&D to min(20, 1 + poziom gry // 5). Tura trwa 3 sekundy, przerażenie do
końca następnej tury około 6 sekund, a istniejące wstawanie z powalenia
zajmuje 1,5 sekundy. Zasięg 5 stóp oznacza 32 jednostki świata; Zabójca
olbrzymów wymaga podejścia bliżej niż ogólny zasięg ataku wielu broni.

Wszystkie rzuty, koszty i wybory rozstrzyga serwer. Dodatkowe ataki zachowują
ochronę miast i przystani, zasady PvP, piętra, przeszkody i zasięgi. Przerażenie
utrudnia rzuty ataku i testy cech, gdy źródło jest widoczne; blokuje dobrowolny
ruch w jego stronę. Nie zmusza postaci do samoczynnej ucieczki.

## Wdrożenie i weryfikacja

Wgraj całą paczkę RAILWAY_GITHUB_READY razem z serwerem i klientem.
Zachowaj bazę SQLite, wolumen Railway i konfigurację Google. Zapisy UI_25
migrują bez resetu postaci. Ekran wejścia, health i cache przeglądarki mają
wersję UI_26. Nie wykonano automatycznego wdrożenia.

Raporty: `docs/qa_0.8.18/ui26/summary.json`, raporty Python/JavaScript oraz
`browser_results.json`. Testy przeglądarkowe korzystają z izolowanej bazy
i jawnego testowego dostawcy Google. Produkcyjne OAuth, Railway oraz
fizyczny telefon nie są objęte tymi testami. Źródła historycznego klienta
Godot są zachowane; ta aktualizacja dotyczy obecnej gry w przeglądarce.

Wynik wybranego zestawu wydania: **258 testów Python, 201 testów JavaScript
i 14 scenariuszy przeglądarkowych — PASS**. Osiem historycznych testów wojownika
z UI_13 oczekuje dawnych czasów odnowienia i asortymentu kupca; potwierdzono
identyczne niepowodzenia na niezmienionej paczce UI_25 i wyłączono je z bramki
wydania. Obecne zasoby odpoczynku mają osobne zaliczone testy. Pełny raport
porównania i lista wyłączeń pozostają w katalogu QA.
