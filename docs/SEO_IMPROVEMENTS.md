# Ulepszenia SEO Bractwa Krain

Aktualizacja obejmuje publiczne treści, metadane i wydajność strony.
Serwer i katalog `web/` trzeba wdrażać razem. Dalsze rozszerzenia — galerię,
nagłówki D&D oraz publiczne komentarze — opisuje
[Galeria i komentarze](KOMENTARZE_I_GALERIA.md).

Sprawdzenia opisane poniżej wykonano lokalnie. Indeksację i stan wdrożenia
należy weryfikować oddzielnie na działającej domenie. Nie wykonano zgłoszenia
stron w Google Search Console.

## Publiczne treści

Dodano trzy odrębne poradniki, dostępne bez logowania i JavaScript:

| Adres | Zakres |
| --- | --- |
| `/poradniki/jak-zaczac` | Konto Google, wybór bohatera, sterowanie, śledzenie zadań, podstawy walki, odpoczynek i odrodzenie. |
| `/poradniki/klasy-postaci` | Porównanie rycerza, łowcy, czarodzieja i druida; progi rozwoju, promocja i wybór specjalizacji. |
| `/poradniki/swiat-i-wyprawy` | Atlas, zadania, podziemia, rejsy, przygotowanie do walki, drużyna i odbieranie nagród. |

Każdy poradnik ma jeden nagłówek H1, hierarchię nagłówków, spis treści,
ścieżkę nawigacji, odnośniki do powiązanych poradników i przycisk prowadzący
do wejścia do gry. Treść jest częścią odpowiedzi HTML. Wspólny `guide.css`
korzysta z fontów systemowych oraz stylu ciemnej zieleni i złota. Strony
nie pobierają skryptów klienta gry ani zewnętrznych zasobów.

Treść sprawdzono na podstawie pomocy w `web/index.html`, `README.md`,
bieżącej implementacji oraz dokumentacji UI_19, UI_20, UI_24–30 i zasad
odpoczynku. Starsze dokumenty uwzględniono tylko tam, gdzie nie zmieniają
ich późniejsze wersje. Przykładowo odrodzenie wymaga użycia kamienia,
a przeprawa przez ocean odbywa się łodzią. Nie dodano fikcyjnych ocen,
liczby aktywnych graczy ani obietnic uzyskania pozycji w wyszukiwarce.

Metadane poradników generuje serwer na podstawie znacznika `SEO_HEAD`.
Zmiana publicznej domeny powinna obejmować wspólne ustawienie
`PUBLIC_SITE_URL`, aby canonical, sitemap i podglądy wskazywały spójne adresy.

Każda z czterech stron ma własny tytuł, opis, canonical, metadane Open Graph
i dane strukturalne. Poradniki zawierają `WebPage` i `BreadcrumbList`,
a strona główna także `WebSite` i `VideoGame`. Mapa witryny obejmuje cztery
publiczne adresy. Warianty adresów poradników z końcowym ukośnikiem lub
`.html` przekierowują kodem 301. Adresy techniczne i błędy otrzymują
`X-Robots-Tag: noindex, nofollow`; nieistniejące strony zwracają prawdziwe 404.
Publiczny HTML obsługuje gzip i ponowne sprawdzenie wersji przez ETag.

## Pierwsze wyświetlenie i transfer

- 28 zewnętrznych skryptów strony głównej ma atrybut `defer`, aby nie
  zatrzymywać parsera HTML.
- 11 arkuszy dotyczących interfejsu rozgrywki ładuje się bez blokowania
  pierwszego renderowania publicznej strony.
- `game.js` nie buduje i nie renderuje świata bez zalogowanej postaci.
- Zapis niezmienionej widoczności powiadomień awansu nie uruchamia już
  kolejnych klatek interfejsu przez obserwator zmian DOM.
- Budowanie obrazu Docker przygotowuje wersje gzip zasobów CSS, JS i SVG.
  Końcowy pomiar 323 zasobów: 1 110 756 → 346 617 bajtów, czyli 68,8% mniej.
  To łączny rozmiar kompresowanych zasobów, nie pomiar szybkości ładowania.

Te zmiany ograniczają pracę przed wejściem do gry. Nie stanowią pomiaru
Core Web Vitals produkcji; wynik należy sprawdzić po wdrożeniu.

## Wdrożenie i kontrola adresów

1. Wdróż aktualny serwer, `web/` i konfigurację budowania razem, zgodnie
   z istniejącym procesem Railway. Zachowaj bazę, trwały wolumen i ustawienia
   Google. Publiczne poradniki nie wymagają resetu postaci.
2. Ustaw lub pozostaw `PUBLIC_SITE_URL=https://bractwo.up.railway.app`.
   Jeśli używasz własnej domeny, wpisz jej pełny adres HTTPS bez ścieżki.
3. Sprawdź stronę główną, trzy poradniki, `/robots.txt` i `/sitemap.xml`.
   Treść oraz metadane powinny być dostępne także po wyłączeniu JavaScript.
4. Sprawdź canonical i adresy w sitemap. Powinny używać tej samej domeny
   oraz ostatecznych adresów bez zbędnych przekierowań.
5. Sprawdź na komputerze i telefonie, że poradniki prowadzą do panelu
   logowania, a logowanie i gra działają po zmianach ładowania zasobów.
6. Uruchom PageSpeed Insights dla strony głównej i jednego poradnika.
   Zapisz wyniki mobilne jako punkt odniesienia. Dane rzeczywistych
   użytkowników mogą wymagać odpowiednio dużego ruchu.

Własna domena wymaga oddzielnej konfiguracji hostingu, przekierowania ze
starego adresu i aktualizacji originów Google OAuth. Samo `PUBLIC_SITE_URL`
nie tworzy przekierowania ani nie podłącza domeny.

## Google Search Console po publikacji

1. W [Google Search Console](https://search.google.com/search-console)
   dodaj usługę **Prefiks adresu URL**: `https://bractwo.up.railway.app/`.
2. W metodzie **Tag HTML** skopiuj samą wartość atrybutu `content`.
   Zapisz ją na Railway w `GOOGLE_SITE_VERIFICATION` i wdróż serwer.
   To oddzielna wartość od identyfikatora klienta logowania Google.
3. Potwierdź weryfikację w Search Console. Pozostaw tę zmienną po weryfikacji.
4. W sekcji **Mapy witryn** prześlij `sitemap.xml`. Sprawdź, czy odczytano
   stronę główną i trzy poradniki.
5. W **Sprawdzeniu adresu URL** uruchom test opublikowanego adresu strony
   głównej i każdego poradnika. Jeśli Google może je pobrać, poproś
   o zindeksowanie.
6. W kolejnych tygodniach przeglądaj raport indeksowania i skuteczności.
   Analizuj zapytania oraz wyświetlenia osobno dla strony głównej
   i poradników. Rozwijaj treści na podstawie rzeczywistych pytań graczy.

Zgłoszenie mapy i prośba o indeksowanie pomagają odkryć strony, ale nie
gwarantują daty indeksacji, pozycji ani wybranego przez Google opisu wyniku.

## Sprawdzenia lokalne

Polecenia weryfikacji:

```bash
python -m unittest discover -s tests -p test_seo.py -v
python -m unittest discover -s tests -p test_precompressed_web.py -v
python -m unittest discover -s tests -p test_app_shell_http_0818.py -v
node --test tests/test_landing_rendering.cjs
python tools/seo_public_smoke.py
python tools/seo_gameplay_smoke.py
```

Kontrola Chromium przeszła 24 kombinacje: cztery strony, szerokości 1440,
390 i 320 px, z JavaScriptem oraz bez niego. Sprawdzono metadane, dane
strukturalne, sześć różnych odnośników lokalnych, odpowiedzi 200 dla 64
zasobów, brak poziomego przepełnienia i błędów JavaScript.
Poradniki mają pojedynczy H1, poprawne odnośniki do sekcji i nie pobierają
skryptów klienta gry.

Oddzielny test z bazą w pamięci i testowym dostawcą Google przeszedł na
komputerze oraz telefonie: logowanie, utworzenie postaci, renderowanie gry,
otwarcie karty postaci, wylogowanie i ponowny wybór postaci. Po ustabilizowaniu
strony wejścia nie odnotowano rysowania canvas ani powtarzanej pętli animacji.
Nie wykonano logowania prawdziwym kontem Google.

Przeszło 17 testów Pythona: 11 SEO, cztery istniejące testy HTTP aplikacji
i dwa testy kompresji zasobów. Sprawdzono także odmowę gzip przez `q=0`,
odpowiedzi HEAD/304 i zakresy bajtów. Przeszło też pięć testów regresyjnych
JavaScript dotyczących cyklu renderowania. Pełny starszy zestaw testów
repozytorium nie jest zielony:
`tests/test_server.py` nadal używa logowania hasłem (`hello`) i bez
konfiguracji Google kończy 33 testy błędem `/ws` 503. Ten sam błąd potwierdzono
dla przykładowego testu na oryginalnym kodzie z HEAD. Ponadto zastane pliki
`test_railway.py`, `test_client_runtime.cjs` i `test_level_up.cjs` zawierają
wyłącznie bajty NUL; `test_app_shell.cjs` oczekuje starej wersji cache.
Nie zmieniano tych plików w ramach SEO.
