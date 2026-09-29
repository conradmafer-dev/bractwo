# Bractwo 0.8.18 UI_16 — jedna lista kręgów czarów

Baza: `BRACTWO_0.8.18_UI_15_FULL_SOURCE.zip`.

## Przyczyna zgłoszenia

Księga sortowała wszystkie wpisy najpierw według poziomu odblokowania, a dopiero
potem według kręgu. Nagłówek sekcji dodawała za każdym razem, gdy etykieta kolejnego
wpisu różniła się od poprzedniej. Wskazówki i Wiodący pocisk, otrzymywane przez
Krąg Gwiazd później niż początkowe czary druida, rozpoczynały więc drugą sekcję
Sztuczek i drugą sekcję Kręgu I. Przemiany oraz inne zdolności dodatkowo rozdzielały
czary na kolejne fragmenty.

## Poprawka

Księga najpierw zbiera wpisy w grupach według **podstawowego kręgu czaru**,
niezależnie od źródła czaru i poziomu jego odblokowania. Dopiero potem wyświetla
każdą niepustą grupę dokładnie raz:

**Sztuczki → Krąg I → Krąg II → … → Krąg IX → Zdolności klasy.**

Wskazówki są razem z pozostałymi sztuczkami; Wiodący pocisk razem z pozostałymi
czarami I kręgu. W obrębie kręgu nazwy są sortowane alfabetycznie z polskim
porządkiem liter. Zdolności klasy są na końcu, według poziomu odblokowania i nazwy.
Zmiana mocy rzucania nie zmienia sekcji czaru: np. Wiodący pocisk rzucany z II kręgu
pozostaje wśród czarów, których podstawowy krąg to I.

Zachowano wcześniejsze zasady widoczności i odblokowania wpisów, przyciski Użyj,
wybór umiejętności Wskazówek, wybór mocy oraz przypisywanie skrótów. Ta poprawka
nie przestawia zapisanych pól paska. Nie zmieniono mechaniki czarów, kosztów many,
progów poziomów, mobilnej skali interfejsu, kamery ani kodu ruchu. Natywny interfejs
Godota pozostaje bez zmian; poprawka dotyczy klienta przeglądarkowego.

## Pliki i wdrożenie

Zmiana działania znajduje się w `web/character_sheet.js`; etykieta logowania
w `web/index.html` pokazuje **UI_16**. Oprócz tego zaktualizowano dokumentację,
narzędzie pakowania i dodano testy. Pliki serwera i istniejące grafiki są te same
co w bazowej paczce UI_15. Obie grafiki Wskazówek i Wiodącego pocisku są w `web/assets/spells/`.

Archiwum RAILWAY_GITHUB_READY ma płaski katalog główny z `Dockerfile`, `run.py`,
`requirements.txt`, `server/` i `web/`; nie zawiera klienta Godota ani starych buildów.
Poprzednie archiwum UI_15 z etykietą RAILWAY_GITHUB_READY pomijało pliki startowe
z katalogu głównego. Nowe archiwum zawiera je ponownie.

Rozpakuj archiwum Railway i podmień pliki w głównym katalogu repozytorium.
Nie usuwaj istniejącej bazy graczy, wolumenu `/data` ani konfiguracji środowiska.
Do repozytorium wysyłaj rozpakowane pliki, nie sam ZIP. Reset postaci nie jest
potrzebny. Po zakończeniu wdrożenia odśwież stronę i sprawdź **UI_16** na logowaniu.
Paczki nie zostały automatycznie wdrożone na Railway.

## Rzeczywiście wykonane testy

- **86/86 nowych testów sortowania**: przypadek druida Kręgu Gwiazd, wyższa moc
  czaru, brak duplikatów i modyfikowania hotbaru, widoczność wpisów oraz rzeczywiste
  katalogi dla czterech klas, kręgów druida i rodzajów lądu na poziomach
  1, 10, 18, 20, 45, 80 i 100.
- **11/11 kontroli w Chromium**: kompletny interfejs z osobnym serwerem testowym,
  druid 18. poziomu, pulpit oraz dotyk w pionie i poziomie. Sprawdzono grupy,
  wszystkie ikony w księdze, zmianę mocy bez przestawiania sekcji, rzucenie Wskazówek
  z wybraną umiejętnością, przypisanie skrótu, przełączanie zakładek i brak błędów JS.
- Uruchomiono też wszystkie obecne testy JavaScript: **248 zaliczonych, 10 błędów**.
  Dla porównania uruchomiono niezmienioną paczkę UI_15: **162 zaliczone, te same
  10 błędów**. Różnica to 86 nowych zaliczonych testów. Starsze testy
  `test_arcane_recovery_0815.cjs` oczekują poprzedniej obsługi odzyskiwania many;
  `test_training_refresh_ui08.cjs` kończą się błędem w swoim uproszczonym DOM.
  Nie poprawiano ich przez zmianę reguł gry ani usuwanie asercji.
- Wybrane testy serwera i geometrii: **60 zaliczonych, 1 błąd**; dokładnie taki sam
  wynik na bazowej UI_15. Błąd pochodzi z historycznego testu wymagającego identycznych
  ikon w obu klientach — w kliencie Godota brak m.in. `star_arrow.svg`. Ikony
  przeglądarkowe sprawdzono osobno; w księdze wszystkie się wczytały.

Raporty i zrzuty: `docs/qa_0.8.18/ui16/`.

## Ograniczenia

Nie testowano na fizycznym telefonie ani na serwerze produkcyjnym. W kontenerze
nawigacja Chromium do lokalnego adresu HTTP jest blokowana, dlatego użyto istniejącego
mostu WebSocket przez Python i osadzonych rzeczywistych plików HTML/JS/CSS. Serwer
pracował na osobnej bazie w pamięci; żadne konta produkcyjne nie były używane.
Nie testowano całej walki, balansu Kolczastego wzrostu, długiego przytrzymania ani
natywnego klienta Godota. Historyczne niepowodzenia testów są wykazane, nie ukryte;
nie jest to deklaracja pełnej bezbłędności całej gry.
