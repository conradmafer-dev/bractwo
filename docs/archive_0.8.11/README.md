# Bractwo 0.8.11 — ruch, okna i atlas

Aktualizacja pełnej wersji **0.8.10**, z zachowaniem przesuwanych okien, mikstur w plecaku, odkrywania źródeł łupu, nagród z zadań i powracających potworów. **Bez resetu postaci i bez zmiany balansu leczenia.**

## Ruch i okna

Zaznaczenie, ręczne usunięcie celu oraz śmierć zaznaczonego potwora nie kasują wciśniętych kierunków. Nie trzeba zatrzymywać się i ponownie wciskać klawisza. Działa również ruch po skosie i puszczanie tylko jednego z dwóch kierunków.

Można dalej chodzić przy otwartej karcie postaci, czarach, dzienniku, graczach, kupcu, świecie, atlasie i pomocy, również podczas przeciągania okna. Okna nie zatrzymują symulacji ani nie zapewniają ochrony przed atakiem. Wpisywanie tekstu do czatu, utrata aktywności aplikacji i śmierć nadal blokują sterowanie tam, gdzie jest to potrzebne.

**E** otwiera kontekstowe okno świata/usług albo kupca i zamyka już otwarte okno po ponownym naciśnięciu. Poza oknami nadal obsługuje rozmowy, miejsca do użycia i schody. **C/I/K/J/P** zachowują swoje skróty; **Esc** zamyka okno. Księga świata nie chowa się za lewym HUD-em na małym ekranie.

## Atlas i minimapa

Kliknij mapę lewym przyciskiem, aby przybliżyć, prawym — aby oddalić. Działa także kółko myszy. Przeciąganie samej mapy przesuwa jej widok, a nagłówka — całe okno. Dostępne są przyciski **+**, **−**, **Cały świat** i **Moja okolica**, również do obsługi na telefonie.

Kliknięcie atlasu nie zamyka okna i nie wyznacza już przypadkowo celu marszu. Przycisk **Wyznacz cel** włącza wybór punktu kolejnym kliknięciem; okno nadal pozostaje otwarte. Powiększenie i położenie mapy pozostają podczas ruchu, zmian stanu serwera i zamknięcia/ponownego otwarcia księgi w tej samej sesji. Nie są zapisywane jako ustawienie konta między ponownymi uruchomieniami klienta.

**Początkowa rzeka i most koło Przystani są widoczne w obu mapach**, obok później dodanych rzek i mostów. Geometria pochodzi z metadanych rzeczywistego świata. To poprawka map, nie przebudowa świata ani zmiana przejść przez wodę. Minimapę pokazuje/ukrywa **M**; kliknięcie jej karty otwiera Atlas.

## Rozwój bez starej listy możliwości

Księga wyświetla progi właściwe dla wybranej klasy: kręgi, odblokowywane czary i zdolności, liczbę ataków, biegłość, wzrost cech i podstawowej many. Dane są generowane na serwerze przez te same funkcje, które wyznaczają rzeczywiste parametry postaci.

Usunięto mylące obietnice wspólnej listy klas i opisano dotychczasowe liczniki treningu jako historię używania — nie jako dodatkową premię do rzutu ataku, KP czy ST czarów. Opis mistrzostwa odpowiada obecnym efektom; punkty można przydzielać poza walką, z zachowaniem promocji i wymaganego poziomu. Potęga nie wzmacnia Iskry czarodzieja ani jego czarów; nie zmieniono tej mechaniki. Aktualne rzuty i założone wyposażenie nadal są w **C → Statystyki**.

## Leczenie — pozostaje zgodne z używanymi zasadami

Projekt korzysta z zasad **2024 / SRD 5.2.1**. Leczenie ran ma bazowo **2k8 + modyfikator cechy**, a za użycie wyższego kręgu otrzymuje **+2k8**. Uzdrawiające słowo ma bazowo **2k4 + modyfikator cechy**, a za wyższy krąg **+2k4**.

To wzrost za **krąg użyty do rzucenia**, nie za pojedynczy poziom rzucającego. Przy progach Bractwa I krąg na poziomie 1, II na 10, III na 20 wzrost pozostaje co 10 poziomów. Nie rozbito pojedynczego przyrostu na mniejsze kości pośrednie i nie zmniejszono leczenia. Wyższy krąg nadal kosztuje odpowiednio więcej many; można ręcznie wybrać niższy w księdze.

Oficjalne opisy, sprawdzone 25.09.2026:
- https://www.dndbeyond.com/spells/2619079-cure-wounds
- https://www.dndbeyond.com/spells/2619143-healing-word

## Uruchomienie i aktualizacja

**Zatrzymaj wcześniejszy serwer**, zrób kopię jego `data/world.sqlite3` i przenieś zapis do nowej paczki. Zaktualizuj **serwer oraz cały katalog web razem**, w tym nowy `atlas_map.js`. Serwer 0.8.11 udostępnia ten plik i nowe dane rozwoju klas. Nie trzeba resetować kont ani przedmiotów.

Na Windows uruchom **`start_windows.bat`** z nowego katalogu, następnie otwórz **`http://127.0.0.1:8080`**. Alternatywnie:

```sh
python -m pip install -r requirements.txt
python run.py
```

Sprawdź wersję **0.8.11** na logowaniu i pod `/health`. Nie otwieraj starego `web/index.html` z folderu 0.8.9 ani 0.8.10 — uruchomiłbyś dawny interfejs mimo podmiany serwera. Po aktualizacji odśwież stronę **Ctrl+F5**.

Na Railway zachowaj dotychczasową usługę, wolumen oraz ścieżkę bazy. Paczka Railway ma pliki bezpośrednio w katalogu głównym; pełna paczka zawiera folder `Bractwo_0.8.11/` i dodatkowe źródła Godota. Szczegóły: `docs/RAILWAY.md`. Nic nie zostało wdrożone na koncie użytkownika.

Nie ma nowej migracji danych ponad 0.8.10. Przy aktualizacji bezpośrednio z 0.8.9 nadal wykonuje się jednorazowe przeniesienie mikstur do plecaka z wersji 0.8.10. Nie uruchamiaj starszego niż 0.8.10 serwera na już zmigrowanej bazie; do cofnięcia takiej zmiany przywróć też kopię zapisu.

Godot: `client/project.godot`. Zmienione źródła wymagają weryfikacji w silniku; nie wykonano importu, uruchomienia ani eksportu Godota. Paczki nie zawierają APK, AAB ani EXE.

## Testy

Aktualny raport, wyniki i zakres weryfikacji: **`docs/TEST_REPORT.md`** oraz **`docs/qa_0.8.11/`**. Starsze raporty dotyczą poprzednich wersji. Atrybucja zasad: `LICENSE-SRD.txt`.
