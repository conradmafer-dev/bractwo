# Bractwo 0.8.17 — aktualizacja istniejącej usługi

Paczka zawiera kod, nie wykonane wdrożenie. Nie zmieniaj usługi ani wolumenu na nowy tylko w celu aktualizacji.

1. Zatrzymaj usługę, zachowaj kopię bazy /data/world.sqlite3 i dotychczasowy wolumen.
2. Podmień zawartość repozytorium. Na pierwszym poziomie: Dockerfile, run.py, requirements.txt, server/ i web/. Nie przesyłaj ZIP-a jako pliku repozytorium, zapisów ani sekretów.
3. Podmień cały web wraz z caster_ui.js, caster_vfx.js, caster.css i assets/; backend i frontend muszą mieć tę samą wersję.
4. Pozostaw mount path /data, BRACTWO_DB_PATH=/data/world.sqlite3, PORT=8080, healthcheck /health, jedną replikę i opróżnianie30s. Dockerfile uruchamia run.py. Te ustawienia pochodzą z istniejącej konfiguracji0.8.13, nie były sprawdzane na koncie Railway w tej aktualizacji.
5. Uruchom wdrożenie. /health powinno zwrócić version:0.8.17 oraz ok:true. W przeglądarce Ctrl+F5, bez starego lokalnego index.html.
6. Sprawdź starą postać: druid ma wybór w C→Atuty, mag Odzyskanie mocy i rytuały. Własne UID i przedmioty pozostają. Nie ma resetu.

Wybór Strażnika nie dodaje pancerza. Stary średni pancerz druida ma przejściowe uprawnienie tylko do pierwszego wyboru ścieżki. Wybierając Mistyka bez osobnego wyszkolenia w średnich pancerzach trzeba potem używać lekkiego lub zdobyć atut. Przedmiot nie zostaje skasowany.

Do cofnięcia aktualizacji potrzebna jest również kopia bazy sprzed migracji. Nie uruchamiaj starego serwera na nowszym zapisie.

Wykonano lokalne testy launchera i restartu, nie build Dockera i nie wdrożenie w Railway. Pełen raport: TEST_REPORT.md.
