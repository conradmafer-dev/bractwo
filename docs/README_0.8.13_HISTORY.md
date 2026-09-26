# Bractwo 0.8.13 — wojownik, style walki i tarcze

Aktualizacja pełnej wersji **0.8.12**. Zachowuje magię łowcy od początku, świat, łupy, mikstury w plecaku, przesuwane okna, interaktywny atlas, ciągły ruch i kaskadę awansów. Klasa wojownika nadal nazywa się w grze **Rycerz**.

## Wybór stylu od 1. poziomu

Otwórz **C → Atuty** albo naciśnij **Wybierz styl** w małym panelu po lewej. Kliknięcie kafelka tylko pokazuje wybór; dopiero **Wybierz ten styl** zatwierdza go na serwerze. Wybór nie zużywa punktów cech ani mistrzostwa. Możesz zamknąć przypomnienie i wrócić do Atutów później. Nie ma automatycznie przydzielonego stylu.

| Jeden wybrany styl | Działanie |
| --- | --- |
| Pojedynek | +2 do obrażeń jednoręczną bronią wręcz, również z tarczą. |
| Obrona | +1 KP w lekkim, średnim lub ciężkim pancerzu. Sama szata nie wystarcza. |
| Walka wielką bronią | Wyniki 1 i 2 na kościach obrażeń broni używanej oburącz liczą się jako 3; także przy krytyku. |

Zmiana wybranego stylu jest **bezpłatna u mistrza profesji w osadzie, poza walką**. Początkowy wybór może być dokonany także poza osadą, ale nie podczas walki. Styl jest zapisany z postacią. Zmiana broni go nie zmienia; niepasujący styl pozostaje wybrany, lecz jego premia nie działa.

## Wyposażenie

Nowy Rycerz otrzymuje **Kolczugę wojownika (KP 16)** i **Tarczę wojownika (+2 KP)**. Razem dają **KP 18**, a z Obroną **KP 19**. Standardowy miecz i Pojedynek na poziomie 1: **1k20+5 do trafienia, 1k8+5 obrażeń**.

Tarcza zajmuje osobny slot w **C → Ekwipunek**. Jest widoczna na postaci, ma własną ikonę i podgląd po kliknięciu/najechaniu. Broń dwuręczna odkłada ją do plecaka, nie usuwa przedmiotu. Nie można uzyskać jednocześnie premii tarczy i broni używanej oburącz.

Miecz długi jest wszechstronny: w Atutach możesz przełączyć **Jednorącz (1k8)** na **Oburącz (1k10)**. Chwyt zmienia się poza walką. Chwyt oburącz odkłada tarczę i może aktywować Walkę wielką bronią; nie włącza jej automatycznie.

U kupca, w zakładce **Kupuj**, są też dostępne od poziomu 1:
- Miecz dwuręczny rekruta: 2k6 ciętych, 25 złota.
- Młot dwuręczny rekruta: 2k6 obuchowych, 15 złota.
- Tarcza wojownika: +2 KP, 10 złota; kolczuga: KP 16, 75 złota.

Ceny są balansem Bractwa. Ten sprzęt jest wyposażeniem startowym/ofertą kupca, a nie dopisanym w ciemno łupem z potworów. Obecne tabele łupów pozostają bez zmian.

## Trzy opanowane mistrzostwa

W tej wersji wojownik od początku zna trzy zaimplementowane rodzaje broni. Nie ma dodatkowego wyboru z większego, jeszcze niezaimplementowanego katalogu. Efekt działa automatycznie przy używaniu odpowiedniej broni, nie zajmuje pola skrótów.

| Broń | Efekt |
| --- | --- |
| Miecz długi | **Osłabienie**: trafiony cel ma utrudnienie przy następnym rzucie ataku przed upływem 3 sekund. Efekt zużywa się na jednym rzucie, nie na całej serii ataków. |
| Miecz dwuręczny | **Draśnięcie**: pudło zadaje obrażenia równe modyfikatorowi Siły (na początku 3), bez kości i innych premii. Nie staje się trafieniem i nie uruchamia efektów wymagających trafienia. |
| Młot dwuręczny | **Powalenie**: po trafieniu cel wykonuje obronę na Kondycję. ST = 8 + biegłość + modyfikator cechy ataku. Niepowodzenie przewraca cel. |

Powalony cel wstaje automatycznie po **1,5 s**, zużywając połowę trzysekundowej rundy ruchu. Do tego czasu nie porusza się i ma utrudnienie ataków. Ataki z bliska mają ułatwienie, z dystansu utrudnienie. Bliskość jest liczona według istniejącego zasięgu walki wręcz Bractwa. To adaptacja ruchu w czasie rzeczywistym, nie ręczny wybór wstawania z sesji stołowej.

Mistrzostwa obejmują potwory i legalne cele PvP. Nie omijają blokady PvP, ochrony osad, niskich poziomów, drużyn, pięter ani ścian. Draśnięcie podlega istniejącym odpornościom gracza i może dobić potwora z normalnym przyznaniem zabójstwa.

Każdy styl i mistrzostwo ma własną ikonę. Osłabienie i powalenie są widoczne jako statusy celu, a trafienia, draśnięcie i Zryw mają osobne animacje. Wyposażona tarcza, duży miecz i młot mają reprezentację na postaci.

## Aktywne zdolności

**Drugi oddech — od poziomu 1:** 0 many, 60 sekund odnowienia, akcja dodatkowa. Leczy **1k10+1** na początku; premia rośnie o +1 na poziomach 5, 10, 15 itd., do +20 na poziomie 95. Nie zużywa głównego ataku. Styl wielkiej broni nie zmienia kości leczenia.

**Zryw akcji — od poziomu 5:** 0 many, 90 sekund odnowienia. Natychmiast wykonuje dodatkową **akcję ataku**, nawet gdy główny atak czeka na odnowienie. Obejmuje aktualną liczbę ataków: 1 przed poziomem 20, 2 od 20, 3 od 50, 4 od 95. Nie odnawia czarów, Drugiego oddechu, mikstur ani akcji dodatkowej. Nie jest stałym drugim atakiem.

Zryw musi mieć prawidłowy cel w zasięgu. Zły cel/ściana/piętro/blokada nie zużywają jego odnowienia. Zmiana celu, śmierć wroga i ponowne logowanie nie zerują odnowień. Czas odnowienia liczy się również podczas nieobecności postaci. Na pasku znajduje się Drugi oddech, a na poziomie 5 dochodzi Zryw; własne poprawne przypisania pozostają. Skrót **F** dalej wynika z ostatnich 100 rzeczywistych użyć.

Kaskada awansów pokazuje odblokowanie Zrywu oraz wzrost leczenia Drugiego oddechu jako oddzielne przyrosty. Styl i mistrzostwa są pasywne i nie zapychają paska.

## Aktualizacja zapisów

**Reset nie jest potrzebny.** Zatrzymaj stary serwer i wykonaj niezależną kopię **data/world.sqlite3**. Podmień serwer i cały katalog **web** razem, w tym nowe `fighter_ui.js`, `fighter_vfx.js`, `fighter.css` oraz `assets/feats/` i nowe ikony wyposażenia.

Stary wojownik zachowuje poziom, zadania, broń, mikstury, ustawienia i przedmioty. Kolczuga i tarcza są dodawane **jednorazowo**. Kolczuga zastępuje tylko brak pancerza albo początkową Kurtkę podróżnika; inny założony pancerz nie jest podmieniany. Tarcza trafia do wolnego slotu tylko przy odpowiedniej broni. Przy pełnym plecaku jednorazowa migracja może przekroczyć jego limit zamiast niszczyć przedmioty. Ponowne logowanie nie rozdaje wyposażenia drugi raz.

Pierwszy styl nie jest wybierany automatycznie nawet dla istniejącej postaci wysokiego poziomu. Przywracając starszą wersję serwera, przywróć też kopię bazy sprzed migracji.

Lokalnie uruchom **start_windows.bat** (Windows) albo **./start_unix.sh**, a następnie otwórz **http://127.0.0.1:8080**. Użyj Ctrl+F5; nie otwieraj `index.html` ze starego folderu. Logowanie i `/health` pokazują **0.8.13**.

Na Railway użyj paczki RAILWAY_GITHUB_READY; zachowaj tę samą usługę, wolumen i ścieżkę bazy. Konfiguracja hostingu nie została zmieniona. Instrukcja: **docs/RAILWAY.md**.

## Zasady i sprawdzenie

Mechaniki stylów i właściwości broni mają punkt odniesienia w zasadach 2024; ich wdrożenie opisano powyżej. Bractwo używa własnych odnowień zamiast limitów odpoczynków, własnej skali poziomów, automatycznego wstawania i Zrywu ograniczonego do akcji ataku. Nie dodano wszystkich stylów, wszystkich mistrzostw, podklas ani całego rozwoju wojownika z podręcznika.

Raport wykonanych testów, warunki testu Chromium i ograniczenia: **docs/TEST_REPORT.md**. Źródła zasad, techniczne różnice i pola protokołu: **docs/PROTOCOL_0.8.13.md**. Własne polskie opisy i grafiki; atrybucja wcześniejszej zawartości: **LICENSE-SRD.txt**.

Pełny ZIP zawiera źródła serwera, WWW i Godota. **Godot nie został uruchomiony ani skompilowany; nie ma APK, AAB ani EXE. Nie zbudowano obrazu Docker i nie wdrożono paczki na koncie Railway.** Poprzedni README i raport zachowano w `docs/archive_0.8.12/`.
