# Bractwo 0.8.18 UI_21 — magia i żywioły

UI_21 rozwija oprawę czarów na podstawie przeglądu wszystkich 99 pozycji
aktualnego katalogu serwera, w tym przemian, rytuałów i zdolności kręgów.
Jest kontynuacją UI_20: geografia, przeciwnicy, łupy i przeprawy pozostają
w paczce. Numer wersji świata pozostaje 20; nie potrzeba resetu postaci.

## Najbardziej widoczne zmiany

- **Wezwanie błyskawicy:** piorun schodzi z góry, rozgałęzia się i rozchodzi
  po ziemi w granicach trafienia. Osobny event odpowiada każdemu rzeczywistemu
  rzuceniu lub ponowieniu; dekoracja nie tworzy samoczynnych wyładowań.
- **Żywioły:** płomienie i iskry kuli ognia, ogniste panele burzy,
  spadające odłamki lodu, rozgałęziony łańcuch błyskawic, rozprysk kwasu,
  fale gromu, słoneczne promienie i nekrotyczne więdnięcie.
- **Natura i wsparcie:** elastyczny cierniowy bicz, rosnące pnącza,
  warstwy kory i kamienia, symbol wskazówek, świetlne więzy, wstęgi leczenia,
  przemiany oraz efekty w miejscu startu i końca teleportacji.
- **Żywe pola:** mgła i trująca chmura, sieci pajęcze, grad, owady,
  wiatr, uszkadzane kamienne ściany, duchowe zwierzęta, cztery żywiołaki
  i cztery odmiany kontroli wody mają własne motywy.
- **Rzeczywiste trafienia:** osobne krótkie efekty dla okresowych obrażeń,
  brakujące animacje gwiezdnej strzały i kroku przez drzewa,
  poprawne punkty obszaru snu, roztrzaskania i fali gromu.
- **Ikony:** uzupełniono 21 brakujących grafik zaklęć kręgów, między innymi
  mgły, pajęczyny, plagi owadów i kontroli wody, w obu klientach.

## Zgodność obrazu z walką

Serwer nadal wyznacza trafienia i rozmiary obszarów. Obrysy korzystają z jego
kół i wielokątów. W przypadku żywych pól podstawą jest aktualny stan pola,
a przerwanie koncentracji kończy jego widoczność. Efekty poszczególnych trafień
są oddzielone od stałej dekoracji. Jeden obszar nie otrzymuje dwóch nakładających
się animacji podłoża.

Wezwanie błyskawicy działa przy rzuceniu i ponowieniu czaru, zgodnie z obecną
mechaniką gry. Promień księżyca i inne pola okresowe pokazują impuls wtedy,
gdy serwer rzeczywiście rozlicza trafienie. Zmiany nie zwiększają obrażeń,
częstotliwości ataków, zasięgu ani kosztu czarów; nie zmieniają testów obrony.

Dekoracje mają ograniczoną liczbę cząstek i segmentów niezależnie od powiększenia
obszaru. Klient pomija efekty poza widokiem z zachowaniem ich czasu życia oraz
wiązek przecinających ekran. Brak pełnoekranowych błysków i nowych tekstur do
pobierania. Pomiar przeglądarkowy dotyczy środowiska testowego, nie fizycznego
telefonu.

## Wdrożenie i źródła natywne

Wgraj kompletną paczkę RAILWAY_GITHUB_READY do głównego katalogu repozytorium
i wdrażaj serwer razem z klientem. Zachowaj bazę, wolumen oraz zmienne środowiska.
Po aktualizacji odśwież stronę i zaloguj się ponownie. Ekran logowania,
`/health` i cache przeglądarki wskazują UI_21. Automatyczne wdrożenie nie zostało
wykonane.

FULL_SOURCE zawiera również zmiany rendererów Godota oraz wszystkie testy
i narzędzia. Klient natywny wymaga ponownego importu projektu i eksportu.
Silnik Godota nie był dostępny w tej sesji: źródła natywne podlegają przeglądowi
kodu, ale nie deklarujemy testu uruchomieniowego ani nowego APK.

## Raporty

- `docs/UI_21_SPELL_AUDIT.md`: cały katalog i przegląd dróg emisji.
- `docs/qa_0.8.18/ui21/summary.json`: końcowe wyniki oraz granice weryfikacji.
- Testy i narzędzia w FULL_SOURCE pozwalają odtworzyć weryfikację serwera,
  geometrii i produkcyjnego klienta przeglądarkowego.
