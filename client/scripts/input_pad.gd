extends Control
## Multi-touch joystick. Other fingers remain available for action buttons.
var vector: Vector2 = Vector2.ZERO
var finger: int = -1
var mouse_drag: bool = false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	custom_minimum_size = Vector2(160, 160)

func reset() -> void:
	finger = -1
	mouse_drag = false
	vector = Vector2.ZERO
	queue_redraw()

func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	if event is InputEventScreenTouch:
		if event.pressed and finger == -1 and get_global_rect().has_point(event.position):
			finger = event.index
			_update_vector(event.position - global_position)
			get_viewport().set_input_as_handled()
		elif event.index == finger and not event.pressed:
			reset()
			get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag and event.index == finger:
		_update_vector(event.position - global_position)
		get_viewport().set_input_as_handled()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		mouse_drag = event.pressed
		if mouse_drag:
			_update_vector(event.position)
		else:
			reset()
		accept_event()
	elif event is InputEventMouseMotion and mouse_drag:
		_update_vector(event.position)
		accept_event()

func _update_vector(pos: Vector2) -> void:
	vector = ((pos - size / 2.0) / 53.0).limit_length(1.0)
	if vector.length() < 0.15:
		vector = Vector2.ZERO
	queue_redraw()

func _draw() -> void:
	var center: Vector2 = size / 2.0
	draw_circle(center, 70, Color(0.04, 0.1, 0.11, 0.7))
	draw_arc(center, 70, 0, TAU, 64, Color(0.65, 0.85, 0.77, 0.35), 2, true)
	draw_circle(center + vector * 48, 27, Color(0.44, 0.72, 0.63, 0.7))
	draw_circle(center + vector * 48, 9, Color(0.78, 0.89, 0.75, 0.85))
