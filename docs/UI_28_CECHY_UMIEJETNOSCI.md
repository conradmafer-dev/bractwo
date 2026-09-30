# UI_28 — cechy, umiejętności i wybrzeża

Aktualizacja pełnego UI_27. Wdrożyć serwer i przeglądarkę razem, zachowując bazę i zmienne Railway. `/health` oraz ekran wejścia pokazują UI_28. Nie wymaga resetu postaci. Przed podmianą zachować kopię bazy; cofanie wersji wymaga też przywrócenia zgodnej bazy. Paczka nie wdraża się automatycznie na serwer.

## Sterowanie i wybory

- **C → Cechy:** aktualne cechy, rozwój za zdobyte wybory i jednorazowy przydział cech początkowych w osobnych podzakładkach.
- **C → Statystyki:** osobne kategorie Ogólne, Walka, Rzuty obronne, Odporności, Ruch i rozwój, Mistrzostwo, Efekty. Widoczna jest tylko wybrana kategoria.
- **C → Umiejętności:** osobne widoki listy umiejętności, wyboru biegłości/ekspertyzy i pobliskich wyzwań.
- **C → Atuty:** osobne podzakładki Atuty, Klasa, Pochodzenie i Wyszkolenie. Cechy oraz atuty mają osobne przyciski, ale nadal wydają tę samą pulę awansową.
- **Złota kość k20 w świecie:** podejdź, użyj E/przycisku interakcji, a następnie wykonaj próbę z panelu. Zobaczysz umiejętność, ST, nagrodę, wynik oraz powód niedostępności.
- **Ukrycie PvE** w Umiejętnościach: korzysta ze Skradania i osłony; nie ukrywa postaci przed innymi graczami. Badanie i rozejrzenie używają odpowiednich umiejętności wiedzy i Percepcji.

## Cechy i budżety

Przelicznik pozostaje `min(20, max(1, 1 + poziom_Bractwa // 5))`. Poziom 10 Bractwa odpowiada 3 D&D. Poziom 95 osiąga 20 D&D; dalsze poziomy Bractwa nie tworzą dodatkowych wyborów tego systemu.

Początkowe cechy kupuje się za **27 punktów**. Cena wartości 8–15 wynosi kolejno **0, 1, 2, 3, 4, 5, 7, 9**. Do tego pochodzenie przyznaje **+2 i +1 do różnych cech albo +1 do trzech cech**. Gracz potwierdza całość raz. Dotychczasowy układ klasy działa do świadomego zatwierdzenia własnego. Wybrane wcześniej atuty pozostają, a serwer sprawdza także ich wpływ na limit 20.

| Klasa | Poziomy Bractwa z wyborem cech/atutu | Liczba wyborów |
|---|---|---:|
| Wojownik | 15, 25, 35, 55, 65, 75, 90 | 7 |
| Łowca, czarodziej, druid | 15, 35, 55, 75, 90 | 5 |

Jeden wybór daje **+2 do jednej cechy**, **+1 do dwóch cech** albo **jeden dostępny atut**. To wspólny budżet, nie dwie nagrody. Zwykły rozwój cech ma limit 20. Wybór na 90. poziomie odpowiada nagrodzie z 19 D&D: gra pozwala wybrać dostępny atut spełniający wymagania; ta paczka nie dodaje katalogu epickich darów.

**Atut pochodzenia** to osobny, jednorazowy wybór od początku: Twardy, Zacięty atak albo Wszechstronny. Nie zużywa wyboru awansowego. Wszechstronny daje trzy biegłości; można wybierać go ponownie za nagrody awansowe, o ile pozostają trzy nowe dostępne umiejętności.

## Umiejętności

Test: **k20 + modyfikator właściwej cechy + premia z biegłości**, jeśli postać ma daną biegłość. Ekspertyza podwaja samą premię z biegłości. Bez biegłości nadal można wykonać test. Nie ma rang ani punktów umiejętności przyznawanych co poziom.

| Premia z biegłości | Poziom Bractwa |
|---|---:|
| +2 | 1 |
| +3 | 20 |
| +4 | 40 |
| +5 | 60 |
| +6 | 80 |

Wojownik, druid i czarodziej wybierają **2 biegłości klasowe**, łowca **3**. Wszyscy wybierają **2 biegłości pochodzenia**. Listy klas ograniczają dostępne wybory; duplikaty nie zużywają punktu. Czarodziej od poziomu **5** wybiera jedną ekspertyzę Uczonego z posiadanych biegłości naukowych. Łowca otrzymuje jedną ekspertyzę na **5**, a dwie kolejne na **40**.

| Cecha | Umiejętności |
|---|---|
| Siła | Atletyka |
| Zręczność | Akrobatyka, Zwinne dłonie, Skradanie |
| Inteligencja | Wiedza tajemna, Historia, Śledztwo, Przyroda, Religia |
| Mądrość | Opieka nad zwierzętami, Intuicja, Medycyna, Percepcja, Przetrwanie |
| Charyzma | Oszustwo, Zastraszanie, Występy, Perswazja |

Kondycja nie ma przypisanej standardowej umiejętności. Parowanie jest zdolnością bojową, nie jedną z 18 umiejętności. Po awansie panel pokazuje „Rozwój cech lub atut” i dwa przyciski: „Rozwiń cechy” oraz „Wybierz atut”; zdobycie ekspertyzy otwiera Umiejętności. Po zalogowaniu istniejąca postać z niewykorzystanym wyborem cech/atutu otrzymuje zamykane przypomnienie.

Wskazówki, utrudnienie Skradania przez pancerz, przewaga i utrudnienie oraz stany postaci są rozpatrywane przez wspólny serwerowy test, nie przez klienta.

## Zastosowania w świecie

Dodano **18 autorskich wydarzeń**, po jednym dla każdej umiejętności: lina i półka skalna, sakwa w trybach, obóz goblinów, runiczna pieczęć, mozaika, skrytka, zioła, kapliczka, juczny kuc, rozmowa ze zwiadowcą, opatrzenie kuriera, zgubiona sakwa przy moście, tropy karawany, próba blefu, awanturnik, występ i negocjacje zapasów.

Sukces przyznaje zapisane jednorazowe PD, złoto lub mikstury. Atletyka i Akrobatyka odblokowują lokalne przejścia dostępne później w obie strony; kolejne użycia nie dają następnej nagrody. Po porażce trzeba odczekać **90 sekund**. Odległość, piętro, widoczność, walka, dostępna akcja, poziom i miejsce w plecaku są sprawdzane na serwerze. Klient nie ustala ST, rzutu, nagrody ani celu przejścia.

## Woda i istniejące postacie

Otwarty ocean blokuje ruch wszystkich aktorów, w tym przemiany, lot i wymuszone przesunięcia. Między wyspami korzysta się z łodzi. Pozostają śródlądowe pływanie, nurkowanie i Kontrola wody. Postać zapisana poza brzegiem wraca na pobliski dostępny ląd; aktywne blokady walki odkładają ratunek. Nie odnawia to HP ani zasobów.

Usunięto dawny automatyczny wzrost głównej cechy na poziomach 20 i 40. Zamiast niego są świadome wybory zgodne z powyższym budżetem. Legalne posiadane atuty pozostają. Nadmiarowe lub błędne wpisy dawnych zapisów trafiają do widocznej historii migracji, bez aktywnej premii i bez dodatkowej waluty. Niewydane wybory wynikają z obecnego poziomu, więc starsza postać od razu może wykorzystać należną pulę. Przy zmianie maksymalnego HP zachowywany jest procent zdrowia.

## Zakres adaptacji

Podstawą tej części są D&D 2024 / SRD 5.2: zakup cech, budżet +3 pochodzenia, rozkład wyborów klasowych, biegłości, ekspertyza i testy. Bractwo zachowuje własne poziomy, manę, czas rzeczywisty oraz wcześniejsze specjalizacje, w tym bojowe wybory z 2014.

Własne pochodzenie Bractwa pozwala swobodnie wybrać premiowane cechy i dwie biegłości; nie implementuje całego katalogu podręcznikowych pochodzeń, gatunków ani języków. Wszechstronny obejmuje umiejętności, bez gałęzi narzędzi. Wydarzenia, ST, nagrody, krótkie lokalne przejścia i ukrycie PvE są adaptacjami świata gry. Paczka nie jest pełnym przeniesieniem wszystkich zasad podręcznika.

Oficjalne źródła:
- [Tworzenie postaci](https://www.dndbeyond.com/sources/dnd/br-2024/creating-a-character)
- [Klasy](https://www.dndbeyond.com/sources/dnd/br-2024/character-classes)
- [Umiejętności i testy](https://www.dndbeyond.com/sources/dnd/br-2024/playing-the-game)
- [Atuty](https://www.dndbeyond.com/sources/dnd/br-2024/feats)
- [Słownik zasad — Hide](https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#Hide)

Raporty sprawdzeń znajdują się w `docs/qa_0.8.18/ui28/`. Wersja przeglądarkowa/PWA zawiera nowe panele; archiwalny klient Godot nie otrzymuje nowego interfejsu.
