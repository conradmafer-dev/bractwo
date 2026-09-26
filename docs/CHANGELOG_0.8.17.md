# 0.8.17 — celowanie różdżką i kolejka czarów

Baza: 0.8.16. Bez zmian kości, many, odnowień, odblokowań i schematu zapisu.

- Autoatak pomija fokusy czarodzieja; ręczna Iskra i trzymana Spacja pozostają.
- Zwykłe bronie / formy zachowują automatyczny atak wybranego przeciwnika.
- Powtórne zaznaczenie tego samego celu nie czyści pending_spell.
- Przyjęty czar nie przegrywa wyścigu o gotową akcję z przychodzącą komendą attack.
- Udany natychmiastowy czar główny zastępuje stary pending_spell; bonus i reakcja
  pozostawiają go nietkniętego.
- Cel z bieżącego zaznaczenia jest utrwalany już przy zakolejkowaniu.
- Przeterminowane komendy są usuwane także przy długim blokowaniu akcji.
- WWW i źródła Godota pokazują potwierdzenie oczekiwania na paskach, F i w księdze.
- Nowe 30 testów serwera i 7 testów JavaScript; istniejące testy kolejkowania
  zaczynają się teraz jawnym strzałem, zamiast zakładać automatyczną Iskrę.
