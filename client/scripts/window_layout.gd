extends RefCounted
## Native header / handle dragging, saved locally. Dialogs remain server-authoritative.
var host: Node
var records: Array[Dictionary] = []
var active: Dictionary = {}
var config: ConfigFile = ConfigFile.new()
var account: String = ""
var controls: MenuButton
var serial: int = 0

func attach(panel: Control, handle: Control = null) -> void:
	for record: Dictionary in records:
		if record["panel"] == panel:
			return
	var record: Dictionary = {"panel":panel, "handle":handle, "restored":"", "key":"", "base":{}}
	records.append(record)
	if handle != null:
		handle.mouse_filter = Control.MOUSE_FILTER_STOP
		handle.mouse_default_cursor_shape = Control.CURSOR_DRAG
		handle.gui_input.connect(func(event: InputEvent) -> void: on_drag(event, record))

func setup(owner: Node) -> void:
	host = owner
	config.load("user://window_layout.cfg")
	# Register direct HUD controls without putting handles inside Containers.
	for child: Node in host.hud.get_children():
		if child is Control:
			attach(child)
	for record: Dictionary in records:
		prepare(record)
	controls = MenuButton.new()
	controls.text = "☷ Panele"
	controls.position = Vector2(14, 128)
	controls.custom_minimum_size = Vector2(126, 30)
	host.hud.add_child(controls)
	var popup: PopupMenu = controls.get_popup()
	var toggles: Array = [["Postać",host.stats_label.get_parent().get_parent().get_parent()], ["Zadanie",host.quest_tracker.get_parent()], ["Minimapa",host.minimap], ["W pobliżu",host.battle_panel], ["Statusy",host.status_strip], ["Awanse",host.level_up_panels.viewport], ["Czat",host.feed.get_parent().get_parent()], ["Mikstury",host.health_button.get_parent()], ["Czary / akcje",host.hud.get_node("ActionDock")]]
	for i: int in range(toggles.size()):
		popup.add_check_item(str(toggles[i][0]), i)
		popup.set_item_checked(i, true)
	popup.add_separator()
	popup.add_item("Przywróć układ", 100)
	popup.id_pressed.connect(func(id: int) -> void:
		if id == 100:
			reset_layout()
			for n: int in range(toggles.size()):
				popup.set_item_checked(n, true)
			return
		var panel: Control = toggles[id][1]
		var show_panel: bool = not popup.is_item_checked(id)
		popup.set_item_checked(id, show_panel)
		panel.set_meta("hud_hidden", not show_panel)
		panel.visible = show_panel
		config.set_value(account, "hidden_" + str(panel.name), not show_panel)
		config.save("user://window_layout.cfg"))

func prepare(record: Dictionary) -> void:
	var panel: Control = record["panel"]
	if record["key"] == "":
		record["key"] = str(panel.name)
		record["base"] = {"anchors":[panel.anchor_left,panel.anchor_top,panel.anchor_right,panel.anchor_bottom], "offsets":[panel.offset_left,panel.offset_top,panel.offset_right,panel.offset_bottom]}
	if record["handle"] == null:
		var grip: Button = Button.new()
		grip.text = "⋮⋮"
		grip.tooltip_text = "Przeciągnij panel"
		grip.custom_minimum_size = Vector2(24, 22)
		grip.size = Vector2(24, 22)
		grip.mouse_default_cursor_shape = Control.CURSOR_DRAG
		host.hud.add_child(grip)
		grip.gui_input.connect(func(event: InputEvent) -> void: on_drag(event, record))
		record["handle"] = grip
		record["overlay"] = true

func on_drag(event: InputEvent, record: Dictionary) -> void:
	if host == null:
		return
	var start: bool = (event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed) or (event is InputEventScreenTouch and event.pressed)
	var finish: bool = (event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed) or (event is InputEventScreenTouch and not event.pressed)
	if start:
		active = record
	elif finish and not active.is_empty():
		var panel: Control = active["panel"]
		config.set_value(account, str(active["key"]), panel.global_position)
		config.save("user://window_layout.cfg")
		active = {}
	elif (event is InputEventMouseMotion or event is InputEventScreenDrag) and active == record:
		var panel: Control = record["panel"]
		var pos: Vector2 = panel.global_position
		var extent: Vector2 = panel.size
		if panel.get_parent() != host.hud:
			panel.reparent(host.hud, true)
		panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
		panel.size = extent
		panel.set_meta("drag_position", true)
		serial += 1
		panel.z_index = mini(100 + serial, 4000)
		set_position(panel, pos + event.relative)
		host.get_viewport().set_input_as_handled()

func set_position(panel: Control, pos: Vector2) -> void:
	var bounds: Vector2 = host.get_viewport().get_visible_rect().size
	panel.global_position = Vector2(clampf(pos.x, 4, maxf(4, bounds.x-panel.size.x-4)), clampf(pos.y, 4, maxf(4, bounds.y-minf(panel.size.y,bounds.y-8)-4)))

func refresh() -> void:
	if host == null:
		return
	account = str(host.local_id)
	for record: Dictionary in records:
		if not is_instance_valid(record["panel"]):
			continue
		prepare(record)
		var panel: Control = record["panel"]
		if record["restored"] != account and not account.is_empty():
			record["restored"] = account
			if config.has_section_key(account, str(record["key"])):
				var extent: Vector2 = panel.size
				panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
				panel.size = extent
				panel.set_meta("drag_position", true)
				set_position(panel, config.get_value(account, str(record["key"])))
			panel.set_meta("hud_hidden", config.get_value(account, "hidden_" + str(panel.name), false))
		if panel.get_meta("hud_hidden", false):
			panel.hide()
		if panel.get_meta("drag_position", false):
			set_position(panel, panel.global_position)
		if record.get("overlay", false):
			var grip: Control = record["handle"]
			grip.visible = panel.visible
			grip.global_position = panel.global_position + Vector2(maxf(0,panel.size.x-26), 2)
			grip.z_index = mini(panel.z_index + 1,4095)

func reset_layout() -> void:
	for record: Dictionary in records:
		if not is_instance_valid(record["panel"]):
			continue
		var panel: Control = record["panel"]
		var base: Dictionary = record["base"]
		if base.is_empty():
			continue
		panel.anchor_left = base["anchors"][0]
		panel.anchor_top = base["anchors"][1]
		panel.anchor_right = base["anchors"][2]
		panel.anchor_bottom = base["anchors"][3]
		panel.offset_left = base["offsets"][0]
		panel.offset_top = base["offsets"][1]
		panel.offset_right = base["offsets"][2]
		panel.offset_bottom = base["offsets"][3]
		panel.set_meta("drag_position", false)
		panel.set_meta("hud_hidden", false)
		panel.z_index = 0
	if config.has_section(account):
		config.erase_section(account)
	config.save("user://window_layout.cfg")
	host.level_up_panels.resize()
