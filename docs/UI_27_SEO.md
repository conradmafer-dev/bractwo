# UI_27 — strona tytułowa i SEO Bractwa Krain

Aktualizacja na bazie UI_26. Publiczna strona główna przedstawia grę przed
logowaniem: cztery klasy, świat, wyprawy, rozwój postaci i sposób rozpoczęcia
rozgrywki. Zrzut pustynnej osady pochodzi z pliku `Bractwo.png` przekazanego
przez autora gry; jest użyty bez zmiany obrazu, także w podglądzie linku.

## Co zawiera aktualizacja

- Polski tytuł strony i opis dla wyszukiwarki, jeden główny nagłówek H1 oraz
  tekst dostępny w odpowiedzi HTML, bez wykonywania JavaScript i logowania.
- Układ na komputer i telefon, nawigacja po sekcjach, przyciski prowadzące
  do logowania, opisy klas, krótka instrukcja i pytania graczy.
- Open Graph oraz karta dużego obrazu dla podglądów linków. Zrzut ekranu ma
  podane rzeczywiste wymiary 1920 × 1080 i opis alternatywny.
- Canonical, dane strukturalne `WebSite` i `VideoGame`, `/robots.txt` oraz
  `/sitemap.xml`. Mapa zawiera publiczną stronę główną, bez prywatnych kont.
- Opcjonalny tag weryfikacyjny Google Search Console.
- Przekierowanie `/index.html` na `/`, aktualna wersja UI_27 w `/health`
  i odświeżenie wersji service workera.

Logowanie Google, limit czterech postaci, zapis postaci oraz rozgrywka z UI_26
pozostają dostępne. Aktualizacja nie zmienia bazy danych ani zdolności klas.
Nie należy otwierać pliku HTML bezpośrednio z dysku: metadane adresów generuje
serwer, który obsługuje również logowanie i mapę witryny.

## Wgranie paczki

1. Rozpakuj `BRACTWO_KRAIN_0.8.18_UI_27_SEO_RAILWAY_GITHUB_READY.zip`.
2. Wgraj zawartość do głównego katalogu istniejącego repozytorium GitHub.
   `Dockerfile`, `run.py`, `server/` i `web/` mają być obok siebie.
3. Zachowaj istniejący wolumen, bazę graczy, jedną replikę oraz ustawienia
   `GOOGLE_CLIENT_ID`, `GOOGLE_AUTH_ORIGIN` i `BRACTWO_DB_PATH`.
4. Wdróż zmianę na Railway i odśwież stronę. `/health` powinno pokazać
   `"ui_revision":"UI_27"`.

Paczka `SEO_PATCH` jest mniejszą alternatywą **wyłącznie dla UI_26**. Zawiera
zmienione i nowe pliki, które należy nałożyć na pełny projekt; nie działa
samodzielnie. Przed nadpisaniem zachowaj własne zmiany. Pełna paczka READY
jest właściwa przy starszej wersji lub niepewności co do wersji serwera.

## Adres strony

Dla obecnej domeny nie trzeba dodawać nowej zmiennej. Domyślnie wszystkie
publiczne adresy SEO wskazują `https://bractwo.up.railway.app/`.
Można też jawnie ustawić w Railway:

```text
PUBLIC_SITE_URL=https://bractwo.up.railway.app
```

Po uruchomieniu własnej domeny ustaw tutaj jej pełny adres HTTPS, bez ścieżki,
parametrów i fragmentu `#`. Canonical, podgląd linku, dane strukturalne i sitemap
zmienią się razem po restarcie. Nieprawidłowa wartość wraca do domyślnego adresu.
Wartość nie jest pobierana z nagłówka Host odwiedzającego.

To ustawienie samo nie podłącza domeny i nie tworzy przekierowania ze starej
domeny. Przy zmianie domeny trzeba osobno skonfigurować hosting i przekierowanie
oraz zaktualizować `GOOGLE_AUTH_ORIGIN` i dozwolony origin klienta Google OAuth.

## Google Search Console po wdrożeniu

1. Otwórz https://search.google.com/search-console i dodaj usługę typu
   **Prefiks adresu URL**: `https://bractwo.up.railway.app/`.
2. Wybierz weryfikację **Tag HTML**. Z otrzymanego znacznika skopiuj tylko
   wartość atrybutu `content`, bez całego znacznika i bez cudzysłowów.
3. Dodaj na Railway zmienną `GOOGLE_SITE_VERIFICATION` z tą wartością
   i ponownie wdróż serwer. Nie wpisuj Client ID OAuth: to dwa różne ustawienia.
4. Kliknij **Zweryfikuj** w Search Console. Pozostaw zmienną po weryfikacji.
5. W sekcji map witryn prześlij `sitemap.xml`. Następnie użyj sprawdzenia
   adresu strony głównej i poproś o zindeksowanie.

Adresy do sprawdzenia po publikacji:

- https://bractwo.up.railway.app/
- https://bractwo.up.railway.app/robots.txt
- https://bractwo.up.railway.app/sitemap.xml

Strona jest przygotowana do indeksowania; czas indeksacji, wybrany opis
wyniku i pozycja zależą od wyszukiwarki. Dane `VideoGame` opisują grę, bez
fikcyjnych ocen i bez obietnicy specjalnego wyniku z gwiazdkami.

## Weryfikacja wydania

Raporty bieżącej aktualizacji znajdują się w `docs/qa_0.8.18/ui27/`.
Obejmują HTTP, metadane, adresy i mapę strony, zgodność logowania i service
workera oraz przeglądarkowy wygląd i przejście do gry na komputerze i telefonie.
Kontrola przeglądarkowa używa osobnej bazy w pamięci i testowego dostawcy
Google. Nie jest logowaniem prawdziwym kontem ani testem fizycznego telefonu.
Nie wykonano publikacji na Railway ani zgłoszenia w Search Console.

## Dokumentacja źródłowa

- Google: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Nazwa witryny: https://developers.google.com/search/docs/appearance/site-names?hl=pl
- Mapa witryny: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=pl
- Weryfikacja własności: https://support.google.com/webmasters/answer/9008080?hl=pl
- Opis typu gry: https://schema.org/VideoGame
