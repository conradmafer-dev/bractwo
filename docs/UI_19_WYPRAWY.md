# UI_19 — wyprawy poza miastami

Nowy moduł dodaje 12 rozmówców, 18 zadań w ośmiu lokalnych opowieściach,
68 punktów odkryć, sześć małych podziemi, trójpoziomowe katakumby,
czteropoziomowe jaskinie i trzy wzgórza z dwoma dostępnymi tarasami każde.
Wejścia oznaczono w Atlasie. Odkrycia korzystają z istniejącego znacznika,
jednorazowej nagrody i skalowania doświadczenia według trudności miejsca.
Cele można śledzić z dziennika. W podziemiach nie ma blokad poziomu wejścia;
podany poziom jest zaleceniem.

| Miejsce | Rozmówcy | Zadania | Końcowa nagroda |
|---|---|---:|---|
| Piwnice Złamanego Dzwonu | Nela Dzwonniczka, Tymon Powroźnik | 3 | Pierścień pływania |
| Jaskinie Szeptającego Korzenia | Bera Zbieraczka, Jaro Mierniczy | 2 | Pierścień swobody działania |
| Katakumby Siedmiu Imion | Matylda Kronikarka, Brat Idzi | 3 | Pierścień ochrony |
| Komnata Zagubionego Południka | Faris Astrolabista | 2 | Mitrylowa kolczuga |
| Sztolnia Czerwonego Oddechu | Pola Żużelniczka | 2 | Pierścień odporności na ogień |
| Schronisko pod Lodowym Łukiem | Wera Zimny Szlak | 2 | Pierścień ciepła |
| Krypta Strażników Grani | Oskar Strażnik Grani | 2 | Tarcza +1 |
| Archiwum Wygaszonych Pieczęci | Ada Archiwistka, Eryk Bez Herbu | 2 | Pierścień odporności na truciznę |

Każdy rozmówca ma własne powitanie i dwa tematy rozmowy. Odbiór zadania
wymaga powrotu do właściwego NPC; kolejne części wymagają ukończenia
poprzednich. Nagrody przedmiotowe są jednorazowe. Zwykłe łupy sześciu nowych
stworzeń nie zawierają tych pierścieni.

## Sześć nowych stworzeń

Źródło statystyk: oficjalny [SRD 5.2.1](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf),
strony 259, 286, 295, 344 i 349. Zachowano HP, KP, premie trafienia, kości
obrażeń, odporności, rzuty obronne i doświadczenie. Poziom wyświetlany na
mapie to lokalna etykieta trudności, która nie zwiększa tych statystyk.

| Stworzenie | HP | KP | Trafienie | PD | Działające cechy |
|---|---:|---:|---:|---:|---|
| Olbrzymi nietoperz | 22 | 13 | +5 | 50 | Lot, ślepowidzenie, ugryzienie kłute |
| Ożywiony latający miecz | 14 | 17 | +4 | 50 | Lot, ślepowidzenie, niewrażliwości konstruktu |
| Ożywiona zbroja | 33 | 18 | +4 | 200 | Dwa oddzielne ataki, niewrażliwości konstruktu |
| Gargulec | 67 | 15 | +4 | 450 | Lot, dwa oddzielne ataki, niewrażliwość na truciznę |
| Grick | 54 | 14 | +4 | 450 | Dziób i macki; chwyt średniego lub mniejszego celu, ST 12 |
| Zombie ogra | 85 | 8 | +6 | 450 | Nieumarła wytrwałość, niewrażliwość na truciznę |

Chwyt gricka zatrzymuje ruch. Gracz korzysta ze zwykłej akcji „Wyrwij się
z chwytu”; chwyt kończy się także po odsunięciu od gricka, jego śmierci,
obezwładnieniu albo zmianie piętra. Grick utrzymuje jeden chwyt naraz.
Zombie ogra przy utracie ostatniego HP wykonuje rzut Kondycji przeciw
ST 5 + otrzymane obrażenia, zachowując 1 HP po sukcesie. Krytyki i dodatni
składnik obrażeń promienistych wyłączają tę cechę.

Grafiki są oryginalnymi czteroklatkowymi sprite SVG; generator znajduje się
w `tools/build_adventure_sprites.py`. Nie wykorzystują ilustracji podręcznika.
Treść zasad SRD podlega atrybucji CC-BY-4.0 opisanej w `LICENSE-SRD`.

## Integracja i sprawdzenie

`adventure_content.configure` działa po konfiguracji kontynentu i starszych
potworów, przed wspólnym naliczeniem odkryć. Nowe identyfikatory mają prefiks
`adv_`; stare questy, NPC oraz kolejność wcześniejszych spawnów są zachowane.
`AdventureGame` znajduje się przed `EnvironmentGame`; ataki z krytykiem
przekazują `critical` do wspólnej ścieżki obrażeń.

`tests/test_adventure_ui19.py` sprawdza połączenia wnętrz na rzeczywistej
mapie kolizji, cele zadań, grafiki/statystyki oraz nowe cechy bojowe.
