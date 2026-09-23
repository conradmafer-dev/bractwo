# Bractwo — Pogranicze · 0.6.0 — Szczyty i Głębiny

Otwarty RPG 2D: cztery profesje, dalekie wyprawy, polowania, rozwój przez używanie umiejętności, podziemia, runy, drużyny i PvP. Aktualizacja rozwija kierunek inspirowany Tibią, z własną mapą, grafiką i balansem.

**Świat ma 128 000 × 92 160 jednostek — 1600 razy większą powierzchnię niż mapa 0.3.** Pięć miast jest rozmieszczonych na odległych krańcach kontynentu. Rozsunięto odległości, zachowując normalne rozmiary domów, postaci i komnat.

Paczka zawiera pełny serwer Python, klienta WWW i źródła Godot. Nie zawiera APK/AAB/EXE. Weryfikację i jej ograniczenia opisuje `docs/TEST_REPORT.md`.


## Nowe w 0.6.0

- **Rzeczywiste piętra +1, +2, +3:** 9 wzniesień, 23 tarasy; schody w obie strony, skalne krawędzie, przeciwnicy i skrytki na szczytach. Poziom wyświetla HUD i mapa. Nie można chodzić poza obrysem tarasu ani atakować między piętrami.
- **Boss ponownie podchodzi i uderza z bliska.** Każdy boss oraz goblin, plujący pająk, cyklop, ogr, harpia, smok, smoczy lord, demon i wędrowiec otchłani mają walkę mieszaną. Zwykły pocisk ma osobne odnowienie i pozwala podchodzić podczas rzutu. Specjalny atak bossa zatrzymuje go tylko na krótki czas zapowiedzi. Łucznicy i typowi czarodzieje zachowują przewagę dystansu, z awaryjnym ciosem przy zwarciu.
- **Rzeka przez kontynent:** ponad 106 tys. jednostek nowego, krętego koryta; woda blokuje ruch i linię strzału. Widoczne mosty łączą przecinające ją drogi. Cztery wąwozy mają prawdziwe skalne ściany i wijące się przejścia.
- **Cztery nowe zejścia:** Zalana Kopalnia, Krypty Przełomu, Korzenie Starego Lasu, Szczelina Mrozu. Każde ma dwie połączone kondygnacje pod ziemią. Łącznie 15 podziemi i 106 kierunkowych przejść.
- **30 miejsc do użycia pod E:** 13 skrytek, 9 kamieni wiatru, 4 źródła, 4 kapliczki. Źródło odnawia HP i manę (co 3 min); wiatr daje +15% ruchu na 90 s (co 5 min); osłona redukuje obrażenia od potworów o 12% na 90 s (co 5 min). Skrytka odnawia się co 30 min, wymaga 3 wolnych miejsc. Wszystkie wymagają odpowiedniego poziomu i zakończenia walki. Terminy są osobiste i zapisane na serwerze.
- **49 nowych przedmiotów, 102 łącznie:** trofea pasujące do gatunku, broń czterech profesji i pierścienie o różnej rzadkości oraz legendarny relikt. Zwykły potwór: wyposażenie 12%, trofeum 24%, mikstura 7%; odpowiednio silny gatunek: przedmiot rodowy 1,5%. Boss: wyposażenie 100%, trofeum 80%, mikstura 35%, uprawniony przedmiot rodowy 8%; boss poziomu 110+: relikt 0,2%. To niezależne rzuty, bez gwarancji po określonej liczbie zabójstw. Szczegóły gatunków: `docs/BESTIARY_0.6.md`.
- **Zachowany styl i jakość grafiki.** Nowe obiekty korzystają z tych samych procedur rysowania. Geometria wody i kolizje mają indeksy przestrzenne; teren nadal korzysta z pamięci podręcznej. Licznik FPS pozostaje w rogu. Nie deklarujemy FPS bez pomiaru na urządzeniu.

Najbliższe nowe wejścia: Strażnica nad Przełomem **(4200, 3000)**, Tarasy Cyklopów **(5963, 3933)**, Trzy Iglice Harpii **(7000, 1550)**. **K → Atlas → Okolica** wyznacza kierunek. Schody i ciekawe obiekty obsługujesz klawiszem **E** lub przyciskiem interakcji.

## Zachowane mechaniki świata

- **48 gatunków, w tym:** bandyta łucznik, szkielet łucznik, plujący pająk, cyklop, niedźwiedź, harpia, ghul, ogr i skorpion. Łącznie 48 typów faktycznie występujących w świecie.
- **Pierwsza wyprawa ma więcej celów:** rozbity wóz bandytów, pajęczy zagajnik, cmentarz, cyklopie wzgórze, harpie na grani, niedźwiedzia barć i smocza jama. **K → Atlas → Okolica** podaje kierunki i zalecany poziom. Silne boczne siedliska można ominąć.
- **Żyjące siedliska:** nieregularne pozycje i patrolowanie przed walką, logiczne mieszane grupy. Zwierzęta mają nory, kości, gniazda lub pajęczyny; namioty i ogniska występują u bandytów, goblinów oraz orków.
- **Walka:** wykrywanie gracza z 380–620 jednostek, przed zasięgiem łuku 310. Część przeciwników strzela z 350–440, rzuca głazami, pluje jadem lub czaruje. Inni podbiegają do walki wręcz. Szybkość zależy od gatunku, nie wyłącznie poziomu.
- **Bossowie:** ostrzegane pola uderzenia, salwy, fala wokół bossa, smoczy oddech i lodowa lanca. Cel zostaje ustalony przy rozpoczęciu ataku — trzeba zejść z oznaczonego miejsca. Poniżej 40% HP specjalne ataki są częstsze. Wycofujący się przeciwnik szybko odzyskuje zdrowie; ostrzał na granicy terytorium nie jest darmowym sposobem na bossa.
- **Kręte, rozgałęzione szlaki**, kamienne wzgórza, blokujące skały i góry, błotniste rozlewiska, ruiny, kości, kryształy i nowe wejście do smoczych podziemi. Duży kontynent i odległości pięciu miast pozostają.
- **Ruch po terenie:** ścieżka +18%, kamień +25%, trawa normalnie, ściółka −6%, piasek −14%, śnieg −12%, popiół −10%, błoto −28%. Te same mnożniki dotyczą potworów. HUD pokazuje podłoże i aktualną szybkość.
- **K → Premium:** „10 zł / miesiąc”, +20% szybkości, obecnie **bezpłatna symulacja na 30 dni**. Włączenie i wyłączenie są dostępne w księdze. Bez płatności, karty, pobierania złota ani automatycznego odnowienia. Termin zapisuje serwer; stare konta nie otrzymują bonusu automatycznie.
- Zachowano styl, tekstury proceduralne, efekty, licznik FPS, wybór celu oraz optymalizacje 0.4.1. Dodano lokalny indeks podłoża i dróg; potwory poza otoczeniem graczy nie obciążają symulacji patrolami. Nowe duże gatunki mają odpowiednio większe sylwetki i obszar wyboru.

**Aktualizuj jednocześnie serwer i klienta.** Zatrzymaj starą wersję i skopiuj jej bazę `data/world.sqlite3` do nowej paczki, zachowując kopię zapasową. Konta i postęp 0.3–0.5.0 są zachowane. Jeśli nowa przeszkoda pokrywa zapisane miejsce postaci, ponowne logowanie poza blokadą walki przeniesie ją do Przystani.

## Uruchomienie

1. Rozpakuj całą paczkę. Wymagany Python 3.11+.
2. Windows: `start_windows.bat`. Linux/macOS: `bash start_unix.sh`.
3. Zostaw okno serwera otwarte i wejdź na **http://127.0.0.1:8080**.
4. Utwórz postać: nazwa, hasło i klasa. **J** otwiera zadania, **K** księgę czarów, rozwoju, atlasu i usług.
5. Pierwsze zadania strażniczki w Przystani prowadzą na szczury, do Starego Młyna, goblinów i ruin. Dodatkowe lokalne miejsca znajdziesz w K → Atlas → Okolica; kolejne miasta nadal leżą daleko.

Pierwszy start pobiera zależność aiohttp. Ręcznie:

```bash
python -m pip install -r server/requirements.txt
python server/server.py --host 127.0.0.1 --port 8080 --db data/world.sqlite3
```

Na telefonie w tej samej sieci Wi-Fi: uruchom `start_windows.bat lan` albo `bash start_unix.sh lan`, a na telefonie otwórz `http://LOKALNY_IP_KOMPUTERA:8080`. Obróć ekran poziomo. Adres 127.0.0.1 na telefonie oznacza telefon. Dla publicznego serwera potrzebne są HTTPS/WSS. Druga karta z inną postacią umożliwia próbę multiplayer.

### Publiczna wersja WWW na Railway

Paczka zawiera `Dockerfile` gotowy dla Railway. Serwer automatycznie korzysta z przydzielonego `PORT`, a klient WWW łączy się z tym samym hostem przez `wss://.../ws`. Po podłączeniu Railway Volume serwer automatycznie zapisuje SQLite w `RAILWAY_VOLUME_MOUNT_PATH`. Szczegółowa instrukcja: `docs/RAILWAY_DEPLOY.md`.

## Kontynent i podróże

- **20 krain**, od Marchii Przystani i Borów Szeptów po Smocze Urwiska i Morze Popiołu.
- **5 miast:** Przystań, Brzezina, Złoty Port, Mroźna Przystań i Popielny Port. Każde ma strefę ochronną, kupca, kapitana, bankiera i mistrza profesji.
- **15 podziemi po 2 piętra:** kopalnie, groty, twierdza, piramida, krypty, pałac lodu, smocze gniazdo i otchłań. Schody mają rzeczywiste przejścia i powrót; ściany zatrzymują ruch oraz ataki.
- **4169 siedliska**, 11130 punktów odrodzenia, 48 typów przeciwników, 120 odkryć i 30 zadań. Rozmieszczenie jest deterministyczne, a gatunki dobierane według siedliska; to nadal proceduralny kontynent z ręcznie ustawionymi lokalnymi przygodami.
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

Poziomy postaci nie mają maksimum. Dostępna zawartość ma skończony zakres, do krain zalecanych na poziomy 110–150. Przedmioty mają 102 szablony i wymagania do poziomu 110; nie skaluje się automatycznie z postacią.

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
| NPC / schody / źródła / skrytki | E | Interakcja |
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

**71 testów serwera oraz 7 testów logiki JS przeszło.** Python i JS zgodnie rozpoznają podłoże w tysiącach punktów rzeczywistej mapy. Sprawdzono składnię JS, Python i wszystkich 7 skryptów GDScript. Szczegóły: `docs/TEST_REPORT.md`.

Nie wykonano graficznego uruchomienia tej wersji w przeglądarce, silniku Godot ani na Androidzie. Zrzuty w `archive_0.3` są wyłącznie historyczne.

To rozbudowany prototyp. Nie ma jeszcze gildii, handlu gracz–gracz, odzyskiwania hasła, płatności ani reklam. Duża mapa korzysta z powtarzalnych szablonów siedlisk; balans długich wypraw i płynność na konkretnych urządzeniach wymagają dalszych prób w grze.
