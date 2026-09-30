# Bractwo Krain 0.8.18 UI_25

## Nazwa i ikony

Gra nazywa się **Bractwo Krain**. Zmieniono ekran logowania, pasek gry, tytuł karty przeglądarki, nazwę instalowanej aplikacji PWA i ekran braku połączenia. Nazwa została także poprawiona w historycznych źródłach Godota. Istniejące klucze ustawień, baza oraz zmienne Railway pozostają zgodne z poprzednią wersją.

Górne przyciski otrzymały osobne, czytelne ikony SVG: karta z postacią, otwarta księga dziennika, drużyna, kompas minimapy, składana mapa atlasu, pomoc, drzwi wylogowania, pełny ekran i instalacja. Na telefonie zachowano tekstowe etykiety menu, a na komputerze podpowiedzi i skróty klawiszowe.

## Usługi NPC po prawej

Kliknięcie NPC lub rozmowa klawiszem **E** otwiera panel tej konkretnej postaci:

| Postać / obiekt | Zawartość panelu |
| --- | --- |
| Kupiec | Kupuj / Sprzedaj; towary wybranego kupca |
| Bankier | Bank / Depozyt; w depozycie osobno odkładanie i zabieranie |
| Mistrz profesji | Promocja / Błogosławieństwo / Mistrzostwo |
| Przewoźnik | Wyłącznie miejscowe połączenia, cena i przycisk Wypłyń |
| Kamień przypisania | Obecne miejsce odrodzenia i potwierdzenie nowego przypisania |

Panel pokazuje jedną usługę naraz. Dawna zakładka zbiorcza jest teraz przewodnikiem po miejscowych usługach, z wyznaczaniem drogi i otwieraniem pobliskiej postaci. Dialogi i zadania mają oddzielną rozmowę. Zwykłe listy przedmiotów mogą przewijać się wewnątrz swojego panelu.

Przyciski uwzględniają odległość, piętro, śmierć, blokadę walki, wymagany poziom, złoto i stan usługi. Serwer nadal sprawdza wszystkie warunki. Panel kupca i operacje banku odnoszą się do wskazanego NPC; nie wybierają innego kupca tylko dlatego, że stoi obok. Panele można zamknąć krzyżykiem lub Escape, a po odblokowaniu układu przesuwać jak inne okna.

## Bezpieczne przystanie

Wszystkie **20 przystani** ma ochronę obejmującą przewoźnika, punkt przybycia i cały pomost. Granice są widoczne w świecie, a HUD pokazuje „Bezpieczna przystań”. Potwory nie mogą wejść do strefy, a punkty ich pojawiania znajdują się poza ochroną.

Obowiązują dotychczasowe zasady stref bezpiecznych: nie można stamtąd atakować, a blokada walki PvP zabrania wejścia do ochrony. Podróż nadal wymaga zakończenia walki i odpowiedniej ilości złota. Zalecany poziom miejsca docelowego pozostaje informacją, nie blokadą rejsu.

## Kamienie przypisania odrodzenia

W każdym z **10 miast** stoi widoczny, runiczny **Kamień przypisania**. Podejdź, kliknij kamień albo naciśnij E, a następnie wybierz **Przypisz odrodzenie**. Jest to bezpłatne i możliwe poza walką. Po śmierci postać odradza się przy przypisanym kamieniu.

Samo wejście do miasta, odkrycie go, logowanie w mieście ani przeprawa łodzią nie zmieniają przypisania. Bankier nie przypisuje już miasta. Serwer akceptuje wyłącznie użycie rzeczywistego, pobliskiego kamienia na tej samej kondygnacji.

Postacie zachowują dotychczas zapisane miasto jako początkowe przypisanie. Zmienią je dopiero przez użycie innego kamienia. Nowe postacie zaczynają z przypisaniem do Przystani. Nie jest potrzebny reset zapisu.

## Google i istniejące postacie

Usunięto opcję **Dodaj dotychczasową postać**, pole starego hasła i obsługę przypisywania starego zapisu na serwerze. Po zalogowaniu Google można wybrać postać należącą do konta albo utworzyć nową, w limicie **4 postaci**.

Postacie wcześniej prawidłowo powiązane z kontem Google nadal działają i zachowują postęp. Niepowiązane stare zapisy nie są kasowane, ale nie można ich już samodzielnie przypisać. Dotychczasowe powiązania, identyfikatory postaci i konfiguracja Google nie są zmieniane. Nazwa aplikacji w zewnętrznym projekcie OAuth nie jest ustawiana przez tę paczkę.

## Wgranie aktualizacji i kontrola

Wgraj całą zawartość **BRACTWO_KRAIN_0.8.18_UI_25_RAILWAY_GITHUB_READY.zip** do głównego katalogu repozytorium serwera, zachowując bazę, trwały wolumen i zmienne środowiskowe. Serwer oraz klient muszą pochodzić z tej samej paczki. Po aktualizacji odśwież stronę: ekran wejścia i `/health` wskazują **UI_25**.

Zachowano cztery szkoły czarodzieja z UI_24, wymaganie promocji od poziomu 10, kręgi druidów, osobne grafiki demonów oraz wcześniejsze zmiany świata, łupów i czarów.

Raport: `docs/qa_0.8.18/ui25/summary.json`. Przeglądarka była sprawdzana przez produkcyjne HTTP/WebSocket z osobną bazą i jawnym testowym dostawcą Google, na desktopie oraz w emulacji telefonu 430 px. Nie wykonano rzeczywistego logowania Google, testu na fizycznym telefonie ani automatycznego wdrożenia Railway. FULL_SOURCE nadal zawiera historyczny klient Godota bez integracji Google; nie jest to nowy APK.
