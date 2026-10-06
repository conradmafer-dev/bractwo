extends RefCounted
## Owner-only sheet, independent from world services and journal.
const ATTRIBUTES: Dictionary = {"strength":"Siła", "dexterity":"Zręczność", "constitution":"Kondycja", "intelligence":"Inteligencja", "wisdom":"Mądrość", "charisma":"Charyzma"}
var host: Node
var panel: PanelContainer
var list: VBoxContainer
var heading: Label
var scroll: ScrollContainer
var tabs: Dictionary = {}
var tab: String = "inventory"
var signature: String = ""
var bag_page: int = 0
var selected_item: String = ""
var selected_style: String = ""
var caster_content = preload("res://scripts/caster_sheet.gd").new()
var wizard_book = preload("res://scripts/wizard_spellbook.gd").new()

func setup(owner: Node) -> void:
	host = owner
	panel = host._window("KARTA POSTACI · C")
	panel.name = "CharacterSheet"
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	panel.offset_left = -454
	panel.offset_right = 454
	panel.offset_top = -312
	panel.offset_bottom = 312
	var box: VBoxContainer = panel.get_child(0)
	heading = host._label("", 19)
	box.add_child(heading)
	var nav: HBoxContainer = HBoxContainer.new()
	box.add_child(nav)
	var names: Dictionary = {"inventory":"Ekwipunek", "stats":"Statystyki", "feats":"Atuty", "spells":"Czary", "book":"Księga"}
	for key: String in names:
		var b: Button = host._button(names[key], func() -> void: show_tab(key))
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.toggle_mode = true
		tabs[key] = b
		nav.add_child(b)
	scroll = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	list = VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 8)
	scroll.add_child(list)

func open(which: String = "") -> void:
	host.inventory_panel.hide()
	host.party_panel.hide()
	host.journal_panel.hide()
	host.progression.panel.hide()
	host.attack_held = false
	panel.move_to_front()
	panel.show()
	show_tab(tab if which.is_empty() else which)

func toggle(which: String = "") -> void:
	if panel.visible and (which.is_empty() or which == tab):
		panel.hide()
	else:
		open(tab if which.is_empty() else which)

func show_tab(which: String) -> void:
	tab = which
	signature = ""
	scroll.scroll_vertical = 0
	refresh()

func text(value: String, large: bool = false) -> void:
	list.add_child(host._wrap_label(value, 18 if large else 14))

func signed(value: Variant) -> String:
	return ("+" if float(value) >= 0 else "") + str(value)

func dice(value: Variant) -> String:
	return "1k20" + signed(value)

func icon(path: String) -> Texture2D:
	return load("res://" + path) as Texture2D if ResourceLoader.exists("res://" + path) else null

func equipment_icon(item: Dictionary, slot: String) -> Texture2D:
	if item.has("icon"):
		return icon(str(item["icon"]))
	var kind: String = slot
	if slot in ["weapon", "offhand"]:
		var weapon_type: String = str(item.get("weapon_type", ""))
		kind = "weapon"
		if weapon_type == "focus":
			kind = "staff"
		elif weapon_type in ["quarterstaff", "club"]:
			kind = "nature_staff"
		elif weapon_type in ["shortbow", "longbow"] or bool(item.get("ranged", false)):
			kind = "bow"
		elif weapon_type.is_empty():
			var classes: Array = item.get("class_ids", [])
			if classes.size() == 1:
				kind = {"mage":"staff", "druid":"nature_staff", "ranger":"bow"}.get(str(classes[0]), "weapon")
	return icon("assets/equipment/" + kind + ".svg")

func refresh() -> void:
	if not panel.visible or host.player.is_empty():
		return
	if host.get_viewport().gui_get_focus_owner() is OptionButton:
		return
	var p: Dictionary = host.player
	tabs["book"].visible = wizard_book.metadata(p).get("enabled", false)
	if tab == "book" and not tabs["book"].visible:
		tab = "spells"
	var next: String = JSON.stringify([tab, bag_page, selected_item, p.get("inventory"), p.get("equipment"), p.get("character_sheet"), selected_style, not host.progression.near_service("master").is_empty(), p.get("attributes"), p.get("skills"), p.get("mastery"), p.get("mastery_points"), float(p.get("combat_remaining", 0)) > 0, float(p.get("bonus_remaining", 0)) > 0, p.get("alive"), p.get("hotbar"), p.get("level"), p.get("gold"), p.get("xp"), p.get("xp_total"), p.get("xp_next_total"), p.get("bank_gold"), p.get("soul"), p.get("kills"), p.get("boss_kills"), p.get("armor_class"), p.get("damage_dice"), p.get("attack_bonus"), p.get("potions"), p.get("potion_slots"), p.get("shield_armed"), p.get("ensnaring_armed"), p.get("concentration"), p.get("form"), int(p.get("mana", 0)), int(p.get("hp", 0)), p.get("queued_spell"), ceili(float(p.get("action_remaining", 0)) * 10) if not str(p.get("queued_spell", "")).is_empty() else 0, p.get("spell_cooldowns"), p.get("spell_profiles"), p.get("status_effects"), host.selected_enemy, host.selected_target, p.get("thrown_weapons"), int(p.get("x", 0)) / 32, int(p.get("y", 0)) / 32, p.get("action_remaining", 0) > 0, p.get("rest", {}), p.get("rest_block_reason", ""), ceili(float(p.get("rest_short_remaining", 0))), ceili(float(p.get("rest_long_remaining", 0)))])
	if signature == next:
		return
	signature = next
	heading.text = "%s · %s · poziom %d" % [p.get("name", ""), p.get("profession", host.CLASS_NAMES.get(p.get("class_id", ""), "")), int(p.get("level", 1))]
	for key: String in tabs:
		tabs[key].set_pressed_no_signal(key == tab)
	for child: Node in list.get_children():
		list.remove_child(child)
		child.queue_free()
	match tab:
		"inventory": equipment(p)
		"stats": statistics(p)
		"spells": spells(p)
		"book": wizard_book.render(self, p)
		"feats": caster_content.render(self, p)
		_: text("Atuty", true); text("Nie masz jeszcze atutów.")

func equipment(p: Dictionary) -> void:
	text("Założone przedmioty", true)
	var worn: Dictionary = p.get("equipment", {})
	var items: Array = p.get("inventory", [])
	var slots: GridContainer = GridContainer.new()
	slots.columns = 2
	list.add_child(slots)
	for slot: String in ["weapon", "offhand", "armor", "shield", "ring"]:
		var item: Dictionary = {}
		for entry: Dictionary in items:
			if str(entry.get("uid", "")) == str(worn.get(slot, "_")):
				item = entry
		var cell: VBoxContainer = VBoxContainer.new()
		cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		slots.add_child(cell)
		var b: Button = host._button(str(host.SLOT_NAMES.get(slot, slot)) + "\n" + str(item.get("name", "Brak")), func() -> void:
			selected_item = str(item.get("uid", ""))
			signature = ""
			refresh())
		b.tooltip_text = str(item.get("name", "")) + "\n" + host._item_details(item)
		b.icon = equipment_icon(item, slot)
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 34)
		b.custom_minimum_size = Vector2(235, 62)
		b.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		cell.add_child(b)
	text("Plecak · przedmioty %d / 40" % items.size(), true)
	var bag: Array = []
	for item: Dictionary in items:
		if not worn.values().has(item.get("uid")):
			bag.append(item)
	var pages: int = maxi(1, ceili(bag.size() / 15.0))
	bag_page = clampi(bag_page, 0, pages - 1)
	var grid: GridContainer = GridContainer.new()
	grid.columns = 5
	list.add_child(grid)
	for i: int in range(15):
		var n: int = bag_page * 15 + i
		var item: Dictionary = bag[n] if n < bag.size() else {}
		var b: Button = host._button(str(item.get("name", "·")) + (" ×%d" % int(item.get("quantity", 1)) if item.has("quantity") else ""), func() -> void:
			selected_item = str(item.get("uid", ""))
			signature = ""
			refresh())
		b.disabled = item.is_empty()
		b.custom_minimum_size = Vector2(153, 54)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		b.tooltip_text = str(item.get("name", "")) + "\n" + host._item_details(item)
		b.add_theme_font_size_override("font_size", 12)
		b.icon = equipment_icon(item, str(item.get("slot", "empty")))
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 24)
		grid.add_child(b)
	var pager: HBoxContainer = HBoxContainer.new()
	pager.alignment = BoxContainer.ALIGNMENT_CENTER
	list.add_child(pager)
	var prev: Button = host._button("‹", func() -> void: bag_page -= 1; signature = ""; refresh())
	prev.disabled = bag_page == 0
	pager.add_child(prev)
	pager.add_child(host._label("%d / %d" % [bag_page + 1, pages], 14))
	var nxt: Button = host._button("›", func() -> void: bag_page += 1; signature = ""; refresh())
	nxt.disabled = bag_page == pages - 1
	pager.add_child(nxt)
	for item: Dictionary in items:
		if str(item.get("uid", "")) != selected_item:
			continue
		text(str(item.get("name", "")), true)
		text(host._item_details(item))
		list.add_child(HSeparator.new())
		var row: HFlowContainer = HFlowContainer.new()
		list.add_child(row)
		var is_worn: bool = worn.values().has(item.get("uid"))
		if str(item.get("slot", "")) == "potion":
			var use: Button = host._button("Użyj", func() -> void: host._send({"type":"potion", "item":item["template"]}))
			use.disabled = not p.get("alive", true) or int(p.get("level", 1)) < int(item.get("min_level", 1))
			row.add_child(use)
			for key: String in ["q", "r"]:
				var bind_button: Button = host._button(("✓ " if p.get("potion_slots", {}).get(key, "") == item["template"] else "Przypisz ") + key.to_upper(), func() -> void: host._send({"type":"potion_bind", "slot":key, "item":item["template"]}))
				bind_button.disabled = use.disabled
				row.add_child(bind_button)
		elif is_worn:
			var worn_slot: String = str(item.get("slot", ""))
			for slot: String in worn:
				if worn[slot] == item.get("uid"):
					worn_slot = slot
			row.add_child(host._button("Zdejmij", func() -> void: host._send({"type":"unequip", "slot":worn_slot})))
		elif str(item.get("slot", "")) in ["weapon", "armor", "shield", "ring"]:
			var equip_button: Button = host._button("Załóż", func() -> void: host._send({"type":"equip", "uid":item["uid"]}))
			equip_button.disabled = not host._item_usable(item) or not p.get("alive", true)
			row.add_child(equip_button)
			if str(item.get("slot", "")) == "weapon" and bool(item.get("light", false)):
				var offhand_button: Button = host._button("Załóż do drugiej ręki", func() -> void: host._send({"type":"equip", "uid":item["uid"], "slot":"offhand"}))
				offhand_button.disabled = equip_button.disabled or not bool(host.weapon_actions.metadata(p).get("can_equip_offhand", false))
				row.add_child(offhand_button)
		if is_worn and item.get("slot", "") == "weapon" and item.has("versatile_dice"):
			for grip: String in ["one", "two"]:
				var grip_button: Button = host._button("Jednorącz" if grip == "one" else "Oburącz", func() -> void: host._send({"type":"weapon_grip", "grip":grip}))
				grip_button.disabled = not p.get("alive", false) or not str(p.get("form", "")).is_empty() or float(p.get("combat_remaining", 0)) > 0
				row.add_child(grip_button)
		if not is_worn and host._near_merchant() and float(p.get("combat_remaining", 0)) <= 0:
			var sell: Button = host._button("Sprzedaj · %d zł" % int(item.get("value", 0)), func() -> void: host._send({"type":"sell", "uid":item["uid"]}))
			sell.disabled = not p.get("alive", true)
			row.add_child(sell)
			if int(item.get("quantity", 1)) > 1:
				var sell_stack: Button = host._button("Stos · %d zł" % (int(item.get("value", 0))*int(item["quantity"])), func() -> void: host._send({"type":"sell", "uid":item["uid"], "quantity":item["quantity"]}))
				sell_stack.disabled = sell.disabled
				row.add_child(sell_stack)
	host.weapon_actions.render(list, p)
	host.weapon_actions.recovery(self, p)

func allocation(p: Dictionary) -> void:
	var points: int = int(p.get("mastery_points", 0))
	if points <= 0:
		return
	text("Punkty mistrzostwa do przydzielenia: %d" % points, true)
	var fighting: bool = float(p.get("combat_remaining", 0)) > 0
	text("Punkty przydzielisz po zakończeniu walki." if fighting else "Wybierz, co chcesz wzmocnić.")
	var names: Dictionary = {"power":"Potęga", "vitality":"Witalność", "focus":"Skupienie"}
	var descriptions: Dictionary = {"power":"+1 do obrażeń broni za każde 10 punktów", "vitality":"+2 HP za punkt", "focus":"+4 many za punkt"}
	for branch: String in names:
		var count: int = int(p.get("mastery", {}).get(branch, 0))
		var row: HBoxContainer = HBoxContainer.new()
		list.add_child(row)
		var info: Label = host._wrap_label("%s · %d/20\n%s" % [names[branch], count, descriptions[branch]], 14)
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(info)
		var b: Button = host._button("+1 punkt", func() -> void: host._send({"type":"mastery", "branch":branch}))
		b.disabled = fighting or not bool(p.get("alive", false)) or count >= 20
		row.add_child(b)

func statistics(p: Dictionary) -> void:
	allocation(p)
	var s: Dictionary = p.get("character_sheet", {})
	text("HP %d/%d · Mana %d/%d · KP %d" % [ceili(p.get("hp", 0)), int(p.get("max_hp", 0)), int(p.get("mana", 0)), int(p.get("max_mana", 0)), int(p.get("armor_class", 10))], true)
	text("Walka", true)
	var fighter: Dictionary = s.get("fighter", {})
	if not str(fighter.get("style", "")).is_empty():
		text("Styl: " + str(fighter.get("style_name", "")) + (" · aktywny" if fighter.get("style_active", false) else " · nieaktywny z obecnym wyposażeniem"))
	text("Atak bronią: %s · Obrażenia: %s · %s\nAtaki na rundę: %d · Trafienie krytyczne: 20 na k20" % [dice(p.get("attack_bonus", 0)), p.get("damage_dice", ""), s.get("damage_name", ""), int(p.get("attacks_per_round", 1))])
	text("Atak czarem: %s · ST obrony: %d · Biegłość: %s · Krąg: %d" % [dice(s.get("spell_attack_bonus", 0)), int(p.get("save_dc", 10)), signed(p.get("proficiency", 2)), int(p.get("spell_circle", 0))])
	text("Cechy i rzuty obronne", true)
	var grid: GridContainer = GridContainer.new()
	grid.columns = 3
	list.add_child(grid)
	for key: String in ATTRIBUTES:
		var label: Label = host._wrap_label("%s: %d (%s)\nObrona %s%s" % [ATTRIBUTES[key], int(p.get("attributes", {}).get(key, 10)), signed(s.get("ability_modifiers", {}).get(key, 0)), dice(s.get("saving_throws", {}).get(key, 0)), " ✦" if s.get("proficient_saves", []).has(key) else ""], 15)
		label.custom_minimum_size.x = 255
		grid.add_child(label)
	text("Odporności", true)
	for r: Dictionary in s.get("resistances", []):
		text(str(r.get("name", "")) + (" · połowa obrażeń" if float(r.get("multiplier", 1)) == 0.5 else " · niewrażliwość" if float(r.get("multiplier", 1)) == 0 else " · zwykłe obrażenia"))
	text("Ruch: %s stóp na rundę · Zasięg broni: %d stóp · Kość zdrowia: %s" % [s.get("movement_per_round", 0), roundi(float(p.get("attack_range", 0)) / 6.4), s.get("hit_die", "")])
	text("PD: %d/%d · Złoto: %d · Bank: %d · Dusza: %d/%d" % [int(p.get("xp_total", p.get("xp", 0))), int(p.get("xp_next_total", p.get("xp_next", 300))), int(p.get("gold", 0)), int(p.get("bank_gold", 0)), int(p.get("soul", 0)), int(p.get("max_soul", 100))])
	text("Potwory: %d · Bossowie: %d" % [int(p.get("kills", 0)), int(p.get("boss_kills", 0))])
	var skills: Dictionary = {"melee":"Walka wręcz", "distance":"Walka dystansowa", "magic":"Magia", "shielding":"Obrona"}
	for key: String in p.get("skills", {}):
		var value: Dictionary = p["skills"][key]
		text("%s: %d · %d/%d" % [skills.get(key, key), int(value.get("level", 0)), int(value.get("progress", 0)), int(value.get("next", 0))])
	var mastery: Dictionary = {"power":"Potęga", "vitality":"Witalność", "focus":"Skupienie"}
	for key: String in p.get("mastery", {}):
		if int(p["mastery"][key]) > 0:
			text("%s: %d" % [mastery.get(key, key), int(p["mastery"][key])])
	text("Aktywne efekty", true)
	for effect: Dictionary in p.get("status_effects", []):
		text("%s · %d rund\n%s" % [effect.get("name", ""), int(effect.get("rounds", 0)), effect.get("description", "")])
	if p.get("status_effects", []).is_empty():
		text("Brak aktywnych efektów.")

func spells(p: Dictionary) -> void:
	caster_content.controls(self, p)
	if wizard_book.metadata(p).get("enabled", false):
		list.add_child(host._button("Otwórz własną księgę · nauka i przygotowania", func() -> void: open("book")))
	text("Krąg %d · Mana %d/%d" % [int(p.get("spell_circle", 0)), int(p.get("mana", 0)), int(p.get("max_mana", 0))], true)
	text("F · " + str(host.world_data.get("spells", {}).get(p.get("favorite_spell", ""), {}).get("name", "—")))
	for key: String in host.world_data.get("spells", {}):
		var spec: Dictionary = host._spell_profile(key)
		if not spec.get("class_ids", []).has(p.get("class_id", "")) and not p.get("character_sheet", {}).get("fighter", {}).get("chosen_cantrips", []).has(key):
			continue
		if not wizard_book.known(p, key, spec):
			continue
		var gate: int = host._spell_gate(spec)
		var unlocked: bool = int(p.get("level", 1)) >= gate
		var prepared: bool = wizard_book.prepared(p, key, spec)
		var row: HBoxContainer = HBoxContainer.new()
		list.add_child(row)
		var art: TextureRect = TextureRect.new()
		art.texture = icon(str(spec.get("icon", "assets/spells/" + key + ".svg")))
		art.custom_minimum_size = Vector2(48, 48)
		art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		row.add_child(art)
		var title: Label = host._wrap_label(str(spec.get("name", "")) + (" · krąg %d" % int(spec.get("circle", 0)) if int(spec.get("circle", 0)) > 0 else " · sztuczka" if not spec.get("feature", false) else " · zdolność") + "\n%d many%s" % [host._spell_mana(key, spec), " · od poziomu %d" % gate if not unlocked else " · nieprzygotowany" if not prepared else ""], 15)
		title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(title)
		var queue_label: String = host._queued_spell_label(key)
		var cast: Button = host._button(queue_label if not queue_label.is_empty() else "Użyj", func() -> void: host._send({"type":"cast", "spell_id":key}))
		var reaction: bool = spec.get("kind", "") == "reaction"
		var revert: bool = spec.get("kind", "") == "shape" and not str(p.get("form", "")).is_empty()
		cast.text = queue_label if not queue_label.is_empty() else "Powrót" if revert else ("Wyłącz" if p.get("shield_armed", false) else "Włącz") if reaction else ("Anuluj" if p.get("ensnaring_armed", false) else "Przygotuj") if spec.get("kind", "") == "weapon_trigger" else "Użyj"
		cast.disabled = not unlocked or not prepared or not p.get("alive", true) or (not reaction and not revert and not (spec.get("kind", "") == "weapon_trigger" and p.get("ensnaring_armed", false)) and (float(p.get("mana", 0)) < host._spell_mana(key, spec) or float(p.get("spell_cooldowns", {}).get(key, 0)) > 0 or not str(p.get("form", "")).is_empty()))
		if spec.get("kind", "") == "recovery":
			cast.disabled = not caster_content.can_recover(p)
		row.add_child(cast)
		if spec.get("ritual", false) and unlocked:
			var ritual: Button = host._button("Rytuał · 0 many · %d s" % int(spec.get("ritual_seconds", 10)), func() -> void: host._send({"type":"ritual", "spell_id":key}))
			ritual.disabled = not p.get("alive", false) or not str(p.get("form", "")).is_empty() or float(p.get("combat_remaining", 0)) > 0 or not p.get("character_sheet", {}).get("caster", {}).get("channel", {}).is_empty() or int(p.get("gold", 0)) < int(spec.get("gold", 0)) or p.get("character_sheet", {}).get("training", {}).get("armor_penalty", false)
			list.add_child(ritual)
		if int(spec.get("gold", 0)) > 0:
			text("Składnik: %d zł" % int(spec["gold"]))
		var picker: OptionButton = OptionButton.new()
		picker.custom_minimum_size.x = 140
		picker.add_item("Przypisz skrót…")
		var bar: Array = p.get("hotbar", [])
		for i: int in range(bar.size()):
			picker.add_item(host._hotbar_key_label(i) + (" ✓" if str(bar[i]) == key else ""))
		picker.disabled = not unlocked or not prepared
		picker.item_selected.connect(func(index: int) -> void:
			host._bind_hotbar(index, key)
			picker.release_focus())
		row.add_child(picker)
		if not str(spec.get("power_summary", "")).is_empty():
			text(str(spec["power_summary"]), true)
		var current: String = str(p.get("concentration", ""))
		if spec.get("concentration", false) and not current.is_empty() and current != key:
			text(("Po trafieniu zastąpi: " if spec.get("kind", "") == "weapon_trigger" else "Zastąpi: ") + str(host.world_data.get("spells", {}).get(current, {}).get("name", current)))
		if unlocked and not str(spec.get("next_upgrade", "")).is_empty():
			text(str(spec["next_upgrade"]))
		var powers: Array = spec.get("power_options", [])
		if unlocked and powers.size() > 1:
			var power: OptionButton = OptionButton.new()
			power.add_item("Auto · najwyższa moc", 0)
			var costs: Array = p.get("mana_budget", {}).get("costs", [])
			for rank_value in powers:
				var rank: int = int(rank_value)
				var cost: int = 0 if spec.get("free_cast", false) else int(costs[rank]) if rank < costs.size() else 0
				power.add_item("Krąg %d · %d many" % [rank, cost], rank)
			power.select(power.get_item_index(int(spec.get("power_choice", 0))))
			power.item_selected.connect(func(index: int) -> void:
				host._send({"type":"spell_power", "spell_id":key, "circle":power.get_item_id(index)})
				power.release_focus())
			list.add_child(power)
		if spec.get("recast_active", false):
			list.add_child(host._button("Zakończ czar", func() -> void: host._send({"type":"stop_concentration"})))
		text(str(spec.get("description", "")).replace("W tej adaptacji ", "").replace("w adaptacji ", ""))


func fighting_styles(p: Dictionary) -> void:
	var f: Dictionary = p.get("character_sheet", {}).get("fighter", {})
	if f.is_empty():
		text("Nie masz jeszcze atutów.")
		return
	var current: String = str(f.get("style", ""))
	var candidate: String = selected_style if not selected_style.is_empty() else current
	var can_choose: bool = bool(p.get("alive", false)) and float(p.get("combat_remaining", 0)) <= 0 and (current.is_empty() or (host._in_town() and not host.progression.near_service("master").is_empty()))
	text("Styl walki", true)
	text("Masz jeden dostępny wybór. Nie zużywa punktu cechy ani późniejszego atutu." if current.is_empty() else "Wybrany: " + str(f.get("style_name", "")) + (" · aktywny" if f.get("style_active", false) else " · nieaktywny z obecnym wyposażeniem"))
	for choice: Dictionary in f.get("choices", []):
		var key: String = str(choice["id"])
		var b: Button = host._button(("✓ " if candidate == key else "") + str(choice["name"]), func() -> void:
			selected_style = key
			signature = ""
			refresh())
		b.icon = icon(str(choice.get("icon", "")))
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 32)
		list.add_child(b)
		text(str(choice.get("description", "")))
		text("Działa z obecnym wyposażeniem." if choice.get("active_with_gear", false) else str(choice.get("requirement", "")))
	if not candidate.is_empty():
		var confirm: Button = host._button("Wybrany styl" if candidate == current else "Wybierz ten styl" if current.is_empty() else "Zmień styl bez opłaty", func() -> void: host._send({"type":"fighting_style", "style":candidate}))
		confirm.disabled = not can_choose or candidate == current
		list.add_child(confirm)
	text("Wybór dostępny po walce." if float(p.get("combat_remaining", 0)) > 0 else "Zmienisz styl bez opłaty u mistrza profesji w osadzie. Zmiana broni nie zmienia stylu.")
	text("Mistrzostwo broni", true)
	text("Opanowane trzy rodzaje broni. Działa właściwość aktualnie używanej broni.")
	for mastery: Dictionary in f.get("masteries", []):
		var row: HBoxContainer = HBoxContainer.new()
		list.add_child(row)
		var art: TextureRect = TextureRect.new()
		art.texture = icon(str(mastery.get("icon", "")))
		art.custom_minimum_size = Vector2(40, 40)
		art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		row.add_child(art)
		var description: Label = host._wrap_label(str(mastery.get("name", "")) + " · " + str(mastery.get("effect_name", "")) + (" · aktywne" if mastery.get("active", false) else "") + "\n" + str(mastery.get("description", "")), 14)
		description.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(description)
	if f.get("can_change_grip", false):
		text("Chwyt broni", true)
		text("Oburącz: większa kość obrażeń. Tarcza pozostaje w plecaku.")
		for grip: String in ["one", "two"]:
			var b: Button = host._button("Jednorącz" if grip == "one" else "Oburącz", func() -> void: host._send({"type":"weapon_grip", "grip":grip}))
			b.disabled = float(p.get("combat_remaining", 0)) > 0 or not p.get("alive", false) or f.get("weapon_grip", "one") == grip
			list.add_child(b)
