extends RefCounted
## Weapon modes and bonus/replacement attacks use server eligibility.
const MODE_NAMES: Dictionary = {"weapon":"Broń", "throw":"Rzut bronią", "unarmed":"Cios bez broni"}
var host: Node
var panel: PanelContainer
var list: VBoxContainer
var signature: String = ""

func setup(owner: Node) -> void:
	host = owner
	panel = host._window("Sposób ataku")
	panel.name = "WeaponActions"
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(290, 300)
	panel.custom_minimum_size = Vector2(290, 230)
	panel.size = Vector2(290, 230)
	list = panel.get_child(0)

func toggle() -> void:
	panel.visible = not panel.visible
	signature = ""
	refresh()

func reset() -> void:
	panel.hide()
	signature = ""

func metadata(p: Dictionary) -> Dictionary:
	return p.get("character_sheet", {}).get("weapon_actions", p.get("weapon_actions", {}))

func refresh() -> void:
	if not panel.visible or host.player.is_empty():
		return
	var p: Dictionary = host.player
	var key: String = JSON.stringify([metadata(p), p.get("alive"), p.get("form"), p.get("action_remaining", 0) > 0, p.get("bonus_remaining", 0) > 0, host.selected_enemy, host.selected_target, p.get("pvp_safety", true)])
	if key == signature:
		return
	signature = key
	# Keep _window's unmarked draggable title/Close row.
	for child: Node in list.get_children():
		if child.get_meta("weapon_control", false):
			list.remove_child(child)
			child.queue_free()
	render(list, p)

func add(box: VBoxContainer, node: Control) -> void:
	node.set_meta("weapon_control", true)
	box.add_child(node)

func render(box: VBoxContainer, p: Dictionary) -> void:
	var w: Dictionary = metadata(p)
	if w.is_empty():
		return
	var alive: bool = bool(p.get("alive", false)) and str(p.get("form", "")).is_empty()
	add(box, host._wrap_label("Sposób ataku · Spacja używa wybranego trybu", 15))
	var row: HFlowContainer = HFlowContainer.new()
	add(box, row)
	for mode: Dictionary in w.get("modes", []):
		var key: String = str(mode["id"])
		var b: Button = host._button(("✓ " if w.get("mode", "weapon") == key else "") + str(MODE_NAMES.get(key, key)), func() -> void: host._send({"type":"weapon_attack_mode", "mode":key}))
		b.disabled = not alive or not bool(mode.get("enabled", false)) or w.get("mode", "weapon") == key
		row.add_child(b)
	var target_ready: bool = not host.selected_enemy.is_empty() or (not host.selected_target.is_empty() and not bool(p.get("pvp_safety", true)))
	var offhand: Button = host._button("Atak drugą lekką bronią · akcja dodatkowa", func() -> void: target_action("offhand_attack"))
	offhand.disabled = not alive or not bool(w.get("offhand_enabled", false)) or not target_ready
	offhand.tooltip_text = str(w.get("offhand_reason", "Najpierw zaatakuj główną lekką bronią w tej turze."))
	add(box, offhand)
	var grapple: Button = host._button("Chwyć cel · zamiast ataku · ST %d" % int(w.get("grapple_dc", 10)), func() -> void: target_action("grapple"))
	grapple.disabled = not alive or not bool(w.get("can_grapple", false)) or float(p.get("action_remaining", 0)) > 0 or not target_ready
	grapple.tooltip_text = "Wymaga wolnej dłoni i celu w zasięgu 5 stóp. Cel broni się Siłą albo Zręcznością."
	add(box, grapple)
	add(box, host._wrap_label("Cios bez broni: " + str(w.get("unarmed_dice", "")) + ". Rzucone bronie podniesiesz klawiszem E w pobliżu albo w ekwipunku.", 13))

func target_action(command: String) -> void:
	if host.selected_enemy.is_empty() and host.selected_target.is_empty():
		host._add_notice("Najpierw wybierz cel.")
		return
	if not host.selected_enemy.is_empty():
		host._send({"type":command, "enemy_id":host.selected_enemy})
	elif not bool(host.player.get("pvp_safety", true)):
		host._send({"type":command, "target_id":host.selected_target})

func recovery(sheet, p: Dictionary) -> void:
	var entries: Array = p.get("thrown_weapons", metadata(p).get("thrown_weapons", []))
	if entries.is_empty():
		return
	sheet.text("Twoje rzucone bronie", true)
	for entry: Dictionary in entries:
		var item: Dictionary = entry.get("item", {})
		var distance: float = Vector2(float(p.get("x", 0)), float(p.get("y", 0))).distance_to(Vector2(float(entry.get("x", 0)), float(entry.get("y", 0))))
		var uid: String = str(item.get("uid", ""))
		var b: Button = host._button("Podnieś: " + str(item.get("name", "Broń")) + " · %d kroków" % ceili(distance), func() -> void: host._send({"type":"recover_thrown", "uid":uid}))
		b.disabled = not bool(p.get("alive", false)) or int(entry.get("floor", 0)) != int(p.get("floor", 0)) or distance > 64
		b.tooltip_text = "Podejdź na 64 kroki, na tym samym poziomie, bez przeszkody między postacią a bronią. Potrzebujesz miejsca w plecaku."
		sheet.list.add_child(b)
