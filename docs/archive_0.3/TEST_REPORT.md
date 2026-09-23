# Raport weryfikacji · 0.3.0

Data: 22 września 2026. Linux, Python 3.12.14, aiohttp 3.13.5, Chromium 153.0.8010.0 + Playwright.

## Serwer: 33 testy integracyjne — zaliczone

Polecenie: `python -m unittest discover -s tests -v`. Ostatnie pełne wykonanie: **33/33, około 3,6 s**. Testy używają prawdziwych lokalnych WebSocketów, tymczasowych baz SQLite i kontrolowanego zegara dla terminów kar/cooldownów.

Nowe sprawdzenia aktualizacji 0.3:

- Ruch odpowiada krzywej poziomu, przekątna jest normalizowana, klient nie może narzucić szybkości.
- Ruch maga po strzale nie zmienia kierunku celowania ani zapisanych współrzędnych efektu; trafienie i cooldown pozostają serwerowe.
- Krąg ognia tworzy zdarzenie animacji i trafia tylko uprawnione potwory w zasięgu. Klient nie może podrobić efektu ani obrażeń.
- Czat identyfikuje nadawcę, usuwa znaki sterujące i wygasza wypowiedź nad postacią po 6 sekundach.
- Zadania sprawdzają zleceniodawcę, zasięg, poprzednie zadania i rzeczywiste zabójstwa. Powtórna komenda nie powiela nagrody.
- Postęp, odebrane nagrody i odkrycia przetrwały restart; wcześniejsze odkrycie zalicza później przyjęty cel.
- Pełny plecak pozostawia gwarantowaną nagrodę u zleceniodawcy; po zwolnieniu miejsca można ją odebrać.
- Wspólna walka zalicza zadanie tylko członkom drużyny uprawnionym do nagrody i posiadającym przyjęte zlecenie.
- Odrzucane są fałszywe liczniki i nagrody, nieznane zadania oraz akcje martwej postaci.
- Metadane obejmują zróżnicowane tereny, potwory i prawidłowe cele zleceń.

Zachowane sprawdzenia wersji 0.2:

- Cztery różne klasy, stałość wyboru, mana, umiejętności, sprzęt i wymagania przedmiotów.
- Rozwój wysokopoziomowej postaci bez limitu, otwarta mapa i nagrody za kolejne odrodzenia bossa.
- Powtórzenie sprzedaży nie powiela złota; mikstury i czasy odnowienia przetrwają ponowne logowanie i restart.
- Drużyna wymaga akceptacji; dzieli nagrody tylko pomiędzy uprawnionych pobliskich członków. Druid leczy drużynę. Limit różnicy poziomów działa także dla układu 1/3/9.
- Własny plecak nie jest wysyłany pozostałym graczom.
- PvP wymaga wskazanego celu, wyłączonej blokady, odpowiedniego poziomu i przebywania poza miastem.
- Odwet na oznaczonym napastniku nie tworzy nieuzasadnionego zabójstwa. PvP nie daje XP ani nagrody w złocie.
- Trzy nieuzasadnione zabójstwa dają trwałe czerwone oznaczenie. Czerwona śmierć nalicza właściwą karę i przenosi jeden niewyposażony przedmiot, jeśli są spełnione warunki.
- Potwór dobijający ofiarę świeżej agresji nie pozwala ominąć odpowiedzialności napastnika; przypisanie wygasa po określonym czasie.
- Rozłączona postać w walce pozostaje celem. Ponowne logowanie zachowuje obrażenia i cooldowny; nie uzdrawia ani nie teleportuje do miasta.
- Dawny zapis 0.1 zachowuje postęp i ma dokładnie jeden wybór klasy w mieście.
- Zachowano ochronę przed fałszowaniem pozycji/statystyk, błędnymi pakietami, podwójnym logowaniem i cofnięciem zapisu podczas sprawdzania hasła.

W części testów ustawiane są pozycje i poziomy po stronie testowego serwera. Nie jest to funkcja dostępna graczom ani endpoint administracyjny.

## Naturalna pierwsza wyprawa — rycerz i mag

`python tools/check_expedition.py`: dwie świeże postacie przechodzą zwykłymi komendami od przyjęcia zadania szczurów, przez polowanie i odbiór nagrody, do odkrycia Starego Młyna, powrotu, odbioru i założenia broni swojej klasy oraz zakupu mikstury. Bez teleportacji, dodawania XP, podnoszenia poziomu ani ustawiania pozycji przez test. Zegar symulacji jest przyspieszony.

| Klasa | Czas symulacji | Poziom | Zabójstwa | Złoto po zakupie | Najniższe HP na początku |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rycerz | 44,2 s | 3 | 4 | 65 | 146 / 150 |
| Mag | 45,8 s | 3 | 4 | 65 | 82 / 85 |

Obie postacie ukończyły `q_rats` i `q_mill`, odkryły młyn, założyły broń drugiego stopnia i miały szybkość około 102,2. Nie zginęły ani nie potrzebowały mikstury zdrowia. Czas dotyczy zoptymalizowanej trasy testowej, a nie pierwszej sesji człowieka.

Dodatkowo sprawdzono przechodniość mapy od punktu startowego: wszystkie trzy NPC i sześć punktów odkryć są dostępne, a 28 punktów odrodzenia potworów nie znajduje się w kolizjach.

## Klient WWW: 15 sprawdzeń scenariusza — zaliczone

`tools/browser_smoke.cjs` uruchomiono przez `tools/run_browser_smoke.py` z osobną bazą. Końcowe wykonanie zakończyło się `ok: true`, bez błędów JavaScript strony. Pełny raport jest w `browser-report.json`.

1. Enter bezpośrednio po logowaniu otwiera pole czatu. Pisanie WASD, F, spacji i cyfr nie wysyła ruchu, ataku ani użycia mikstur. Escape anuluje bez wysyłania.
2. Rycerz i druid otrzymują różne statystyki w tym samym świecie.
3. Początkowy ruch wynosi około 100 jednostek/s i jest widoczny u drugiego gracza.
4. E przy kupcu otwiera handel pomimo pobliskiego NPC. Zdjęcie/założenie pancerza zmienia statystyki, a zakup bez złota jest zablokowany.
5. Zaproszenie i akceptacja drużyny działają między desktopem i klientem dotykowym.
6. Enter działa także przy fokusie na przycisku HUD. Drugi klient otrzymuje wypowiedź, rzeczywiście rysuje ją nad postacią i zachowuje w czacie.
7. Emulowany dotyk porusza postacią; desktop, oba układy telefonu i mobilny ekwipunek nie przepełniają strony poziomo.
8. Wybranie celu i przełącznik PvP działają; chroniona postać w mieście nie otrzymuje obrażeń, a agresor oznaczenia.
9. Ponowne logowanie zachowuje konto/klasę i przywraca blokadę PvP. Hasło nie trafia do localStorage.
10. E przy zleceniodawcy otwiera dziennik; przyjęcie zadania aktualizuje wskaźnik celu, a J ponownie otwiera postęp.
11. Świeży rycerz zwykłym sterowaniem zabija trzy szczury, zdobywa poziom i wzrost szybkości, wraca do NPC po nagrodę. Odbiór z oddali jest wyłączony.
12. Wyprawa do młyna zapisuje odkrycie w atlasie. Powrót daje broń klasy; założenie jej na osiągniętym 3. poziomie zwiększa atak o 5. Odblokowuje się wyprawa do goblinów.
13. Mag strzela podczas ruchu w bok: kierunek ataku odpowiada faktycznemu przeciwnikowi, jest inny niż kierunek chodu, a początek/koniec efektu pozostają niezmienne w kolejnych stanach.
14. Krąg ognia generuje widoczny efekt w dwóch fazach, zużywa manę i uruchamia odnowienie. Skrót mikstury zużywa posiadaną sztukę.
15. Przez interfejs utworzono wszystkie cztery klasy; paladyn otrzymał łuk.

Przejrzano zrzuty 1440×900, 844×390 i 390×844, w tym mowę drugiego gracza, dziennik, młyn oraz dwie różne klatki kręgu ognia. Na małych ekranach ograniczono komunikaty i odsunięto podpowiedź interakcji od czatu. Obrazy w `screenshots/` pochodzą z końcowego sprawdzenia. Wczesne uruchomienia wymagały doprecyzowania testowej trasy obok domów i podejścia do NPC; końcowy scenariusz używa normalnych klawiszy, bez zmiany pozycji przez test.

Pełne zasady zabójstw PvP i trwałości kar sprawdza zestaw serwera. Przeglądarka sprawdza kontrolki PvP oraz ochronę początkujących. Przeglądarkowa wyprawa obejmuje pierwsze dwa zadania; późniejsze cele mają testy reguł serwera i przechodniości mapy, bez pełnej długiej sesji gry.

## Godot i granice sprawdzenia

Wszystkie cztery pliki GDScript przeszły `gdparse`. Kod WWW przeszedł `node --check`, Python kontrolę składni, skrypt startowy kontrolę Bash.

**Nie uruchomiono klienta Godot i nie wykonano eksportu APK/AAB/EXE.** Parser składni nie zastępuje silnika. Nie testowano fizycznego telefonu, mobilnej sieci, Safari/iOS, opóźnień internetu, dużej liczby graczy ani długich sesji.

To nadal prototyp: jedna mapa z siedmioma regionami, sześcioma odkryciami i pięcioma zadaniami, ograniczona pula wyposażenia, ofensywne umiejętności tylko PvE, leczenie innych uczestników PvP wyłączone. Brak gildii, handlu gracz–gracz, płatności i odzyskiwania kont. Pojemność publicznego serwera i balans przy długim farmieniu wymagają późniejszych prób.
