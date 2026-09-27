extends RefCounted
## Nonblocking, draggable first-choice reminder. Dismissal does not spend the choice.
var host: Node
var panel: PanelContainer
var dismissed: Dictionary = {}
var config: ConfigFile = ConfigFile.new()

func setup(owner: Node) -> void:
	host = owner
	config.load("user://caster_choices.cfg")
	panel = host._window("Ścieżka druida")
	panel.name = "CasterChoice"
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(290, 138)
	panel.custom_minimum_size = Vector2(250, 120)
	panel.size = Vector2(250, 120)
	var box: VBoxContainer = panel.get_child(0)
	box.add_child(host._wrap_label("Strażnik czy Mistyk natury?", 14))
	box.add_child(host._button("Wybierz ścieżkę", func() -> void: host.character_sheet.open("feats")))
	panel.visibility_changed.connect(func() -> void:
		if not panel.visible and host.player.get("character_sheet", {}).get("caster", {}).get("order_pending", false):
			var id: String = str(host.player.get("id", ""))
			if not id.is_empty():
				dismissed[id] = true
				config.set_value("closed", id, true)
				config.save("user://caster_choices.cfg"))

func refresh() -> void:
	var id: String = str(host.player.get("id", ""))
	panel.visible = not id.is_empty() and bool(host.player.get("character_sheet", {}).get("caster", {}).get("order_pending", false)) and not dismissed.get(id, false) and not config.get_value("closed", id, false)
