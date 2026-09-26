# Bractwo 0.8.9 — mikstury, najczęstszy czar i statusy

Baza: `BRACTWO_0.8.8_NOWE_PRZEDMIOTY_POTWORY_LOOT_FULL_SOURCE.zip`.

- Wspólny dolny układ WWW utrzymuje kolejność czat → mikstury → oba paski czarów. Mikstury Q/R zachowują oryginalne identyfikatory, liczniki oraz obsługę.
- Najczęściej używany czar/zdolność F przeniesiono obok K Czary. Wybór według historii, aktualizowana ikona, mana i odnowienia pozostają bez zmian. F jest poza przewijanym obszarem slotów.
- Własne efekty i efekty celu przeniesiono na górę. Nie mają wspólnego tła ani ramki, a puste miejsce nie przejmuje kliknięć. Zachowano szczegóły po kliknięciu, czas i rundy. Przyciski celu otrzymały oznaczenie „Cel”.
- Dopasowano układ pionowy i poziomy. Na krótkim ekranie pionowym śledzone zadanie pozostaje jako klikalny tytuł, żeby nie zasłaniać czatu.
- Dodano `web/hud_layout.css`, jego odnośnik w HTML oraz rzeczywistą trasę HTTP. Istniejące pliki stylów nie zostały zastąpione.
- W źródłach Godota przeniesiono mikstury oraz F i zastąpiono zbiorcze teksty efektów oddzielnymi przyciskami z opisem. Weryfikacja Godota obejmuje tylko źródła, nie pracę silnika.
- Podniesiono oznaczenie aplikacji do 0.8.9. Brak migracji bazy, zmian balansu, zawartości świata lub lootu.

Pełna paczka i Railway zawierają bajtowo identyczny serwer i klient WWW. Nowa wersja wymaga podmiany obu katalogów razem.
