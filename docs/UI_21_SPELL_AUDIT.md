# UI21 — końcowy audyt animacji zaklęć

**Pokrycie przeglądu: 99/99 pozycji katalogu serwera.** Wersja UI21 ma przypisaną drogę wizualizacji każdej pozycji, w tym zdolności klasowe, 10 dzikich kształtów, 12 zdolności kręgów i 23 czary kręgów. Wyrwanie się, odzyskanie mocy i zryw wojownika zachowują właściwe im komunikaty rozgrywki. Audyt nie zmienia produkcji.

## Weryfikacja

- **Przegląd implementacji:** 99 pozycji i ich emitery, 10 żywych pól `circle_fields`, stany `circle_visual`, geometria i limity pętli w obu klientach.
- **Przeglądarka:** odtworzenie komunikatów `Game.spell_effect` dla wszystkich 99 pozycji w 6 fazach (594 wywołania). To kontrola rysowania, nie 99 pełnych rzutów w rozgrywce.
- **Rzeczywiste rzuty przez produkcyjny WebSocket:** `call_lightning`, `cure_wounds`, `fireball`, `fog_cloud`, `ice_storm`, `insect_plague`, `magic_missile`, `misty_step`, `moonbeam`, `ray_of_frost`, `thorn_whip`, `web`. Osobno sprawdzono ręczne ponowienie błyskawicy i rzeczywisty tick obrażeń Moonbeam.
- **Końcowa bramka przeglądarki:** zaliczona: 18 kontroli, zero błędów JavaScript i HTTP; 16 wariantów pól ze snapshotów. Szczegóły w `browser_vfx_results.json`.
- **Zasoby i reguły:** wszystkie 99 powiązań ikon rozwiązują się w web i Godot (część ikon jest współdzielona). `icons.json` potwierdza zasoby, a `gameplay_compatibility.json` niezmienione reguły i przegląd zmienionych emiterów. 10 hashy produkcyjnych zapisanych w końcowym raporcie przeglądarki zgadza się z audytowanymi plikami.
- **Godot:** przegląd statyczny kodu i podłączeń. Silnik jest niedostępny, więc nie zadeklarowano parsowania ani testu renderowania w czasie działania.

## Usunięte braki o najwyższym priorytecie

- `call_lightning`: błyskawica z góry na każdy rzeczywisty `cast/recast`, bez samoczynnych dodatkowych trafień.
- `circle_star_arrow`, `beast_trample`, udany krok `tree_stride` i towarzyszący Moonlight Step mają właściwe eventy źródłowe. Dekoracyjne eventy `visual_only` nie zadają obrażeń i nie zmieniają akcji.
- `sleep`, `shatter`, `thunderwave`: rysowany obszar zachowuje punkt wybrany przez gracza oraz geometrię serwera.
- Godot konsumuje teraz `circle_fields` i `circle_visual`: mury, mgły, pajęczyna, roje, żywioły, sanktuarium, morze i konstelacje mają żywe odpowiedniki.
- Wyróżniono grad, deszcz strzał, leczenie grupowe, cierniowy bicz, więzy, teleportację, gwiezdny pocisk i liczne ochrony. Wielocelowe więzy/oddychanie korzystają z listy rzeczywistych odbiorców.

## Granice i zachowana mechanika

- `event.area` pozostaje autorytatywną figurą trafienia. Pionowe płomienie, błyskawice i wstęgi są dekoracją; nie rozszerzają hitboxów. Tick odtwarza tylko faktycznie rozstrzygnięte trafienia, nie zegar animacji.
- Żywe pola korzystają ze snapshotu oraz identyfikatora efektu. Zduplikowany event trwały jest pomijany wyłącznie, gdy odpowiadające mu pole rzeczywiście narysowano. Koniec koncentracji usuwa pole.
- Pętle mają stałe limity drobin/celów; odsiew efektów poza widokiem uwzględnia geometrię, końce wiązki i cele łańcucha. Wyniki pomiaru Chromium są w raporcie QA; nie stanowią pomiaru na fizycznym Androidzie.
- Przeglądarka i Godot nie są identyczne wizualnie. Oba klienty mają specjalizowane motywy źródła księżyca, początkowego kroku drzew, nekrotycznych czarów, gradu i aktywacji kręgów. Część pokrewnych efektów nadal korzysta ze wspólnej rodziny, np. przemiany, osłony i leczenie; nie jest to brak obsługi.
- `arcane_recovery` uruchamia odpoczynek, który kończy się wspólnym eventem `heal`; `escape_grapple` emituje test i zmianę stanu; `action_surge` używa `fighter_surge`. Dostępne gałęzie katalogowe w rendererach nie oznaczają nowych eventów w rozgrywce.
- Pajęczyna nie udaje wypalonych komórek, których nie otrzymuje w snapshotach.

## Pełny katalog po integracji

Tabela przedstawia rzeczywistą drogę produkcyjną. Pełne metadane, bazowe problemy, emitery, fazy, hashe i indywidualny poziom weryfikacji są w `docs/qa_0.8.18/ui21/spell_audit_final.json`; niezmienny stan sprzed poprawek pozostaje w `spell_audit_baseline.json`.

### Zaklęcia podstawowe — 47

| ID / nazwa | Emisja produkcyjna | Web | Godot — przegląd statyczny |
|---|---|---|---|
| `fire_bolt` — Ognisty pocisk | `spell` / cast | Ognisty pocisk z smugą i impaktem | Ognisty pocisk z smugą i impaktem |
| `ray_of_frost` — Promień mrozu | `spell` / cast | Lodowy promień i kryształy przy celu | Lodowy promień i kryształy przy celu |
| `shocking_grasp` — Porażający uścisk | `spell` / cast | Poszarpane wyładowanie do celu | Poszarpane wyładowanie do celu |
| `acid_splash` — Rozprysk kwasu | `spell` / cast | Rozbryzg kwasu w kole serwera | Koło serwera + impakt i wspólne drobiny w palecie kwasu |
| `shillelagh` — Shillelagh · magiczna laska | `spell` / cast | Laska opleciona roślinnymi detalami | Laska opleciona roślinnymi detalami |
| `produce_flame` — Wytworzenie płomienia | `spell` / cast | Ognisty pocisk z smugą i impaktem | Ognisty pocisk z smugą i impaktem |
| `thorn_whip` — Ciernisty bicz | `spell` / cast | Wyginający się cierniowy bicz | Wyginający się cierniowy bicz |
| `starry_wisp` — Gwiaździsty ognik | `spell` / cast | Promienisty pocisk z gwiazdą i śladem | Promienisty pocisk z gwiazdą i śladem |
| `magic_missile` — Magiczny pocisk | `spell` / cast | Łukowe pociski; liczba pochodzi z event.shots | Łukowe pociski; liczba pochodzi z event.shots |
| `burning_hands` — Płonące dłonie | `spell` / cast | Ognisty wachlarz w stożku serwera | Płomienie wewnątrz stożka serwera |
| `shield` — Tarcza | `spell` / cast | Kontur tarczy/pancerza przy odbiorcy | Kontur tarczy/pancerza przy odbiorcy |
| `mage_armor` — Zbroja maga | `spell` / cast | Kontur tarczy/pancerza przy odbiorcy | Kontur tarczy/pancerza przy odbiorcy |
| `cure_wounds` — Leczenie ran | `spell` / cast | Wstęgi leczenia i unoszące się detale przy odbiorcy | Wstęgi leczenia i unoszące się detale przy odbiorcy |
| `healing_word` — Uzdrawiające słowo | `spell` / cast | Wstęgi leczenia i unoszące się detale przy odbiorcy | Wstęgi leczenia i unoszące się detale przy odbiorcy |
| `entangle` — Oplątanie | `spell` / cast | Rośliny/ciernie w dokładnym obszarze serwera | Rośliny/ciernie w dokładnym obszarze serwera |
| `hunters_mark` — Znak łowcy | `spell` / cast | Celownik przy celu + nakładka aktywnego statusu | Celownik przy celu + nakładka aktywnego statusu |
| `longstrider` — Długonogi | `spell` / cast | Smugi przy stopach | Smugi przy stopach |
| `scorching_ray` — Palący promień | `spell` / cast | Warstwowe ogniste promienie; liczba z event.shots | Warstwowe ogniste promienie; liczba z event.shots |
| `misty_step` — Mglisty krok | `spell` / cast | Zanik i pojawienie w obu końcach teleportacji | Zanik i pojawienie w obu końcach teleportacji |
| `moonbeam` — Promień księżyca | `spell persistent + spell tick when damage resolves` / field, tick | Pionowy księżycowy słup; osobny błysk rzeczywistego trafienia | Pionowy księżycowy słup; osobny błysk rzeczywistego trafienia |
| `barkskin` — Dębowa skóra | `spell` / cast | Płytki kory/kamienia wokół postaci | Płytki kory/kamienia wokół postaci |
| `spike_growth` — Kolczasty wzrost | `spell persistent + spell tick when damage resolves` / field, tick | Rośliny/ciernie w dokładnym obszarze serwera | Rośliny/ciernie w dokładnym obszarze serwera |
| `fireball` — Kula ognia | `spell` / cast | Ognista eksplozja w kole serwera | Impakt i płomienie w kole serwera |
| `lightning_bolt` — Błyskawica | `spell` / cast | Poszarpana błyskawica wewnątrz pasa serwera | Poszarpana błyskawica wewnątrz pasa serwera |
| `call_lightning` — Wezwanie błyskawicy | `spell` / cast, recast | Pojedyncza błyskawica z góry na rzeczywisty cast/recast | Pojedyncza błyskawica z góry na rzeczywisty cast/recast |
| `protection_from_energy` — Ochrona przed energią | `spell` / cast | Obrotowe znaki ochronne i tarcza | Obrotowe sześciokąty ochronne |
| `plant_growth` — Rozrost roślin | `spell persistent` / field | Rośliny/ciernie w dokładnym obszarze serwera | Rośliny/ciernie w dokładnym obszarze serwera |
| `blight` — Uschnięcie | `spell` / cast | Nekrotyczne więdnięcie przy celu | Nekrotyczne wijące się pędy i więdnięcie przy celu |
| `ice_storm` — Lodowa burza | `spell` / cast | Spadający grad w zimnej palecie; koło serwera | Spadający grad w zimnej palecie; koło serwera |
| `freedom_of_movement` — Swoboda ruchu | `spell` / cast | Ruchome fragmenty/zerwane więzy przy stopach | Ruchome fragmenty/zerwane więzy przy stopach |
| `stoneskin` — Kamienna skóra | `spell` / cast | Płytki kory/kamienia wokół postaci | Płytki kory/kamienia wokół postaci |
| `cone_of_cold` — Stożek zimna | `spell` / cast | Lodowy wachlarz w stożku serwera | Lodowe odłamki wewnątrz stożka serwera |
| `mass_cure_wounds` — Masowe leczenie ran | `spell` / cast | Obszar serwera + osobne wstęgi leczenia odbiorców | Obszar serwera + osobne wstęgi leczenia odbiorców |
| `conjure_volley` — Przywołanie salwy | `spell` / cast | Deszcz strzał w kole serwera | Deszcz strzał w kole serwera |
| `chain_lightning` — Łańcuch błyskawic | `spell` / cast | Wyładowanie do pierwszego celu i gałęzie do kolejnych | Wyładowanie do pierwszego celu i gałęzie do kolejnych |
| `sunbeam` — Promień słońca | `spell` / cast | Warstwowa świetlna wiązka w pasie serwera | Warstwowa świetlna wiązka w pasie serwera |
| `heal` — Uzdrowienie | `spell` / cast | Wstęgi leczenia i unoszące się detale przy odbiorcy | Wstęgi leczenia i unoszące się detale przy odbiorcy |
| `finger_of_death` — Palec śmierci | `spell` / cast | Poszarpany nekrotyczny promień i więdnięcie | Dymiący nekrotyczny promień wysysający |
| `fire_storm` — Burza ognia | `spell` / cast | Płomienie w dokładnych panelach serwera | Płomienie w dokładnych panelach serwera |
| `sunburst` — Rozbłysk słońca | `spell` / cast | Promienisty rozbłysk w kole serwera | Świetlny impakt i drobiny w kole serwera |
| `incendiary_cloud` — Zapalająca chmura | `spell persistent + spell tick when damage resolves` / field, tick | Płomienie i dym w aktywnym obszarze | Płomienie i dym w aktywnym obszarze |
| `meteor_swarm` — Rój meteorów | `spell` / cast | Cztery spadające meteory i impakty w kołach serwera | Cztery spadające meteory i impakty w kołach serwera |
| `foresight` — Przewidywanie | `spell` / cast | Oko/gwiazda przewidywania nad postacią | Oko/gwiazda przewidywania nad postacią |
| `ensnaring_strike` — Uderzenie oplątujące | `spell` / cast | Pnącza po legalnym trafieniu + aktywna nakładka spętania | Pnącza po legalnym trafieniu + aktywna nakładka spętania |
| `alarm` — Alarm | `spell` / cast | Znaki strażnicze; aktywny alarm w snapshot.alarms | Pierścień znaków; aktywny alarm w snapshot.alarms |
| `find_familiar` — Przywołanie chowańca | `spell` / cast | Spiralna przemiana/przywołanie; sylwetka z rzeczywistego stanu | Gwiazdy przemiany/przywołania; sylwetka z rzeczywistego stanu |
| `speak_with_animals` — Rozmowa ze zwierzętami | `spell` / cast | Fale i roślinne detale komunikacji | Fale komunikacji i drobiny |

### Zdolności klasowe — 7

| ID / nazwa | Emisja produkcyjna | Web | Godot — przegląd statyczny |
|---|---|---|---|
| `second_wind` — Drugi oddech | `spell` / cast | Wstęgi leczenia i unoszące się detale przy odbiorcy | Wstęgi leczenia i unoszące się detale przy odbiorcy |
| `animal_companion` — Zew towarzysza | `spell` / cast | Spiralna przemiana/przywołanie; sylwetka z rzeczywistego stanu | Gwiazdy przemiany/przywołania; sylwetka z rzeczywistego stanu |
| `action_surge` — Zryw akcji | `fighter_surge + ordinary attack` | Rzeczywisty fighter_surge + normalny atak | Rzeczywisty fighter_surge + normalny atak |
| `arcane_recovery` — Odzyskanie mocy | `rest_state then heal` | Interfejs odpoczynku; kind=heal dopiero po zakończeniu | Interfejs odpoczynku; kind=heal dopiero po zakończeniu |
| `wild_companion` — Dziki towarzysz | `spell` / cast | Spiralna przemiana/przywołanie; sylwetka z rzeczywistego stanu | Gwiazdy przemiany/przywołania; sylwetka z rzeczywistego stanu |
| `beast_trample` — Tratowanie | `spell` / cast | Fizyczny tupot, pył i kamyki przy trafieniu | Fizyczny tupot, pył i kamyki przy trafieniu |
| `escape_grapple` — Wyrwij się z chwytu | `combat_roll + state change` | combat_roll i zmiana stanu; brak spell_effect jest zamierzony | combat_roll i zmiana stanu; brak spell_effect jest zamierzony |

### Dzikie kształty — 10

| ID / nazwa | Emisja produkcyjna | Web | Godot — przegląd statyczny |
|---|---|---|---|
| `wild_shape_wolf` — Dziki kształt · wilk | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_bear` — Dziki kształt · niedźwiedź brunatny | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_cat` — Dziki kształt · kot | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_black_bear` — Dziki kształt · niedźwiedź czarny | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_polar_bear` — Dziki kształt · niedźwiedź polarny | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_giant_scorpion` — Dziki kształt · olbrzymi skorpion | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_elephant` — Dziki kształt · słoń | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_giant_crocodile` — Dziki kształt · olbrzymi krokodyl | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_mammoth` — Dziki kształt · mamut | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |
| `wild_shape_eagle` — Dziki kształt · orzeł | `spell` / cast | Spiralna przemiana; sylwetka bestii z entity.form | Gwiazdy przemiany; sylwetka bestii z entity.form |

### Zdolności kręgów druida — 12

| ID / nazwa | Emisja produkcyjna | Web | Godot — przegląd statyczny |
|---|---|---|---|
| `circle_lands_aid` — Pomoc ziemi | `spell` / cast | Korzenie w kole serwera | Roślinność w kole serwera |
| `circle_natures_sanctuary` — Sanktuarium natury | `spell` / cast | Roślinność w kwadracie + żywe sanktuarium circle_visual | Roślinność w kwadracie + żywe sanktuarium circle_visual |
| `circle_move_sanctuary` — Przesuń sanktuarium | `spell` / cast | Roślinność w kwadracie + żywe sanktuarium circle_visual | Roślinność w kwadracie + żywe sanktuarium circle_visual |
| `circle_moonlight_step` — Księżycowy krok | `spell` / cast | Zanik i pojawienie w obu końcach teleportacji | Zanik i pojawienie w obu końcach teleportacji |
| `circle_wrath_of_sea` — Gniew morza | `spell` / cast | Krótka morska aura + żywy krąg morza | Wyładowanie do rzeczywistego targets[0], jeśli trafiono; żywy krąg morza |
| `circle_wrath_strike` — Uderzenie fali | `spell` / cast | Fala do rzeczywistego targets[0] | Zimna wiązka i impakt do rzeczywistego targets[0] |
| `circle_oceanic_gift` — Dar oceanu | `spell` / cast | Morska aura ze skrzydłami + żywy krąg morza | Morskie spirale przy aktywacji + żywy krąg morza i skrzydła |
| `circle_oceanic_gift_shared` — Wspólny dar oceanu | `spell` / cast | Morska aura ze skrzydłami + żywy krąg morza | Morskie spirale przy aktywacji + żywy krąg morza i skrzydła |
| `circle_star_archer` — Gwiezdna postać · Łucznik | `spell` / cast | Konstelacja właściwej formy; aktywny stan circle_visual | Konstelacja przy aktywacji; aktywna konstelacja właściwej formy circle_visual |
| `circle_star_chalice` — Gwiezdna postać · Kielich | `spell` / cast | Konstelacja właściwej formy; aktywny stan circle_visual | Konstelacja przy aktywacji; aktywna konstelacja właściwej formy circle_visual |
| `circle_star_dragon` — Gwiezdna postać · Smok | `spell` / cast | Konstelacja właściwej formy; aktywny stan circle_visual | Konstelacja przy aktywacji; aktywna konstelacja właściwej formy circle_visual |
| `circle_star_arrow` — Gwiezdna strzała | `spell` / cast | Promienisty pocisk z gwiazdą i śladem | Promienisty pocisk z gwiazdą i śladem |

### Dodatkowe zaklęcia kręgów — 23

| ID / nazwa | Emisja produkcyjna | Web | Godot — przegląd statyczny |
|---|---|---|---|
| `blur` — Rozmycie | `spell` / cast | Przesunięte kontury postaci | Przesunięte kontury postaci |
| `fog_cloud` — Mglista chmura | `spell persistent + circle_fields snapshot` / field | Niskie kłęby mgły — żywy snapshot circle_fields | Niskie kłęby mgły — żywy snapshot circle_fields |
| `hold_person` — Unieruchomienie osoby | `spell` / cast | Więzy na rzeczywistych odbiorcach event.targets | Więzy na rzeczywistych odbiorcach event.targets |
| `sleet_storm` — Śnieżyca | `spell persistent + circle_fields snapshot` / field | Wiatr i grad — żywy snapshot circle_fields | Wiatr i grad — żywy snapshot circle_fields |
| `wall_of_stone` — Kamienny mur | `spell persistent + circle_fields snapshot` / field | Rzeczywiste żywe segmenty muru, pęknięcia zależne od HP — żywy snapshot circle_fields | Rzeczywiste żywe segmenty muru, pęknięcia zależne od HP — żywy snapshot circle_fields |
| `sleep` — Sen | `spell` / cast | Senne znaki we właściwym kole rzucenia | Senne znaki we właściwym kole rzucenia |
| `tree_stride` — Wędrówka drzew | `spell` / cast, recast | Korzenie przy aktywacji; oba końce dopiero przy phase=recast | Roślinny łuk przy aktywacji; oba końce dopiero przy phase=recast |
| `ray_of_sickness` — Promień choroby | `spell` / cast | Chorobowy pocisk z kroplami | Warstwowy promień w palecie kwasu |
| `web` — Pajęczyna | `spell persistent + circle_fields snapshot` / field, tick przy rzeczywistych obrażeniach | Promienista pajęczyna w kwadracie — żywy snapshot circle_fields | Promienista pajęczyna w kwadracie — żywy snapshot circle_fields |
| `stinking_cloud` — Śmierdząca chmura | `spell persistent + circle_fields snapshot` / field | Zielone kłęby trującej chmury — żywy snapshot circle_fields | Zielone kłęby trującej chmury — żywy snapshot circle_fields |
| `polymorph` — Polimorfia | `spell` / cast | Spiralna przemiana/przywołanie; sylwetka z rzeczywistego stanu | Gwiazdy przemiany/przywołania; sylwetka z rzeczywistego stanu |
| `insect_plague` — Plaga owadów | `spell persistent + circle_fields snapshot` / field, tick | Ruchome owady ze skrzydłami — żywy snapshot circle_fields | Ruchome owady ze skrzydłami — żywy snapshot circle_fields |
| `gust_of_wind` — Podmuch wiatru | `spell persistent + circle_fields snapshot` / field | Pas wiatru zgodny z direction/length — żywy snapshot circle_fields | Pas wiatru zgodny z direction/length — żywy snapshot circle_fields |
| `shatter` — Roztrzaskanie | `spell` / cast | Fale ciśnienia w rzeczywistej figurze serwera | Fale/odłamki w rzeczywistej figurze serwera |
| `thunderwave` — Fala gromu | `spell` / cast | Fale ciśnienia w rzeczywistej figurze serwera | Fale/odłamki w rzeczywistej figurze serwera |
| `water_breathing` — Oddychanie wodą | `spell` / cast | Bąble wokół rzeczywistych odbiorców event.targets | Bąble wokół rzeczywistych odbiorców event.targets |
| `control_water` — Kontrola wody | `spell persistent + circle_fields snapshot` / field, tick przy rzeczywistych obrażeniach | Fale rozróżniające flood/part/redirect/whirlpool — żywy snapshot circle_fields | Fale rozróżniające flood/part/redirect/whirlpool — żywy snapshot circle_fields |
| `conjure_elemental` — Przywołanie żywiołaka | `spell persistent + circle_fields snapshot` / field, tick | Rozróżnione żywioły z damage_type — żywy snapshot circle_fields | Rozróżnione żywioły z damage_type — żywy snapshot circle_fields |
| `hold_monster` — Unieruchomienie potwora | `spell` / cast | Więzy na rzeczywistych odbiorcach event.targets | Więzy na rzeczywistych odbiorcach event.targets |
| `conjure_animals` — Przywołanie zwierząt | `spell persistent + circle_fields snapshot` / field, tick | Duchy wilków — żywy snapshot circle_fields | Duchy wilków — żywy snapshot circle_fields |
| `fount_of_moonlight` — Źródło księżycowego blasku | `spell` / cast | Półksiężyc i gwiazdy przy postaci | Księżycowy słup, półksiężyc i gwiazdy |
| `guidance` — Wskazówki | `spell` / cast | Oko/gwiazda przewidywania nad postacią | Oko/gwiazda przewidywania nad postacią |
| `guiding_bolt` — Wiodący pocisk | `spell` / cast | Promienisty pocisk z gwiazdą i śladem | Promienisty pocisk z gwiazdą i śladem |

