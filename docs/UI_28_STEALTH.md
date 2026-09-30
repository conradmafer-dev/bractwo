# Ukrywanie i Skradanie — UI 28

Przycisk **Ukryj się** w zakładce Umiejętności uruchamia powtarzalną akcję,
nie jednorazowy obiekt przygody. Serwer wykonuje test Zręczności (Skradanie)
przeciw ST 15. Biegłość, Ekspertyza, Wskazówki, wyczerpanie i utrudnienie
zbroi działają przez wspólny mechanizm testów. Próba zużywa akcję także przy
niepowodzeniu. Wynik udanej próby staje się ST wykrycia postaci.
Pancerz bez odpowiedniego wyszkolenia utrudnia wszystkie testy Siły i
Zręczności, nie tylko Skradanie.

Wymagana jest rzeczywista osłona albo gęsta mgła oraz brak linii wzroku
pobliskich potworów. Samo oślepienie postaci nie pozwala ukryć się na otwartej
przestrzeni. Ukrycie kończy atak, wykrycie, mówienie na czacie, rzucanie czaru,
opuszczenie osłony lub ręczne wyłączenie. Pierwszy atak zachowuje korzyść
ukrycia, a następne już jej nie otrzymują. Dane ukrycia nie trafiają do zapisu.

## Jawne dostosowania gry czasu rzeczywistego

- **Tylko PvE:** inni gracze nadal widzą postać i mogą ją wskazać. Ukrycie nie
  zmienia rzutów przeciw graczom i jest niedostępne podczas blokady PvP.
- Osłonę wyznaczają istniejące przeszkody w odległości do 40 jednostek oraz
  faktyczne zasłonięcie widoku. Gra nie oblicza ułamka sylwetki za osłoną.
- Słuch potworów obejmuje 30 stóp i nie przechodzi przez lite przeszkody.
  Pasywna Percepcja może wykryć postać. Ścigający potwór może także poświęcić
  akcję na aktywne poszukiwanie raz na trzy sekundy, bez rzutów co klatkę.
- Jeżeli autorski potwór nie ma osobnej Percepcji, korzysta z istniejącej
  premii Mądrości w swoim bloku obron. Nie są to kompletne oficjalne statystyki.
- Katalog czarów nie rozróżnia jeszcze komponentów werbalnych, dlatego każde
  faktycznie rozpoczęte rzucanie czaru lub rytuału ujawnia postać.
- Ukrycie nie usuwa wcześniej znanej lokalizacji z pamięci ścigającego
  potwora. Przeciwnik nadal może podejść do miejsca ostatniego kontaktu.

## Podstawa reguł i weryfikacja

Zasady Hide, Invisible i Passive Perception sprawdzono w oficjalnych
[D&D 2024 Basic Rules](https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary/#Hide).
Powyższe ograniczenia PvE, zasięgi i sposób interpretacji osłony są adaptacją
Bractwa, a nie dodatkowymi zasadami podręcznika.

Testy: `tests/test_hide_ui28.py` obejmuje osłonę, mgłę, widoczność, koszty akcji,
wykrywanie, przewagę pierwszego ataku, komponenty zastępcze, czat, prywatność
stanu, zakolejkowane czary i brak korzyści PvP. `tests/test_environment_0818.py` chroni wcześniejsze
mechanizmy środowiskowe.
