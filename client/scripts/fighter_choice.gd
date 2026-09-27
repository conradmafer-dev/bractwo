extends RefCounted
## Nonblocking, draggable first-choice reminder. Dismissal does not spend the choice.
var host: Node
var panel: PanelContainer
var dismissed: Dictionary = {}
var config: ConfigFile = ConfigFile.new()

func setup(owner: Node) -> void:
	host = owner
	config.load("user://fighter_choices.cfg")
	panel = host._window("Wybierz styl walki")
	panel.name = "FighterChoice"
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(290, 138)
	panel.custom_minimum_size = Vector2(250, 120)
	panel.size = Vector2(250, 120)
	var box: VBoxContainer = panel.get_child(0)
	box.add_child(host._wrap_label("Masz jeden dostępny wybór.", 14))
	box.add_child(host._button("Wybierz styl", func() -> void: host.character_sheet.open("feats")))
	panel.visibility_changed.connect(func() -> void:
		if not panel.visible and host.player.get("character_sheet", {}).get("fighter", {}).get("pending", false):
			var id: String = str(host.player.get("id", ""))
			if not id.is_empty():
				dismissed[id] = true
				config.set_value("closed", id, true)
				config.save("user://fighter_choices.cfg"))

func refresh() -> void:
	var id: String = str(host.player.get("id", ""))
	panel.visible = not id.is_empty() and bool(host.player.get("character_sheet", {}).get("fighter", {}).get("pending", false)) and not dismissed.get(id, false) and not config.get_value("closed", id, false)
