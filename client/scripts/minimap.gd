extends Control
## One renderer for the local minimap and zoomable atlas, including the starter river.
signal view_changed
var world_data: Dictionary = {}
var state: Dictionary = {}
var local_id: String = ""
var map_bounds: Rect2 = Rect2(0, 0, 128000, 92160)
var atlas_mode: bool = false
var zoom: float = 1.0
var center: Vector2 = Vector2(-1, -1)
var dragging: bool = false
var drag_start: Vector2
var drag_last: Vector2
var moved: bool = false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP if atlas_mode else Control.MOUSE_FILTER_IGNORE
	focus_mode = Control.FOCUS_NONE
	clip_contents = true

func set_data(world: Dictionary, snapshot: Dictionary, player_id: String) -> void:
	world_data = world
	state = snapshot
	local_id = player_id
	if center.x < 0:
		center = _extent() / 2.0
	queue_redraw()

func _extent() -> Vector2:
	return Vector2(float(world_data.get("width", 128000)), float(world_data.get("height", 92160)))

func _me() -> Dictionary:
	for p: Dictionary in state.get("players", []):
		if str(p.get("id", "")) == local_id:
			return p
	return {}

func _map_size() -> Vector2:
	return Vector2(maxf(1, size.x - 16), maxf(1, size.y - 32))

func _update_bounds() -> void:
	var p: Dictionary = _me()
	var here: Vector2 = Vector2(float(p.get("x", 560)), float(p.get("y", 1180)))
	if not atlas_mode:
		var mini_span: Vector2 = Vector2(2200, 1700) if int(p.get("floor", 0)) != 0 else Vector2(4800, 3400)
		map_bounds = Rect2(here - mini_span / 2.0, mini_span)
		return
	var extent: Vector2 = _extent()
	var aspect: float = _map_size().x / _map_size().y
	var span_x: float = maxf(extent.x, extent.y * aspect) / zoom
	var span: Vector2 = Vector2(span_x, span_x / aspect)
	center.x = extent.x / 2.0 if span.x >= extent.x else clampf(center.x, span.x / 2.0, extent.x - span.x / 2.0)
	center.y = extent.y / 2.0 if span.y >= extent.y else clampf(center.y, span.y / 2.0, extent.y - span.y / 2.0)
	map_bounds = Rect2(center - span / 2.0, span)

func _point(data: Dictionary) -> Vector2:
	return Vector2(8, 24) + (Vector2(float(data.get("x", 0)), float(data.get("y", 0))) - map_bounds.position) / map_bounds.size * _map_size()

func zoom_by(factor: float, uv: Vector2 = Vector2(0.5, 0.5)) -> void:
	_update_bounds()
	var anchor: Vector2 = map_bounds.position + uv * map_bounds.size
	zoom = clampf(zoom * factor, 1.0, 64.0)
	_update_bounds()
	center = anchor + (Vector2(0.5, 0.5) - uv) * map_bounds.size
	_update_bounds()
	view_changed.emit()
	queue_redraw()

func show_all() -> void:
	zoom = 1.0
	center = _extent() / 2.0
	view_changed.emit()
	queue_redraw()

func show_nearby(p: Dictionary) -> void:
	zoom = 32.0
	center = Vector2(float(p.get("x", 560)), float(p.get("y", 1180)))
	_update_bounds()
	view_changed.emit()
	queue_redraw()

func _uv(pos: Vector2) -> Vector2:
	return ((pos - Vector2(8, 24)) / _map_size()).clamp(Vector2.ZERO, Vector2.ONE)

func _gui_input(event: InputEvent) -> void:
	if not atlas_mode:
		return
	if event is InputEventMouseButton:
		if event.pressed and event.button_index in [MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			zoom_by(2.0 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 0.5, _uv(event.position))
		elif event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				dragging = true
				moved = false
				drag_start = event.position
				drag_last = event.position
			elif dragging:
				dragging = false
				if not moved:
					zoom_by(2.0, _uv(event.position))
		accept_event()
	elif event is InputEventMouseMotion and dragging:
		if event.position.distance_to(drag_start) < 5 and not moved:
			return
		moved = true
		center -= (event.position - drag_last) / _map_size() * map_bounds.size
		drag_last = event.position
		_update_bounds()
		view_changed.emit()
		queue_redraw()
		accept_event()

func _draw_water() -> void:
	var pixel_scale: Vector2 = _map_size() / map_bounds.size
	var river: Dictionary = world_data.get("river", {})
	if not river.is_empty():
		draw_rect(Rect2(_point(river), Vector2(maxf(1, float(river["w"]) * pixel_scale.x), maxf(1, float(river["h"]) * pixel_scale.y))), Color("559ebc"))
	for r: Dictionary in world_data.get("waterways", []):
		draw_line(_point({"x":r["a"][0], "y":r["a"][1]}), _point({"x":r["b"][0], "y":r["b"][1]}), Color("559ebc"), maxf(1.5, float(r.get("width", 24)) * pixel_scale.x))
	if not river.is_empty():
		draw_rect(Rect2(_point({"x":river["x"], "y":river["bridge_y"]}), Vector2(maxf(1, float(river["w"]) * pixel_scale.x), maxf(1, float(river["bridge_h"]) * pixel_scale.y))), Color("e3c388"))
	for bridge: Dictionary in world_data.get("bridges", []):
		draw_line(_point({"x":bridge["a"][0], "y":bridge["a"][1]}), _point({"x":bridge["b"][0], "y":bridge["b"][1]}), Color("e3c388"), maxf(2, float(bridge.get("width", 64)) * pixel_scale.x))

func _draw() -> void:
	_update_bounds()
	draw_style_box(_panel(), Rect2(Vector2.ZERO, size))
	var me: Dictionary = _me()
	var floor_id: int = int(me.get("floor", 0))
	var map_rect: Rect2 = Rect2(Vector2(8, 24), _map_size())
	draw_rect(map_rect, Color("303039") if floor_id != 0 else Color("446446"))
	if floor_id == 0:
		for region: Dictionary in world_data.get("regions", []):
			var extent: Vector2 = Vector2(float(region["w"]), float(region["h"])) / map_bounds.size * map_rect.size
			draw_rect(Rect2(_point(region), extent), Color(str(region["color"])))
		for road: Array in world_data.get("roads", []):
			for i in range(1, road.size()):
				draw_line(_point({"x":road[i-1][0], "y":road[i-1][1]}), _point({"x":road[i][0], "y":road[i][1]}), Color("d5bd85"), maxf(1, 64 * map_rect.size.x / map_bounds.size.x))
		_draw_water()
		for city: Dictionary in world_data.get("cities", []):
			draw_circle(_point(city), 3.5, Color("ffe8a1"))
			if atlas_mode:
				draw_string(ThemeDB.fallback_font, _point(city) + Vector2(4, -7), str(city["name"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("ffe8a1"))
	else:
		for area: Dictionary in world_data.get("dungeons", []) + world_data.get("elevations", []):
			if int(area["floor"]) != floor_id:
				continue
			for room: Dictionary in area["rooms"]:
				var rect: Rect2 = Rect2(room["x"], room["y"], room["w"], room["h"])
				if map_bounds.intersects(rect):
					draw_rect(Rect2(_point(room), rect.size / map_bounds.size * map_rect.size), Color("b6afa0"))
	for stair: Dictionary in world_data.get("stairs", []):
		if int(stair["floor"]) == floor_id and map_bounds.has_point(Vector2(stair["x"], stair["y"])):
			var p: Vector2 = _point(stair)
			draw_colored_polygon(PackedVector2Array([p+Vector2(0,-4),p+Vector2(4,0),p+Vector2(0,4),p+Vector2(-4,0)]), Color("ddbbef"))
	for site: Dictionary in world_data.get("pois", []):
		if int(site["floor"]) == floor_id and map_bounds.has_point(Vector2(site["x"], site["y"])):
			draw_circle(_point(site), 2.5, Color("ffd86b"))
	for candidate: Dictionary in state.get("players", []):
		if int(candidate.get("floor", 0)) == floor_id and map_bounds.has_point(Vector2(candidate["x"], candidate["y"])):
			var mine: bool = str(candidate.get("id", "")) == local_id
			draw_circle(_point(candidate), 3.5 if mine else 2.0, Color("ffffff") if mine else Color("96e6ee"))
	if not me.is_empty():
		draw_arc(_point(me), 5.5, 0, TAU, 16, Color("173c37"), 1.5)
	draw_rect(Rect2(0, 0, size.x, 23), Color("172c32"))
	var title: String = "ATLAS · %d×" % int(zoom) if atlas_mode else "OKOLICA"
	if floor_id != 0:
		title += " · PIĘTRO %d" % floor_id
	draw_string(ThemeDB.fallback_font, Vector2(10, 17), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("f1d792"))

func _panel() -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.09, 0.1, 0.94)
	style.border_color = Color("b09563")
	style.set_border_width_all(1)
	style.set_corner_radius_all(5)
	return style
