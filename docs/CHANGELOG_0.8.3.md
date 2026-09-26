# Bractwo 0.8.3 — pierwszy krąg od 1. poziomu

## Zmiana
Czarodziej i druid mogą rzucać wszystkie obecne czary I kręgu od poziomu 1. Katalog i rzeczywiste sprawdzanie dostępu na serwerze korzystają z nowego progu. Pole `spell_circle` jest zgodne z księgą i paskiem. Nie dodano nowych czarów ani zmian kości obrażeń.

- Czarodziej: Magiczny pocisk, Płonące dłonie, Tarcza, Zbroja maga, Długonogi.
- Druid: Leczenie ran, Uzdrawiające słowo, Oplątanie, Długonogi.
- II–IX pozostają na poziomach 20/30/40/50/60/70/80/90. Na 10. poziomie nie odblokowuje się nowy krąg.
- Łowca: I–V nadal na 20/40/60/80/100, również dla czarów dzielonych z druidem i czarodziejem.
- Mana, 6 many za I krąg, bezpłatne sztuczki, rundy, koncentracja, przemiany i dodatkowe ataki pozostają bez zmian. Tarcza pobiera manę dopiero za reakcję, nie za włączenie.

## Klienci i zapisy
Księga, pasek, opis klasy, pomoc oraz lista odblokowań pokazują nowe progi. Domyślny pasek już zawiera czary I kręgu — nic nie trzeba kupować ani przypisywać, żeby użyć slotów 4/5. Pozostałe czary można przypisać w księdze. Nie nadpisuje się własnych skrótów zapisanych postaci. Poprawiono przy okazji historyczny opis PvP w pomocy WWW; zasady PvP pozostają bez zmian.

Zaktualizuj serwer i klienta, zachowując `data/world.sqlite3` po wykonaniu kopii przy zatrzymanym serwerze. Nie jest wymagany reset ani migracja schematu. Wcześniejsze postacie poziomów 1–9 uzyskują I krąg po zalogowaniu do nowego serwera. Blokada PvP, ochrona osad i postaci poniżej poziomu 8 nadal obowiązują.

Wersja źródeł i metadanych eksportu: 0.8.3; Android version/code: 10. Nie przygotowano binarnych eksportów ani nie uruchamiano silnika Godot.

## Sprawdzenie
Bieżące testy i ograniczenia weryfikacji: `TEST_REPORT.md` oraz `qa_0.8.3/`. Wyniki starszych paczek zostały zachowane jako historia, nie jako dowód przetestowania tej wersji.
