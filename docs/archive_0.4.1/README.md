# Bractwo — Pogranicze · 0.4.1 — Płynność, cele i FPS

Otwarty RPG 2D: cztery profesje, dalekie wyprawy, polowania, rozwój przez używanie umiejętności, podziemia, runy, drużyny i PvP. Aktualizacja rozwija kierunek inspirowany Tibią, z własną mapą, grafiką i balansem.

**Świat ma 128 000 × 92 160 jednostek — 1600 razy większą powierzchnię niż mapa 0.3.** Pięć miast jest rozmieszczonych na odległych krańcach kontynentu. Rozsunięto odległości, zachowując normalne rozmiary domów, postaci i komnat.

Paczka zawiera pełny serwer Python, klienta WWW i źródła Godot. Nie zawiera APK/AAB/EXE. Weryfikację i jej ograniczenia opisuje `docs/TEST_REPORT.md`.


## Poprawki 0.4.1

- **Licznik FPS** działa stale podczas gry: WWW — prawy dolny róg, Godot — prawa strona górnego HUD. Odczyt odświeża się co około pół sekundy i mierzy klatki klienta.
- **Kliknięcie potwora lub jego wiersza na liście wybiera cel.** Wybrany przeciwnik otrzymuje czerwone oznaczenie. Spacja / Atakuj, mocny strzał paladyna i runy trafiają wskazanego potwora. Esc albo przycisk czyszczenia usuwa cel. Bez celu atak nadal wybiera najbliższego potwora w zasięgu.
- **Trafiony potwór zapamiętuje napastnika i podejmuje pościg** również spoza pasywnego zasięgu wykrywania. Dotyczy broni, umiejętności, czarów i run. Atakowanie podtrzymuje walkę; strefy ochronne, piętra, kolizje i ograniczona odległość od legowiska nadal obowiązują.
- Świat i grafika zachowują rozmiar, kolory, rozdzielczość, rysunki i efekty. Optymalizacja obejmuje indeks przestrzenny obiektów, buforowanie fragmentów gruntu, przygotowanie terenu z wyprzedzeniem, rzadsze odrysowywanie niezmienionej minimapy, stabilne wiersze listy oraz mniejsze wiadomości serwera.
- Pozycje są interpolowane między stanami serwera, żeby ruch nie zwalniał i nie przyspieszał przy każdej kolejnej wiadomości.

**Aktualizuj jednocześnie serwer i używanego klienta.** Po zatrzymaniu starego serwera zachowaj kopię katalogu danych i użyj kopii bazy z nową pełną paczką. Zapis 0.4.0 jest zgodny, nie trzeba tworzyć nowych postaci.

Pomiar laboratoryjny przy 24 nieruchomych postaciach w odległych rejonach: krok serwera około 13,24 → 0,82 ms. Dla jednej postaci niezmieniona wiadomość stanu spadła z około 21,7 kB do 2,0 kB. To pomiary pracy serwera i danych. Faktyczną płynność renderowania na swoim urządzeniu sprawdzisz nowym licznikiem FPS.

## Uruchomienie

1. Rozpakuj całą paczkę. Wymagany Python 3.11+.
2. Windows: `start_windows.bat`. Linux/macOS: `bash start_unix.sh`.
3. Zostaw okno serwera otwarte i wejdź na **http://127.0.0.1:8080**.
4. Utwórz postać: nazwa, hasło i klasa. **J** otwiera zadania, **K** księgę czarów, rozwoju, atlasu i usług.
5. Pierwsze zadania strażniczki w Przystani prowadzą na szczury, do Starego Młyna, goblinów i ruin. Nowe krainy leżą dużo dalej.

Pierwszy start pobiera zależność aiohttp. Ręcznie:

```bash
python -m pip install -r server/requirements.txt
python server/server.py --host 127.0.0.1 --port 8080 --db data/world.sqlite3
```

Na telefonie w tej samej sieci Wi-Fi: uruchom `start_windows.bat lan` albo `bash start_unix.sh lan`, a na telefonie otwórz `http://LOKALNY_IP_KOMPUTERA:8080`. Obróć ekran poziomo. Adres 127.0.0.1 na telefonie oznacza telefon. Dla publicznego serwera potrzebne są HTTPS/WSS. Druga karta z inną postacią umożliwia próbę multiplayer.

## Kontynent i podróże

- **20 krain**, od Marchii Przystani i Borów Szeptów po Smocze Urwiska i Morze Popiołu.
- **5 miast:** Przystań, Brzezina, Złoty Port, Mroźna Przystań i Popielny Port. Każde ma strefę ochronną, kupca, kapitana, bankiera i mistrza profesji.
- **10 podziemi po 2 piętra:** kopalnie, groty, twierdza, piramida, krypty, pałac lodu, smocze gniazdo i otchłań. Schody mają rzeczywiste przejścia i powrót; ściany zatrzymują ruch oraz ataki.
- **1435 deterministycznie rozmieszczonych łowisk**, 7729 punktów odrodzenia przeciwników, 39 typów przeciwników, 109 odkryć i 30 zadań. Rozległą dzicz wypełniają powtarzalne obozy i grupy potworów; nie są to tysiące ręcznie zaprojektowanych lokacji.
- Krainy mają stałą trudność. Zalecany poziom nie blokuje wejścia. Wyjątkiem jest zejście do najgłębszego Serca Otchłani wymagające poziomu 100.

Najbliższe miasta dzieli około **34 441 jednostek**, czyli **5,7 minuty** marszu postaci z szybkością 100 w linii prostej. Z Przystani do Brzeziny to 7,6 minuty, a do Popielnego Portu 22,4 minuty. To wyliczenia bez walki, omijania przeszkód i postojów; nie czasy zmierzone w rozgrywce. Wyższy poziom i przyspieszenie skracają drogę.

Atlas pod K pozwala wybrać miasto, krainę lub wejście do podziemi. Klient WWW ma dodatkowo klikalną mapę kontynentu. Wskaźnik pokazuje kierunek, nie steruje postacią automatycznie. Statki od poziomu 8 wymagają kapitana, złota i zakończenia walki; cena rośnie z odległością. Przy bankierze można wybrać miasto odrodzenia.

## Rozwój postaci

| Poziom | Nowa możliwość | Warunki |
| --- | --- | --- |
| 1 | Trening walki wręcz, dystansu, magii i obrony | Umiejętności rosną przez używanie |
| 8 | Lekkie leczenie, przyspieszenie, podróże statkiem | Mana na czary; złoto i kapitan na rejs |
| 12 | Runa ognistej kuli | Każda profesja kupuje i używa; mag/druid także wytwarza |
| 20 | Promocja profesji i mocniejsze mikstury | Promocja u mistrza za 2000 złota |
| 30 | Zaawansowany czar profesji, runa lodu | Czar wymaga promocji |
| 40 | Błogosławieństwo | U mistrza za 500 złota; chroni przy jednej śmierci |
| 50 | Specjalizacja: siła, witalność, skupienie | Promocja; pierwszy punkt na 50, kolejne co 5 poziomów |
| 60 | Pierwsze kontrakty na bossów, runa nagłej śmierci | Późniejsze kontrakty mają wyższe wymagania |
| 80 | Mistrzowski czar profesji i najlepsze mikstury | Czar wymaga promocji |
| 100 | Ostatnie zejście w Sercu Otchłani | Do walki zalecana drużyna 120+ |

| Klasa | Podstawowa umiejętność F | Czary poziomu 30 / 80 | Promocja |
| --- | --- | --- | --- |
| Rycerz | Obrona i prowokowanie | Wir ostrzy / Furia rycerza | Elitarny Rycerz |
| Paladyn | Silny strzał | Salwa strzał / Słoneczna salwa | Królewski Paladyn |
| Mag | Krąg ognia | Fala ognia / Wielkie piekło | Mistrz Magii |
| Druid | Leczenie siebie i drużyny | Fala lodu / Wieczna zima | Starszy Druid |

Promocja przyspiesza regenerację i zwiększa limit duszy ze 100 do 200. Dusza odnawia się przez nagradzane zabójstwa. Runy zużywają ładunki; tworzenie kosztuje manę i duszę. Czary mają koszt many i odnowienie. Nowe ataki obszarowe oraz runy działają na potwory, z kontrolą piętra i linii widzenia.

Specjalizacja daje za punkt: siła +3 ataku; witalność +12 maksymalnego HP; skupienie +8 maksymalnej many i +1 ataku. Limit to 20 punktów na gałąź. Zmiana specjalizacji u mistrza kosztuje 200 złota.

Poziomy postaci nie mają maksimum. Dostępna zawartość ma skończony zakres, do krain zalecanych na poziomy 110–150. Wyposażenie ma 53 szablony i wymagania do poziomu 110; nie skaluje się automatycznie z postacią.

## Zapasy, bank i drużyna

Plecak mieści 40 przedmiotów wraz z wyposażonymi. Bank przechowuje złoto, wspólny między miastami depozyt 120 przedmiotów. Usługi wymagają odpowiedniego NPC, tego samego piętra i zakończenia walki. Wyposażony przedmiot trzeba zdjąć przed odłożeniem. Bank i depozyt są chronione przed karą śmierci.

Mikstury zdrowia i many mają cztery stopnie: poziomy 1, 20, 50, 80. Skróty 1 i 2 używają najsilniejszej posiadanej mikstury, której wymagania spełniasz. Wspólne odnowienie mikstur to 3 sekundy, limit 99 sztuk danego rodzaju.

Drużyna wymaga zaproszenia i akceptacji, maksymalnie cztery osoby. Podział XP i złota wymaga bliskości (650 jednostek), tego samego piętra, obszaru poza miastem i stosunku poziomów najwyżej 3:1. Do puli XP dochodzi 10% za każdego dodatkowego uprawnionego członka. Liczy się niedawny udział drużyny w walce. Loot jest indywidualny; boss gwarantuje przedmiot, jeżeli plecak ma miejsce. Potwory odradzają się po śmierci; nowi bossowie po 180 sekundach.

Zadania i nagrody za odkrycia są jednorazowe. Polować można bez końca. Zabójstwa liczą się po przyjęciu zadania, wcześniejsze odkrycia mogą od razu wypełnić cel. Nagrodę odbiera się u zleceniodawcy. Brak miejsca w plecaku blokuje odbiór przedmiotu, zachowując nagrodę.

## Sterowanie

| Działanie | Klawiatura | Dotyk |
| --- | --- | --- |
| Ruch | WASD / strzałki | Joystick |
| Atak / umiejętność klasy | Spacja / F | Przyciski walki |
| Mikstura zdrowia / many | 1 / 2 | Mikstury |
| Leczenie / przyspieszenie | 3 / 4 | Pasek czarów lub księga |
| Czar zaawansowany / mistrzowski | 5 / 6 | Pasek czarów lub księga |
| Runa | 7 | Księga; WWW pozwala wybrać runę pod 7, Godot używa ognia |
| NPC / schody | E | Interakcja |
| Księga rozwoju i atlas | K | Księga |
| Zadania / ekwipunek / gracze | J / I / P | Przyciski HUD |
| Mapa | M | Mapa |
| Czat | Enter, tekst, Enter | Czat i wyślij |
| Zamknij panel / anuluj | Escape | Przycisk zamknięcia |

## PvP i śmierć

Pięć miast chroni obszar w promieniu 260. Postacie poniżej poziomu 8 nie uczestniczą w PvP. Atak gracza wymaga wyłączenia własnej ochrony przed przypadkowym atakiem i wybrania konkretnego celu; ochrona ta nie zapewnia nietykalności poza miastem.

Nieuzasadniona agresja daje białą czaszkę na 120 sekund. Trzy nieuzasadnione zabójstwa w 24 godziny dają czerwoną czaszkę na 24 godziny; kolejne przedłużają karę. Obrona przed oznaczonym agresorem nie karze ofiary. PvP blokuje wejście do strefy ochronnej i zmianę piętra przez 20 sekund. Każda walka blokuje usługi i bezpieczne wylogowanie przez 20 sekund; rozłączona postać pozostaje w świecie do końca blokady. Przed potworami można wycofać się do miasta.

Zwykła śmierć zabiera 5% niesionego złota i 10% postępu XP w bieżącym poziomie. Błogosławieństwo zmniejsza te straty o połowę i zużywa się przy śmierci. Czerwona czaszka wyłącza tę ochronę: kara to 20% złota, 20% bieżącego XP oraz jeden niewyposażony przedmiot, jeżeli jest w plecaku. Osiągnięty poziom nie spada. Zabicie gracza nie generuje złota ani XP. Odrodzenie następuje w wybranym mieście.

## Zachowanie istniejących postaci

Zatrzymaj stary serwer, skopiuj jego cały katalog `data` jako kopię zapasową, a kopię `world.sqlite3` umieść w `data` nowej paczki. Uruchom tylko jeden serwer na danej bazie.

Zapis 0.3 zachowuje konta, klasy, poziom, złoto, wyposażenie, mikstury, zadania, odkrycia i kary PvP. Nowe pola otrzymują wartości początkowe: brak promocji, brak run i specjalizacji, 100 duszy, pusty bank i depozyt, odrodzenie w Przystani. Współrzędne starej mapy pozostają ważne. Starsze migracje 0.1/0.2 są zachowane; postać 0.1 nadal otrzymuje jednorazowy wybór klasy w mieście. Powrót do starszego serwera wymaga przywrócenia kopii bazy.

## Godot i granice wydania

Zaimportuj `client/project.godot` w Godot 4.5.1 Standard. Uruchom oddzielnie serwer Python. Klient łączy się pod `ws://127.0.0.1:8080/ws` lub adresem własnego serwera. Instrukcja eksportu jest w `docs/BUILD.md`.

**50 testów serwera oraz 5 testów logiki klienta JS przeszło. Kod WWW i GDScript sprawdzono składniowo. Nie wykonano testu graficznego klienta 0.4.1, uruchomienia w silniku Godot ani testu na Androidzie.** Stare zrzuty i raporty 0.3 są wyłącznie archiwum w `docs/archive_0.3/`.

To rozbudowany prototyp. Nie ma jeszcze gildii, handlu gracz–gracz, odzyskiwania hasła, płatności ani reklam. Duża mapa wykorzystuje proceduralne powtórzenia; balans długich wypraw, różnorodność lokacji i wydajność na telefonach wymagają prób w grze.
