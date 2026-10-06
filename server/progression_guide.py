"""Class-specific guide generated from the same gates and rolls as combat.

This is a guide to permanent unlocks, not a saved level-up receipt. It carries
no character/inventory/loot data and does not alter progression or balance.
"""
from types import SimpleNamespace
try:
    from . import combat_rules as rules, dnd_content as dnd, wizard_spellbook
    from .profession_rules import PROMOTION_LEVEL, PROMOTION_COST
except ImportError:
    import combat_rules as rules, dnd_content as dnd, wizard_spellbook
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
        for level in range(1, 22):
            before,after = profile(max(1,level-1)),profile(level)
            details=[]; titles=[]
            circle=dnd.circle_for(class_id,level)
            if circle and (level==1 or circle!=dnd.circle_for(class_id,level-1)):
                titles.append(ROMAN[circle]+' krąg')
                details.append('Dostęp do '+ROMAN[circle]+' kręgu czarów.')
            unlocked=[(key,s) for key,s in dnd.SPELLS.items()
                      if class_id in s['class_ids'] and dnd.spell_level(s,class_id)==level]
            if unlocked:
                learnable=[(key,s) for key,s in unlocked if class_id=='mage' and wizard_spellbook.is_book_spell(key)]
                granted=[(key,s) for key,s in unlocked if (key,s) not in learnable]
                if not titles:
                    titles.append('Czary do nauki' if learnable and not granted else
                                  'Nowe zdolności' if all(s.get('feature') for _,s in unlocked) else 'Nowe czary')
                if granted:details.append(', '.join(s['name'] for _,s in granted)+'.')
                if learnable:details.append('Możliwe do nauki w księdze: '+', '.join(s['name'] for _,s in learnable)+'.')
            if class_id=='mage' and level<=20:
                limit=wizard_spellbook.prepared_limit(level)
                if level==1:
                    titles.append('Własna księga')
                    details.append('Wybierz 6 czarów I kręgu do własnej księgi i przygotuj 4. Sztuczki nie zajmują miejsca na przygotowane czary. Rytuały zapisane w księdze można rzucać bez przygotowania.')
                else:
                    details.append(f'Dopisz 2 wybrane czary do księgi, maksymalnie {circle}. kręgu. Limit przygotowanych czarów: {limit}.')
                if level==1 or limit>wizard_spellbook.prepared_limit(level-1):
                    details.append('Uzupełnij wolne miejsca przygotowanych czarów w C → Czary. Całą listę można zmienić po długim odpoczynku.')
                if level==5:
                    titles.append('Memorize Spell')
                    details.append('Po ukończeniu krótkiego odpoczynku możesz wymienić jeden przygotowany czar na inny zapisany w księdze. Wybierz wymianę w C → Czary przed odpoczynkiem; nie zwiększa ona limitu przygotowania.')
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
            if level==1:
                details.append('C → Cechy: wybierz cechy za 27 punktów. C → Atuty: wybierz atut pochodzenia. C → Umiejętności: wybierz biegłości klasy i dwie biegłości pochodzenia.')
            if level in rules.gear.feat_levels(after):
                titles.append('Rozwój cech lub atut')
                details.append('Jeden wybór: +2 do cechy albo +1 do dwóch cech (limit 20), lub atut. C → Cechy / Atuty.')
            if level==2 and class_id in ('mage','ranger'):
                details.append('C → Umiejętności: wybierz jedną ekspertyzę w posiadanej biegłości.'+(' Uczony obejmuje umiejętności wiedzy.' if class_id=='mage' else ''))
            if level==9 and class_id=='ranger':
                details.append('C → Umiejętności: wybierz dwie kolejne ekspertyzy.')
            if class_id=='knight' and level==1:
                details.append('Wybierz jeden styl walki w C → Atuty. Mistrzostwa: miecz długi, miecz dwuręczny, młot dwuręczny. Kolczuga i tarcza na start.')
            if class_id=='ranger' and level==2:
                titles.append('Styl walki')
                details.append('C → Atuty: wybierz jeden z 10 stylów walki albo Druidycznego wojownika z dwiema sztuczkami druida używającymi Mądrości. Styl nie zużywa punktu atutu.')
            if class_id=='druid' and level==7:
                titles.append('Elemental Fury')
                details.append('C → Atuty: wybierz Potent Spellcasting (+Mądrość do obrażeń sztuczek druida) albo Primal Strike (+1k8 zimna, ognia, błyskawic lub grzmotu raz w swojej turze po trafieniu bronią albo atakiem bestii).')
            if class_id=='druid' and level==15:
                titles.append('Improved Elemental Fury')
                details.append('Primal Strike rośnie do 2k8. Potent Spellcasting wydłuża o 300 stóp zasięg sztuczek druida o zasięgu co najmniej 10 stóp; zasięg Własny i Dotyk nie rośnie.')
            if level==2:details.append('Rejsy i możliwość odblokowania PvP poza osadami.')
            if level==PROMOTION_LEVEL:
                details.append(f'Możliwość promocji u mistrza: {PROMOTION_COST} złota.')
                if class_id=='druid':details.append('Po promocji możesz wybrać krąg druida w C → Atuty.')
                if class_id=='mage':details.append('Po promocji wybierz szkołę czarodzieja w C → Atuty: Ewokacja, Odpychanie, Wróżbiarstwo lub Iluzja.')
                if class_id=='knight':details.append('Po promocji wybierz w C → Atuty: Mistrz Bitewny (trzy manewry i 4 kości przewagi k8) albo Czempion (krytyk bronią 19–20).')
                if class_id=='ranger':details.append('Po promocji wybierz Huntera i jedną technikę w C → Atuty: Pogromca kolosów, Rozbijacz hord albo Zabójca olbrzymów.')
            if class_id=='knight' and level in (7,10,15,18):
                details.append({7:'Mistrz Bitewny: piąta kość przewagi.',10:'Mistrz Bitewny: kości przewagi k10.',15:'Mistrz Bitewny: szósta kość przewagi. Czempion: krytyk bronią 18–20.',18:'Mistrz Bitewny: kości przewagi k12.'}[level])
            if class_id=='mage' and level in (6,10,14):details.append('Nowa zdolność wybranej szkoły czarodzieja; szczegóły w C → Atuty.')
            if level==9:details.append('Możliwość zakupu błogosławieństwa u mistrza: 500 złota.')
            if level==11:details.append('Po promocji: pierwszy punkt mistrzostwa; kolejne co poziom. Przydzielasz poza walką.')
            if level==21:details.append('Dalszy rozwój Bractwa: kolejne poziomy i mistrzostwa. Biegłość, HP i zdolności D&D osiągają limit na poziomie 20.')
            if details:
                entries.append(dict(level=level,name=' / '.join(titles) or 'Wzrost postaci',
                                    description=' '.join(details),spells=[key for key,_ in unlocked]))
        result[class_id]=entries
    return result
