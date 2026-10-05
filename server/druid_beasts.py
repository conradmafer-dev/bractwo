"""Additional Wild Shape stat blocks, SRD 5.2.1 pp. 348, 350, 353, 357, 359.

https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf
The data preserve beast attacks; Wild Shape HP and mental scores stay the druid's.
"""
BEASTS = {
    'polar_bear': dict(name='Niedźwiedź polarny', level=6, ac=12, hp=42,
        attributes=dict(strength=20, dexterity=14, constitution=16), mental_attributes=dict(intelligence=2, wisdom=13, charisma=7),
        attacks=[[1, 8, 5], [1, 8, 5]], attack_types=['slashing', 'slashing'], damage='slashing', attack_bonus=7,
        beast_proficiency=2, speed=40, swim=40, cr='2', size='large', resistances=['cold'], darkvision=60,
        trait='Dwa rozdarcia · pływanie · odporność na zimno', render='polar_bear'),
    'giant_scorpion': dict(name='Olbrzymi skorpion', level=9, ac=15, hp=52,
        attributes=dict(strength=16, dexterity=13, constitution=15), mental_attributes=dict(intelligence=1, wisdom=9, charisma=3),
        attacks=[[1, 6, 3], [1, 6, 3], [1, 8, 3]], attack_types=['bludgeoning', 'bludgeoning', 'piercing'], damage='bludgeoning', attack_bonus=5,
        beast_proficiency=2, speed=40, cr='3', size='large', blindsight=60,
        extra_attacks={2: dict(dice=[2, 10, 0], damage_type='poison')}, grapple_attacks=[0, 1], grapple_dc=13, grapple_slots=2,
        trait='Dwie chwytające szczypce i jadowite żądło', render='scorpion'),
    'elephant': dict(name='Słoń', level=12, ac=12, hp=76,
        attributes=dict(strength=22, dexterity=9, constitution=17), mental_attributes=dict(intelligence=3, wisdom=11, charisma=6),
        attacks=[[2, 8, 6], [2, 8, 6]], attack_types=['piercing', 'piercing'], damage='piercing', attack_bonus=8,
        beast_proficiency=2, speed=40, cr='4', size='huge', charge_prone=True,
        trample=dict(dice=[2, 10, 6], save_dc=16), trait='Dwa ciosy kłami · szarża · tratowanie powalonego celu', render='elephant'),
    'giant_crocodile': dict(name='Olbrzymi krokodyl', level=15, ac=14, hp=85,
        attributes=dict(strength=21, dexterity=9, constitution=17), mental_attributes=dict(intelligence=2, wisdom=10, charisma=7),
        attacks=[[3, 10, 5], [3, 8, 5]], attack_types=['piercing', 'bludgeoning'], damage='piercing', attack_bonus=8,
        beast_proficiency=3, speed=30, swim=50, hold_breath=3600, cr='5', size='huge', reach=10,
        grapple_attacks=[0], grapple_dc=15, grapple_slots=1, grapple_restrains=True, tail_no_grapple=True,
        prone_attacks=[1], trait='Chwyt szczękami · ogon powala inne cele · pływanie', render='crocodile'),
    'mammoth': dict(name='Mamut', level=18, ac=13, hp=126,
        attributes=dict(strength=24, dexterity=9, constitution=21), mental_attributes=dict(intelligence=3, wisdom=11, charisma=6),
        attacks=[[2, 10, 7], [2, 10, 7]], attack_types=['piercing', 'piercing'], damage='piercing', attack_bonus=10,
        beast_proficiency=3, speed=50, cr='6', size='huge', reach=10, saves=dict(strength=10, constitution=8), charge_prone=True,
        trample=dict(dice=[4, 10, 7], save_dc=18), trait='Dwa ciosy kłami · szarża · potężne tratowanie', render='mammoth'),
    'eagle': dict(name='Orzeł', level=8, ac=12, hp=4,
        attributes=dict(strength=6, dexterity=15, constitution=12), mental_attributes=dict(intelligence=2, wisdom=14, charisma=7),
        attacks=[[1, 4, 2]], damage='slashing', attack_bonus=4, beast_proficiency=2, speed=10, fly=60,
        cr='0', size='small', trait='Lot · szpony', render='eagle'),
}
