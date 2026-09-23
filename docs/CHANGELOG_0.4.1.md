# 0.4.1 — Płynność, cele i FPS · 2026-09-22

## Zaznaczanie i walka

Lista WWW była wyłącznie informacyjna, a kliknięcie w świecie wyszukiwało tylko graczy. Dodano wybór potworów przez stabilne przyciski listy i trafienie w narysowaną postać. Godot otrzymał analogiczny wybór w świecie i listę czterech pobliskich przeciwników. Cel utrzymuje się przez aktualizacje stanu, jest oznaczony i znika po śmierci, utracie zasięgu przesyłania lub zmianie piętra.

Protokół rozróżnia `enemy_id` od gracza `target_id`. Atak podstawowy, mocny strzał i runy sprawdzają wskazanego potwora. Nieprawidłowy, martwy, oddalony, zasłonięty lub znajdujący się na innym piętrze cel jest odrzucany bez zastępowania go innym wrogiem. Wybranie potwora nie wymaga wyłączenia blokady PvP.

Potwory pamiętają napastnika po rzeczywistym trafieniu lub prowokacji. Podejmują pościg spoza naturalnego promienia wykrywania i podtrzymują go w walce. Pamięć wygasa po 20 sekundach bez podtrzymania; pościg nadal ma granicę 700 jednostek od legowiska, uwzględnia piętra i ochronę miasta. Nie zmieniono statystyk obrażeń ani szybkości potworów.

## Płynność bez obniżania jakości

- WWW: indeks obiektów statycznych ładowany raz; wyszukiwanie okolicy kamery zamiast wszystkich 2653 obiektów na każdej klatce.
- WWW: identycznie rysowane fragmenty gruntu przygotowywane przed wejściem kamery; bufor nie wyrzuca widocznych fragmentów na dużym ekranie.
- WWW: minimapa odrysowywana przy nowym stanie lub zmianie widoku; ponownie używane elementy listy i formatter liczb.
- Godot: fragmenty terenu 768 × 768 przechowują istniejące kafle 48 × 48; przesuwanie kamery nie generuje całego gruntu ponownie. Dane regionów, dróg, komnat i obiektów mają buforowane opisy oraz indeks.
- Oba klienty: interpolacja ruchu między próbkami zamiast cyklicznego doganiania każdej nowej pozycji.
- Serwer: lokalne grupy graczy do AI, jeden zestaw publicznych danych na rozsyłanie, przestrzenne wyszukiwanie odkryć.
- Nowi klienci negocjują wysyłanie prywatnych list tylko po zmianie. Pierwszy stan i ponowne logowanie zawsze zawierają komplet. Starsze klienty nadal dostają pełne stany.
- Licznik FPS odświeżany dwa razy na sekundę. Nie zmieniono limitu klatek, rozdzielczości, palet, geometrii postaci ani efektów.

## Sprawdzenia

50 testów serwera, 5 testów JS, parser sześciu skryptów Godot, kontrola składni Python/JS/Bash i 90 porównań poleceń rysowania terenu. Szczegółowe pomiary oraz granice weryfikacji: TEST_REPORT.md. Brak testu graficznego i eksportu APK/AAB/EXE.
