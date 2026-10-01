# Galeria, mechaniki D&D i komentarze

Zmiany są częścią aplikacji Bractwo Krain. Ten dokument opisuje kod;
sam zapis plików nie wdraża go na Railway.

## Strona gry

- Galeria `/#galeria` zawiera wszystkie sześć screenshotów dostarczonych
  przez właściciela w `Desktop.zip` i `screeny.zip`. Pełne PNG zachowano
  bez zmian. Podglądy WebP 640/960 px mają responsywny `srcset`, rozmiary,
  opóźnione ładowanie, podpisy oraz osobne polskie alty opisujące sceny.
  Komplet podglądów 960 px ma około 313 KB, a oryginały około 3,06 MB.
- Tytuł i główny nagłówek zawierają „polskie MMORPG” i „D&D”. Pełne
  „Dungeons & Dragons” występuje w opisie, podtytule oraz nagłówku sekcji
  `/#mechanika-dnd`. Tekst opisuje atuty, kręgi czarów, koncentrację,
  rzuty k20, klasę pancerza, rzuty obronne i trafienia krytyczne.
  Gra jest opisana jako autorska adaptacja wybranych zasad.
- Komentarze `/#komentarze` może czytać każdy. Pierwsze 20 jest renderowane
  w HTML na serwerze, także bez JavaScript. Starsze wpisy wczytuje przycisk.
  Wyświetlany tekst nie jest interpretowany jako HTML ani zamieniany w linki.

## Pisanie i usuwanie

Zalogowany użytkownik wybiera podpis spośród własnych postaci. Serwer
sprawdza powiązanie postaci z kontem, niezależnie od pól formularza.
Użytkownik bez postaci najpierw tworzy ją w istniejącym panelu logowania.
E-mail oraz identyfikator Google nie są publikowane.

Komentarz ma od 3 do 1000 znaków. Serwer odrzuca rozpoznane polskie
i popularne angielskie wulgaryzmy, także typowe odmiany oraz zapis
z separatorami, cyframi, powtarzanymi literami lub niewidocznymi znakami.
Słownik znajduje się w `server/profanity.py`. Wulgarny podpis jest zastępowany
neutralnym „Gracz Bractwa Krain”. Filtr jest również stosowany przy odczycie,
więc jego rozszerzenie może ukryć wcześniej zaakceptowany wpis.

Automatyczny filtr nie rozpoznaje każdego obejścia i może wymagać korekt
słownika. Nie jest pełnym systemem moderacji wypowiedzi i kontekstu.

Jedno konto może dodawać wpis co 30 sekund i najwyżej 20 wpisów na godzinę.
Duplikaty z ostatnich 24 godzin są odrzucane. Usunięcie wpisu nie resetuje
limitów. Autor może usunąć własny komentarz; obce wpisy są chronione
sprawdzeniem właściciela na serwerze.

## Zapis i sesja

Komentarze i limity trafiają do tabel `public_comments` oraz
`comment_post_events` w tej samej bazie SQLite, z której korzysta gra.
Tabele są tworzone automatycznie bez usuwania istniejących danych.
Na Railway trzeba zachować dotychczasową trwałą bazę/volume.

Sesja komentarzy powstaje wyłącznie po zweryfikowanym logowaniu Google.
Używa osobnego losowego cookie HttpOnly, SameSite=Strict i Secure
(wyjątek: lokalny serwer HTTP). W pamięci serwera jest wyłącznie hash
tokenu sesji. Sesja trwa maksymalnie osiem godzin; restart wymaga ponownego
logowania do komentarzy, ale nie usuwa wpisów.

Żądania zapisujące wymagają dokładnego `GOOGLE_AUTH_ORIGIN` oraz nagłówka
`X-Bractwo-Comments: 1`. API nie udostępnia CORS, stosuje `no-store` i
`noindex`; publiczna treść jest dostępna na indeksowalnej stronie głównej.
Nie dodano ocen gwiazdkowych ani sztucznych danych Review/AggregateRating.

## Weryfikacja

```bash
python -m unittest discover -s tests -p test_profanity.py
python -m unittest discover -s tests -p test_comments.py
python -m unittest discover -s tests -p test_seo.py
python tools/comments_smoke.py
python tools/comments_race_smoke.py
python tools/seo_public_smoke.py
python tools/seo_gameplay_smoke.py
```

Testy przeglądarkowe używają lokalnej bazy w pamięci i testowego dostawcy
logowania. Nie tworzą komentarzy na produkcji ani nie logują prawdziwego
konta Google.
