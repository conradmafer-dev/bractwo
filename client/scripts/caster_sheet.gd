extends RefCounted
## Class grants and purchases are distinct; the server owns all eligibility.
var selected_order: String = ""
const ABILITIES: Dictionary = {"strength":"Siła", "dexterity":"Zręczność", "constitution":"Kondycja"}


static func can_recover(p: Dictionary) -> bool:
	return str(p.get("class_id", "")) == "mage" and bool(p.get("alive", false)) and str(p.get("form", "")).is_empty() and p.get("character_sheet", {}).get("caster", {}).get("channel", {}).is_empty() and float(p.get("mana", 0)) < float(p.get("max_mana", 0)) and float(p.get("bonus_remaining", 0)) <= 0 and float(p.get("spell_cooldowns", {}).get("arcane_recovery", 0)) <= 0

func controls(sheet, p: Dictionary) -> void:
	var host: Node = sheet.host
	var c: Dictionary = p.get("character_sheet", {}).get("caster", {})
	var channel: Dictionary = c.get("channel", {})
	if not channel.is_empty():
		sheet.text(str(channel.get("name", "")) + " · %d s" % ceili(float(channel.get("remaining", 0))), true)
		sheet.list.add_child(host._button("Przerwij", func() -> void: host._send({"type":"channel_cancel"})))
	if not c.get("familiar", {}).is_empty():
		sheet.text("Chowaniec · " + ("Pomaga" if c["familiar"].get("mode", "") == "help" else "Podąża"), true)
		var row: HFlowContainer = HFlowContainer.new()
		sheet.list.add_child(row)
		for pair: Array in [["follow","Za mną"],["help","Pomagaj"],["scout","Zwiad"],["dismiss","Odeślij"]]:
			var mode: String = str(pair[0])
			row.add_child(host._button(str(pair[1]), func() -> void: host._send({"type":"familiar_command", "mode":mode})))

func render(sheet, p: Dictionary) -> void:
	var host: Node = sheet.host
	var c: Dictionary = p.get("character_sheet", {}).get("caster", {})
	var training: Dictionary = p.get("character_sheet", {}).get("training", {})
	var alive: bool = bool(p.get("alive", false))
	var busy: bool = float(p.get("combat_remaining", 0)) > 0 or not str(p.get("form", "")).is_empty()
	if str(p.get("class_id", "")) == "knight":
		sheet.fighting_styles(p)
	if str(p.get("class_id", "")) == "druid":
		sheet.text("Ścieżka druida", true)
		var current: String = str(c.get("order", ""))
		var candidate: String = current if selected_order.is_empty() else selected_order
		for choice: Dictionary in c.get("orders", []):
			var key: String = str(choice["id"])
			var b: Button = host._button(("✓ " if current == key else "") + str(choice["name"]), func() -> void:
				selected_order = key
				sheet.signature = ""
				sheet.refresh())
			b.icon = sheet.icon(str(choice.get("icon", "")))
			b.expand_icon = true
			b.add_theme_constant_override("icon_max_width", 32)
			sheet.list.add_child(b)
			sheet.text(str(choice.get("description", "")))
		if not candidate.is_empty() and candidate != current:
			var confirm: Button = host._button("Wybierz tę ścieżkę" if current.is_empty() else "Zmień ścieżkę", func() -> void: host._send({"type":"primal_order", "order":candidate}))
			confirm.disabled = not alive or busy or (not current.is_empty() and (not host._in_town() or host.progression.near_service("master").is_empty()))
			sheet.list.add_child(confirm)
		sheet.text("Jeden bezpłatny wybór. Zmiana u mistrza. Pancerz zdobywasz osobno.")
		if c.get("legacy_medium_grace", false):
			sheet.text("Stary średni pancerz działa do pierwszego wyboru ścieżki.")
	if not c.get("features", []).is_empty():
		sheet.text("Zdolności klasy", true)
		for feature: Dictionary in c.get("features", []):
			sheet.text(str(feature["name"]), true)
			sheet.text(str(feature.get("description", "")))
			if feature.get("id", "") == "arcane_recovery":
				var use: Button = host._button("Odzyskanie mocy", func() -> void: host._send({"type":"cast", "spell_id":"arcane_recovery"}))
				use.disabled = not can_recover(p)
				sheet.list.add_child(use)
	controls(sheet, p)
	if not c.get("forms", []).is_empty():
		sheet.text("Postacie zwierzęce", true)
		for form: Dictionary in c.get("forms", []):
			var key: String = "wild_shape_" + str(form["id"])
			var b: Button = host._button(str(form["name"]) + (" · KP %d · +%d tymcz. HP" % [int(form["ac"]), int(form["temp_hp"])] if form.get("unlocked", false) else " · poziom %d" % int(form["level"])), func() -> void: host._send({"type":"cast", "spell_id":key}))
			b.icon = sheet.icon("assets/spells/" + key + ".svg")
			b.expand_icon = true
			b.add_theme_constant_override("icon_max_width", 32)
			b.disabled = not alive or not form.get("unlocked", false) or (str(p.get("form", "")).is_empty() and float(p.get("spell_cooldowns", {}).get(key, 0)) > 0)
			sheet.list.add_child(b)
	sheet.text("Wyszkolenie", true)
	for grant: Dictionary in training.get("granted", []):
		var label: Label = host._wrap_label("✓ " + str(grant["name"]), 14)
		label.tooltip_text = str(grant.get("description", "Klasa"))
		label.mouse_filter = Control.MOUSE_FILTER_STOP
		sheet.list.add_child(label)
	for feat: Dictionary in training.get("chosen", []):
		sheet.text(str(feat["name"]) + " · +1 " + str(ABILITIES.get(feat.get("ability", ""), "")) + (" · wymagania niespełnione" if not feat.get("active", true) else ""))
	var points: int = int(training.get("points", 0))
	sheet.text("Atuty wyposażenia · wybory: %d" % points, true)
	if points == 0:
		sheet.text("Wybory na poziomach 15, 35, 55 i 75.")
	if training.get("options", []).is_empty():
		sheet.text("Masz już dostępne wyszkolenia. Niewydane wybory pozostają zapisane.")
	for feat: Dictionary in training.get("options", []):
		var key: String = str(feat["id"])
		sheet.text(str(feat["name"]), true)
		sheet.text(str(feat.get("description", "")))
		var abilities: Array = feat.get("abilities", [])
		var picker: OptionButton = OptionButton.new()
		for ability: String in abilities:
			picker.add_item("+1 " + str(ABILITIES.get(ability, ability)))
		sheet.list.add_child(picker)
		var select: Button = host._button("Wybierz atut", func() -> void:
			if picker.selected >= 0 and picker.selected < abilities.size():
				host._send({"type":"training_feat", "feat":key, "ability":abilities[picker.selected]})
			picker.release_focus())
		select.disabled = not alive or busy or points < 1 or abilities.is_empty()
		sheet.list.add_child(select)
