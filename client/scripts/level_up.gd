extends RefCounted
## Persistent owner-only advancement receipts; each Close dismisses exactly one ID.
var host: Node
var viewport: ScrollContainer
var layer: Control
var cards: Dictionary = {}
var closing: Dictionary = {}
var events: Array = []
var active_id: String = ""
var signature: String = ""
var last_size: Vector2 = Vector2.ZERO

func setup(owner: Node) -> void:
	host = owner
	viewport = ScrollContainer.new()
	viewport.name = "LevelUpCascade"
	viewport.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	viewport.mouse_filter = Control.MOUSE_FILTER_PASS
	host.hud.add_child(viewport)
	layer = Control.new()
	layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	viewport.add_child(layer)
	viewport.hide()
	host.get_viewport().size_changed.connect(resize)

func reset() -> void:
	for card: Control in cards.values():
		card.get_parent().remove_child(card)
		card.queue_free()
	cards.clear()
	closing.clear()
	signature = ""
	active_id = ""
	events = []
	viewport.hide()

func raise_card(id: String) -> void:
	if cards.has(id):
		active_id = id
		resize()
		viewport.set_deferred("scroll_vertical", maxi(0, (events.size() - 1) * 42))

func dismiss(id: String) -> void:
	if host.socket == null or host.socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	closing[id] = true
	host._send({"type":"dismiss_level_up", "id":id})
	signature = ""
	refresh()

func action_button(action: Dictionary) -> Button:
	var tab_name: String = "feats" if str(action.get("tab", "stats")) == "feats" else "stats"
	var b: Button = host._button(str(action.get("label", "Wybierz")), func() -> void: host.character_sheet.open(tab_name))
	b.set_meta("level_action", str(action.get("kind", "")))
	b.set_meta("original_text", b.text)
	b.custom_minimum_size.y = 32
	return b

func make_card(event: Dictionary) -> PanelContainer:
	var id: String = str(event["id"])
	var panel: PanelContainer = PanelContainer.new()
	panel.clip_contents = true
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color("183729")
	style.border_color = Color("d5b871")
	style.set_border_width_all(1)
	style.set_corner_radius_all(6)
	style.content_margin_left = 9
	style.content_margin_right = 9
	style.content_margin_top = 4
	style.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", style)
	var box: VBoxContainer = VBoxContainer.new()
	box.add_theme_constant_override("separation", 5)
	panel.add_child(box)
	var head: HBoxContainer = HBoxContainer.new()
	box.add_child(head)
	var title: Button = host._button("⇧  Poziom %d" % int(event.get("level", 1)), func() -> void: raise_card(id))
	title.flat = true
	title.alignment = HORIZONTAL_ALIGNMENT_LEFT
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", 17)
	head.add_child(title)
	var x: Button = host._button("×", func() -> void: dismiss(id))
	x.tooltip_text = "Zamknij ten awans"
	x.custom_minimum_size = Vector2(32, 32)
	head.add_child(x)
	var body: ScrollContainer = ScrollContainer.new()
	body.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(body)
	var rows: VBoxContainer = VBoxContainer.new()
	rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rows.add_theme_constant_override("separation", 8)
	body.add_child(rows)
	for change: Dictionary in event.get("rows", []):
		var row: HBoxContainer = HBoxContainer.new()
		rows.add_child(row)
		var path: String = str(change.get("icon", ""))
		if not path.is_empty() and ResourceLoader.exists("res://" + path):
			var image: TextureRect = TextureRect.new()
			image.texture = load("res://" + path) as Texture2D
			image.custom_minimum_size = Vector2(24, 24)
			image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			row.add_child(image)
		var value: String = str(change.get("label", "")) + " " + str(change.get("gain", ""))
		if not str(change.get("unit", "")).is_empty():
			value += " " + str(change["unit"])
		var label: Label = host._wrap_label(value, 14, Color("dce9bb"))
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(label)
		if str(change.get("id", "")) == "mastery":
			for action: Dictionary in event.get("actions", []):
				if str(action.get("kind", "")) == "mastery":
					rows.add_child(action_button(action))
	for action: Dictionary in event.get("actions", []):
		if str(action.get("kind", "")) != "mastery":
			rows.add_child(action_button(action))
	var close_button: Button = host._button("Zamknij", func() -> void: dismiss(id))
	close_button.custom_minimum_size.y = 36
	box.add_child(close_button)
	panel.name = "Awans_" + id
	layer.add_child(panel)
	host.window_layout.attach(panel, title)
	return panel

func update_actions(node: Node) -> void:
	if node is Button and node.has_meta("level_action"):
		var assigned: bool = str(node.get_meta("level_action")) == "mastery" and int(host.player.get("mastery_points", 0)) <= 0
		node.disabled = assigned
		node.text = "Przydzielono" if assigned else str(node.get_meta("original_text"))
	for child: Node in node.get_children():
		update_actions(child)

func refresh() -> void:
	if host.player.is_empty():
		return
	var incoming: Array = host.player.get("pending_level_ups", [])
	var ids: Array = []
	for entry: Dictionary in incoming:
		ids.append(str(entry["id"]))
	for id: String in closing.keys():
		if not ids.has(id):
			closing.erase(id)
	events = []
	for entry: Dictionary in incoming:
		if not closing.has(str(entry["id"])):
			events.append(entry)
	var key: String = JSON.stringify(events)
	if key != signature:
		signature = key
		var wanted: Array = []
		var added: bool = false
		for entry: Dictionary in events:
			var id: String = str(entry["id"])
			wanted.append(id)
			if not cards.has(id):
				cards[id] = make_card(entry)
				added = true
		for id: String in cards.keys():
			if not wanted.has(id):
				var card: Control = cards[id]
				card.get_parent().remove_child(card)
				card.queue_free()
				cards.erase(id)
		viewport.visible = not events.is_empty()
		resize()
		if added:
			viewport.set_deferred("scroll_vertical", maxi(0, (events.size() - 1) * 42))
			if not events.is_empty():
				raise_card(str(events.back()["id"]))
	update_actions(layer)

func resize() -> void:
	if viewport == null:
		return
	var screen: Vector2 = host.get_viewport().get_visible_rect().size
	var top: float = 210.0 if screen.y >= 650 else 156.0
	var bottom: float = 176.0 if screen.y >= 650 else 126.0
	var width: float = minf(334, screen.x * 0.72)
	var available: float = maxf(160, screen.y - top - bottom)
	if not viewport.get_meta("drag_position", false):
		viewport.position = Vector2(410 if screen.x >= 1000 else 8, top)
	viewport.size = Vector2(width, available)
	var end: float = 0.0
	if not cards.has(active_id) and not events.is_empty():
		active_id = str(events.back()["id"])
	var ordered: Array = []
	for entry: Dictionary in events:
		if str(entry["id"]) != active_id:
			ordered.append(entry)
	for entry: Dictionary in events:
		if str(entry["id"]) == active_id:
			ordered.append(entry)
	for i: int in range(ordered.size()):
		var entry: Dictionary = ordered[i]
		var card: Control = cards.get(str(entry["id"]))
		if card == null or card.get_meta("drag_position", false):
			continue
		var rows: Array = entry.get("rows", [])
		var height: float = minf(available - 4, 96 + rows.size() * 36 + entry.get("actions", []).size() * 36)
		card.move_to_front()
		card.position = Vector2(mini(i, 3) * 9, i * 42)
		card.size = Vector2(width - 36, height)
		end = maxf(end, i * 42 + height)
	layer.custom_minimum_size = Vector2(width - 14, end + 4)
