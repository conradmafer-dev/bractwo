> Aktualizacja łowcy w 0.8.12: patrz CHANGELOG_0.8.12.md i PROTOCOL_0.8.12.md. Starsze progi łowcy i koszt Znaku poniżej zastępują nowe zasady.

# Skalowanie czarów — Bractwo 0.8.7

## Reguły i poziomy

Punktem odniesienia pozostaje SRD 5.2.1 (zasady z 2024 r.), a nie mieszanka dawnych edycji. W tej wersji D&D większość skalowalnych czarów kręgowych wzmacnia **wyższa komórka czaru**, nie sam poziom rzucającego. Bractwo zastępuje komórki wspólną maną: wyższy krąg rzucania oznacza odpowiednio wyższy koszt. Sztuczki wzmacnia sam poziom, bez dodatkowej opłaty.

Czarodziej i druid: kręgi I–IX na poziomach **1, 10, 20, 30, 40, 50, 60, 70, 80**. Łowca zachowuje późniejszą ścieżkę I–V: **20, 40, 60, 80, 100**. Przelicznik poziomu klasy D&D to `min(20, max(1, 1 + poziom_gry // 5))`. Przyrost co jeden poziom klasy daje zatem progi co 5 poziomów gry; co dwa — co 10; co trzy — co 15. Funkcja `caster_steps` obsługuje te odstępy, ale nie dopisuje takich premii zaklęciom, których opis ich nie przewiduje.

Na przykład Drugi oddech ma `1k10 + poziom klasy`, więc jego stała część rośnie o 1 na poziomach 5, 10, 15 itd., do +20 na poziomie 95. Sztuczki otrzymują dodatkowe kości na poziomach **20, 50, 80**, odpowiadających poziomom D&D 5, 11, 17. Dziki kształt, towarzysz, dodatkowe ataki i automatyczne wzrosty cech zachowują dotychczasowe reguły.

## Czary wzmacniane wyższym kręgiem

Każdy wiersz opisuje przyrost **za jeden krąg powyżej bazowego**, chyba że podano inne progi. Dla czarodzieja/druida kolejny krąg jest dostępny co 10 poziomów gry; dla łowcy co 20.

| Czar | Krąg bazowy | Przyrost |
|---|---:|---|
| Magiczny pocisk | I | +1 pocisk; każdy nadal zadaje 1k4+1 |
| Płonące dłonie | I | +1k6 obrażeń |
| Leczenie ran | I | +2k8 leczenia |
| Uzdrawiające słowo | I | +2k4 leczenia |
| Długonogi | I | +1 sojuszniczy cel; szybkość i czas bez wzrostu |
| Palący promień | II | +1 promień; każdy nadal zadaje 2k6 |
| Promień księżyca | II | +1k10 obrażeń na impuls pola |
| Kula ognia | III | +1k6 obrażeń |
| Błyskawica | III | +1k6 obrażeń |
| Wezwanie błyskawicy | III | +1k10 obrażeń każdego wywołanego uderzenia |
| Uschnięcie | IV | +1k8 obrażeń |
| Swoboda ruchu | IV | +1 sojuszniczy cel; czas bez wzrostu |
| Lodowa burza | IV | +1k10 obuchowych; 4k6 zimna nie zwiększa się |
| Stożek zimna | V | +1k8 obrażeń |
| Masowe leczenie ran | V | +1k8 leczenia |
| Łańcuch błyskawic | VI | +1 cel; obrażenia 10k8 bez zwiększania |
| Uzdrowienie | VI | +10 HP leczenia |
| Znak łowcy | I | Czas: 600 rund przy I–II, 4800 przy III–IV, 14400 przy V+; premia obrażeń pozostaje 1k6 |

Czary bez odpowiedniej reguły skalowania (np. Tarcza, Zbroja maga, Oplątanie, Mglisty krok, Kolczasty wzrost, Kamienna skóra, Promień słońca) nie otrzymują wymyślonych dodatkowych kości, pocisków, długości efektu ani wyższego kosztu. Zdolności spoza kategorii czarów nie są wzmacniane wyższym kręgiem.

## Moc i mana

Domyślne **Auto · najwyższa moc** wybiera najwyższy dostępny krąg, który w ogóle zmienia regułę danego czaru. Koszty kręgów I–IX: **20, 30, 50, 60, 70, 90, 100, 110, 130 many**. Znak łowcy ma wybór tylko I, III i V; płacenie za II lub IV nie dawałoby dodatkowego efektu. Sztuczki nadal kosztują 0.

W **C → Czary** lub **K** przy czarze można wybrać niższy odblokowany krąg. Wybór zapisuje się z postacią i obejmuje przycisk Użyj, oba paski skrótów, F oraz PvP. Nie trzeba zajmować dodatkowego slotu osobnymi wersjami tego samego czaru. Brak many nie przełącza potajemnie na słabszą wersję: gracz sam wybiera moc. Przed odblokowaniem kolejnego kręgu zbędny selektor nie zajmuje miejsca.

Przykład czarodzieja: Magiczny pocisk na poziomie 1 ma 3 pociski i koszt 20; na 10 w Auto ma 4 i koszt 30; na 20 ma 5 i koszt 50; na 80 ma 11 i koszt 130. Wybranie I kręgu na dowolnym wyższym poziomie zachowuje 3 pociski za 20 many. Animacja pokazuje rzeczywistą liczbę pocisków, a każdy ma własny łuk. Palący promień otrzymuje również rzeczywistą większą liczbę promieni i osobnych rzutów trafienia.

Przykład druida: Leczenie ran na poziomie 1 to 2k8+3, na 10 w Auto 4k8+3, a na 20 6k8+4. Przyrost kości z kręgu i przyrost stałego modyfikatora z cechy są różnymi zmianami. Modyfikator jest dodawany tylko raz.

## Czary utrzymywane i czas

Pola oraz powtarzane wywołania czarów przechowują **krąg i kości opłacone przy rzuceniu**. Awans ani przestawienie selektora nie podnosi za darmo siły istniejącego pola. Wezwanie błyskawicy i Promień słońca nadal pozwalają na kolejne użycia bez many podczas koncentracji, z opłaconą mocą. Karta pokazuje aktualnie utrzymywany profil. Przycisk **Zakończ czar** kończy koncentrację; dopiero nowy rzut korzysta z nowej mocy i pobiera koszt. Zmiana preferencji nie przerywa samoczynnie koncentracji. Rzuty obronne nadal korzystają z istniejących zasad statystyk postaci.

Znak łowcy otrzymał prawidłowe progi skalowania czasu. Bractwo liczy rundy po 3 sekundy, podczas gdy podręcznikowe rundy trwają 6 sekund. Dlatego 600/4800/14400 rund daje odpowiednio **30 minut / 4 godziny / 12 godzin rzeczywistego czasu**; odpowiada to liczbie rund w podręcznikowych 1/8/24 godzinach. Znak łowcy nadal wymaga koncentracji; samo istnienie większego limitu nie gwarantuje utrzymania go przez ten czas.

Długonogi nadal trwa **600 rund**, daje +10 stóp szybkości, nie wymaga koncentracji i nie kończy się od ataku. Wyższy krąg zwiększa jedynie liczbę odbiorców. Wybrany sojusznik ma pierwszeństwo, następnie rzucający i najbliżsi członkowie drużyny. Każdy musi osobno spełniać zasięg dotyku, linię widzenia, piętro i reguły pomocy w PvP. Żadnych przypadkowych obcych ani automatycznego pomijania zabezpieczeń.

Pozostałe dotychczasowe skrócenia bazowych czasów/efektów wymienione we wcześniejszych notatkach adaptacji nie są w tej aktualizacji całościowo zmieniane. To implementacja skalowania istniejących zaklęć, nie deklaracja pełnej zgodności całej gry z podręcznikiem.

## Księga i awanse

Księga pokazuje bieżące kości/liczbę pocisków/cele/czas oraz pierwszy następny próg wzrostu. Koszt na pasku odpowiada wybranemu kręgowi. Przy aktywnym powtarzanym czarze koszt kolejnego wywołania wynosi 0.

Panel awansu nadal jest kaskadowy i zamykany indywidualnym **Zamknij**. Przykładowe osobne wiersze: `Magiczny pocisk +1 pocisk`, `Płonące dłonie +1k6 do obrażeń`, `Leczenie ran +2k8 do leczenia`, `Leczenie ran +1 do leczenia`, `Długonogi +1 cel`, `Znak łowcy +4200 tur trwania efektu`. Wzrost kosztu maksymalnej mocy ma odrębny wiersz. Nie pokazuje się dawnych i nowych sum ani zmian zerowych.

Podsumowanie opisuje **nowo dostępną maksymalną moc** również wtedy, gdy postać wybrała tańszy krąg. Nie nadpisuje jej wyboru. Nowo odblokowany czar ma swój wpis Nowy czar; nie dostaje fikcyjnego wzrostu względem nieposiadanego zaklęcia. Sztuczki i premie cech są liczone odrębnie. Zmiana rodzaju kości Shillelagh, której nie da się uczciwie przedstawić jako dodatkowej pełnej kości, zachowuje podpisany przyrost średnich obrażeń.

Każdy pośredni poziom z wielokrotnego awansu jest oceniany osobno. Stare niezamknięte podsumowania 0.8.6 zachowują dawny zestaw zmian; dopiero nowe podsumowania mają wersję skalowania 1. Zapobiega to dopisywaniu nowych premii do historycznego awansu przy wczytaniu bazy.

## Źródła

- Oficjalne SRD i atrybucja: https://www.dndbeyond.com/srd oraz `../LICENSE-SRD.txt`.
- Opisy czarów w zasadach 2024: https://www.dndbeyond.com/sources/dnd/br-2024/spell-descriptions
- Zasady czarów i wyższych komórek: https://www.dndbeyond.com/sources/dnd/free-rules/spells

Zweryfikowano 24 września 2026. Własne polskie opisy służą interfejsowi gry. Nowa implementacja nie dodaje płatnych podręczników ani znaków graficznych wydawcy.
