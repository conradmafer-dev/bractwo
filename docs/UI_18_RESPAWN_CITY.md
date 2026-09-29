# UI_18 — odrodzenie w ostatnio odwiedzonym mieście

Baza: pełne źródła UI_17 przekazane przez użytkownika. Przed zmianami zweryfikowano sumy SHA-256 wszystkich plików i zgodność wspólnych plików obu paczek UI_17.

## Zmiana

- Wejście żywej postaci na teren miasta automatycznie ustawia je jako miejsce odrodzenia.
- Dotyczy także ponownych wizyt w już odkrytym mieście oraz podróży kapitanem.
- Miejsce odrodzenia jest zapisywane w istniejącym polu `home_city` i pozostaje po ponownym logowaniu oraz restarcie serwera.
- Pobyt poza miastem, podziemie pod miastem oraz pozycja martwej postaci nie zmieniają zapisanego miasta.
- Ekran śmierci pokazuje nazwę miasta odrodzenia. W Usługach zamiast przycisku ręcznego przypisywania miasta jest informacja o automatycznym zapisie.
- Czas odrodzenia, kary za śmierć i pozostałe zasady gry pozostają bez zmian.

## Aktualizacja

Zastąp pliki aplikacji paczką UI_18 i uruchom serwer ponownie. Zachowaj dotychczasową bazę danych, konfigurację i wolumen Railway. Zmiana nie wymaga migracji bazy ani resetowania postaci.

Postać zalogowana w mieście otrzyma je jako miejsce odrodzenia. Postać zapisana poza miastem zachowa dotychczasowe miejsce aż do następnej wizyty w mieście — stare zapisy nie przechowują kolejności wcześniejszych wizyt.
