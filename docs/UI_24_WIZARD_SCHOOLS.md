# Bractwo 0.8.18 UI_24 — szkoły czarodzieja

## Wybór szkoły

Czarodziej wybiera jedną z czterech szkół w **C → Atuty**. Wymagane są **poziom 10 i promocja**, kupowana u mistrza profesji za **2000 złota**. Sam wybór szkoły nie pobiera dodatkowego złota ani punktów mistrzostwa. Można wcześniej przeglądać wszystkie szkoły i ich zdolności.

Wybór jest trwały i wymaga zaznaczenia potwierdzenia. Należy go dokonać poza walką, odpoczynkiem, przemianą i rzucaniem czaru. Warunki sprawdza serwer: zmiana danych w przeglądarce, wysłanie własnego pakietu lub próba ponownego wyboru nie omijają wymagań. Promowany mag poniżej poziomu 10 również nie może wybrać szkoły.

## Działające zdolności

| Szkoła | Poziom 10 | Poziom 25 | Poziom 45 | Poziom 65 |
| --- | --- | --- | --- | --- |
| Ewokacja | Potężne sztuczki: połowa obrażeń przy pudle lub udanej obronie celu, bez dodatkowego skutku pudła | Rzeźbienie czarów: obszarowe ewokacje z obroną oszczędzają do 1 + krąg czaru niezaznaczonych graczy | Wzmocniona ewokacja: modyfikator Inteligencji do jednego rzutu obrażeń podczas rzucenia czaru | Przeciążenie: maksymalne kości płatnego czaru I–V kręgu; pierwsze użycie bezpieczne, następne powodują rosnące obrażenia własne |
| Odpychanie | Magiczna osłona tworzona płatnym czarem odpychania; osobne HP osłony i doładowanie za manę | Projekcja osłony na wskazanego członka drużyny, wykorzystująca reakcję | Krótki odpoczynek odbudowuje utworzoną osłonę | Połowa obrażeń czarów i ułatwienie obron przeciw czarom |
| Wróżbiarstwo | Dwa wyniki k20 przygotowywane przed własnym atakiem, własną obroną lub obroną celu czaru | Zużyta przepowiednia przywraca 20 many do maksimum | Trzecie oko ignoruje magiczną mgłę i Rozmycie przez 30 sekund | Trzy przepowiednie po długim odpoczynku |
| Iluzja | Sobowtór utrudnia następny atak na maga; dwa użycia na długi odpoczynek | Walczący widmowy wilk, pierwsze przywołanie darmowe i z połową HP | Przygotowana reakcja Iluzorycznego ja zamienia trafienie w pudło | Nieruchoma osłona drużyny: +2 KP i +2 do obrony Zręczności w promieniu 15 stóp przez 30 sekund |

To adaptacje do systemu walki Bractwa. Nazwy nie oznaczają pełnej zgodności z podręcznikowymi zdolnościami gry stołowej. Opisy w interfejsie podają rzeczywiście zaimplementowane działanie.

### Koszty i ograniczenia

- **Ewokacja:** Potężne sztuczki nie obejmują Iskry różdżki. Ochrona obszarowa pozostawia zaznaczonego przeciwnika PvP jako cel. Premia Inteligencji jest jednokrotna podczas rzucenia czaru, nie osobna dla każdego pocisku lub kolejnego tyknięcia pola. Przeciążenie wzmacnia obrażenia w turze rzucenia; po pierwszym użyciu na długi odpoczynek zadaje magowi 2k12 za krąg, przy każdym następnym o 1k12 za krąg więcej. Odrzut omija odporności, osłonę i tymczasowe HP oraz może zabić postać.
- **Odpychanie:** pojemność osłony wynosi `2 × efektywny poziom + modyfikator Inteligencji`. Pierwszy płatny czar odpychania po długim odpoczynku tworzy pełną osłonę; następne odnawiają 2 HP za krąg. Akcja dodatkowa za 20 many odnawia 2 HP już utworzonej osłony. Osłona działa po odporności na obrażenia, przed koncentracją i tymczasowymi HP. Projekcja wymaga żywego członka drużyny w zasięgu 30 stóp, widoczności, tej samej kondygnacji i dostępnej reakcji. Odporność poziomu 65 obejmuje źródła oznaczone jako czary, a nie dowolny atak obszarowy potwora.
- **Wróżbiarstwo:** wyniki losuje serwer przy wyborze szkoły i po długim odpoczynku. Wynik oraz tryb trzeba wybrać przed rzutem. Anulowanie przygotowania nie zużywa kości. Limit wynosi jedną przepowiednię na turę, także po ponownym połączeniu. Trzecie oko zużywa akcję dodatkową, odnawia się po krótkim lub długim odpoczynku i nie pozwala widzieć przez ściany ani ignorować ślepoty.
- **Iluzja:** Sobowtór trwa najwyżej 30 sekund i zużywa akcję dodatkową. Kolejne przywołania wilka kosztują 30 many i zapewniają pełne HP; może istnieć tylko jeden towarzysz. Iluzoryczne ja odnawia się po krótkim odpoczynku; zużyte użycie można także przywrócić akcją dodatkową za 30 many. Osłona poziomu 65 zużywa akcję i jedno użycie na długi odpoczynek. Jej premie nie sumują się z Sanktuarium natury i przestają działać po wyjściu z obszaru. Pomoc drużynie respektuje zasady PvP.

## Interfejs, grafiki i zapis

Panel pokazuje kolejne progi rozwoju, rzeczywiste wyniki przepowiedni, HP osłony i pozostałe użycia. Zdolności aktywne można rzucać z panelu lub przypisać do paska. Księga filtruje zdolności należące do innych szkół. Przyciski uwzględniają brak zasobów, aktywny efekt oraz odnawianie akcji.

Dodano własne ikony czterech szkół i sześciu zdolności aktywnych. Efekty obejmują runiczną osłonę, widmowe sobowtóry, złote Trzecie oko, widmowego wilka oraz granicę osłony z filarami. Trwałe efekty wynikają z aktualnego stanu serwera.

Wybór szkoły, HP osłony, wykorzystane zdolności i wyniki przepowiedni są zapisywane. Odświeżenie strony ani ponowne logowanie nie odnawia zasobów. Tymczasowe efekty i przygotowany cel projekcji wygasają przy rozłączeniu; przygotowanie przepowiedni trzeba ponowić. Istniejące postacie nie dostają szkoły ani promocji automatycznie. Wcześniej wybrane kręgi druidów pozostają zachowane.

## Wdrożenie

Paczka zawiera poprawki UI_23, w tym promocję od poziomu 10 oraz osobne grafiki demonów, a także wcześniejszy świat, łupy, animacje i konta Google. Wgraj cały **RAILWAY_GITHUB_READY**, zachowując bazę, wolumen i zmienne Google. Serwer i klient muszą być z tej samej paczki. Odśwież stronę; ekran wejścia i `/health` pokazują **UI_24**. Reset postaci nie jest potrzebny.

Aktualizacja nie została automatycznie wdrożona na Railway. FULL_SOURCE zawiera także historyczny klient Godota, który nadal nie ma integracji kont Google; nie jest to nowa wersja APK.

## Weryfikacja

Raport zbiorczy: `docs/qa_0.8.18/ui24/summary.json`. Testy obejmują wybór, zapis i odpoczynek, obrażenia i ochronę, przepowiednie, przyciski, ikony i rysowanie efektów. Przepływy przeglądarkowe używają produkcyjnego HTTP/WebSocket, izolowanej bazy i jawnego testowego dostawcy Google. Sprawdzono widok desktopowy oraz emulację telefonu; nie wykonano logowania prawdziwym kontem Google ani testu na fizycznym telefonie.
