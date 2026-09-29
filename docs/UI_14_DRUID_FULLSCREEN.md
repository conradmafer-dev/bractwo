# Bractwo 0.8.18 UI_14 — Strzała, powrót do druida i kompaktowy pełny ekran

## Obsługa gwiezdnych postaci

Przycisk „Gwiazdy” na mobilnym pasku otwiera wybór Łucznika, Kielicha lub Smoka.
Po potwierdzonej przez serwer aktywacji Łucznika ten sam przycisk ma krótki napis
„Strzała” i oddzielną ikonę pocisku. Wysyła `circle_star_arrow`, nie ponowną
aktywację `circle_star_archer`. Pokazuje czas oczekiwania na akcję dodatkową,
a następnie 0 MP. Działa również przy pustej puli Dzikiego kształtu, dopóki Łucznik
jest aktywny. Status u góry nazywa aktywną konstelację i wyjaśnia sterowanie.

Przycisk ▾ przy grupie otwiera menu. „Powrót do druida” znajduje się na górze,
w części nieprzewijanej wraz z listą postaci; nie wymaga użyć ani zakończenia
odnowienia strzału. Kielich i Smok mają też bezpośredni powrót po dotknięciu
głównego przycisku aktywnej postaci. Zakończenie nie zwraca wydanego użycia.
Pozostają ograniczenia serwera dotyczące śmierci i obezwładnienia.

Przy 0/2 nie można rozpocząć nowej przemiany. Krótki odpoczynek odnawia jedno
użycie, długi — całą pulę, zgodnie z dotychczasowymi zasadami. Restart serwera
lub ponowne logowanie nie zachowują aktywnych efektów czasowych — nie jest to
nowa zmiana UI_14. Nie resetuj postaci, by sprawdzić nowe przyciski.

W bezpiecznej osadzie próba strzału pokazuje czytelny komunikat. W terenie brak
przeciwnika w zasięgu również nie kończy się już wyłącznie cichą odmową.
Nie zmieniono obrażeń, czasu trwania, kosztów przemian ani progów kręgów.

## Stan serwera a interfejs

W UI_13 lokalnie udało się odtworzyć prawidłowe przełączanie funkcji przycisku.
Nie potwierdzono więc jednej uniwersalnej przyczyny zgłoszenia z produkcji.
Potwierdzono natomiast niemal identyczne skrócenie długich nazw, wspólną ikonę,
zakończenie postaci na dole przewijanej listy oraz zależność przycisku od pola
używanego również do efektów wizualnych.

UI_14 dodaje aktualny stan `druid_forms` do każdego pakietu właściciela,
niezależnie od skracania niezmienionych katalogów. Aktywna konstelacja jest
zapisana w efekcie i odczytywana także po utracie pomocniczego cache runtime.
Klient traktuje jawny pusty stan jako zakończenie postaci, a nie przywraca jej
ze starszej karty postaci. Aktualizacja nie dodaje optymistycznej przemiany
wyłącznie po stronie przeglądarki: serwer nadal zatwierdza akcje i zasoby.

## Mniejszy HUD również na pełnym ekranie

Mobilny HUD ma jawny kompaktowy współczynnik 0,74. Rozmiary kart, przycisków,
paska i joysticka oraz skala świata nie wracają do większych wartości tylko
z powodu wejścia w pełny ekran lub zmiany wysokości po schowaniu pasków telefonu.
Zmniejszenie przeglądarkowego VisualViewport poniżej 1 jest kompensowane raz;
celowe powiększenie powyżej 1 pozostaje możliwe. Nie zastosowano transformacji
całego DOM, więc obszary dotyku, menu i joystick używają zwykłych współrzędnych.

Przy dotykowym widoku poziomym profil nie przełącza się automatycznie na duży
pulpit po przekroczeniu starego progu wysokości. Pion ma własną stałą skalę.
Desktop zachowuje swój układ. Oddzielne zapisane profile HUD są zachowane.
Nie zmieniono interpolacji ruchu, sterowania ani zasad walki.

W próbie 760×340 CSS px pasek mieścił 13 pełnych pól, a po zmianie obszaru na
800×400 — 14, bez zmiany szerokości przycisków. Nie jest to gwarantowana liczba
na każdym urządzeniu; zależy od dostępnego miejsca. Nadal są 17 zajętych pól
u druida Kręgu Gwiazd na poziomie 15, bez trzeciego rzędu i bez usuwania czarów.

## Wdrożenie

Wgraj razem `server` i `web` z UI_14. W paczce RAILWAY_GITHUB_READY pliki
`Dockerfile`, `run.py`, `requirements.txt`, katalogi `server` i `web` są bezpośrednio
w katalogu głównym repozytorium. Zachowaj bazę graczy, wolumen, `.git` i ustawienia
Railway. Nie wrzucaj do repozytorium samego ZIP-a zamiast rozpakowanych plików.

Po ukończeniu wdrożenia przeładuj stronę, również przy uruchomieniu z ikony PWA.
Na ekranie logowania powinno być `UI_14`. Reset postaci nie jest potrzebny.
Ta paczka nie została automatycznie wdrożona na Railway. Źródła natywnego
interfejsu Godota pozostały niezmienione; poprawka interfejsu dotyczy przeglądarki.

## Weryfikacja

Przeszło 56 celowanych testów serwera, 63 testy JavaScript i 28 kontroli w Chromium
(16 nowych scenariuszy UI_14 oraz 12 powtórzonych scenariuszy UI_13).
Sprawdzono między innymi rzeczywiste obrażenia strzały przy 0 użyć i 0 many,
zakończenie podczas odnowienia, wygaśnięcie i śmierć, stan w kolejnych pakietach,
menu dostępne bez przewijania w poziomie i pionie, pełny ekran, zmianę rozmiaru,
kompensację skali oraz zachowanie przewijania drugim palcem podczas ruchu.
Sprawdzono składnię wszystkich plików Python serwera i JavaScript klienta.

Ograniczenia: to wybrane zestawy regresji, nie cała historyczna kolekcja testów.
Przeglądarka testowa wyświetlała rzeczywisty kod produkcyjny przez `set_content`
i istniejący most WebSocket do izolowanego serwera w pamięci. Nawigacja sieciowa
przeglądarki jest zablokowana w środowisku testowym. Nie testowano produkcyjnego
hostingu, trwałego localStorage, cyklu service workera ani instalacji PWA.
API pełnego ekranu uruchomiono dotykiem; zmiany obszaru rysowania telefonu
modelowano zmianą viewportu, a reset pomniejszenia — kontrolowaną wartością
VisualViewport.scale. Nie wykonano testu na fizycznym Androidzie użytkownika.

Raporty i logi: `docs/qa_0.8.18/ui14/`. Foldery starszych wersji zawierają historyczne
wyniki, nie deklarację aktualnego zakresu UI_14. Testy i narzędzia powtórzenia są
w paczce FULL_SOURCE. `SOURCE_MANIFEST.json` zawiera sumy SHA-256 plików pakietu.
