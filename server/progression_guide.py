"""Class-specific guide generated from the same gates and rolls as combat.

This is a guide to permanent unlocks, not a saved level-up receipt. It carries
no character/inventory/loot data and does not alter progression or balance.
"""
from types import SimpleNamespace
try:
    from . import combat_rules as rules, dnd_content as dnd
    from .profession_rules import PROMOTION_LEVEL, PROMOTION_COST
except ImportError:
    import combat_rules as rules, dnd_content as dnd
    from profession_rules import PROMOTION_LEVEL, PROMOTION_COST

ATTRIBUTE_NAMES = {'strength':'Siła', 'dexterity':'Zręczność', 'constitution':'Kondycja',
    'intelligence':'Inteligencja', 'wisdom':'Mądrość', 'charisma':'Charyzma'}
ROMAN = ('', 'I','II','III','IV','V','VI','VII','VIII','IX')


def catalog():
    result = {}
    for class_id,spec in dnd.CLASS_SPECS.items():
        entries = []
        def profile(level):
            return SimpleNamespace(class_id=class_id, spec=spec, level=level,
                                   form='', mastery={})
        for level in range(1, 101):
            before,after = profile(max(1,level-1)),profile(level)
            details=[]; titles=[]
            circle=dnd.circle_for(class_id,level)
            if circle and (level==1 or circle!=dnd.circle_for(class_id,level-1)):
                titles.append(ROMAN[circle]+' krąg')
                details.append('Dostęp do '+ROMAN[circle]+' kręgu czarów.')
            unlocked=[(key,s) for key,s in dnd.SPELLS.items()
                      if class_id in s['class_ids'] and dnd.spell_level(s,class_id)==level]
            if unlocked:
                if not titles:titles.append('Nowe zdolności' if all(s.get('feature') for _,s in unlocked) else 'Nowe czary')
                details.append(', '.join(s['name'] for _,s in unlocked)+'.')
            attacks=rules.attacks_per_round(after)
            if level>1 and attacks!=rules.attacks_per_round(before):
                titles.append(f'{attacks} ataki' if attacks<5 else f'{attacks} ataków')
                details.append(f'Ataki bronią na rundę +{attacks-rules.attacks_per_round(before)}.')
            if level>1:
                for key,value in rules.attributes(after).items():
                    delta=value-rules.attributes(before)[key]
                    if delta:details.append(f'{ATTRIBUTE_NAMES[key]} +{delta}.')
                prof=rules.proficiency(after)-rules.proficiency(before)
                if prof:details.append(f'Biegłość +{prof}.')
                mana=dnd.max_mana(after)-dnd.max_mana(before)
                if mana:details.append(f'Mana +{mana}.')
                if class_id=='mage':
                    recovery=rules.caster.recovery_amount(after)-rules.caster.recovery_amount(before)
                    if recovery:details.append(f'Odzyskanie mocy +{recovery} many.')
                scalable=[s['name'] for key,s in dnd.SPELLS.items()
                          if dnd.spell_allowed(before,key) and (s.get('scales') or key=='shillelagh')]
                if scalable and rules.cantrip_count(after)>rules.cantrip_count(before):
                    details.append('Wzmocnienie sztuczek: '+', '.join(scalable)+'.')
                if class_id=='knight':
                    delta=rules.effective_level(after)-rules.effective_level(before)
                    if delta:details.append(f'Drugi oddech +{delta} do leczenia.')
            if class_id=='knight' and level==1:
                details.append('Wybierz jeden styl walki w C → Atuty. Mistrzostwa: miecz długi, miecz dwuręczny, młot dwuręczny. Kolczuga i tarcza na start.')
            if level==8:details.append('Rejsy i możliwość odblokowania PvP poza osadami.')
            if level==PROMOTION_LEVEL:
                details.append(f'Możliwość promocji u mistrza: {PROMOTION_COST} złota.')
                if class_id=='druid':details.append('Po promocji możesz wybrać krąg druida w C → Atuty.')
                if class_id=='mage':details.append('Po promocji wybierz szkołę czarodzieja w C → Atuty: Ewokacja, Odpychanie, Wróżbiarstwo lub Iluzja.')
                if class_id=='knight':details.append('Po promocji wybierz w C → Atuty: Mistrz Bitewny (trzy manewry i 4 kości przewagi k8) albo Czempion (krytyk bronią 19–20).')
                if class_id=='ranger':details.append('Po promocji wybierz Huntera i jedną technikę w C → Atuty: Pogromca kolosów, Rozbijacz hord albo Zabójca olbrzymów.')
            if class_id=='knight' and level in (30,45,70,85):
                details.append({30:'Mistrz Bitewny: piąta kość przewagi.',45:'Mistrz Bitewny: kości przewagi k10.',70:'Mistrz Bitewny: szósta kość przewagi. Czempion: krytyk bronią 18–20.',85:'Mistrz Bitewny: kości przewagi k12.'}[level])
            if class_id=='mage' and level in (25,45,65):details.append('Nowa zdolność wybranej szkoły czarodzieja; szczegóły w C → Atuty.')
            if level==40:details.append('Możliwość zakupu błogosławieństwa u mistrza: 500 złota.')
            if level==50:details.append('Po promocji: pierwszy punkt mistrzostwa; kolejne co 5 poziomów. Przydzielasz poza walką.')
            if details:
                entries.append(dict(level=level,name=' / '.join(titles) or 'Wzrost postaci',
                                    description=' '.join(details),spells=[key for key,_ in unlocked]))
        result[class_id]=entries
    return result
