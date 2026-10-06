extends RefCounted
## A missed class choice returns next login, including existing eligible heroes.
var host: Node
var panel: PanelContainer
var info: Label
var button: Button
var key: String = ""
var dismissed: Dictionary = {}
var updating: bool = false
var destination: String = "feats"

func setup(owner: Node) -> void:
	host = owner
	panel = host._window("Dostępny wybór klasy")
	panel.name = "ClassChoice"
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(290, 138)
	panel.custom_minimum_size = Vector2(280, 150)
	panel.size = Vector2(280, 150)
	var box: VBoxContainer = panel.get_child(0)
	info = host._wrap_label("", 14)
	box.add_child(info)
	button = host._button("Wybierz w karcie postaci", func() -> void:
		if destination == "book":
			var book: Dictionary = host.player.get("character_sheet", {}).get("caster", {}).get("spellbook", {})
			host.character_sheet.wizard_book.mode = "learn" if book.get("pending_learning", false) else "prepare"
		host.character_sheet.open(destination))
	box.add_child(button)
	panel.visibility_changed.connect(func() -> void:
		if not updating and not panel.visible and not key.is_empty():
			dismissed[key] = true)

func reset() -> void:
	dismissed.clear()
	key = ""
	updating = true
	panel.hide()
	updating = false

func refresh() -> void:
	var p: Dictionary = host.player
	var f: Dictionary = p.get("character_sheet", {}).get("fighter", {})
	var e: Dictionary = p.get("character_sheet", {}).get("caster", {}).get("elemental_fury", {})
	var book: Dictionary = p.get("character_sheet", {}).get("caster", {}).get("spellbook", {})
	var pending: String = ""
	destination = "feats"
	if str(p.get("class_id", "")) == "ranger" and f.get("pending", false):
		pending = "ranger_style"
		info.text = "Poziom 2: wybierz jeden styl walki albo Druidycznego wojownika z dwiema sztuczkami. Wybór jest bezpłatny i nie zużywa punktu atutu."
	elif str(p.get("class_id", "")) == "druid" and e.get("pending", false):
		pending = "elemental_fury"
		info.text = "Poziom 7: wybierz Potężne sztuczki (+Mądrość do obrażeń sztuczek) albo Pierwotne uderzenie (+1k8 raz w swojej turze). Na poziomie 15 zdolność się ulepszy."
	elif str(p.get("class_id", "")) == "mage" and book.get("enabled", false) and (book.get("pending_learning", false) or int(book.get("free_preparations", 0)) > 0):
		pending = "wizard_book:" + str(p.get("level", 1))
		destination = "book"
		info.text = "Otwórz własną księgę: nauka czarów i uzupełnienie nowych przygotowań. Zmianę całego zestawu wykonasz podczas długiego odpoczynku."
		if book.get("memorize_available", false):
			info.text += " Memorize Spell: po krótkim odpoczynku zamienisz jeden przygotowany czar."
	button.text = "Otwórz własną księgę" if destination == "book" else "Wybierz w karcie postaci"
	key = str(p.get("id", "")) + ":" + pending if not pending.is_empty() else ""
	updating = true
	panel.visible = not key.is_empty() and not dismissed.get(key, false)
	updating = false
