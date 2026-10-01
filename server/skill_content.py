"""Eight authored world scenes, replacing the eighteen UI_28 dice markers.

Options use existing skill checks. Outcomes/rewards are personal and permanent.
Legacy receipt IDs remain recognised, so grouped scenes cannot pay twice.
"""

def check(id_, label, skill, ability, dc=10):
    return dict(id=id_, label=label, kind='check', skill=skill, ability=ability, dc=dc)


CHALLENGES = (
    dict(id='scout_first_aid', name='Ranny strażnik', scene='wounded_guard',
         anchor='old_bridge', offset=(-310, -365), min_level=1,
         description='Pod wierzbą nad rzeką siedzi strażnik z ranną nogą. Obok leżą tarcza i złamana włócznia.',
         dialogue='„Wilki dopadły mnie na patrolu… Nie zdołam wrócić z taką nogą. Pomożesz?”',
         options=(check('bandage','Opatrz ranę','medicine','wisdom'),
                  dict(id='potion',label='Podaj małą miksturę zdrowia',kind='potion',item='health_potion',quantity=1),
                  dict(id='heal',label='Rzuć Leczenie ran',kind='spell',spell='cure_wounds')),
         success='Strażnik podnosi się i dziękuje za pomoc. Otrzymujesz zapłatę za uratowanie patrolu.',
         aftermath='„Noga już nie boli. Dziękuję — będę miał na ciebie oko, wędrowcze.”',
         failure='Opatrunek się zsuwa. Strażnik prosi, abyś chwilę zaczekał albo podał mu lekarstwo.',
         xp=30,gold=25, hint_dc=12,hint='Pod osłoną tarczy widzisz głębokie rozcięcie nogi. Strażnik potrzebuje opatrunku lub leczenia.'),
    dict(id='mill_tangled_pouch', name='Zablokowany wóz młynarza', scene='broken_cart',
         anchor='old_mill', offset=(170, 140), min_level=1,
         legacy_ids=('mill_climb','mill_false_bottom'),
         description='Wóz z workami mąki utknął przy młynie. Pod koło wsunęła się belka, a woźnica bezradnie szarpie za dyszel.',
         dialogue='„Sam go nie ruszę. Podważysz koło albo wyciągniesz to drewno spod osi?”',
         options=(check('lift','Podważ wóz','athletics','strength'),
                  check('free','Uwolnij zaklinowaną belkę','sleight_of_hand','dexterity'),
                  check('inspect','Znajdź przyczynę zacięcia','investigation','intelligence')),
         success='Koło rusza, a młynarz stawia wóz na trakcie. Wdzięczny dzieli się zapasami.',
         aftermath='„Wóz znów jest sprawny. Dzięki tobie mąka dotrze do osady.”',
         failure='Belka nadal klinuje koło. Odsapnij przed następną próbą.',
         xp=35,gold=25,potions=1,hint_dc=12,hint='Spod koła wystaje koniec belki — to ona blokuje wóz, nie pęknięta oś.'),
    dict(id='guard_extortionist',name='Podejrzany poborca',scene='road_dispute',
         anchor='strazniczka',offset=(-150,-410),min_level=1,
         legacy_ids=('scout_story','cartographer_supplies'),
         description='Na północnym trakcie obcy zatrzymał podróżną. Żąda opłaty za przejście, pokazując zniszczoną pieczęć.',
         dialogue='„Myto dla straży! Płaci każdy, kto tędy przechodzi.” Podróżna spogląda na ciebie, ściskając pustą sakwę.',
         options=(check('warn','Każ mu oddać pieniądze','intimidation','charisma',12),
                  check('question','Wypytaj o jego rozkazy','insight','wisdom'),
                  check('persuade','Przekonaj go, żeby odszedł','persuasion','charisma',12)),
         success='Fałszywy poborca zwraca pieniądze i odchodzi. Podróżna wynagradza ci pomoc.',
         aftermath='„Dobrze, że się zjawiłeś. Już mogę spokojnie ruszyć do Przystani.”',
         failure='Obcy nie ustępuje. Przemyśl, jak go przekonać, zanim spróbujesz ponownie.',
         xp=35,gold=30,hint_dc=13,hint='Na pieczęci brakuje znaku Przystani. Mężczyzna nie jest strażnikiem.'),
    dict(id='bridge_watch',name='Sakwa przy przeprawie',scene='lost_pouch',
         anchor='old_bridge',offset=(130,155),min_level=1,
         description='Między kamieniami przy wschodnim brzegu leży zerwany pas. Coś pobłyskuje w trawie.',
         dialogue='Mokre ślady urywają się przy głazie. W splątanych korzeniach mogło coś zostać.',
         options=(check('spot','Przyjrzyj się trawie','perception','wisdom'),
                  check('search','Przeszukaj kamienie','investigation','intelligence')),
         success='Wyciągasz z korzeni zagubioną sakwę. W środku zachowały się monety.',
         aftermath='Pozostały tylko ślady w mokrej trawie. Sakwa została już zabrana.',
         failure='Nie znajdujesz sakwy. Daj wodzie opaść i przyjrzyj się temu miejscu ponownie.',
         xp=25,gold=20,hint_dc=12,hint='W korzeniach miga mosiężna klamra. Tam leży zagubiona sakwa.'),
    dict(id='camp_dispatches',name='Skradzione zapasy',scene='stolen_supplies',
         anchor='goblin_camp',offset=(-210,180),min_level=1,
         legacy_ids=('camp_ledge','captain_bluff'),
         description='Na skraju obozu stoją skrzynie ze znakiem Przystani. Mały goblin drzemie obok płachty i porzuconej miski.',
         dialogue='To zapasy skradzione zwiadowcom. Strażnik co chwila przymyka oczy, ale skrzynie stoją blisko jego posłania.',
         options=(check('sneak','Podkradnij się do skrzyni','stealth','dexterity',12),
                  check('bluff','Podszyj się pod posłańca','deception','charisma',12),
                  check('balance','Przejdź po zwalonym pniu','acrobatics','dexterity',12)),
         success='Wynosisz ocalałe zapasy. Goblin zostaje przy pustych skrzyniach.',
         aftermath='Skrzynie są już puste. Ocalałe zapasy zabrałeś z obozu.',
         failure='Goblin podnosi głowę. Wycofujesz się, zanim zdąży podnieść alarm.',
         xp=45,gold=30,potions=1,hint_dc=13,hint='Sznur przy skrzyniach porusza miską obok wartownika. Tędy łatwo go obudzić.'),
    dict(id='dawn_arcane_seal',name='Zapomniany relikwiarz',scene='sealed_relic',
         anchor='dawn_ruins',offset=(-170,130),min_level=1,
         legacy_ids=('dawn_chronicle','shrine_rite'),
         description='Wśród pękniętych kolumn ocalał kamienny relikwiarz. Na pokrywie wyryto runy, korony i symbol świtu.',
         dialogue='Trzy kamienne znaki otaczają szczelinę w pokrywie. Właściwa kolejność powinna zwolnić stary mechanizm.',
         options=(check('runes','Odczytaj runy','arcana','intelligence',12),
                  check('history','Rozpoznaj królewskie znaki','history','intelligence',12),
                  check('rite','Odtwórz dawny obrządek','religion','intelligence',12)),
         success='Kamienna pokrywa odsuwa się. Zabierasz zachowane monety i miksturę.',
         aftermath='Relikwiarz jest otwarty. Wewnątrz pozostał tylko pył.',
         failure='Znaki gasną, a pokrywa pozostaje zamknięta. Poczekaj przed następną próbą.',
         xp=50,gold=35,potions=1,hint_dc=14,hint='Na najstarszej koronie ślady dotyku są wyraźniejsze niż na pozostałych znakach.'),
    dict(id='grove_herbs',name='Zielarka z doliny',scene='herbalist',
         anchor='land_6_0',offset=(120,100),min_level=10,
         legacy_ids=('grove_tracks',),
         description='Zielarka siedzi przy koszyku fiolek. Część ziół rozwiała się po ściółce, między podobnymi, trującymi roślinami.',
         dialogue='„Potrzebuję liści o jasnych żyłkach. Pomożesz je rozpoznać albo odszukać moją zgubioną wiązkę?”',
         options=(check('identify','Rozpoznaj lecznicze zioła','nature','intelligence'),
                  check('track','Odszukaj rozwianą wiązkę','survival','wisdom')),
         success='Zielarka kończy przygotowywanie lekarstw i oddaje ci dwie fiolki.',
         aftermath='„Te zioła wystarczą na dziś. Niech lekarstwo dobrze ci służy.”',
         failure='Rośliny są zbyt podobne. Zanim spróbujesz ponownie, uważniej obejrzyj liście.',
         xp=50,gold=0,potions=2,hint_dc=12,hint='Właściwe liście mają jasne żyłki. Trujące rośliny rosną bliżej ciemnego kamienia.'),
    dict(id='birch_pack_animal',name='Spłoszony kuc',scene='frightened_pony',
         anchor='city_brzezina',offset=(335,-310),min_level=10,
         legacy_ids=('birch_performance',),
         description='Na drodze do Brzeziny kuc szarpie uprząż. Karawaniarz nie może zbliżyć się do rozsypanych tobołów.',
         dialogue='„Przestraszył się wilków. Tylko spokojnie — nie ciągnij go za uzdę!”',
         options=(check('calm','Uspokój zwierzę','animal_handling','wisdom'),
                  check('sing','Zanuć spokojną melodię','performance','charisma',12)),
         success='Kuc opuszcza łeb. Właściciel zapina uprząż i przekazuje ci nagrodę.',
         aftermath='„Już spokojny. Możemy dokończyć drogę do Brzeziny.”',
         failure='Kuc nadal się płoszy. Daj mu chwilę spokoju przed kolejnym podejściem.',
         xp=45,gold=25,potions=1,hint_dc=12,hint='Kuc uspokaja się, gdy nikt nie napina uprzęży.'),
)

# Compatibility fields support old clients while the event client uses options.
for _row in CHALLENGES:
    _first=next(o for o in _row['options'] if o['kind']=='check')
    _row.update({k:_first[k] for k in ('skill','ability','dc')})

BY_ID={row['id']:row for row in CHALLENGES}
CANONICAL={old:row['id'] for row in CHALLENGES for old in (row['id'],*row.get('legacy_ids',()))}
IDS=frozenset(CANONICAL)
FAILURE_COOLDOWN=90
NEARBY_DISTANCE=1000
INTERACTION_RADIUS=112
HINT_DISTANCE=230


def reward_hint(row):
    parts=[]
    if row.get('xp'):parts.append(f"{row['xp']} PD")
    if row.get('gold'):parts.append(f"{row['gold']} złota")
    if row.get('potions'):parts.append(f"mała mikstura zdrowia ×{row['potions']}")
    return ' · '.join(parts)
