# Bractwo — Pogranicze · 0.3.0 — Wyprawy

Kolorowy prototyp otwartego RPG 2D inspirowanego klasyczną rozgrywką w stylu Tibii: **cztery klasy, poziomy bez limitu, odradzające się potwory, loot, drużyny i PvP z karami**. Aktualizacja dodaje zadania mieszkańców, atlas odkryć, różne tereny i nowe potwory. Mapa jest dostępna od początku.

Paczka zawiera klienta przeglądarkowego, serwer Python i źródła klienta Godot. Stan rzeczywistej weryfikacji jest w `docs/TEST_REPORT.md`. Nie jest to publicznie uruchomiony serwer ani gotowe wydanie na Google Play.

## Szybki start

Wymagany Python 3.11 lub nowszy. Pierwszy start wymaga internetu do instalacji aiohttp.

1. Rozpakuj **całą** paczkę.
2. Windows: uruchom `start_windows.bat`. Linux/macOS: `bash start_unix.sh`.
3. Pozostaw okno serwera otwarte i wejdź na **http://127.0.0.1:8080**.
4. Utwórz postać, wybierając nazwę, hasło i klasę.
5. Naciśnij **J** lub porozmawiaj ze strażniczką pod **E**. Przyjmij pierwsze zadanie; panel wypraw wskaże cel.
6. Do próby multiplayer otwórz drugą kartę i utwórz postać z inną nazwą.

Ręczne uruchomienie po zainstalowaniu zależności:

```bash
python -m pip install -r server/requirements.txt
python server/server.py --host 127.0.0.1 --port 8080 --db data/world.sqlite3
```

Do próby na telefonie w tej samej sieci Wi-Fi uruchom `start_windows.bat lan` lub `bash start_unix.sh lan`. Na telefonie otwórz `http://LOKALNY_IP_KOMPUTERA:8080`. Adres 127.0.0.1 na telefonie oznacza sam telefon. Obróć ekran poziomo. Tryb LAN udostępnia serwer w lokalnej sieci; publiczne połączenie powinno korzystać z HTTPS/WSS. Nie trzeba instalować aplikacji z Google Play.

## Co zmienia aktualizacja 0.3

- Jaśniejszy świat, brukowane drogi, domy w mieście, kolorowa roślinność, rozpoznawalne miejsca i nowi przeciwnicy.
- Dziennik pod **J**, wskaźnik następnego celu i trwały atlas odkryć. Zlecenia prowadzą od szczurów przez Stary Młyn i gobliny do ruin oraz bossa.
- Strzały i pociski magiczne lecą do celu zapisanego przy ataku. Późniejszy kierunek marszu nie zmienia ich trajektorii.
- Krąg ognia ma rozwijającą się animację; pozostałe umiejętności także otrzymują własne efekty.
- **Enter → wpisz wiadomość → Enter**. Tekst pojawia się nad głową postaci na 6 sekund i w czacie. Escape anuluje pisanie; skróty walki i ruchu są podczas niego wyłączone.
- Wolniejszy ruch początkującej postaci, rosnący stopniowo wraz z poziomem. Szybkość ustala serwer.

## Pierwsza wyprawa

Strażniczka zleca pokonanie trzech szczurów poza miastem. Przyjmij zlecenie przed polowaniem, a po zakończeniu wróć po nagrodę. Kolejne zlecenie prowadzi do Starego Młyna i zapewnia broń twojej klasy drugiego stopnia. Później pojawiają się obóz goblinów, ruiny ze szkieletami oraz zadanie na Władcę Twierdzy. Ostatnia wyprawa jest przeznaczona na później, najlepiej z drużyną.

Zadania są jednorazowe i nie blokują swobodnego polowania. Liczniki zabójstw ruszają po przyjęciu zlecenia; odkryte wcześniej miejsce może od razu spełnić cel. Nagrodę odbierasz przy wskazanym zleceniodawcy. Jeżeli gwarantowany przedmiot nie mieści się w plecaku, zwolnij miejsce i odbierz nagrodę ponownie — nie przepada.

Każde miejsce z atlasu ma opis i jednorazową nagrodę za podejście. Odkrycia, zadania i odebrane nagrody są zapisywane razem z postacią. Potwory nadal się odradzają, więc można farmić także po zakończeniu zleceń.

## Klasy i rozwój

| Klasa | Rola | Broń | Umiejętność F |
| --- | --- | --- | --- |
| Rycerz | Wytrzymały front | Miecz | Obrona i prowokowanie potworów |
| Paladyn | Dystans | Łuk | Silny strzał |
| Mag | Obrażenia obszarowe | Kostur | Atak obszarowy na potwory |
| Druid | Wsparcie | Kostur | Leczenie siebie i pobliskiej drużyny |

Klasy różnią się zdrowiem, maną, przyrostami i wyposażeniem. Klasa nowej postaci jest stała. **Poziomy nie mają zaprogramowanego maksimum**, ale ta paczka nadal ma jedną małą mapę i skończony zestaw potworów/przedmiotów.

Broń, pancerz i pierścień zmieniają statystyki. Przedmiot może wymagać odpowiedniej klasy i poziomu. Loot trafia indywidualnie do plecaka. Kupiec w mieście skupuje niewyposażony sprzęt i sprzedaje mikstury: zdrowia za 15 złota, many za 12. Na start masz po 3 mikstury obu rodzajów i 0 złota. Plecak mieści 40 przedmiotów łącznie z założonymi; dodatkowy wylosowany łup przepada z komunikatem, jeśli plecak jest pełny. Mikstury mają wspólny czas odnowienia 3 s i limit 99 sztuk każdego rodzaju. Statystyki i ceny rozstrzyga serwer.

Prędkość ruchu wynosi `100 + 90 × (poziom − 1) / (poziom + 79)` jednostek na sekundę. Przykładowo: poziom 1 → 100, 10 → 109,1, 50 → 134,2, 100 → 149,7. Przyrost stopniowo maleje, a szybkość zbliża się do 190. Jest to własna krzywa tego prototypu, nie odtworzenie wzoru Tibii. Poziomy pozostają bez limitu.

## Polowanie i współpraca

Wilki odradzają się po 16 s, ogniki po 20 s, strażnicy po 25 s, a boss po 90 s. Można zdobywać doświadczenie i loot podczas kolejnych polowań; pokonanie bossa nie kończy świata. Most i wejście do sanktuarium są otwarte od początku.

Drużynę tworzy zaproszenie oraz jawna akceptacja. Limit to cztery osoby. Drużyna dzieli pulę doświadczenia i złota w promieniu 650 jednostek od przeciwnika, poza miastem, przy różnicy poziomów najwyżej 3:1 pomiędzy nagradzanymi członkami. Do puli XP dochodzi 10% za każdego dodatkowego członka. Wymagany jest udział w walce członka drużyny w ostatnich 30 sekundach; pozostali pobliscy członkowie mogą pełnić rolę wsparcia. Każdy nagradzany gracz ma własną szansę na przedmiot. Zwykły loot ma szansę 35%, boss gwarantuje jeden przedmiot przy wolnym miejscu. Nie ma jeszcze handlu między graczami.

## Sterowanie

| Działanie | Klawiatura | Dotyk |
| --- | --- | --- |
| Ruch | WASD / strzałki | Joystick |
| Atak | Przytrzymaj Spację | Przytrzymaj Atak |
| Umiejętność klasy | F | Przycisk umiejętności |
| Mikstura zdrowia / many | 1 / 2 | Przyciski mikstur |
| NPC / kupiec | E | Przycisk interakcji |
| Dziennik wypraw | J | Dziennik |
| Czat | Enter, tekst, Enter | Czat i wyślij |
| Mapa | M | Mapa |
| Ekwipunek | I | Ekwipunek |
| Gracze i drużyna | P | Gracze |
| Wyczyść cel / zamknij panel | Escape | Odpowiedni przycisk panelu |

Zwykły atak wybiera potwora w zasięgu. **Gracza można zaatakować tylko po świadomym wyłączeniu ochrony PvP i wskazaniu konkretnego celu.** Klasy zastępują dawny swobodny przełącznik miecz/kostur. Umiejętności ofensywne w tej wersji służą PvE; PvP korzysta z bezpośredniego podstawowego ataku. Druid leczy siebie oraz członków drużyny w zasięgu 300. Leczenie innych postaci aktualnie walczących w PvP jest wyłączone; samoleczenie pozostaje dostępne.

## Zasady PvP i śmierci

Wartości startowe prototypu:

- Miasto jest strefą ochronną o promieniu 260 wokół punktu odrodzenia.
- Postacie poniżej **8. poziomu** nie uczestniczą w PvP.
- Ochrona przed przypadkowym atakowaniem graczy jest domyślnie włączona po logowaniu. Nie daje nietykalności poza strefą ochronną: blokuje własne rozpoczynanie ataków.
- Nieuzasadniony atak oznacza agresora białym oznaczeniem na **120 sekund**.
- Obrona przed oznaczonym agresorem nie nadaje broniącemu się białego oznaczenia.
- **3 nieuzasadnione zabójstwa w 24 godziny** dają czerwone oznaczenie na 24 godziny. Następne takie zabójstwa przedłużają karę.
- Po walce PvP trwa blokada wejścia do miasta przez **20 sekund**. Walka z potworami pozwala wycofać się do miasta. Każda walka blokuje handel/odpoczynek przez 20 s i pozostawia rozłączoną postać w świecie do końca blokady; dalsze trafienia mogą ją przedłużać.
- Zwykła śmierć kosztuje **5% niesionego złota i 10% bieżącego postępu XP w poziomie**. Nie obniża osiągniętego poziomu.
- Czerwono oznaczona postać traci **20% złota i 20% bieżącego postępu XP**, a także jeden niewyposażony przedmiot, jeśli ma taki w plecaku.
- Utracony przedmiot czerwono oznaczonej postaci trafia do zabójcy, jeśli ten ma miejsce; w innym przypadku przepada. Jeśli gracz zaatakuje ofiarę, a w ciągu 20 sekund dobije ją potwór, odpowiedzialność może nadal przypaść ostatniemu napastnikowi.
- Zabicie gracza nie daje XP i nie tworzy nagrody w złocie. Utracone złoto znika z gospodarki.

Oznaczenia i terminy kar są zapisywane. Nie usuwa ich restart serwera. Są to nasze robocze zasady do testowania; nie deklarują zgodności z zasadami Tibii.

## Wczytanie zapisu 0.1 lub 0.2

Zatrzymaj stary serwer i wykonaj kopię całego jego katalogu danych. Następnie użyj kopii pliku `world.sqlite3` z nowym serwerem, np. przez `--db data/world.sqlite3`. Nie uruchamiaj dwóch serwerów na tym samym pliku.

Aktualizacja zapisu 0.2 zachowuje konta, klasy, ekwipunek, mikstury, postęp oraz kary PvP; dodaje pusty dziennik i atlas odkryć. Migracja z 0.1 zachowuje nazwę, poziom, doświadczenie i złoto, a dawna postać otrzymuje jednorazowy wybór klasy w mieście. Dawne relikty i jednorazowe otwarcie świata nie są już potrzebne. Po migracji nie uruchamiaj starej wersji na zmienionej bazie; do powrotu użyj kopii zapasowej.

Hasła nie są zapisywane w przeglądarce. Prototyp nie ma odzyskiwania hasła. Połączenie przez publiczny internet wymaga TLS; lokalny tryb testowy korzysta z HTTP/WS.

## Godot i Android

Zaimportuj `client/project.godot` w Godot 4.5.1 Standard. Uruchom osobno serwer Python, a w kliencie podaj `ws://127.0.0.1:8080/ws` lub adres swojego serwera. Ten sam świat obsługuje oba rodzaje klienta.

**Źródła Godot są dołączone, ale tej wersji nie uruchomiono w silniku ani na fizycznym Androidzie. APK/AAB i Windows EXE nie są dołączone.** Do eksportu potrzebne są odpowiednie szablony Godot oraz, dla Androida, JDK i Android SDK. Szczegóły w `docs/BUILD.md`.

## Zakres i dalsze prace

Wersja 0.3 to nadal jedna mapa prototypu z ograniczoną pulą wyposażenia. Nie zawiera gildii, handlu między graczami, odzyskiwania kont, płatności ani reklam. Nie przeprowadzono testu pojemności publicznego serwera. Kod i dane tego projektu nie zmieniają Alien Colonies.
