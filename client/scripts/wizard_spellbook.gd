extends RefCounted
## Drafts remain local until the server accepts learning or completes a rest.
var mode: String = "prepare"
var signature: String = ""
var draft: Array = []
var learn_key: String = ""
var forget_key: String = ""
var memorize_key: String = ""

static func metadata(p: Dictionary) -> Dictionary:
	return p.get("character_sheet", {}).get("caster", {}).get("spellbook", {})

static func managed(p: Dictionary, spec: Dictionary) -> bool:
	return str(p.get("class_id", "")) == "mage" and bool(metadata(p).get("enabled", false)) and int(spec.get("circle", 0)) > 0 and not bool(spec.get("feature", false))

static func known(p: Dictionary, key: String, spec: Dictionary) -> bool:
	return not managed(p, spec) or metadata(p).get("known", []).has(key)

static func prepared(p: Dictionary, key: String, spec: Dictionary) -> bool:
	return not managed(p, spec) or metadata(p).get("prepared", []).has(key)

func invalidate(sheet) -> void:
	sheet.signature = ""
	sheet.refresh()

func name_of(host: Node, key: String) -> String:
	var spec: Dictionary = host._spell_profile(key)
	return "%s · krąg %d" % [str(spec.get("name", key)), int(spec.get("circle", 1))]

func picker(sheet, keys: Array, current: String, callback: Callable) -> OptionButton:
	var choice: OptionButton = OptionButton.new()
	choice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	choice.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	for key: String in keys:
		choice.add_item(name_of(sheet.host, key))
	choice.select(keys.find(current))
	choice.disabled = keys.is_empty()
	choice.item_selected.connect(func(index: int) -> void:
		if index >= 0 and index < keys.size():
			callback.call(str(keys[index]))
		choice.release_focus()
		invalidate(sheet))
	sheet.list.add_child(choice)
	return choice

func rest_reason(p: Dictionary, kind: String, rules: Dictionary) -> String:
	if not p.get("rest", {}).is_empty():
		return "Trwa odpoczynek. Przygotowania zmienią się dopiero po jego ukończeniu."
	if not p.get("alive", false):
		return "Odpoczynek jest dostępny dla żywej postaci."
	var reasons: Dictionary = {"moving":"Zatrzymaj się, aby odpocząć.", "combat_pve":"Odczekaj po walce z potworami.", "combat_pvp":"Trwa blokada walki z graczem.", "channel":"Najpierw zakończ trwającą czynność.", "disconnected":"Połącz się ponownie.", "dead":"Postać musi być żywa."}
	var reason: String = str(p.get("rest_block_reason", ""))
	if not reason.is_empty():
		return str(reasons.get(reason, "Odpoczynek jest teraz niedostępny."))
	var wait: int = ceili(float(p.get("rest_" + kind + "_remaining", 0)))
	if wait > 0:
		return "Odpoczynek dostępny za %d s." % wait
	if kind == "long" and rules.get("long_safe_only", false) and not p.get("rest_safe", false):
		return "Długi odpoczynek wymaga bezpiecznego miejsca."
	return ""

func render(sheet, p: Dictionary) -> void:
	var host: Node = sheet.host
	var book: Dictionary = metadata(p)
	if not book.get("enabled", false):
		sheet.text("Własna księga jest dostępna dla czarodzieja.")
		return
	var keys: Array = book.get("known", [])
	var active: Array = book.get("prepared", [])
	var choices: Array = book.get("learning_choices", [])
	var state_key: String = JSON.stringify([p.get("id", ""), keys, active, choices, book.get("free_preparations", 0)])
	if state_key != signature:
		signature = state_key
		draft = active.duplicate()
		if not choices.has(learn_key):
			learn_key = str(choices[0]) if not choices.is_empty() else ""
		if not active.has(forget_key):
			forget_key = str(active[0]) if not active.is_empty() else ""
	var available: Array = []
	for key: String in keys:
		if not active.has(key):
			available.append(key)
	if not available.has(memorize_key):
		memorize_key = str(available[0]) if not available.is_empty() else ""
	var limit: int = int(book.get("prepared_limit", 0))
	var free: int = int(book.get("free_preparations", 0))
	var idle: bool = p.get("alive", false) and float(p.get("combat_remaining", 0)) <= 0 and p.get("rest", {}).is_empty() and p.get("character_sheet", {}).get("caster", {}).get("channel", {}).is_empty()
	sheet.text("Własna księga · %d czarów · przygotowane %d/%d" % [keys.size(), active.size(), limit], true)
	sheet.text("Sztuczki i zdolności szkoły nie zajmują miejsc. Rytuał zapisany w księdze możesz odprawić bez przygotowania.")
	if book.get("legacy_migrated", false):
		sheet.text("Twoje dotychczas odblokowane czary pozostały w księdze. Pozostałe przygotujesz podczas długiego odpoczynku.")
	var nav: HFlowContainer = HFlowContainer.new()
	sheet.list.add_child(nav)
	var modes: Dictionary = {"prepare":"Przygotowania", "learn":"Nauka · %d wyborów" % int(book.get("learning_credits", 0))}
	if book.get("memorize_available", false):
		modes["memorize"] = "Memorize Spell"
	for value: String in modes:
		var tab_button: Button = host._button(str(modes[value]), func() -> void:
			mode = value
			invalidate(sheet))
		tab_button.toggle_mode = true
		tab_button.set_pressed_no_signal(mode == value)
		nav.add_child(tab_button)
	var rest: Dictionary = p.get("rest", {})
	if not rest.is_empty():
		sheet.text("Odpoczynek · pozostało %d s. Ruch przerywa odpoczynek i odrzuca wybraną zmianę." % ceili(float(rest.get("remaining", 0))))
		sheet.list.add_child(host._button("Przerwij odpoczynek", func() -> void: host._send({"type":"rest_cancel"})))
	if mode == "learn":
		sheet.text("Nauka czarów", true)
		sheet.text("Zacznij od sześciu czarów 1. kręgu. Każdy kolejny poziom daje dwa wybory czarów z dostępnych kręgów. Wybór zapisuje czar trwale w twojej księdze.")
		var schools: Dictionary = {"evocation":"wywoływanie", "abjuration":"odpychanie", "divination":"wieszczenie", "illusion":"iluzja"}
		var grants: Dictionary = {}
		for grant: Dictionary in book.get("learning_grants", []):
			var school: String = str(grant.get("school", ""))
			var label: String = "do %d. kręgu" % int(grant.get("max_circle", 1)) + (" · " + str(schools.get(school, school)) if not school.is_empty() else "")
			grants[label] = int(grants.get(label, 0)) + int(grant.get("remaining", 0))
		for label: String in grants:
			sheet.text("Pozostałe wybory: %d · %s" % [int(grants[label]), label])
		sheet.text("Niewydane wybory zachowują krąg z poziomu, na którym je otrzymałeś. Wybory szkoły dotyczą tylko jej czarów.")
		if book.get("catalog_limited", false):
			sheet.text("W obecnym katalogu brakuje kolejnych czarów do nauki; niewydane wybory pozostają zapisane.")
		picker(sheet, choices, learn_key, func(key: String) -> void: learn_key = key)
		if not learn_key.is_empty():
			sheet.text(str(host._spell_profile(learn_key).get("description", "")))
		var learn: Button = host._button("Dopisz wybrany czar do księgi", func() -> void: host._send({"type":"wizard_learn", "spell":learn_key}))
		learn.disabled = not idle or learn_key.is_empty() or not choices.has(learn_key) or int(book.get("learning_credits", 0)) <= 0
		sheet.list.add_child(learn)
	elif mode == "memorize" and book.get("memorize_available", false):
		sheet.text("Memorize Spell · poziom 5", true)
		sheet.text("Po ukończeniu krótkiego odpoczynku zastąpisz jeden przygotowany czar innym z własnej księgi. Liczba przygotowanych czarów nie wzrasta.")
		sheet.text("Przestań przygotowywać:")
		picker(sheet, active, forget_key, func(key: String) -> void: forget_key = key)
		sheet.text("Przygotuj zamiast niego:")
		picker(sheet, available, memorize_key, func(key: String) -> void: memorize_key = key)
		var rules: Dictionary = host.world_data.get("rest_rules", {})
		var reason: String = rest_reason(p, "short", rules)
		var memorize: Button = host._button("Krótki odpoczynek i zamiana · %d s" % int(rules.get("short_seconds", 10)), func() -> void:
			host.attack_held = false
			host._send({"type":"rest", "kind":"short", "recover":true, "wizard_preparation":{"memorize":{"forget":forget_key, "prepare":memorize_key}}}))
		memorize.disabled = not reason.is_empty() or forget_key.is_empty() or memorize_key.is_empty()
		sheet.list.add_child(memorize)
		if not reason.is_empty():
			sheet.text(reason)
		if available.is_empty():
			sheet.text("Do zamiany potrzebujesz nieprzygotowanego czaru w księdze.")
	else:
		sheet.text("Wybór przygotowanych · %d/%d" % [draft.size(), limit], true)
		sheet.text("Zaznacz czary na kolejną wyprawę. Pełna zmiana zostanie zapisana po ukończeniu długiego odpoczynku. Przerwanie odpoczynku zachowuje dotychczasowy zestaw.")
		for key: String in keys:
			var choose: CheckButton = CheckButton.new()
			choose.text = name_of(host, key) + (" · przygotowany" if active.has(key) else "")
			choose.tooltip_text = str(host._spell_profile(key).get("description", ""))
			choose.set_pressed_no_signal(draft.has(key))
			choose.disabled = not rest.is_empty() or (not draft.has(key) and draft.size() >= limit)
			choose.toggled.connect(func(checked: bool) -> void:
				if checked and not draft.has(key):
					draft.append(key)
				elif not checked:
					draft.erase(key)
				invalidate(sheet))
			sheet.list.add_child(choose)
		var only_additions: bool = true
		for key: String in active:
			if not draft.has(key):
				only_additions = false
		var added: int = draft.size() - active.size()
		if free > 0:
			sheet.text("Nowe miejsca do uzupełnienia bez odpoczynku: %d. Ten wybór pozwala tylko dodać czary." % free)
			var fill: Button = host._button("Uzupełnij nowe przygotowania", func() -> void: host._send({"type":"wizard_prepare", "spells":draft.duplicate()}))
			fill.disabled = not idle or not only_additions or added <= 0 or added > free or draft.size() > limit
			sheet.list.add_child(fill)
		var rules: Dictionary = host.world_data.get("rest_rules", {})
		var reason: String = rest_reason(p, "long", rules)
		var prepare: Button = host._button("Długi odpoczynek i przygotowanie · %d s" % int(rules.get("long_seconds", 30)), func() -> void:
			host.attack_held = false
			host._send({"type":"rest", "kind":"long", "recover":true, "wizard_preparation":{"prepared":draft.duplicate()}}))
		prepare.disabled = not reason.is_empty() or draft.size() > limit or keys.is_empty()
		sheet.list.add_child(prepare)
		if not reason.is_empty():
			sheet.text(reason)
		if keys.is_empty():
			sheet.text("Najpierw otwórz zakładkę Nauka i wybierz czary do księgi.")
