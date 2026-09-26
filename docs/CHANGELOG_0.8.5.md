# Bractwo 0.8.5 — 24.09.2026

Baza: pełne źródła 0.8.4. Nie zmieniono progów kręgów, kosztów many, podstawowych kości i HP, zasad pościgu ani zabezpieczeń PvP.

## Mechanika i grafika

Wspólna geometria serwer/klient: stożek-trójkąt bez starego kołowego ograniczenia i marginesu, linia-prostokąt, koło, kwadrat, dziesięć przylegających kwadratów Burzy ognia, cztery oddzielne centra meteorów. Rozmiary odpowiednich obszarów przeliczone z opisów SRD: 32 jednostki = 5 stóp. Wyszukiwanie odbiorców obejmuje cały obrys, także dalekie rogi stożka. Wielokrotne nakładanie części jednego obszaru nie powoduje wielokrotnych obrażeń temu samemu celowi. Błyskawica łańcuchowa ma główny cel i do trzech odgałęzień, nie kołowy wybuch.

Własne animacje wszystkich obecnych czarów/zdolności i 47 różnych ikon. Magiczny pocisk: trzy rozdzielone krzywe i ślady; Promień mrozu: biało-błękitny promień z rozpryskiem. Pozostałe rodziny obejmują płomienie, lód, kwas, błyskawice, korzenie, meteory, tarcze, leczenie, przemiany i przyzwanie. Każda zdolność wskazuje własną ikonę i profil wizualny; efekty tej samej rodziny współdzielą renderer, nie 47 oddzielnych plików animacji. Pola utrzymują grafikę i wygasają wraz z serwerem lub koncentracją.

Przygotowane 7 ikon wyposażenia uwzględnia typ broni klasy. Nie są to indywidualne ilustracje każdego przedmiotu gry. Generator SVG i renderery należą do źródeł projektu.

## Karta, skróty i zapisy

Samodzielna karta pod C oraz prawym górnym przyciskiem: Ekwipunek, Statystyki, Atuty, Czary. I/K otwierają właściwe zakładki. Dziennik/atlas pozostają osobno. Ekwipunek: trzy istniejące sloty wyposażenia u góry, plecak 5 × 3 ze stronami, szczegóły i działania. Statystyki korzystają z faktycznych obliczeń, obejmują 6 cech i obron, 13 typów obrażeń/odporności, kości broni, atak czarami, KP, ST, liczbę ataków, ruch i istniejące zasoby. Dane właściciela nie są ujawniane w publicznych rekordach innych graczy. Atuty są świadomie puste; mechanika atutów nie została dodana.

Dwa rzędy po 12 miejsc (1–0, −, = oraz F1–F12), wspólne strony po 24. Poprawne stare indeksy pozostają, brakujące czary są dopisywane, obce/zablokowane i duplikaty usuwane. Rezerwowe strony obsługują więcej niż 24 czary. Mobile: wspólne przewijanie poziome dwóch rzędów. Usunięto stare, nieosiągalne implementacje księgi w panelu świata. Poprawiono także stare opisy specjalizacji, by odpowiadały rzeczywistym wartościom.

F korzysta z utrwalanej historii ostatnich 100 rzeczywistych użyć: najczęstszy wygrywa, przy remisie ostatnio użyty. Nieudane próby i sam wybór skrótu nie zwiększają wyniku. Reakcja Tarczy liczy się po uruchomieniu, a pole i wielopociskowy czar raz na rzucenie. Dotychczasowe konta bez historii korzystają początkowo z domyślnej zdolności. Dodano ochronę skrótów przed przechwytywaniem Ctrl/Alt/Meta. Nie dodano automatycznego powtarzania czaru pod F.

## Granice adaptacji i weryfikacja

Wybrana istota wyznacza środek/kierunek. Brak oddzielnego trybu wyboru punktu na ziemi, swobodnej konfiguracji dziesięciu pól lub czterech meteorów, dzielenia trzech pocisków między różnych odbiorców. Trafienie używa środka postaci i dodatkowych kontroli widoczności, piętra oraz PvP. Grafika nie jest przycinana do każdej ściany ani do chronionych graczy. Pociski są animacją, a wynik jest rozstrzygany przy wykonaniu akcji na serwerze. Zachowano dotychczasowe adaptacje czasów i pozostałych zasięgów.

Pełny zakres wykonanych prób i niewykonanego uruchomienia/kompilacji Godota: `TEST_REPORT.md`. Bez resetu bazy; aktualizować serwer i klienta razem. Wersja 0.8.5, Android code 12, brak eksportów binarnych.
