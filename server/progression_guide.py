"""Class-specific guide generated from the same gates and rolls as combat.

This is a guide to permanent unlocks, not a saved level-up receipt. It carries
no character/inventory/loot data and does not alter progression or balance.
"""
from types import SimpleNamespace
try:
    from . import combat_rules as rules, dnd_content as dnd
except ImportError:
    import combat_rules as rules, dnd_content as dnd

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
            if level==20:details.append('Możliwość promocji u mistrza: 2000 złota.')
            if level==40:details.append('Możliwość zakupu błogosławieństwa u mistrza: 500 złota.')
            if level==50:details.append('Po promocji: pierwszy punkt mistrzostwa; kolejne co 5 poziomów. Przydzielasz poza walką.')
            if details:
                entries.append(dict(level=level,name=' / '.join(titles) or 'Wzrost postaci',
                                    description=' '.join(details),spells=[key for key,_ in unlocked]))
        result[class_id]=entries
    return result
