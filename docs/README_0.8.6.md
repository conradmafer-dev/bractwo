# Bractwo 0.8.6 — przyrosty po awansie i kaskada paneli

Pełny projekt rozwijający `BRACTWO_0.8.5_GRAFIKA_CZAROW_KARTA_POSTACI_FULL_SOURCE.zip`: serwer Python, klient WWW i źródła Godota. Paczka nie zawiera APK, AAB ani EXE. Zachowano dotychczasowy świat, grafikę czarów, walkę, PvP, kręgi, manę, kartę postaci i 24 skróty.

## Podsumowanie każdego awansu

Przy lewej krawędzi pojawia się osobny pionowy panel dla każdego zdobytego poziomu, również gdy jedna nagroda daje kilka poziomów naraz. Wyświetla wyłącznie zmiany, każdą w oddzielnym wierszu: np. `HP +1`, `Mana +80`, `Atak czarem +2`, osobne rzuty obronne, przyrost cechy, krąg, dodatkowe ataki i kości obrażeń. Nie pokazuje wartości sprzed awansu ani nowych sum. Wiersze bez zmiany są pomijane.

Nowe czary i zdolności mają własne wiersze i dotychczasowe ikony. Zmiana rodzaju kości Shillelagh jest przedstawiona jako wyraźnie podpisany przyrost **średnich obrażeń**, a nie zestawienie starej i nowej kości. Ruch pokazuje przyrost prędkości podstawowej; chwilowe efekty, teren i przemiana nie zanieczyszczają podsumowania stałego rozwoju.

## Kaskada i zamykanie

Kolejne panele zachodzą na siebie z przesunięciem w dół i w prawo. Kliknięcie nagłówka przenosi wybrany awans na wierzch kaskady, pozostawiając dostęp do nagłówków pozostałych. **Na dole każdego panelu jest przycisk „Zamknij”**; krzyżyk w nagłówku robi to samo. Oba zamykają tylko wybrany awans.

Panele nie wygasają z czasem i nie są zastępowane jednym zbiorczym komunikatem. Zamknięcie karty postaci nie zamyka podsumowań. Niezamknięte awanse zapisują się razem z postacią i wracają po ponownym logowaniu. Zamknięcie jest potwierdzeniem, nie wydaniem punktu ani wyborem nagrody.

Na wąskim ekranie długa lista zmian przewija się wewnątrz panelu; dolny przycisk pozostaje dostępny. Przy ponad 32 niezamkniętych awansach naraz interfejs pokazuje 32 ostatnie i licznik wszystkich; zamykanie odsłania kolejne starsze podsumowania. **Żaden starszy awans nie jest automatycznie usuwany.** Serwer zapisuje bardzo długie serie jako zwarte zakresy, zamiast tworzyć milion obiektów przy dużej nagrodzie PD.

## Punkty i atuty

Zdobyty punkt istniejącego systemu mistrzostwa daje wiersz `Punkt mistrzostwa +1` i przycisk **„Przydziel punkt”**. Przycisk otwiera Statystyki w karcie postaci. Można przydzielać istniejące punkty do Potęgi, Witalności lub Skupienia bez wracania do mistrza; pozostają dotychczasowe wymagania poziomu, promocji, limitów i zakończenia walki. Serwer sprawdza każdy wydatek. Reset mistrzostwa i zakup promocji nadal wymagają mistrza.

Nie dodano nowych punktów cech ani samych atutów. Dotychczasowy automatyczny wzrost cechy na progach poziomów pozostaje automatyczny. Zakładka Atuty nadal nie zawiera sztucznych nagród. Panel obsługuje przejście do tej zakładki dla przyszłego rzeczywistego wyboru przekazanego przez serwer.

## Uruchomienie i aktualizacja

Windows: rozpakuj ZIP, uruchom `start_windows.bat` i otwórz `http://127.0.0.1:8080`. Pozostaw okno serwera włączone. Wymagany Python 3.11+. Sieć lokalna: `start_windows.bat lan`. Linux/macOS: `./start_unix.sh`. Import Godota: `client/project.godot`.

**Reset postaci nie jest potrzebny.** Zatrzymaj stary serwer, zabezpiecz `data/world.sqlite3` i przenieś tę bazę do nowej paczki. Aktualizuj serwer i klienta razem; w WWW odśwież stronę z pominięciem pamięci podręcznej. Nie kopiuj starego kodu na nowe źródła. Stare zapisy bez historii awansów nie wyświetlają nagle wszystkich historycznych poziomów.

## Weryfikacja

**369 testów Python, 28 testów JavaScript i 17 sprawdzeń interfejsu Chromium — PASS.** Logi oraz zrzuty są w `docs/qa_0.8.6/`. Sprawdzono wielokrotny awans, same przyrosty, zamykanie środkowego panelu, trwałość, prywatność historii, przydzielenie rzeczywistego punktu, ponowne logowanie i małe rozdzielczości.

WWW testowano rzeczywistymi skryptami i serwerem przez kontrolowany most WebSocket Python, z testowym localStorage. To nie jest test natywnej sieci Chromium ani fizycznego telefonu. **Zmodyfikowany klient Godot nie został uruchomiony, zaimportowany, skompilowany ani wyeksportowany.** Wersja natywna wymaga osobnego testu w silniku. Szczegóły: `docs/TEST_REPORT.md`.

```sh
python -m unittest discover -s tests -v
node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs tests/test_level_up.cjs
python tools/browser_086_smoke.py
```

Opis wcześniejszych funkcji: `docs/README_0.8.5.md`. Bieżące zmiany: `docs/CHANGELOG_0.8.6.md`. Protokół: `docs/PROTOCOL.md`. Eksport: `docs/BUILD.md`. Atrybucja otwartych reguł: `LICENSE-SRD.txt`. Wcześniejsze raporty i zrzuty mają charakter historyczny.
