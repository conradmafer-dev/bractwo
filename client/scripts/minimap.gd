extends Control
## Compact metadata-driven atlas. Amber diamonds are discoveries; yellow dots are NPCs.
var world_data: Dictionary = {}
var state: Dictionary = {}
var local_id: String = ""
var map_bounds: Rect2 = Rect2(0, 0, 128000, 92160)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func set_data(world: Dictionary, snapshot: Dictionary, player_id: String) -> void:
	world_data = world
	state = snapshot
	local_id = player_id
	queue_redraw()

func _point(data: Dictionary) -> Vector2:
	return Vector2(8, 24) + (Vector2(float(data.get("x", 0)), float(data.get("y", 0))) - map_bounds.position) / map_bounds.size * (size - Vector2(16, 32))

func _draw() -> void:
	clip_contents = true
	draw_style_box(_panel(), Rect2(Vector2.ZERO, size))
	var me: Dictionary = {}
	for candidate: Dictionary in state.get("players", []):
		if str(candidate.get("id", "")) == local_id:
			me = candidate
	var floor_id: int = int(me.get("floor", 0))
	map_bounds = Rect2(0, 0, float(world_data.get("width", 128000)), float(world_data.get("height", 92160)))
	if floor_id != 0:
		map_bounds = Rect2(Vector2(float(me.get("x", 0)), float(me.get("y", 0))) - Vector2(1100, 850), Vector2(2200, 1700))
	var map_rect: Rect2 = Rect2(Vector2(8, 24), size - Vector2(16, 32))
	draw_rect(map_rect, Color("303039") if floor_id < 0 else Color("6e9c42"))
	if floor_id == 0:
		for region: Dictionary in world_data.get("regions", []):
			var extent: Vector2 = Vector2(float(region["w"]), float(region["h"])) / map_bounds.size * map_rect.size
			draw_rect(Rect2(_point(region), extent), Color(str(region["color"])))
		for river: Dictionary in world_data.get("waterways", []):
			draw_line(_point({"x":river["a"][0],"y":river["a"][1]}), _point({"x":river["b"][0],"y":river["b"][1]}), Color("67b4c7"), 1.5)
		for city: Dictionary in world_data.get("cities", []):
			draw_circle(_point(city), 3.5, Color("ffe8a1"))
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
	var title: String = "KONTYNENT · K: ATLAS" if floor_id == 0 else "PIĘTRO %s%d · K: ATLAS" % ["+" if floor_id > 0 else "", floor_id]
	draw_string(ThemeDB.fallback_font, Vector2(10, 17), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("f1d792"))

func _panel() -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.09, 0.1, 0.94)
	style.border_color = Color("b09563")
	style.set_border_width_all(1)
	style.set_corner_radius_all(5)
	return style
