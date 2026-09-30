# Bractwo 0.8.18 UI_23 — promocja i demony

## Wprowadzone zmiany

- Promocja wszystkich profesji od poziomu 10 (wcześniej 20), jednorazowo za 2000 złota u mistrza w mieście, poza walką.
- Serwer udostępnia klientowi rzeczywisty wymagany poziom i koszt. Interfejs oraz opis rozwoju wskazują nowy próg.
- Nowy wybór kręgu druida wymaga poziomu 10 i uzyskanej promocji. W C → Atuty można obejrzeć możliwości przed zakupem; przycisk wyboru wyjaśnia brak promocji.
- Wcześniej wybrane kręgi i ich zdolności pozostają aktywne bez wymuszania ponownego zakupu. Migracja nie pobiera złota i nie nadaje promocji automatycznie.
- Punkty Potęgi i Skupienia są konsekwentnie nazwane punktami mistrzostwa. Pierwszy punkt nadal na poziomie 50, następne co 5 poziomów.
- Demon ma własną humanoidalną sylwetkę z rogami, pazurami, kopytami i ogonem. Wędrowiec Otchłani i Władca Otchłani otrzymały odrębne warianty; Władca nosi koronę i włócznię. Każdy ma cztery klatki ruchu.
- Także rysowanie awaryjne rozróżnia demony i smoki. Dodano zgodne zasoby do historycznych źródeł Godota.

## Zakres szkół czarodzieja

Szkoły czarodzieja nie były dotąd zaimplementowane i nie zostały dodane w tej paczce. Wcześniejsza rozmowa dotyczyła propozycji. Planowany warunek wyboru szkoły to poziom 10 i promocja; wymaga to osobnego wdrożenia szkół i ich działających zdolności. W tej wersji sprawdzany jest wybór już istniejących kręgów druida.

## Propozycje do ustalenia — jeszcze niewprowadzone

- Wojownik: dodatkowe maksymalne użycie Drugiego oddechu; krótki odpoczynek nadal przywraca jedno, długi wszystkie.
- Łowca: dodatkowe przywołanie wilczego towarzysza między długimi odpoczynkami, nadal najwyżej jeden aktywny towarzysz.
- Druid: odblokowanie kręgu zapewnia korzyść od poziomu 10. Jeżeli potrzebna będzie osobna premia samej rangi, można rozważyć dodatkowe użycie Dzikiego kształtu.

To propozycje autorskich premii Bractwa, nie deklaracja zgodności z zasadami D&D.

## Wdrożenie i weryfikacja

Wgraj cały pakiet RAILWAY_GITHUB_READY, zachowując bazę, wolumen i zmienne Google. Ekran wejścia i `/health` wskazują UI_23. Odśwież stronę. Aktualizacja nie jest automatycznie wdrażana na Railway.

Raport: `docs/qa_0.8.18/ui23/summary.json`. Przeglądarka jest sprawdzana lokalnie z testowym dostawcą Google. Natywny klient Godot nadal ma historyczne logowanie i nie obsługuje kont Google; brak nowego APK. Nie przeprowadzono logowania prawdziwym kontem Google ani testu na fizycznym telefonie.
