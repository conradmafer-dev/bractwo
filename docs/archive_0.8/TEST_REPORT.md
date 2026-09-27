# Raport weryfikacji 0.8.0 — 23.09.2026

## Wykonane

**82 testy Python: PASS.** `python -m unittest discover -s tests -v`; 4,576 s w tej sesji. Reguły kości i krytyków, HP, kręgi, sześć cech, ograniczone premie, dodatkowe ataki, wszystkie43 czary i4 zdolności, koncentracja i jej zerwanie, rzuty obronne, leczenie drużynowe, reakcja Tarcza, wilk/kształty, mana, bezpłatne ponawianie przy koncentracji, migracja, tożsamość ekwipunku, odrzucenie wadliwych celów, autoatak/śmierć/odległość/piętra/PvP/kolejka, zapis paska i ranking. Zestaw obejmuje rzeczywiste połączenia testowe HTTP oraz WebSocket do aiohttp, rejestrację, ranking bez logowania i serwowanie zasobów.

**10 testów JavaScript Node: PASS.** Przestrzenne indeksy, pomiar klatek, interpolacja, trafianie kursorem, scalanie zmian właściciela, teren, duże sylwetki, ignorowanie sojuszniczego wilka i opis rzeczywistych kości. `node --check` dla game.js/runtime.js: PASS. `python -m compileall -q server`: PASS.

**Wizualny test WWW w Chromium:** logowanie i utworzenie druida,8 pól paska, zamknięcie wskazówki i zapis preferencji, przypisanie Uzdrawiającego słowa do slotu1 i potwierdzenie zmiany na prawdziwym serwerze, wilcza forma/powrót, wybór z listy → autoatak z rzutem, Esc → zatrzymanie, ranking konta bez logowania oraz ponowna inicjalizacja UI z zapamiętaną preferencją. Zrzuty desktop1440×900, telefon390×844, poziomy960×540. Po korekcie ranking jest widoczny także na mobilnym logowaniu, a czat nie przykrywa mikstur. Brak błędów JavaScript zgłoszonych przez stronę w tej próbie.

Surowe wyniki i zrzuty: `qa_0.8/`. Wykorzystany harness: `../tools/browser_dnd_inline.py` (opcjonalnie Playwright i lokalny Chromium).

## Metoda i ograniczenia

Środowisko Chromium blokowało nawigację sieciową, dlatego test UI ładował niezmienione źródła HTML/CSS/JS przez `set_content`. WebSocket w przeglądarce zastąpiono kontrolowanym mostem Python do rzeczywistego serwera aiohttp; localStorage był obiektem testowym zachowującym wartości pomiędzy inicjalizacjami. Nie jest to pełny test zwykłego wejścia po adresie HTTP ani przetrwania lokalnego magazynu po restarcie przeglądarki. Transport HTTP/WS serwera sprawdzono niezależnie testami Python. Zrzuty pokazują prawdziwy canvas aplikacji, nie projekt graficzny.

**Godot: zmieniono źródła, lecz nie wykonano importu, kompilacji, uruchomienia ani eksportu.** W środowisku nie było silnika. Nie ma potwierdzenia typowania i zgodności API przez Godot. Nie ma APK/AAB/EXE. Nie wykonano próby na fizycznym Androidzie, hostingu internetowym, długiego testu wielu graczy ani wielogodzinnego testu balansu. Nie deklarujemy osiąganych FPS na urządzeniach użytkownika.

Część upraszczających różnic i ograniczeń czarów jest jawna w `RULES_0.8.md`. Historyczne raporty0.6/0.7 oraz `tests/legacy_0_7` nie są wynikami nowej wersji; ich starych oczekiwań nie zaliczono do82 testów.
