extends RefCounted
## Class choices are server-owned and do not spend an advancement feat point.
var selected_style: String = ""
var selected_cantrips: Array[String] = []
var selected_fury: String = ""

func reset() -> void:
	selected_style = ""
	selected_cantrips.clear()
	selected_fury = ""

func available(p: Dictionary, level: int) -> bool:
	return int(p.get("level", 1)) >= level and bool(p.get("alive", false)) and float(p.get("combat_remaining", 0)) <= 0 and str(p.get("form", "")).is_empty()

func ranger(sheet, p: Dictionary) -> void:
	var host: Node = sheet.host
	var f: Dictionary = p.get("character_sheet", {}).get("fighter", {})
	var current: String = str(f.get("style", ""))
	var candidate: String = current if not current.is_empty() else selected_style
	var can_choose: bool = current.is_empty() and available(p, int(f.get("required_level", 2)))
	sheet.text("Styl walki łowcy · poziom 2", true)
	sheet.text("Jeden bezpłatny wybór stylu albo dwóch sztuczek druida. Nie zużywa punktu atutu. Styl pozostaje na stałe." if current.is_empty() else "Wybrany: " + str(f.get("style_name", current)) + (" · aktywny" if f.get("style_active", false) else " · sprawdź wymagania wyposażenia"))
	for choice: Dictionary in f.get("choices", []):
		var key: String = str(choice["id"])
		if not current.is_empty() and key != current:
			continue
		var b: Button = host._button(("✓ " if candidate == key else "") + str(choice["name"]), func() -> void:
			selected_style = key
			sheet.signature = ""
			sheet.refresh())
		b.disabled = not current.is_empty() or int(p.get("level", 1)) < int(f.get("required_level", 2))
		sheet.list.add_child(b)
		sheet.text(str(choice.get("description", "")))
		if not str(choice.get("requirement", "")).is_empty():
			sheet.text(str(choice["requirement"]))
	if candidate == "druidic_warrior":
		sheet.text("Sztuczki druida · Mądrość · wzrost obrażeń na poziomach 5, 11 i 17", true)
		var chosen: Array = f.get("chosen_cantrips", [])
		for spell: Dictionary in f.get("cantrips", []):
			var key: String = str(spell["id"])
			var picked: bool = chosen.has(key) if not current.is_empty() else selected_cantrips.has(key)
			var b: Button = host._button(("✓ " if picked else "") + str(spell["name"]), func() -> void:
				if selected_cantrips.has(key):
					selected_cantrips.erase(key)
				elif selected_cantrips.size() < 2:
					selected_cantrips.append(key)
				sheet.signature = ""
				sheet.refresh())
			b.disabled = not current.is_empty() or (not picked and selected_cantrips.size() >= 2)
			sheet.list.add_child(b)
			if picked:
				sheet.text(str(spell.get("description", "")))
		if not current.is_empty():
			cantrip_replacement(sheet, p, f)
	if current.is_empty() and not candidate.is_empty():
		var confirm: Button = host._button("Wybierz styl i dwie sztuczki" if candidate == "druidic_warrior" else "Wybierz ten styl", func() -> void:
			host._send({"type":"fighting_style", "style":candidate, "cantrips":selected_cantrips.duplicate() if candidate == "druidic_warrior" else []}))
		confirm.disabled = not can_choose or (candidate == "druidic_warrior" and selected_cantrips.size() != 2)
		sheet.list.add_child(confirm)
	if current.is_empty() and not can_choose:
		sheet.text("Wybór od poziomu 2, po walce i poza przemianą.")
	var reactions: Dictionary = f.get("ranger_style_reactions", {})
	if reactions.get("available", false):
		sheet.text(str(reactions.get("description", "")))
		var enabled: bool = bool(reactions.get("enabled", true))
		var toggle: Button = host._button("Wyłącz automatyczną reakcję" if enabled else "Włącz automatyczną reakcję", func() -> void: host._send({"type":"style_reaction", "enabled":not enabled}))
		toggle.disabled = not bool(p.get("alive", false))
		sheet.list.add_child(toggle)

func cantrip_replacement(sheet, p: Dictionary, f: Dictionary) -> void:
	var host: Node = sheet.host
	sheet.text("Po zdobyciu poziomu łowcy możesz wymienić jedną sztuczkę. Niewykorzystana wymiana nie kumuluje się.")
	if not f.get("cantrip_replacement_available", false):
		return
	var old_picker: OptionButton = OptionButton.new()
	var new_picker: OptionButton = OptionButton.new()
	var chosen: Array = f.get("chosen_cantrips", [])
	var old_ids: Array[String] = []
	var new_ids: Array[String] = []
	for spell: Dictionary in f.get("cantrips", []):
		var key: String = str(spell["id"])
		if chosen.has(key):
			old_ids.append(key)
			old_picker.add_item("Zastąp: " + str(spell["name"]))
		else:
			new_ids.append(key)
			new_picker.add_item("Nowa: " + str(spell["name"]))
	sheet.list.add_child(old_picker)
	sheet.list.add_child(new_picker)
	var replace_button: Button = host._button("Wymień jedną sztuczkę", func() -> void:
		if old_picker.selected >= 0 and new_picker.selected >= 0:
			host._send({"type":"ranger_cantrip", "old_spell":old_ids[old_picker.selected], "new_spell":new_ids[new_picker.selected]})
		old_picker.release_focus()
		new_picker.release_focus())
	replace_button.disabled = not available(p, 2) or old_ids.is_empty() or new_ids.is_empty()
	sheet.list.add_child(replace_button)

func elemental(sheet, p: Dictionary) -> void:
	var host: Node = sheet.host
	var f: Dictionary = p.get("character_sheet", {}).get("caster", {}).get("elemental_fury", {})
	if f.is_empty():
		return
	var current: String = str(f.get("id", f.get("choice", "")))
	var candidate: String = current if not current.is_empty() else selected_fury
	sheet.text("Elemental Fury · poziom 7", true)
	sheet.text("Wybierz Potężne sztuczki albo Pierwotne uderzenie. Ten wybór klasy nie zużywa punktu atutu. Ulepszenie otrzymasz na poziomie 15.")
	for choice: Dictionary in f.get("options", []):
		var key: String = str(choice["id"])
		if not current.is_empty() and key != current:
			continue
		var b: Button = host._button(("✓ " if candidate == key else "") + str(choice["name"]), func() -> void:
			selected_fury = key
			sheet.signature = ""
			sheet.refresh())
		b.disabled = not current.is_empty() or int(p.get("level", 1)) < int(f.get("required_level", 7))
		sheet.list.add_child(b)
		sheet.text(str(choice.get("description", "")))
	if current.is_empty() and not candidate.is_empty():
		var confirm: Button = host._button("Wybierz Elemental Fury", func() -> void: host._send({"type":"elemental_fury", "choice":candidate}))
		confirm.disabled = not available(p, int(f.get("required_level", 7)))
		sheet.list.add_child(confirm)
	if f.get("upgraded", false) and not str(f.get("upgrade_description", "")).is_empty():
		sheet.text("Ulepszenie aktywne: " + str(f["upgrade_description"]), true)
	if current == "primal_strike":
		var enabled: bool = bool(f.get("strike_enabled", true))
		var toggle: Button = host._button("✓ Pierwotne uderzenie: włączone" if enabled else "Pierwotne uderzenie: zachowaj na później", func() -> void: host._send({"type":"elemental_strike", "enabled":not enabled}))
		toggle.disabled = not bool(p.get("alive", false))
		sheet.list.add_child(toggle)
		sheet.text("Typ następnego Pierwotnego uderzenia · zmieniaj przed atakiem", true)
		var row: HFlowContainer = HFlowContainer.new()
		sheet.list.add_child(row)
		for damage: Dictionary in f.get("damage_types", []):
			var key: String = str(damage["id"])
			var b: Button = host._button(("✓ " if f.get("damage_type", "cold") == key else "") + str(damage["name"]), func() -> void: host._send({"type":"elemental_damage_type", "damage_type":key}))
			b.disabled = not bool(p.get("alive", false))
			row.add_child(b)
