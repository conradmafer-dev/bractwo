extends RefCounted
## Shared metadata drives this book; every button sends a validated server command.
var host: Node
var panel: PanelContainer
var list: VBoxContainer
var subtitle: Label
var tab: String = "Czary"
var signature: String = ""

func setup(owner: Node) -> void:
	host = owner
	panel = host._window("KSIĘGA WĘDROWCA · K")
	panel.offset_bottom = 704
	var box: VBoxContainer = panel.get_child(0)
	subtitle = host._wrap_label("", 15)
	box.add_child(subtitle)
	var tabs: HBoxContainer = HBoxContainer.new()
	box.add_child(tabs)
	for title: String in ["Czary", "Rozwój", "Atlas", "Usługi", "Premium"]:
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

func show_book(which: String = "Czary") -> void:
	tab = which
	host.inventory_panel.hide()
	host.party_panel.hide()
	host.journal_panel.hide()
	host._stop_controls()
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
		panel.hide()
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
		availability.append([id, float(p.get("mana", 0)) >= float(w["spells"][id]["mana"]), float(p.get("spell_cooldowns", {}).get(id, 0)) <= 0])
	for id: String in w.get("runes", {}):
		availability.append([id, float(p.get("mana", 0)) >= float(w["runes"][id]["mana"])])
	var key: String = JSON.stringify([p.get("premium_demo", false), ceili(float(p.get("premium_demo_remaining", 0)) / 86400), tab, p.get("skills", {}), level, gold, availability, p.get("runes", {}), p.get("soul", 0), p.get("potions", {}), p.get("alive", true), p.get("promoted", false), p.get("mastery", {}), p.get("blessed", false), p.get("depot", []), p.get("inventory", []), p.get("equipment", {}), p.get("bank_gold", 0), p.get("home_city", ""), float(p.get("rune_cooldown", 0)) <= 0, master, bank, captain, free, host._near_merchant(), p.get("floor", 0), int(p.get("x", 0)) / 64, int(p.get("y", 0)) / 64])
	if key == signature:
		return
	signature = key
	host._clear_children(list)
	subtitle.text = "%s · poziom %d · dusza %d/%d" % [p.get("profession", ""), level, int(p.get("soul", 0)), int(p.get("max_soul", 100))]
	if tab == "Czary":
		text("Skróty: 3 leczenie · 4 przyspieszenie · 5 czar zaawansowany · 6 mistrzowski · 7 runa ognia")
		for id: String in w.get("spells", {}):
			var s: Dictionary = w["spells"][id]
			if s.has("class_ids") and not s["class_ids"].has(p.get("class_id", "")):
				continue
			var unlocked: bool = level >= int(s["min_level"]) and (not bool(s.get("promotion", false)) or bool(p.get("promoted", false)))
			text("%s · %s · poz. %d · %d many%s" % [s["name"], s["words"], int(s["min_level"]), int(s["mana"]), " · wymaga promocji" if s.get("promotion", false) else ""], true)
			text(str(s["description"]))
			action("Rzuć czar", {"type":"cast", "spell_id":id}, unlocked and float(p.get("mana", 0)) >= float(s["mana"]) and float(p.get("spell_cooldowns", {}).get(id, 0)) <= 0)
		for id: String in w.get("runes", {}):
			var rune: Dictionary = w["runes"][id]
			var count: int = int(p.get("runes", {}).get(id, 0))
			text("%s · %d/99 · poz. %d" % [rune["name"], count, int(rune["min_level"])], true)
			text("Wytworzenie: %d many, %d duszy. Mag lub druid. Każda klasa może kupić i używać run." % [int(rune["mana"]), int(rune["soul"])])
			action("Użyj runy", {"type":"rune_use", "rune_id":id}, level >= int(rune["min_level"]) and count > 0 and float(p.get("rune_cooldown", 0)) <= 0)
			action("Stwórz runę", {"type":"rune_craft", "rune_id":id}, level >= int(rune["min_level"]) and ["mage", "druid"].has(p.get("class_id", "")) and float(p.get("mana", 0)) >= float(rune["mana"]) and float(p.get("soul", 0)) >= float(rune["soul"]) and count < 99 and float(p.get("rune_cooldown", 0)) <= 0)
			action("Kup · %d zł" % int(rune["price"]), {"type":"rune_buy", "rune_id":id}, host._near_merchant() and free and level >= int(rune["min_level"]) and gold >= int(rune["price"]) and count < 99)
	elif tab == "Rozwój":
		var labels: Dictionary = {"melee":"Walka wręcz", "distance":"Walka dystansowa", "magic":"Poziom magiczny", "shielding":"Obrona"}
		for id: String in labels:
			var skill: Dictionary = p.get("skills", {}).get(id, {})
			text("%s: %d · %d/%d do kolejnego" % [labels[id], int(skill.get("level", 10)), int(skill.get("progress", 0)), int(skill.get("next", 30))])
		text("Umiejętności rosną przez trafienia, wydawaną manę i otrzymywane ciosy.")
		for milestone: Dictionary in w.get("milestones", []):
			text("%s Poziom %d · %s" % ["✓" if level >= int(milestone["level"]) else "◇", int(milestone["level"]), milestone["name"]], true)
			text(str(milestone["description"]))
		action("Promocja profesji · 2000 zł", {"type":"promote"}, master and level >= 20 and gold >= 2000 and not bool(p.get("promoted", false)))
		text("Punkty specjalizacji: %d. Pierwszy na poziomie 50, następne co 5 poziomów. Maks. 20 na gałąź." % int(p.get("mastery_points", 0)), true)
		for id: String in ["power", "vitality", "focus"]:
			var descriptions: Dictionary = {"power":"Siła: +3 ataku", "vitality":"Witalność: +12 HP", "focus":"Skupienie: +8 many, +1 ataku"}
			action("%s · %d/20 · dodaj" % [descriptions[id], int(p.get("mastery", {}).get(id, 0))], {"type":"mastery", "branch":id}, master and int(p.get("mastery_points", 0)) > 0 and int(p.get("mastery", {}).get(id, 0)) < 20)
		action("Wyzeruj specjalizację · 200 zł", {"type":"mastery_reset"}, master and gold >= 200)
	elif tab == "Atlas":
		text("OKOLICA · wybierz cel pierwszej wyprawy", true)
		text("E: skrytki (3 wolne miejsca, odnowienie 30 min), źródła (leczenie), kamienie wiatru (+15% marszu), kapliczki (−12% obrażeń PvE). Używaj poza walką.")
		text("Łup: wyposażenie 12%, trofeum 24%, mikstura 7%; odpowiednio silny gatunek: 1,5% przedmiot rodowy. Boss: 100% / 80% / 35%, do 8% przedmiot rodowy. Boss 110+: 0,2% legendarny relikt. Niezależne rzuty. Skrytka: 6% dodatkowy przedmiot rodowy, jeśli jej poziom na to pozwala.")
		var local_places: Array = w.get("landmarks", []).filter(func(l: Dictionary) -> bool: return l.get("hint", false))
		var here: Vector2 = Vector2(p["x"], p["y"])
		local_places.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return here.distance_to(Vector2(a["x"], a["y"])) < here.distance_to(Vector2(b["x"], b["y"])))
		for place: Dictionary in local_places:
			text("%s · zalecany poz. %d" % [place["name"], int(place.get("recommended_level", 1))], true)
			text(str(place.get("description", "")))
			route("Kierunek: %s" % host._direction_to(place), place)
		text("128 000 × 92 160 · 20 krain, 5 dalekich miast, 15 podziemi po dwa piętra, 9 wzniesień z piętrami +1 do +3. Poziomy regionów są zaleceniem, nie blokadą.")
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
		text("Zapasy u kupca · klawisze 1 i 2 używają najsilniejszej posiadanej mikstury", true)
		for id: String in w.get("potions", {}):
			var potion: Dictionary = w["potions"][id]
			action("%s ×%d · poz. %d · +%d · kup %d zł" % [potion["name"], int(p.get("potions", {}).get(id, 0)), int(potion.get("min_level", 1)), int(potion["restore"]), int(potion["price"])], {"type":"buy", "item":id}, host._near_merchant() and free and gold >= int(potion["price"]) and level >= int(potion.get("min_level", 1)))
