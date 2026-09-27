extends RefCounted
## Shared metadata drives this book; every button sends a validated server command.
var host: Node
var panel: PanelContainer
var list: VBoxContainer
var subtitle: Label
var tab: String = "Rozwój"
var signature: String = ""
var atlas: Control
var atlas_camera: Dictionary = {}

func setup(owner: Node) -> void:
	host = owner
	panel = host._window("ŚWIAT I USŁUGI")
	panel.offset_bottom = 704
	var box: VBoxContainer = panel.get_child(0)
	subtitle = host._wrap_label("", 15)
	box.add_child(subtitle)
	var tabs: HBoxContainer = HBoxContainer.new()
	box.add_child(tabs)
	for title: String in ["Rozwój", "Atlas", "Usługi", "Premium"]:
		tabs.add_child(host._button(title, func() -> void: show_book(title)))
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.custom_minimum_size.y = 260
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	list = VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 7)
	scroll.add_child(list)

func show_book(which: String = "Rozwój") -> void:
	if which == "Czary":
		host.character_sheet.open("spells")
		return
	host.character_sheet.panel.hide()
	tab = which
	host.inventory_panel.hide()
	host.party_panel.hide()
	host.journal_panel.hide()
	panel.show()
	signature = ""
	refresh()

func toggle() -> void:
	if panel.visible:
		panel.hide()
	else:
		show_book(tab)

func near_service(service: String) -> Dictionary:
	for npc: Dictionary in host.world_data.get("npcs", []):
		if npc.get("service", "") == service and host._npc_in_range(str(npc.get("id", ""))):
			return npc
	return {}

func text(value: String, heading: bool = false) -> void:
	list.add_child(host._wrap_label(value, 17 if heading else 14))

func action(label: String, command: Dictionary, enabled: bool = true) -> void:
	var button: Button = host._button(label, func() -> void: host._send(command))
	button.disabled = not enabled or not bool(host.player.get("alive", true))
	list.add_child(button)

func route(label: String, point: Dictionary) -> void:
	var button: Button = host._button(label, func() -> void:
		host.navigation_goal = point.duplicate(true)
		host.navigation_goal["label"] = label
		host._refresh_tracker())
	list.add_child(button)

func refresh() -> void:
	if not panel.visible or host.player.is_empty():
		return
	var p: Dictionary = host.player
	var w: Dictionary = host.world_data
	var level: int = int(p.get("level", 1))
	var gold: int = int(p.get("gold", 0))
	var free: bool = float(p.get("combat_remaining", 0)) <= 0
	var master: bool = not near_service("master").is_empty() and free
	var bank: Dictionary = near_service("bank")
	var captain: Dictionary = near_service("captain")
	# Rebuild on availability changes, not every fractional mana/cooldown tick.
	var availability: Array = []
	for id: String in w.get("spells", {}):
		availability.append([id, float(p.get("mana", 0)) >= host._spell_mana(id, w["spells"][id]), float(p.get("spell_cooldowns", {}).get(id, 0)) <= 0])
	for id: String in w.get("runes", {}):
		availability.append([id, float(p.get("mana", 0)) >= float(w["runes"][id]["mana"])])
	if tab == "Atlas" and is_instance_valid(atlas):
		atlas.set_data(w, host.state, host.local_id)
	var key: String = JSON.stringify([p.get("hotbar", []), p.get("form", ""), p.get("concentration", ""), p.get("shield_armed", false), float(p.get("action_remaining", 0)) <= 0, p.get("premium_demo", false), ceili(float(p.get("premium_demo_remaining", 0)) / 86400), tab, p.get("skills", {}), level, gold, availability, p.get("runes", {}), p.get("soul", 0), p.get("potions", {}), p.get("alive", true), p.get("promoted", false), p.get("mastery", {}), p.get("blessed", false), p.get("depot", []), p.get("inventory", []), p.get("equipment", {}), p.get("bank_gold", 0), p.get("home_city", ""), float(p.get("rune_cooldown", 0)) <= 0, master, bank, captain, free, host._near_merchant(), p.get("floor", 0), int(p.get("x", 0)) / 64, int(p.get("y", 0)) / 64])
	if tab == "Atlas":
		key = JSON.stringify([tab, level, p.get("floor", 0), p.get("discoveries", [])])
	if key == signature:
		return
	signature = key
	host._clear_children(list)
	subtitle.text = "%s · poziom %d · krąg %d" % [p.get("profession", ""), level, int(p.get("spell_circle", 0))]
	if tab == "Rozwój":
		text("KP %d · %s · %d atak/akcję · biegłość +%d · ST %d" % [int(p.get("armor_class", 10)), str(p.get("damage_dice", "")), int(p.get("attacks_per_round", 1)), int(p.get("proficiency", 2)), int(p.get("save_dc", 10))], true)
		text("Liczniki treningu nie zwiększają trafienia, KP ani ST czarów. Aktualne rzuty: C → Statystyki.")
		var labels: Dictionary = {"melee":"Walka wręcz", "distance":"Walka dystansowa", "magic":"Używanie magii", "shielding":"Obrona"}
		for id: String in labels:
			var skill: Dictionary = p.get("skills", {}).get(id, {})
			text("%s: %d · %d/%d do kolejnego" % [labels[id], int(skill.get("level", 10)), int(skill.get("progress", 0)), int(skill.get("next", 30))])
		text("Historia treningu: trafienia, wydawana mana i otrzymywane ciosy.")
		for milestone: Dictionary in w.get("class_progression", {}).get(str(p.get("class_id", "")), []):
			text("%s Poziom %d · %s" % ["✓" if level >= int(milestone["level"]) else "◇", int(milestone["level"]), milestone["name"]], true)
			text(str(milestone["description"]))
		action("Promocja profesji · 2000 zł", {"type":"promote"}, master and level >= 20 and gold >= 2000 and not bool(p.get("promoted", false)))
		text("Punkty specjalizacji: %d. Pierwszy na poziomie 50, następne co 5 poziomów. Maks. 20 na gałąź." % int(p.get("mastery_points", 0)), true)
		for id: String in ["power", "vitality", "focus"]:
			var descriptions: Dictionary = {"power":"Potęga: bez premii do Iskry i czarów" if str(p.get("class_id", "")) == "mage" else "Potęga: broń +1 obr./10 pkt (maks. +2), nie przemiany", "vitality":"Witalność: +2 HP", "focus":"Skupienie: +4 many"}
			action("%s · %d/20 · dodaj" % [descriptions[id], int(p.get("mastery", {}).get(id, 0))], {"type":"mastery", "branch":id}, free and bool(p.get("promoted", false)) and level >= 50 and int(p.get("mastery_points", 0)) > 0 and int(p.get("mastery", {}).get(id, 0)) < 20)
		action("Wyzeruj specjalizację · 200 zł", {"type":"mastery_reset"}, master and gold >= 200)
	elif tab == "Atlas":
		text("Klik: przybliż · prawy klik: oddal · przeciągnij: przesuń. Atlas nie zamyka się po kliknięciu.")
		atlas = preload("res://scripts/minimap.gd").new()
		atlas.atlas_mode = true
		atlas.custom_minimum_size = Vector2(280, 320)
		atlas.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if not atlas_camera.is_empty():
			atlas.zoom = float(atlas_camera["zoom"])
			atlas.center = atlas_camera["center"]
		atlas.view_changed.connect(func() -> void: atlas_camera = {"zoom":atlas.zoom, "center":atlas.center})
		var map_tools: HFlowContainer = HFlowContainer.new()
		list.add_child(map_tools)
		map_tools.add_child(host._button("−", func() -> void: atlas.zoom_by(0.5)))
		map_tools.add_child(host._button("+", func() -> void: atlas.zoom_by(2.0)))
		map_tools.add_child(host._button("Cały świat", func() -> void: atlas.show_all()))
		map_tools.add_child(host._button("Moja okolica", func() -> void: atlas.show_nearby(host.player)))
		list.add_child(atlas)
		atlas.set_data(w, host.state, host.local_id)
		text("Wyznacz cel przyciskiem przy wybranym miejscu poniżej. Nie zamyka to Atlasu.")
		text("E: skrytki (3 wolne miejsca, odnowienie 30 min), źródła (leczenie), kamienie wiatru (+15% marszu), kapliczki (−12% obrażeń PvE). Używaj poza walką.")
		var local_places: Array = w.get("landmarks", []).filter(func(l: Dictionary) -> bool: return l.get("hint", false))
		var here: Vector2 = Vector2(p["x"], p["y"])
		local_places.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return here.distance_to(Vector2(a["x"], a["y"])) < here.distance_to(Vector2(b["x"], b["y"])))
		for place: Dictionary in local_places:
			text("%s · zalecany poz. %d" % [place["name"], int(place.get("recommended_level", 1))], true)
			text(str(place.get("description", "")))
			route("Kierunek: %s" % host._direction_to(place), place)
		text("%d krain · %d miast. Poziomy krain to zalecenie, nie blokada." % [w.get("regions", []).size(), w.get("cities", []).size()])
		for city: Dictionary in w.get("cities", []):
			route("Miasto: %s · %s" % [city["name"], host._direction_to(city)], city)
		for region: Dictionary in w.get("regions", []):
			var point: Dictionary = {"x":float(region["x"])+float(region["w"])*0.5, "y":float(region["y"])+float(region["h"])*0.5, "floor":0}
			route("%s · poz. %d–%d · %s" % [region["name"], int(region["min_level"]), int(region["max_level"]), host._direction_to(point)], point)
		for stair: Dictionary in w.get("stairs", []):
			if int(stair["floor"]) == 0:
				route("%s · %s" % [stair["name"], host._direction_to(stair)], stair)
		list.add_child(host._button("Usuń cel nawigacji", func() -> void: host.navigation_goal = {}; host._refresh_tracker()))
	elif tab == "Premium":
		text("Premium · szybki marsz", true)
		text("10 zł / miesiąc · +20% szybkości ruchu. Teraz bezpłatna symulacja. Bez płatności, karty i automatycznego odnowienia.")
		var active: bool = bool(p.get("premium_demo", false))
		text("Aktywne przez jeszcze %d dni." % ceili(float(p.get("premium_demo_remaining", 0)) / 86400) if active else "Możesz włączyć test na 30 dni i wyłączyć go w dowolnym momencie.")
		action("Wyłącz symulację" if active else "Włącz bezpłatną symulację", {"type":"premium_demo", "enabled":not active})
		text("Ścieżka +18%, kamień +25%, trawa normalnie, ściółka −6%, piasek −14%, śnieg −12%, błoto −28%. Podłoże wpływa też na potwory.")
	else:
		text("Usługi wymagają odpowiedniego NPC i zakończenia walki. Wybierz mieszkańca, aby wskazać kierunek.")
		var sorted: Array = w.get("npcs", []).duplicate()
		var here: Vector2 = Vector2(float(p.get("x", 0)), float(p.get("y", 0)))
		sorted.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return here.distance_squared_to(Vector2(a["x"], a["y"])) < here.distance_squared_to(Vector2(b["x"], b["y"])))
		var shown: Array[String] = []
		for npc: Dictionary in sorted:
			var service: String = str(npc.get("service", ""))
			if not service.is_empty() and not shown.has(service):
				shown.append(service)
				route("%s · %s" % [npc["name"], host._direction_to(npc)], npc)
		for city: Dictionary in w.get("cities", []):
			var cost: int = 40 + int(here.distance_to(Vector2(city["x"], city["y"])) / 1000.0) * 8
			action("Rejs: %s · %d zł" % [city["name"], cost], {"type":"travel", "city_id":city["id"]}, not captain.is_empty() and captain.get("city_id", "") != city["id"] and free and level >= 8 and gold >= cost)
		text("Bank: %d zł · depozyt %d/120 · odrodzenie: %s" % [int(p.get("bank_gold", 0)), p.get("depot", []).size(), p.get("home_city", "przystan")], true)
		action("Wpłać całe złoto", {"type":"bank_deposit", "amount":"all"}, not bank.is_empty() and free and gold > 0)
		action("Wypłać 100 zł", {"type":"bank_withdraw", "amount":100}, not bank.is_empty() and free and int(p.get("bank_gold", 0)) >= 100)
		action("Wypłać całe złoto", {"type":"bank_withdraw", "amount":"all"}, not bank.is_empty() and free and int(p.get("bank_gold", 0)) > 0)
		action("Ustaw odrodzenie w tym mieście", {"type":"bind_city"}, not bank.is_empty() and free)
		action("Błogosławieństwo · poz. 40 · 500 zł", {"type":"bless"}, master and level >= 40 and gold >= 500 and not bool(p.get("blessed", false)))
		for item: Dictionary in p.get("inventory", []):
			if not p.get("equipment", {}).values().has(item["uid"]):
				action("Odłóż: " + str(item["name"]), {"type":"depot_store", "uid":item["uid"]}, not bank.is_empty() and free and p.get("depot", []).size() < 120)
		for item: Dictionary in p.get("depot", []):
			action("Zabierz: " + str(item["name"]), {"type":"depot_take", "uid":item["uid"]}, not bank.is_empty() and free and p.get("inventory", []).size() < 40)
		text("Mikstury Q/R · używasz dokładnie odmiany przypisanej w plecaku", true)
		for id: String in w.get("potions", {}):
			var potion: Dictionary = w["potions"][id]
			action("%s ×%d · poz. %d · +%d · kup %d zł" % [potion["name"], int(p.get("potions", {}).get(id, 0)), int(potion.get("min_level", 1)), int(potion["restore"]), int(potion["price"])], {"type":"buy", "item":id}, host._near_merchant() and free and gold >= int(potion["price"]) and level >= int(potion.get("min_level", 1)))
