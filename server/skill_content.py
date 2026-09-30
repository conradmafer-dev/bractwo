"""Authored skill encounters. Checks use D&D; these places and rewards are Bractwo.

Every encounter is personal and pays once. Traversal encounters then remain
usable as short, local routes. IDs, DCs, rewards and endpoints are server data.
"""

CHALLENGES = (
    dict(id='mill_climb', skill='athletics', ability='strength', dc=10,
         name='Lina na taras młyna', anchor='old_mill', offset=(150, -120), route=(150, 210),
         description='Wespnij się po starej linie na drugi taras młyna. Po zabezpieczeniu liny przejście pozostanie dostępne.',
         success='Mocujesz linę. Możesz odtąd korzystać z tego przejścia w obie strony.', xp=30, gold=0),
    dict(id='camp_ledge', skill='acrobatics', ability='dexterity', dc=15,
         name='Wąska półka przy obozie', anchor='goblin_camp', offset=(-250, 160), route=(-250, -180),
         description='Przejdź wąską półką na tyły obozu. Sukces wyznaczy bezpieczne przejście powrotne.',
         success='Poznajesz pewne oparcia półki. Przejście działa odtąd w obie strony.', xp=45, gold=0),
    dict(id='mill_tangled_pouch', skill='sleight_of_hand', ability='dexterity', dc=10,
         name='Sakwa w trybach młyna', anchor='old_mill', offset=(-95, 55),
         description='Wyplącz porzuconą sakwę z nieruchomych, zardzewiałych trybów, nie rozsypując zawartości.',
         success='Ostrożnie uwalniasz sakwę: znajdujesz oszczędności dawnego młynarza.', xp=25, gold=25),
    dict(id='camp_dispatches', skill='stealth', ability='dexterity', dc=15,
         name='Meldunki przy namiocie', anchor='goblin_camp', offset=(80, 135),
         description='Przekradnij się między namiotami i odzyskaj skradzioną sakwę zwiadowcy. Ciężka, hałaśliwa zbroja utrudnia test.',
         success='Wracasz niepostrzeżenie ze skradzionymi zapasami zwiadowcy.', xp=45, gold=30, potions=1),
    dict(id='dawn_arcane_seal', skill='arcana', ability='intelligence', dc=15,
         name='Pieczęć maga Świtu', anchor='dawn_ruins', offset=(-145, 95),
         description='Rozpoznaj kolejność wygasłych run i otwórz skrytkę dawnego maga.',
         success='Układasz znaki we właściwej kolejności. Skrytka zawiera zapas na wyprawę.', xp=50, gold=30, potions=1),
    dict(id='dawn_chronicle', skill='history', ability='intelligence', dc=10,
         name='Mozaika dawnych władców', anchor='dawn_ruins', offset=(85, -110),
         description='Ustal kolejność władców na mozaice, by odsunąć ukrytą płytę skarbca.',
         success='Odczytujesz chronologię dynastii. Pod płytą zachowała się sakiewka monet.', xp=35, gold=35),
    dict(id='mill_false_bottom', skill='investigation', ability='intelligence', dc=10,
         name='Ślady pod podłogą młyna', anchor='old_mill', offset=(65, 60),
         description='Porównaj ślady kurzu i gwoździ. Wskaż deskę, pod którą ukryto zapasy.',
         success='Ślady prowadzą do luźnej deski. Odkrywasz nienaruszone zapasy.', xp=30, gold=15, potions=1),
    dict(id='grove_herbs', skill='nature', ability='intelligence', dc=10,
         name='Zioła nad leśnym strumieniem', anchor='land_6_0', offset=(100, 80), min_level=10,
         description='Oddziel zioła lecznicze od podobnych trujących roślin. Zielarka pozostawiła tu fiolki i przepis.',
         success='Rozpoznajesz właściwe rośliny i przygotowujesz dwie małe mikstury zdrowia.', xp=50, gold=0, potions=2),
    dict(id='shrine_rite', skill='religion', ability='intelligence', dc=10,
         name='Inskrypcja Kapliczki Świetlików', anchor='marsh_shrine', offset=(-65, -100),
         description='Odczytaj dawny obrządek pielgrzymów, by odnaleźć schowek z ich zapasami.',
         success='Modlitwa wskazuje schowek pielgrzymów. Odnajdujesz pozostawione mikstury.', xp=35, gold=0, potions=2),
    dict(id='birch_pack_animal', skill='animal_handling', ability='wisdom', dc=10,
         name='Spłoszony juczny kuc', anchor='merchant_brzezina', offset=(0, 120), min_level=10,
         description='Uspokój przestraszonego kuca i popraw zerwaną uprząż. To oswojone zwierzę potrzebuje cierpliwego opiekuna.',
         success='Kuc uspokaja się. Wdzięczny karawaniarz przekazuje zapasy i zapłatę.', xp=45, gold=25, potions=1),
    dict(id='scout_story', skill='insight', ability='wisdom', dc=10,
         name='Przemilczana zasadzka', anchor='zwiadowca', offset=(70, 60),
         description='Porozmawiaj z Borysem: jego wahanie zdradza, że ukrywa szczegół ostatniej wyprawy.',
         success='Borys przyznaje się do utraty zwiadowczych zapasów i powierza ci rezerwę na bezpieczny powrót.', xp=25, gold=0, potions=1),
    dict(id='scout_first_aid', skill='medicine', ability='wisdom', dc=10,
         name='Ranny kurier przy strażnicy', anchor='strazniczka', offset=(170, -45),
         description='Rozpoznaj uraz rannego kuriera i załóż opatrunek. Pomoc poszkodowanemu nie odnawia twoich punktów zdrowia.',
         success='Tamujesz krwawienie kuriera. Mira wypłaca nagrodę za udzieloną pomoc.', xp=30, gold=25),
    dict(id='bridge_watch', skill='perception', ability='wisdom', dc=10,
         name='Błysk pod kamieniem mostu', anchor='old_bridge', offset=(95, 30),
         description='Wypatrz słaby błysk ukrytej klamry pomiędzy kamieniami przy wschodnim przyczółku.',
         success='Dostrzegasz zamaskowaną sakwę podróżnego i odzyskujesz jej zawartość.', xp=25, gold=20),
    dict(id='grove_tracks', skill='survival', ability='wisdom', dc=10,
         name='Ślady zaginionej karawany', anchor='land_6_0', offset=(-110, 70), min_level=10,
         description='Odróżnij ślady wozu od tropów zwierząt i odnajdź zgubioną skrzynię karawany.',
         success='Trop kończy się pod korzeniami brzozy. Odnajdujesz zgubione zapasy i drobne monety.', xp=55, gold=30, potions=1),
    dict(id='captain_bluff', skill='deception', ability='charisma', dc=15,
         name='Próba blefu przewoźnika', anchor='captain_brzezina', offset=(-100, -15), min_level=10,
         description='Kapitan ćwiczy rozpoznawanie przemytników. Zagraj rolę kupca i przekonująco ukryj sprzeczność w zmyślonej historii.',
         success='Kapitan daje się nabrać podczas umówionej próby i wypłaca obiecaną stawkę.', xp=45, gold=40),
    dict(id='guard_extortionist', skill='intimidation', ability='charisma', dc=15,
         name='Awanturnik przy strażnicy', anchor='strazniczka', offset=(-90, -95),
         description='Stanowczym ostrzeżeniem nakłoń awanturnika do zwrotu wymuszonych pieniędzy. Straż nagradza pokojowe rozwiązanie.',
         success='Awanturnik oddaje pieniądze mieszkańcom. Straż wypłaca ci nagrodę.', xp=35, gold=30),
    dict(id='birch_performance', skill='performance', ability='charisma', dc=10,
         name='Występ na placu Brzeziny', anchor='city_brzezina', offset=(0, 90), min_level=10,
         description='Zaprezentuj pieśń, taniec lub opowieść podróżnym czekającym na karawanę. Organizator płaci za jeden udany występ.',
         success='Podróżni nagradzają występ oklaskami. Otrzymujesz umówione honorarium.', xp=40, gold=35),
    dict(id='cartographer_supplies', skill='persuasion', ability='charisma', dc=10,
         name='Zapasy dla wyprawy Orena', anchor='kartograf', offset=(-80, 95),
         description='Przedstaw kartografowi rzeczowy plan pierwszej wyprawy i przekonaj go do wsparcia zapasami.',
         success='Oren przyznaje zapasy na jedną wyprawę. Otrzymujesz dwie małe mikstury zdrowia.', xp=25, gold=0, potions=2),
)

IDS = frozenset(row['id'] for row in CHALLENGES)
FAILURE_COOLDOWN = 90
NEARBY_DISTANCE = 1200
INTERACTION_RADIUS = 125


def reward_hint(row):
    parts = []
    if row.get('route'):parts.append('stałe przejście w obie strony')
    if row.get('xp'):parts.append(f"{row['xp']} PD")
    if row.get('gold'):parts.append(f"{row['gold']} złota")
    if row.get('potions'):parts.append(f"mała mikstura zdrowia ×{row['potions']}")
    return ', '.join(parts)+'; nagroda jednorazowa'
