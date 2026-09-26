# Bractwo 0.8.16 — mana na każdym poziomie

Pełna aktualizacja na bazie **0.8.15**. Zmienia wyłącznie rozkład przyrostów
maksymalnej many i ilości przywracanej przez Odzyskanie mocy. Zachowuje pozostałe
funkcje, klasy, przedmioty, mapę, rytuały, układ okien i odnowienia.

## Co się zmieniło

**Czarodziej i druid** dostają mały przyrost many przy każdym awansie do dotychczasowego
końcowego limitu. **Łowca** otrzymuje analogiczny, wolniejszy wzrost.
**Odzyskanie mocy** czarodzieja również rośnie stopniowo, nadal jest natychmiastową
akcją dodatkową używaną w walce, za 0 many, z odnowieniem **180 sekund**.

| Poziom | Czarodziej / druid: pula | Łowca: pula | Odzyskanie mocy czarodzieja |
| ---: | ---: | ---: | ---: |
| 1 | 40 | 40 | 20 |
| 2 | 51 | 42 | 22 |
| 3 | 62 | 44 | 24 |
| 4 | 73 | 47 | 27 |
| 5 | 84 | 49 | 29 |
| 6 | 96 | 51 | 31 |
| 7 | 107 | 53 | 33 |
| 8 | 118 | 56 | 36 |
| 9 | 129 | 58 | 38 |
| 10 | 140 | 60 | 40 |

Wartości podstawowe, przed premią mistrzostwa Skupienie. Koszty rzucania, kręgi
czarów i skalowanie obrażeń NIE zostały zmienione. Większa pula przed progiem
pozwala częściej używać znanych czarów; nie udostępnia wcześniej nowego kręgu.
To celowe wzmocnienie poziomów pośrednich, bez zwiększania sum na głównych progach.

Od 10 do 20: czarodziej/druid **+13 many na poziom**, łowca **+8**,
Odzyskanie mocy **+2**. Dalej tak samo rozdzielono przyrosty między kolejnymi
progami dziesiątek. Pełny rozkład: **docs/MANA_0.8.16.md** i **docs/MANA_0.8.16.json**.

**Wojownik pozostaje przy 30 podstawowej many**; jego zdolności są bezpłatne.
Nie zmieniono mu zdrowia, Drugiego oddechu, Zrywu ani ataków.

## Podsumowania i opisy

Po każdym rzeczywistym awansie nowe podsumowanie pokazuje oddzielne przyrosty, np.
na 6. poziomie czarodzieja:

```text
Mana +12
Odzyskanie mocy +2 many
```

Na poziomie 10 jest teraz **Mana +11**, zamiast starego +80. Osobno nadal widać
nowy krąg i nowe czary. Kaskada i indywidualne „Zamknij” pozostają bez zmian.

Księga, Atuty, paski oraz F używają tych samych rzeczywistych wartości serwera.
Dymek puli pokazuje jej wielkość i przyrost następnego poziomu, bez przedstawiania
starego zestawu komórek jako rzekomego odpowiednika nowej, pośredniej puli.

Nie ukryto nieposiadanych atutów i przyszłych czarów; nie dodano zwojów.

## Zapisy i aktualizacja

1. Zatrzymaj stary serwer i zrób kopię `data/world.sqlite3` (Railway: `/data/world.sqlite3`).
2. Podmień serwer i cały `web` razem. Zachowaj dotychczasową bazę i wolumen.
3. Uruchom `start_windows.bat` / `./start_unix.sh`, otwórz `http://127.0.0.1:8080`
   i odśwież Ctrl+F5. Nie otwieraj pliku `index.html` ze starego folderu.

**Bez resetu postaci.** Nowa maksymalna mana wynika z aktualnego poziomu.
Podczas pierwszego wczytania starych zapisów zachowany zostaje procent pozostałej
many, z uwzględnieniem premii Skupienia. Przykład: czarodziej poziomu 5 z 30/60
many przechodzi na 42/84, a pusta pula pozostaje pusta. Kolejne logowania nie
powtarzają przeliczenia. Odnowienia (w tym rozpoczęte 180 s), wyposażenie,
wybory, XP i HP nie są resetowane.

**Stare niezamknięte podsumowania zachowują swoje historyczne przyrosty.**
Nie są przeliczane na nowe nagrody, a brakujące dawne awanse nie są odtwarzane.
Nowe podsumowania zawierają nowy rozkład. Awans nadal uzupełnia HP/manę tak jak
w poprzedniej wersji; nie zmieniano tej osobnej mechaniki.

Przed cofnięciem wersji przywróć także kopię bazy sprzed migracji.

Pełny ZIP: katalog **Bractwo_0.8.16**, Godot: `client/project.godot`.
ZIP Railway: pliki w głównym katalogu, bez dodatkowego folderu.
Pakiety zawierają źródła, nie APK/AAB/EXE. Godot nie był uruchamiany/kompilowany;
Docker nie był budowany; nie wykonano wdrożenia na koncie Railway.

Raport: **docs/TEST_REPORT.md**. Protokół: **docs/PROTOCOL_0.8.16.md**.
Opis pozostałych zachowanych funkcji: **docs/README_0.8.15_HISTORY.md** (historyczne
stwierdzenia o braku zmiany skalowania zastępuje niniejszy opis).
