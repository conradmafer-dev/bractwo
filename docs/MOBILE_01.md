# Bractwo 0.8.17 — Mobile01

Bazą tej aktualizacji jest paczka `BRACTWO_0.8.17_ROZDZKA_PRIORYTET_CZAROW_FULL_SOURCE.zip`. Mobile01 porządkuje interfejs przeglądarkowej wersji gry na telefonie, w orientacji poziomej i pionowej.

## Zmiany widoku

- Kompaktowy panel postaci oraz minimapa zostawiają więcej miejsca na świat gry.
- Joystick, atak i interakcja mają stałe miejsca przy dolnych krawędziach ekranu.
- Wszystkie zajęte sloty czarów tworzą jeden przewijany poziomo rząd. Obejmuje on również czary przypisane do F1–F12; puste sloty są ukryte.
- Menu z opisanymi przyciskami i czat otwierają się na żądanie.
- Ustawienia widoczności paneli są zapisywane osobno dla widoku mobilnego. Powrót do widoku komputerowego przywraca jego zapisany układ.
- Okna na telefonie korzystają z dostępnej powierzchni ekranu, a stałych elementów HUD nie można przypadkowo przeciągnąć.

Reguły różdżki, priorytet czarów, zużycie i przyrost many pozostają takie jak w wersji 0.8.17. Nie zmieniono schematu zapisu ani układu natywnego klienta Godot.

## Instalacja na istniejącej wersji 0.8.17

1. Zatrzymaj serwer i zachowaj dotychczasową bazę `data/world.sqlite3` oraz wolumen danych. Wykonaj kopię bazy przed aktualizacją.
2. Podmień cały katalog `web` oraz plik `server/server.py`. Zmiana tego pliku serwera dodaje wyłącznie trasy nowych zasobów `mobile.css` i `mobile.js`.
3. Uruchom serwer ponownie.
4. Odśwież stronę gry z pominięciem pamięci podręcznej. Na komputerze można użyć Ctrl+F5; na telefonie w razie potrzeby zamknij kartę i otwórz stronę ponownie.

Baza graczy pozostaje bez zmian; reset postaci nie jest potrzebny. Archiwum FULL_SOURCE zachowuje katalog główny `Bractwo_0.8.17/`.

## Sprawdzenie

- 35/35 istniejących testów JavaScript, 7/7 testów Python z `test_hud_089.py` oraz kontrola składni zmienionych skryptów: wynik poprawny.
- Nowe zasoby `mobile.css` i `mobile.js`: odpowiedź HTTP 200, zgodna treść i nagłówki typu oraz cache.
- Układ telefonu: 734×260, 568×280, 915×330, 844×390, 667×375, 390×844 i 360×640. Zmierzone kontrolki mieszczą się na ekranie, a główne przyciski pozostają dostępne.
- Interakcje: menu, czat, czat nad kartą postaci, księga czarów, dostęp do zajętego slotu F12 po przewinięciu oraz ruch postaci przez dotykowy joystick.
- Komputer: 1440×900, osobny kontekst bez emulacji dotyku. Po przejściu komputer → telefon → komputer panel wraca dokładnie na zapisaną pozycję (712, 320), z szerokością 280 px i wysokością 89 px. W telefonie ta pozycja nie jest stosowana.

Raport zbiorczy: `docs/qa_mobile/browser_results.json`; osobny końcowy test przywracania panelu: `docs/qa_mobile_profile/browser_results.json`. Raport zachowuje informację o wykrytym i poprawionym błędzie przywracania szerokości przed pomiarem wysokości.

Testy przeglądarkowe wykonano w Chrome z emulacją rozmiaru ekranu i dotyku, na rzeczywistym kodzie klienta i izolowanym serwerze gry połączonym przez most WebSocket w Pythonie. Nie jest to pomiar wydajności ani test na fizycznym telefonie. Zrzuty ekranu znajdują się obok raportów.

Historyczna dokumentacja i wyniki walidacji bazowej wersji 0.8.17 pozostają w README oraz pozostałych plikach projektu.

## Utworzenie paczki źródłowej

Skrypt `tools/package_mobile.ps1` tworzy archiwum `BRACTWO_0.8.17_MOBILE_01_FULL_SOURCE.zip` w katalogu nadrzędnym projektu i aktualizuje `SOURCE_MANIFEST.json`. Hashe SHA-256 dotyczą plików faktycznie umieszczonych w archiwum; manifest nie zawiera własnego hasha.

Skrypt pomija lokalne środowiska, katalogi danych graczy, cache, repozytorium Git, archiwa ZIP i tymczasowe logi. Do zastąpienia wcześniej utworzonej paczki służy parametr `-Force`.
