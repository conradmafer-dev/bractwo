extends Node2D
## 0.4: continent size comes from server metadata; draw only the camera vicinity.
## Collision and interactions remain server-authoritative; art never sends positions.

var snapshot: Dictionary = {}
var world_data: Dictionary = {}
var local_id: String = ""
var selected_target: String = ""
var selected_enemy: String = ""
var _static_index = preload("res://scripts/spatial_index.gd").new()
var _surface_map = preload("res://scripts/surface_map.gd").new()
var _mills: Array = []
var _samples: Dictionary = {}
var _local: Dictionary = {}
var _terrain_chunks: Dictionary = {}
var _terrain_stamp: String = ""
var _region_rects: Array = []
var _room_rects: Dictionary = {}
var _road_shapes: Array = []
var _positions: Dictionary = {}
var _camera: Camera2D
var _ground: GroundLayer
var _clock: float = 0.0
var _ground_cell: Vector3i = Vector3i(-999, -999, -999)
var _font: Font
var _last_flags: Dictionary = {}
var _server_time: float = 0.0
var _effects: Dictionary = {}

const INK: Color = Color("172c32")
const GOLD: Color = Color("e8c87e")
const TEAL: Color = Color("79c8c0")
const WARM: Color = Color("dfd2ac")

class TerrainLayer:
	extends Node2D
	var renderer: Node2D
	var area: Rect2
	var floor_id: int
	func _draw() -> void:
		renderer._draw_terrain(self, area, floor_id)

class GroundLayer:
	extends Node2D
	var renderer: Node2D
	func _draw() -> void:
		if is_instance_valid(renderer):
			renderer._draw_ground(self)

func _ready() -> void:
	_font = ThemeDB.fallback_font
	_ground = GroundLayer.new()
	_ground.renderer = self
	_ground.z_index = -9
	add_child(_ground)
	_camera = Camera2D.new()
	_camera.position = Vector2(560, 1180)
	_camera.zoom = Vector2.ONE
	_camera.limit_left = 0
	_camera.limit_top = 0
	_camera.limit_right = 3200
	_camera.limit_bottom = 2304
	_camera.position_smoothing_enabled = false
	add_child(_camera)
	queue_redraw()

func set_world(data: Dictionary) -> void:
	world_data = data
	_static_index.build(data)
	_surface_map.build(data)
	_mills = data.get("obstacles", []).filter(func(o: Dictionary) -> bool: return o.get("type", "") == "mill")
	_region_rects.clear()
	_room_rects.clear()
	_road_shapes.clear()
	for chunk: Node2D in _terrain_chunks.values():
		chunk.queue_free()
	_terrain_chunks.clear()
	_terrain_stamp = ""
	for region: Dictionary in data.get("regions", []):
		_region_rects.append({"rect":Rect2(region["x"], region["y"], region["w"], region["h"]), "color":Color(str(region["color"]))})
	for dungeon: Dictionary in data.get("dungeons", []) + data.get("elevations", []):
		var floor_id: int = int(dungeon["floor"])
		if not _room_rects.has(floor_id):
			_room_rects[floor_id] = []
		for room: Dictionary in dungeon["rooms"]:
			_room_rects[floor_id].append(Rect2(room["x"], room["y"], room["w"], room["h"]))
	for road: Array in data.get("roads", []):
		var points: PackedVector2Array = PackedVector2Array()
		var bounds: Rect2 = Rect2(Vector2(road[0][0], road[0][1]), Vector2.ZERO)
		for point: Array in road:
			var pos: Vector2 = Vector2(point[0], point[1])
			points.append(pos)
			bounds = bounds.expand(pos)
		_road_shapes.append({"points":points, "bounds":bounds.grow(80)})
	if is_instance_valid(_camera):
		_camera.limit_right = int(data.get("width", 3200))
		_camera.limit_bottom = int(data.get("height", 2304))
	if is_instance_valid(_ground):
		_ground.queue_redraw()

func set_state(data: Dictionary) -> void:
	snapshot = data
	_local = {}
	for entry: Dictionary in data.get("players", []):
		if str(entry.get("id", "")) == local_id:
			_local = entry
	_server_time = float(data.get("time", 0))
	if data.is_empty():
		_effects.clear()
		_samples.clear()
	for effect: Dictionary in data.get("effects", []):
		var id: String = str(effect.get("id", ""))
		if not _effects.has(id) and _server_time < float(effect.get("time", 0)) + float(effect.get("duration", 0.32)):
			_effects[id] = effect.duplicate(true)
	var flags: Dictionary = snapshot.get("world", {})
	if flags != _last_flags:
		_last_flags = flags.duplicate()
		if is_instance_valid(_ground):
			_ground.queue_redraw()
	var active: Dictionary = {}
	for group: String in ["players", "enemies"]:
		for entry: Dictionary in snapshot.get(group, []):
			var key: String = group + ":" + str(entry.get("id", ""))
			active[key] = true
			var point: Vector2 = Vector2(float(entry["x"]), float(entry["y"]))
			var history: Array = _samples.get(key, [])
			var floor_id: int = int(entry.get("floor", 0))
			if not history.is_empty() and (int(history.back()["floor"]) != floor_id or point.distance_to(history.back()["point"]) > 450):
				history.clear()
			history.append({"point":point, "time":_server_time, "floor":floor_id})
			if history.size() > 6:
				history.pop_front()
			_samples[key] = history
			if not _positions.has(key):
				_positions[key] = Vector2(float(entry.get("x", 560)), float(entry.get("y", 1180)))
	for key: String in _positions.keys():
		if not active.has(key):
			_positions.erase(key)
			_samples.erase(key)
	queue_redraw()

func get_local_position() -> Vector2:
	var key: String = "players:" + local_id
	if _positions.has(key):
		return _positions[key]
	for player: Dictionary in snapshot.get("players", []):
		if str(player.get("id", "")) == local_id:
			return Vector2(float(player.get("x", 560)), float(player.get("y", 1180)))
	return Vector2(560, 1180)

func _process(delta: float) -> void:
	_clock += delta
	_server_time += delta
	for id: String in _effects.keys():
		var effect: Dictionary = _effects[id]
		if _server_time > float(effect.get("time", 0)) + float(effect.get("duration", 0.32)):
			_effects.erase(id)
	for key: String in _samples:
		var history: Array = _samples[key]
		var a: Dictionary = history[0]
		var b: Dictionary = a
		for i: int in range(1, history.size()):
			b = history[i]
			if float(b["time"]) >= _server_time - 0.1:
				break
			a = b
		var amount: float = clampf((_server_time - 0.1 - float(a["time"])) / maxf(0.001, float(b["time"]) - float(a["time"])), 0, 1)
		_positions[key] = (a["point"] as Vector2).lerp(b["point"], amount)
	if is_instance_valid(_camera):
		_camera.position = get_local_position()
		_camera.force_update_scroll()
		_update_terrain_cache()
		var cell: Vector3i = Vector3i(int(_camera.position.x / 128), int(_camera.position.y / 128), int(_local_player().get("floor", 0)))
		if cell != _ground_cell:
			_ground_cell = cell
			_ground.queue_redraw()
	queue_redraw()

func _update_terrain_cache() -> void:
	var center: Vector2 = _camera.get_screen_center_position()
	var extent: Vector2 = get_viewport_rect().size / _camera.zoom * 0.5 + Vector2(160, 160)
	var floor_id: int = int(_local.get("floor", 0))
	var start: Vector2i = Vector2i(floori((center.x - extent.x) / 768), floori((center.y - extent.y) / 768))
	var finish: Vector2i = Vector2i(floori((center.x + extent.x) / 768), floori((center.y + extent.y) / 768))
	var stamp: String = str(start) + str(finish) + str(floor_id)
	if stamp == _terrain_stamp:
		return
	_terrain_stamp = stamp
	var required: Dictionary = {}
	for x: int in range(start.x, finish.x + 1):
		for y: int in range(start.y, finish.y + 1):
			var key: Vector3i = Vector3i(x, y, floor_id)
			required[key] = true
			if not _terrain_chunks.has(key):
				var chunk: TerrainLayer = TerrainLayer.new()
				chunk.renderer = self
				chunk.area = Rect2(x * 768, y * 768, 768, 768)
				chunk.floor_id = floor_id
				chunk.z_index = -10
				add_child(chunk)
				_terrain_chunks[key] = chunk
			_terrain_chunks[key].show()
	for key: Vector3i in _terrain_chunks.keys():
		if not required.has(key):
			_terrain_chunks[key].hide()
			if key.z != floor_id or _terrain_chunks.size() > maxi(24, required.size() + 8):
				_terrain_chunks[key].queue_free()
				_terrain_chunks.erase(key)

func _draw_terrain(c: Node2D, view: Rect2, floor_id: int) -> void:
	var rooms: Array = _room_rects.get(floor_id, [])
	for yy: int in range(int(view.position.y), int(view.end.y), 48):
		for xx: int in range(int(view.position.x), int(view.end.x), 48):
			var point: Vector2 = Vector2(xx, yy)
			var color: Color = _ground_color(point)
			var surface: String = _surface_map.at(point + Vector2(24, 24), mini(floor_id, 0))
			if surface not in ["grass", "path"] and (point.x > 3200 or point.y > 2304):
				color = Color(str(world_data.get("surfaces", {}).get(surface, {}).get("color", "#7dab4f")))
			if floor_id != 0:
				if floor_id < 0:
					color = Color("303039")
				for room: Rect2 in rooms:
					if room.has_point(point + Vector2(24, 24)):
						color = Color("b6afa0") if floor_id > 0 else Color("8e8272")
						surface = "stone"
			var noise: float = float(posmod(xx * 71 + yy * 93, 13)) / 260.0
			c.draw_rect(Rect2(point, Vector2(48, 48)), color.lightened(noise))
			c.draw_line(point + Vector2(4, 46), point + Vector2(43, 46), color.darkened(0.09), 1)
			if surface == "mud" and floor_id == 0:
				c.draw_arc(point + Vector2(22, 23), 13, 0, PI, 12, Color("6e6453"), 4)
			elif surface == "stone":
				c.draw_line(point + Vector2(3, 4), point + Vector2(42, 4), Color("c3c1a8"), 1)

func pick_actor(screen: Vector2) -> Dictionary:
	var point: Vector2 = get_canvas_transform().affine_inverse() * screen
	var best: float = INF
	var result: Dictionary = {}
	for group: String in ["enemies", "players"]:
		for entry: Dictionary in snapshot.get(group, []):
			var id: String = str(entry.get("id", ""))
			if float(entry.get("hp", 0)) <= 0 or int(entry.get("floor", 0)) != int(_local.get("floor", 0)) or (group == "players" and id == local_id):
				continue
			var pos: Vector2 = _positions.get(group + ":" + id, Vector2(entry["x"], entry["y"]))
			var species_scale: float = float(entry.get("size", 1))
			var size: float = 40.0 * species_scale
			var distance: float = point.distance_to(pos + Vector2(0, -27 * species_scale))
			if distance < size and distance < best:
				best = distance
				result = {"kind":group, "id":id}
	return result

func _draw_ground(c: Node2D) -> void:
	var center: Vector2 = get_local_position()
	var floor_id: int = int(_local_player().get("floor", 0))
	var view: Rect2 = Rect2(center - Vector2(1250, 900), Vector2(2500, 1800))
	if floor_id == 0:
		for road: Dictionary in _road_shapes:
			if view.intersects(road["bounds"]):
				_path(c, road["points"], 64, Color("ad986e"), Color("c6b283"))
		for city: Dictionary in world_data.get("cities", []):
			var pos: Vector2 = Vector2(city["x"], city["y"])
			if view.has_point(pos):
				c.draw_circle(pos, 205, Color("b3ab87"))
		_draw_waterways(c, view)
		c.draw_rect(Rect2(1500, 0, 180, 2304), Color("3295c7"))
		_bridge(c)
	if floor_id > 0:
		for area: Dictionary in _static_index.query("elevations", view, floor_id):
			_draw_cliff(c, Rect2(area["x"], area["y"], area["w"], area["h"]), true)
	for item: Dictionary in _static_index.query("obstacles", view, floor_id):
		if int(item.get("floor", 0)) != floor_id:
			continue
		var rect: Rect2 = Rect2(item["x"], item["y"], item["w"], item["h"])
		if not view.intersects(rect):
			continue
		if item.get("type", "") in ["house", "mill"]:
			_house(c, rect.get_center(), rect.size, Color("a56f52"), 0)
		elif item.get("type", "") in ["terrace", "canyon"]:
			_draw_cliff(c, rect)
		elif item.get("type", "") == "mountain":
			_draw_mountain(c, rect)
		elif item.get("type", "") == "grove":
			c.draw_rect(rect, Color("416b3c"))
			_tree(c, rect.get_center(), 1.0, 0)
		else:
			_obstacle(c, rect)
	for landmark: Dictionary in _static_index.query("landmarks", view, floor_id):
		if int(landmark.get("floor", 0)) == floor_id and view.has_point(Vector2(landmark["x"], landmark["y"])):
			_draw_landmark(c, landmark)
	for stair: Dictionary in _static_index.query("stairs", view, floor_id):
		var pos: Vector2 = Vector2(stair["x"], stair["y"])
		if int(stair["floor"]) != floor_id or not view.has_point(pos):
			continue
		c.draw_rect(Rect2(pos - Vector2(26, 19), Vector2(52, 42)), Color("292934"))
		for step: int in range(5):
			c.draw_rect(Rect2(pos + Vector2(-22 + step * 3, -15 + step * 7), Vector2(44 - step * 6, 5)), Color("ccb78f"))
		_map_label(c, pos + Vector2(0, -33), "E · %s%d · " % ["+" if int(stair["to_floor"]) > 0 else "", int(stair["to_floor"])] + str(stair["name"]), Color("e7c6f5"))
	for camp: Dictionary in _static_index.query("hunting_grounds", view, floor_id):
		var pos: Vector2 = Vector2(camp["x"], camp["y"])
		if floor_id == 0 and view.has_point(pos):
			_draw_habitat(c, camp)

func _ground_color(p: Vector2) -> Color:
	if p.x > 3200 or p.y > 2304:
		for region: Dictionary in _region_rects:
			if region["rect"].has_point(p):
				return region["color"]
	if p.x > 2240 and p.y > 1430:
		return Color("9a9878")
	if p.x > 2080 and p.y < 1050:
		return Color("acac78")
	if p.x > 1710 and p.x < 2180 and p.y > 1390:
		return Color("648d53")
	if p.x > 1120 and p.x < 1470 and p.y < 610:
		return Color("b39858")
	if p.x < 1410 and p.y < 900:
		return Color("528f3e")
	return Color("83b747")

func _draw_landmark(c: Node2D, landmark: Dictionary) -> void:
	if str(landmark.get("id", "")).begins_with("habitat_"):
		return
	var p: Vector2 = Vector2(float(landmark.get("x",0)),float(landmark.get("y",0)))
	if landmark.has("action"):
		_draw_site(c, landmark, p)
		return
	var biome: String = str(landmark.get("biome",""))
	c.draw_arc(p,58,0,TAU,32,Color(0.92,0.85,0.48,0.45),2)
	# Floor mosaics/ruined foundations mark discoveries without pretending to block.
	if landmark.get("decoration", "") == "sign":
		c.draw_rect(Rect2(p+Vector2(-3,-57),Vector2(6,62)),Color("77573a"))
		c.draw_rect(Rect2(p+Vector2(-43,-57),Vector2(86,17)),Color("c4a26c"))
		_map_label(c,p+Vector2(0,-63),"SZLAKI · K / Atlas",GOLD)
	elif biome == "meadow":
		c.draw_rect(Rect2(p-Vector2(44,35),Vector2(88,70)),Color("cbbb89"))
		for i: int in range(4):
			c.draw_line(p+Vector2(-38,-28+i*18),p+Vector2(38,-28+i*18),Color("8d9770"),2)
		c.draw_arc(p,26,0,TAU,20,Color("986b3f"),6)
		for i: int in range(8):
			c.draw_line(p,p+Vector2.from_angle(i*TAU/8)*25,Color("986b3f"),3)
	elif biome == "goblin_camp":
		for i: int in range(5):
			var q: Vector2 = p + Vector2.from_angle(i*TAU/5)*70
			c.draw_colored_polygon(PackedVector2Array([q+Vector2(-20,12),q+Vector2(4,-11),q+Vector2(24,9),q+Vector2(-2,23)]),Color("b77249"))
			c.draw_line(q+Vector2(-18,11),q+Vector2(22,10),Color("e2b477"),2)
		c.draw_circle(p,18,Color("665846"))
		c.draw_line(p+Vector2(-13,-6),p+Vector2(13,6),Color("c98a47"),5)
		c.draw_line(p+Vector2(-12,7),p+Vector2(11,-8),Color("cb9655"),5)
	elif biome == "swamp":
		c.draw_circle(p,35,Color("989d85"))
		c.draw_circle(p,26,Color("609885"))
		c.draw_arc(p,22,0,TAU,12,Color("afd7bb"),3)
		for i: int in range(6):
			c.draw_circle(p+Vector2.from_angle(i*TAU/6)*40,4,Color("ceb3e5"))
	elif biome == "ruins" or biome == "sanctuary":
		c.draw_rect(Rect2(p-Vector2(46,38),Vector2(92,76)),Color("c4baa0"))
		for i: int in range(5):
			c.draw_line(p+Vector2(-44,-32+i*16),p+Vector2(44,-32+i*16),Color("9d997f"),2)
		c.draw_arc(p,29,0,TAU,8,Color("7b907e"),4)
		c.draw_line(p+Vector2(-19,-19),p+Vector2(19,19),Color("ded293"),3)
		c.draw_line(p+Vector2(19,-19),p+Vector2(-19,19),Color("ded293"),3)
	else:
		c.draw_circle(p,23,Color("ceb981"))
		c.draw_arc(p,18,0,TAU,12,Color("b39764"),3)
	_map_label(c,p+Vector2(0,91),str(landmark.get("name","Odkrycie")),Color("fff0b3"))

func _path(c: Node2D, points: PackedVector2Array, width: float, edge: Color, fill: Color) -> void:
	c.draw_polyline(points, edge, width + 16, true)
	c.draw_polyline(points, fill, width, true)
	for point: Vector2 in points:
		c.draw_circle(point, width * 0.5 + 7, edge)
		c.draw_circle(point, width * 0.5, fill)
	c.draw_polyline(points, fill, width, true)

func _tree(c: Node2D, p: Vector2, s: float, variant: int) -> void:
	c.draw_set_transform(p, 0, Vector2(s, s))
	c.draw_set_transform(p + Vector2(6, 7), 0, Vector2(s, s * 0.45))
	c.draw_circle(Vector2.ZERO, 40, Color(0.04, 0.11, 0.13, 0.38))
	c.draw_set_transform(p, 0, Vector2(s, s))
	c.draw_colored_polygon(PackedVector2Array([Vector2(-8, 6), Vector2(-5, -50), Vector2(5, -50), Vector2(10, 6)]), Color("514b3d"))
	c.draw_line(Vector2(-1, 2), Vector2(0, -46), Color("827056"), 3, true)
	var base: Color = [Color("306e2e"), Color("377e36"), Color("4c8233")][variant]
	var top: Color = [Color("65a947"), Color("77b649"), Color("93b958")][variant]
	for i: int in range(3):
		var y: float = -float(i) * 23.0
		var w: float = 41.0 - float(i) * 8.0
		c.draw_colored_polygon(PackedVector2Array([Vector2(-w, y - 12), Vector2(-w * 0.45, y - 43), Vector2(0, y - 73), Vector2(w * 0.55, y - 41), Vector2(w, y - 12), Vector2(10, y - 17), Vector2(-4, y - 7)]), base)
		c.draw_colored_polygon(PackedVector2Array([Vector2(-w, y - 12), Vector2(0, y - 73), Vector2(-4, y - 25)]), top)
	c.draw_set_transform(Vector2.ZERO)

func _house(c: Node2D, p: Vector2, size: Vector2, roof: Color, variant: int) -> void:
	var rect: Rect2 = Rect2(p - size * 0.5, size)
	c.draw_rect(Rect2(rect.position + Vector2(9, 14), size + Vector2(5, 2)), Color(0.03, 0.1, 0.11, 0.35))
	c.draw_rect(rect, Color("b6a484"))
	c.draw_rect(Rect2(rect.position + Vector2(0, size.y - 23), Vector2(size.x, 23)), Color("82785e"))
	c.draw_rect(Rect2(p + Vector2(-14, size.y * 0.5 - 33), Vector2(28, 33)), Color("33423e"))
	c.draw_rect(Rect2(p + Vector2(-10, size.y * 0.5 - 28), Vector2(20, 26)), Color("785e42"))
	for x: float in [-size.x * 0.31, size.x * 0.31]:
		c.draw_rect(Rect2(p + Vector2(x - 10, size.y * 0.5 - 34), Vector2(20, 17)), Color("455951"))
		c.draw_rect(Rect2(p + Vector2(x - 7, size.y * 0.5 - 31), Vector2(14, 11)), Color("e4bd6b"))
		c.draw_line(p + Vector2(x, size.y * 0.5 - 32), p + Vector2(x, size.y * 0.5 - 20), Color("705b42"), 2)
	var left: float = rect.position.x - 10
	var right: float = rect.end.x + 10
	var mid: float = p.y - size.y * 0.39
	var bottom: float = p.y + size.y * 0.22
	c.draw_colored_polygon(PackedVector2Array([Vector2(left, bottom), Vector2(p.x, mid - 42), Vector2(right, bottom)]), roof.darkened(0.14))
	c.draw_colored_polygon(PackedVector2Array([Vector2(left, bottom), Vector2(left + 5, mid - 5), Vector2(p.x, mid - 42), Vector2(p.x, bottom)]), roof.lightened(0.06))
	c.draw_colored_polygon(PackedVector2Array([Vector2(p.x, mid - 42), Vector2(right - 5, mid - 5), Vector2(right, bottom), Vector2(p.x, bottom)]), roof)
	c.draw_line(Vector2(p.x, mid - 42), Vector2(p.x, bottom), roof.lightened(0.26), 3, true)
	for i: int in range(4):
		var y: float = mid + float(i) * 15.0
		c.draw_line(Vector2(left + 4, y), Vector2(p.x - 2, y - 23), roof.lightened(0.14), 1.5, true)
		c.draw_line(Vector2(p.x + 3, y - 23), Vector2(right - 4, y), roof.darkened(0.18), 1.5, true)
	c.draw_rect(Rect2(p + Vector2(size.x * 0.25, -size.y * 0.5 - 18), Vector2(19, 34)), Color("86857a"))
	c.draw_rect(Rect2(p + Vector2(size.x * 0.25 - 3, -size.y * 0.5 - 20), Vector2(25, 7)), Color("a8a18b"))
	if variant == 1:
		c.draw_line(p + Vector2(size.x * 0.5 + 8, 20), p + Vector2(size.x * 0.5 + 8, 70), Color("5e4c3a"), 4)
		c.draw_rect(Rect2(p + Vector2(size.x * 0.5 - 10, 32), Vector2(38, 22)), Color("344f52"))
		c.draw_circle(p + Vector2(size.x * 0.5 + 9, 43), 6, GOLD)
	if variant == 2:
		c.draw_circle(p + Vector2(size.x * 0.5 + 25, 30), 17, Color("846a43"))
		c.draw_circle(p + Vector2(size.x * 0.5 + 25, 30), 13, Color("b09463"))

func _well(c: Node2D, p: Vector2) -> void:
	c.draw_circle(p + Vector2(4, 6), 34, Color(0.06, 0.15, 0.16, 0.4))
	c.draw_circle(p, 29, Color("87948a"))
	c.draw_circle(p, 20, Color("35464b"))
	c.draw_circle(p, 15, Color("41727a"))
	c.draw_arc(p, 25, 0, TAU, 16, Color("bdbea5"), 5, true)
	for x: float in [-26.0, 26.0]:
		c.draw_line(p + Vector2(x, 2), p + Vector2(x, -44), Color("78664a"), 5)
	c.draw_line(p + Vector2(-32, -43), p + Vector2(32, -43), Color("b7a177"), 6)
	c.draw_line(p + Vector2(0, -43), p + Vector2(0, 3), Color("ccb98c"), 2)

func _lamp(c: Node2D, p: Vector2) -> void:
	c.draw_circle(p + Vector2(0, -31), 26, Color(0.99, 0.72, 0.29, 0.055))
	c.draw_circle(p + Vector2(0, -31), 16, Color(0.99, 0.72, 0.29, 0.09))
	c.draw_line(p, p + Vector2(0, -40), Color("564d39"), 5)
	c.draw_rect(Rect2(p + Vector2(-7, -44), Vector2(14, 17)), Color("3f4d48"))
	c.draw_rect(Rect2(p + Vector2(-4, -41), Vector2(8, 11)), Color("efc276"))
	c.draw_line(p + Vector2(-9, -45), p + Vector2(9, -45), Color("b6a174"), 3)

func _pillar(c: Node2D, p: Vector2) -> void:
	c.draw_circle(p + Vector2(8, 6), 28, Color(0.03, 0.1, 0.14, 0.4))
	c.draw_rect(Rect2(p + Vector2(-24, -11), Vector2(48, 19)), Color("647777"))
	c.draw_rect(Rect2(p + Vector2(-17, -65), Vector2(34, 56)), Color("84928b"))
	c.draw_rect(Rect2(p + Vector2(4, -65), Vector2(13, 56)), Color("617779"))
	c.draw_rect(Rect2(p + Vector2(-23, -71), Vector2(46, 12)), Color("a5afa2"))
	c.draw_line(p + Vector2(-9, -60), p + Vector2(-9, -16), Color("a5afa2"), 3)
	c.draw_line(p + Vector2(4, -54), p + Vector2(-3, -39), Color("445a5e"), 2)

func _obstacle(c: Node2D, rect: Rect2) -> void:
	c.draw_rect(Rect2(rect.position + Vector2(5, 5), rect.size), Color(0.03, 0.1, 0.12, 0.25))
	c.draw_rect(rect, Color("56675f"))
	c.draw_rect(Rect2(rect.position + Vector2(3, 3), rect.size - Vector2(6, 7)), Color("7c8878"))
	c.draw_line(rect.position + Vector2(3, 3), rect.position + Vector2(rect.size.x - 3, 3), Color("a1aa91"), 3)
	var divisions: int = int(maxf(rect.size.x, rect.size.y) / 32)
	for i: int in range(1, divisions):
		if rect.size.x > rect.size.y:
			var x: float = rect.position.x + float(i) * rect.size.x / float(divisions)
			c.draw_line(Vector2(x, rect.position.y + 4), Vector2(x, rect.end.y - 3), Color("586d64"), 2)
		else:
			var y: float = rect.position.y + float(i) * rect.size.y / float(divisions)
			c.draw_line(Vector2(rect.position.x + 3, y), Vector2(rect.end.x - 3, y), Color("586d64"), 2)

func _bridge(c: Node2D) -> void:
	# The permanent walkable crossing is y=1080..1230 in the protocol.
	c.draw_rect(Rect2(1480, 1080, 220, 150), Color("4d6755"))
	for i: int in range(18):
		var x: float = 1484 + i * 12
		c.draw_line(Vector2(x, 1086), Vector2(x, 1224), Color("918972") if i % 2 == 0 else Color("a29b7e"), 9, true)
	for y: float in [1086.0, 1224.0]:
		c.draw_polyline(PackedVector2Array([Vector2(1468, y + 5), Vector2(1530, y - 8), Vector2(1585, y + 1), Vector2(1650, y - 5), Vector2(1710, y + 2)]), Color("4e634c"), 14, true)
		c.draw_polyline(PackedVector2Array([Vector2(1468, y + 2), Vector2(1530, y - 10), Vector2(1585, y - 1), Vector2(1650, y - 7), Vector2(1710, y)]), Color("8ea875"), 4, true)

func _draw_trail_gate(c: Node2D) -> void:
	# Decorative entrance only; the route is permanently open.
	for x: float in [2370.0, 2670.0]:
		_pillar(c, Vector2(x, 1480))
		c.draw_circle(Vector2(x, 1427), 7, Color("ade7e0"))
	for i: int in range(7):
		c.draw_circle(Vector2(2400 + i * 40, 1478), 3, Color("8fb5a7"))

func _map_label(c: Node2D, p: Vector2, value: String, color: Color) -> void:
	var font: Font = ThemeDB.fallback_font
	var width: float = font.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
	c.draw_string(font, p - Vector2(width * 0.5, 0), value, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, color)
	c.draw_line(p + Vector2(-35, 11), p + Vector2(35, 11), Color(color, 0.35), 1, true)

func _draw() -> void:
	if _font == null:
		_font = ThemeDB.fallback_font
	if int(_local_player().get("floor", 0)) == 0:
		_draw_safe_zone()
		_draw_merchant()
	_draw_npcs()
	_draw_mill_blades()
	var actors: Array[Dictionary] = []
	for enemy: Dictionary in snapshot.get("enemies", []):
		if not bool(enemy.get("alive", true)) or float(enemy.get("hp", 1)) <= 0:
			continue
		var key: String = "enemies:" + str(enemy.get("id", ""))
		var p: Vector2 = _positions.get(key, Vector2(float(enemy.get("x", 0)), float(enemy.get("y", 0))))
		actors.append({"type": "enemy", "data": enemy, "p": p})
	for player: Dictionary in snapshot.get("players", []):
		var key: String = "players:" + str(player.get("id", ""))
		var p: Vector2 = _positions.get(key, Vector2(float(player.get("x", 0)), float(player.get("y", 0))))
		actors.append({"type": "player", "data": player, "p": p})
	actors.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a["p"].y < b["p"].y)
	for actor: Dictionary in actors:
		# Avoid submitting offscreen character geometry for large multiplayer snapshots.
		var p: Vector2 = actor["p"]
		if int(actor["data"].get("floor", 0)) != int(_local_player().get("floor", 0)) or p.distance_squared_to(get_local_position()) > 1100 * 1100:
			continue
		if actor["type"] == "player":
			_draw_player(actor["data"], p)
		else:
			_draw_enemy(actor["data"], p)
	_draw_effects()
	for actor: Dictionary in actors:
		if actor["type"] == "player" and int(actor["data"].get("floor", 0)) == int(_local_player().get("floor", 0)):
			_draw_speech(actor["data"], actor["p"])

func _local_player() -> Dictionary:
	return _local

func _draw_safe_zone() -> void:
	for zone: Dictionary in world_data.get("safe_zones", [world_data.get("safe_zone", {"x":560, "y":1180, "radius":260})]):
		var center: Vector2 = Vector2(float(zone.get("x", 560)), float(zone.get("y", 1180)))
		var radius: float = float(zone.get("radius", 260))
		if center.distance_to(get_local_position()) < 1300:
			draw_arc(center, radius, 0, TAU, 80, Color(0.55, 0.87, 0.65, 0.46), 2, true)
			_text_center(center + Vector2(0, radius - 12), str(zone.get("name", "OSADA")) + " · STREFA CHRONIONA", Color("a4d4ae"), 13)

func _draw_merchant() -> void:
	var merchant: Dictionary = world_data.get("merchant", {"x":680, "y":1180, "name":"Kupiec"})
	var p: Vector2 = Vector2(float(merchant.get("x", 680)), float(merchant.get("y", 1180)))
	_shadow(p, Vector2(25, 10))
	draw_rect(Rect2(p + Vector2(-22, -14), Vector2(44, 24)), Color("9c784d"))
	draw_rect(Rect2(p + Vector2(-25, -18), Vector2(50, 8)), Color("c4a066"))
	draw_circle(p + Vector2(0, -39), 9, Color("ddb891"))
	draw_colored_polygon(PackedVector2Array([p + Vector2(-13, -15), p + Vector2(-9, -32), p + Vector2(9, -32), p + Vector2(15, -15)]), Color("a98757"))
	draw_rect(Rect2(p + Vector2(-12, -51), Vector2(24, 6)), Color("6f694d"))
	draw_circle(p + Vector2(-14, -22), 4, Color("cc6761"))
	draw_circle(p + Vector2(13, -22), 4, Color("74afd4"))
	_text_center(p + Vector2(0, -67), str(merchant.get("name", "Kupiec")), GOLD, 13)
	if p.distance_to(get_local_position()) <= float(merchant.get("radius", 150)):
		_text_center(p + Vector2(0, 32), "E · Handel i leczenie", WARM, 12)

func _draw_player(player: Dictionary, p: Vector2) -> void:
	var mine: bool = str(player.get("id", "")) == local_id
	var facing_data: Array = player.get("facing", [0, 1])
	var facing: Vector2 = Vector2(float(facing_data[0]), float(facing_data[1])) if facing_data.size() >= 2 else Vector2.DOWN
	var bob: float = sin(_clock * 5 + float(str(player.get("id", "1")).hash() % 100)) * 0.6
	var robe: Color = _class_color(str(player.get("class_id", "knight")))
	if bool(player.get("disconnected", false)):
		robe = robe.darkened(0.35)
	_shadow(p, Vector2(18, 8))
	if mine:
		draw_arc(p + Vector2(0, 1), 22, 0, TAU, 32, Color(0.45, 0.87, 0.84, 0.72), 1.7, true)
	if str(player.get("id", "")) == selected_target:
		draw_arc(p + Vector2(0, 1), 27, 0, TAU, 32, Color("e98a77"), 3, true)
	var own: Dictionary = _local_player()
	if not str(own.get("party_id", "")).is_empty() and own.get("party_id", "") == player.get("party_id", ""):
		draw_circle(p + Vector2(-26, -12), 4, Color("84c7ed"))
	var o: Vector2 = p + Vector2(0, bob)
	# Layered cape, boots, tunic, shoulder highlights and hood create a compact sprite.
	draw_colored_polygon(PackedVector2Array([o + Vector2(-10, -31), o + Vector2(9, -31), o + Vector2(19, -1), o + Vector2(4, 4), o + Vector2(-18, 0)]), robe.darkened(0.43))
	draw_line(o + Vector2(-6, -3), o + Vector2(-7, 3), Color("263c3d"), 7)
	draw_line(o + Vector2(6, -3), o + Vector2(8, 3), Color("263c3d"), 7)
	draw_colored_polygon(PackedVector2Array([o + Vector2(-10, -30), o + Vector2(9, -30), o + Vector2(12, -6), o + Vector2(-12, -6)]), robe)
	draw_colored_polygon(PackedVector2Array([o + Vector2(-10, -30), o + Vector2(-2, -30), o + Vector2(-2, -6), o + Vector2(-12, -6)]), robe.lightened(0.18))
	draw_line(o + Vector2(-11, -13), o + Vector2(10, -13), Color("c8ab74"), 3)
	draw_circle(o + Vector2(0, -36), 12, robe.darkened(0.32))
	draw_arc(o + Vector2(0, -35), 11, PI, TAU, 16, robe.lightened(0.34), 3, true)
	if facing.y >= -0.2:
		draw_circle(o + Vector2(0, -34), 7, Color("d7b88e"))
		draw_arc(o + Vector2(0, -35), 9, PI, TAU, 12, robe, 5, true)
		draw_line(o + Vector2(-4, -34), o + Vector2(-2, -34), INK, 1.5)
		draw_line(o + Vector2(3, -34), o + Vector2(5, -34), INK, 1.5)
	else:
		draw_line(o + Vector2(0, -43), o + Vector2(0, -29), robe.lightened(0.1), 2)
	draw_line(o + Vector2(-10, -26), o + Vector2(-15, -17), robe.lightened(0.1), 7, true)
	draw_circle(o + Vector2(-15, -16), 4, Color("d7b88e"))
	draw_line(o + Vector2(9, -25), o + Vector2(16, -19), robe.darkened(0.1), 7, true)
	draw_circle(o + Vector2(16, -18), 4, Color("d7b88e"))
	var attacking: bool = float(player.get("attack_until", 0)) > float(snapshot.get("time", 0))
	if str(player.get("weapon", "sword")) == "staff":
		draw_line(o + Vector2(19, 1), o + Vector2(22, -40), Color("8e7550"), 4, true)
		draw_circle(o + Vector2(22, -42), 9, Color(0.48, 0.81, 0.86, 0.12))
		draw_circle(o + Vector2(22, -42), 5, Color("b7e2dc"))
	elif str(player.get("weapon", "sword")) == "bow":
		draw_arc(o + Vector2(16, -25), 19, -PI * 0.5, PI * 0.5, 20, Color("c49e62"), 3, true)
		draw_line(o + Vector2(16, -44), o + Vector2(16, -6), Color("e4d6ad"), 1.5, true)
		draw_line(o + Vector2(10, -25), o + Vector2(40, -25), Color("e1d1a8"), 2, true)
	else:
		draw_line(o + Vector2(17, -12), o + Vector2(30, -38), Color("273d42"), 7, true)
		draw_line(o + Vector2(18, -13), o + Vector2(30, -38), Color("d5e5dc"), 4, true)
		draw_line(o + Vector2(13, -19), o + Vector2(24, -14), GOLD, 3, true)
		if attacking:
			var aim_data: Array = player.get("attack_facing", [facing.x, facing.y])
			var angle: float = Vector2(float(aim_data[0]), float(aim_data[1])).angle()
			draw_arc(p + Vector2(0, -13), 48, angle - 0.8, angle + 0.8, 18, Color(0.87, 0.93, 0.77, 0.9), 5, true)
			draw_arc(p + Vector2(0, -13), 54, angle - 0.5, angle + 0.6, 16, Color(0.87, 0.93, 0.77, 0.3), 2, true)
	var name_text: String = str(player.get("name", "Wędrowiec")) + " · " + str(int(player.get("level", 1)))
	if bool(player.get("disconnected", false)):
		name_text += " [offline]"
	var skull: String = str(player.get("skull", "none"))
	var name_color: Color = Color("ed907c") if skull == "red" else (Color("ffffff") if skull == "white" else Color("d8f2e7"))
	_text_center(p + Vector2(0, -64), name_text, name_color, 13)
	if skull != "none":
		var skull_p: Vector2 = p + Vector2(0, -87)
		draw_circle(skull_p, 6, name_color)
		draw_rect(Rect2(skull_p + Vector2(-4, 3), Vector2(8, 5)), name_color)
		draw_circle(skull_p + Vector2(-2, 0), 1.5, INK)
		draw_circle(skull_p + Vector2(2, 0), 1.5, INK)
	_health_bar(p + Vector2(0, -56), 44, float(player.get("hp", 1)), float(player.get("max_hp", 1)), Color("7bbc9a"))

func _draw_enemy(enemy: Dictionary, p: Vector2) -> void:
	var size: float = float(enemy.get("size", 1))
	if str(enemy.get("id", "")) == selected_enemy:
		draw_rect(Rect2(p + Vector2(-30, -62) * size, Vector2(60, 70) * size), Color("f05942"), false, 2)
	var spec: Dictionary = world_data.get("enemy_types", {}).get(str(enemy.get("kind", "wolf")), {})
	var kind: String = str(spec.get("appearance", enemy.get("kind", "wolf")))
	if kind in ["bear", "harpy", "cyclops", "ghoul", "scorpion"]:
		_draw_wild_enemy(enemy, p, spec)
		return
	if kind in ["dragon", "demon"]:
		_draw_winged_enemy(enemy, p, spec)
		return
	var scale_factor: float = float(spec.get("size", 1))
	_shadow(p, Vector2(23, 9) * scale_factor)
	if kind == "rat" or kind == "boar":
		var rat: bool = kind == "rat"
		var scale_value: float = (0.7 if rat else 1.1) * scale_factor
		var body: Color = Color("aa8a70") if rat else Color("916846")
		draw_set_transform(p, 0, Vector2(scale_value, scale_value))
		draw_line(Vector2(-15, -7),Vector2(-31, -3),Color("c39180") if rat else body.darkened(0.2),4)
		draw_rect(Rect2(-18,-19,35,17),body.darkened(0.15))
		draw_rect(Rect2(-13,-24,27,16),body)
		draw_rect(Rect2(-13,-5,6,9),body.darkened(0.3))
		draw_rect(Rect2(9,-5,6,9),body.darkened(0.3))
		draw_rect(Rect2(11,-18,19,12),body.lightened(0.1))
		draw_circle(Vector2(15,-20),5,Color("cd9a8c") if rat else body.darkened(0.2))
		draw_circle(Vector2(24,-15),2,Color("261f29"))
		draw_rect(Rect2(29,-11,4,4),Color("cc9191") if rat else Color("443734"))
		if not rat:
			draw_colored_polygon(PackedVector2Array([Vector2(21,-6),Vector2(24,-15),Vector2(29,-7)]),Color("f1dfb6"))
			draw_line(Vector2(-9,-24),Vector2(12,-24),Color("493d37"),5)
		draw_set_transform(Vector2.ZERO)
	elif kind == "goblin" or kind == "skeleton":
		draw_set_transform(p * (1.0 - scale_factor), 0, Vector2.ONE * scale_factor)
		var skeleton: bool = kind == "skeleton"
		var skin: Color = Color(str(spec.get("color", "e8dcac" if skeleton else "81b44f")))
		draw_line(p+Vector2(-5,-11),p+Vector2(-8,3),skin.darkened(0.2),5)
		draw_line(p+Vector2(6,-11),p+Vector2(9,3),skin.darkened(0.2),5)
		draw_rect(Rect2(p+Vector2(-9,-30),Vector2(18,20)),Color("6b625e") if skeleton else Color("ae7046"))
		if skeleton:
			draw_line(p+Vector2(0,-29),p+Vector2(0,-10),skin,3)
			for i: int in range(4):
				draw_line(p+Vector2(-7,-26+i*4),p+Vector2(7,-26+i*4),skin,2)
		elif not str(enemy.get("kind", "")).begins_with("bandit"):
			draw_colored_polygon(PackedVector2Array([p+Vector2(-9,-39),p+Vector2(-22,-42),p+Vector2(-9,-29)]),skin)
			draw_colored_polygon(PackedVector2Array([p+Vector2(9,-39),p+Vector2(22,-42),p+Vector2(9,-29)]),skin)
		draw_rect(Rect2(p+Vector2(-10,-45),Vector2(20,17)),skin)
		draw_rect(Rect2(p+Vector2(-6,-38),Vector2(4,4)),Color("463b31"))
		draw_rect(Rect2(p+Vector2(3,-38),Vector2(4,4)),Color("463b31"))
		draw_line(p+Vector2(-10,-25),p+Vector2(-17,-13),skin,5)
		draw_line(p+Vector2(10,-25),p+Vector2(17,-18),skin,5)
		draw_line(p+Vector2(16,-13),p+Vector2(25,-36),Color("d5e0cc") if skeleton else Color("8c6741"),5)
		if not skeleton:
			draw_circle(p+Vector2(25,-37),7,Color("8f7954"))
	elif kind == "spider":
		draw_set_transform(p * (1.0 - scale_factor), 0, Vector2.ONE * scale_factor)
		var phase: float = sin(_clock*7+p.x)*3
		for side: int in [-1,1]:
			for i: int in range(4):
				var root: Vector2 = p+Vector2(side*8,-18+i*4)
				var bend: Vector2 = p+Vector2(side*(23+phase*(1 if i%2 else -1)),-29+i*10)
				var foot: Vector2 = p+Vector2(side*31,-23+i*11)
				draw_polyline(PackedVector2Array([root,bend,foot]),Color("3c5942"),4)
		draw_circle(p+Vector2(0,-20),13,Color("487c48"))
		draw_circle(p+Vector2(-3,-24),7,Color("79b662"))
		draw_circle(p+Vector2(0,-7),9,Color("487045"))
		draw_circle(p+Vector2(-4,-5),2.4,Color("edaf78"))
		draw_circle(p+Vector2(4,-5),2.4,Color("edaf78"))
	elif kind == "wolf":
		draw_set_transform(p * (1.0 - scale_factor), 0, Vector2.ONE * scale_factor)
		var o: Vector2 = p + Vector2(0, sin(_clock * 4 + p.x) * 0.6)
		draw_colored_polygon(PackedVector2Array([o + Vector2(-19, -9), o + Vector2(-13, -24), o + Vector2(6, -25), o + Vector2(19, -17), o + Vector2(17, -4), o + Vector2(-9, -3)]), Color("788c91"))
		draw_line(o + Vector2(-14, -6), o + Vector2(-17, 4), Color("50636c"), 5)
		draw_line(o + Vector2(10, -6), o + Vector2(12, 4), Color("50636c"), 5)
		draw_colored_polygon(PackedVector2Array([o + Vector2(-13, -22), o + Vector2(3, -30), o + Vector2(10, -18), o + Vector2(-5, -13)]), Color("9ba9a6"))
		draw_line(o + Vector2(-17, -17), o + Vector2(-31, -25), Color("6c8188"), 8, true)
		draw_colored_polygon(PackedVector2Array([o + Vector2(9, -17), o + Vector2(11, -32), o + Vector2(17, -27), o + Vector2(23, -30), o + Vector2(24, -18), o + Vector2(33, -13), o + Vector2(25, -7)]), Color("8e9e9d"))
		draw_circle(o + Vector2(23, -19), 2, Color("e8b370"))
		draw_circle(o + Vector2(32, -13), 3, Color("2c414a"))
	elif kind == "wisp":
		draw_set_transform(p * (1.0 - scale_factor), 0, Vector2.ONE * scale_factor)
		var o: Vector2 = p + Vector2(0, -23 + sin(_clock * 2.3 + p.x) * 5)
		draw_circle(o, 30, Color(0.39, 0.81, 0.85, 0.06))
		draw_circle(o, 21, Color(0.39, 0.81, 0.85, 0.12))
		draw_colored_polygon(PackedVector2Array([o + Vector2(-14, 6), o + Vector2(-11, -9), o + Vector2(-2, -23), o + Vector2(8, -9), o + Vector2(14, 6), o + Vector2(9, 15), o + Vector2(3, 10), o + Vector2(-3, 17)]), Color("62b9b5"))
		draw_circle(o, 10, Color("a1dcd1"))
		draw_circle(o + Vector2(-3, -3), 5, Color("e0f3db"))
		draw_circle(o + Vector2(-4, 2), 1.8, Color("286475"))
		draw_circle(o + Vector2(5, 2), 1.8, Color("286475"))
	else:
		var is_boss: bool = kind == "boss"
		var s: float = scale_factor
		var stone: Color = Color("82645d") if is_boss else Color("849b96")
		var glow: Color = Color("f0a16d") if is_boss else Color("91ded3")
		draw_set_transform(p, 0, Vector2(s, s))
		draw_line(Vector2(-10, -10), Vector2(-13, 2), stone.darkened(0.24), 12)
		draw_line(Vector2(10, -10), Vector2(13, 2), stone.darkened(0.24), 12)
		draw_colored_polygon(PackedVector2Array([Vector2(-19, -35), Vector2(17, -35), Vector2(21, -13), Vector2(8, -7), Vector2(-16, -10)]), stone)
		draw_colored_polygon(PackedVector2Array([Vector2(-19, -35), Vector2(-6, -39), Vector2(-5, -11), Vector2(-16, -10)]), stone.lightened(0.17))
		draw_line(Vector2(-19, -31), Vector2(-27, -15), stone.darkened(0.18), 14, true)
		draw_line(Vector2(18, -31), Vector2(28, -15), stone.darkened(0.08), 14, true)
		draw_rect(Rect2(-12, -53, 24, 20), stone.lightened(0.12))
		draw_rect(Rect2(1, -53, 11, 20), stone.darkened(0.1))
		draw_line(Vector2(-7, -44), Vector2(-2, -44), glow, 3, true)
		draw_line(Vector2(3, -44), Vector2(8, -44), glow, 3, true)
		draw_line(Vector2(-4, -30), Vector2(4, -19), glow, 2, true)
		draw_line(Vector2(4, -19), Vector2(-3, -15), glow, 2, true)
		if is_boss:
			draw_colored_polygon(PackedVector2Array([Vector2(-12, -53), Vector2(-20, -68), Vector2(-4, -57), Vector2(0, -71), Vector2(5, -57), Vector2(21, -68), Vector2(12, -53)]), Color("b88d62"))
			draw_circle(Vector2(0, -25), 7, Color("ffd296"))
			draw_arc(Vector2(0, -15), 46, 0, TAU, 36, Color(0.95, 0.4, 0.21, 0.18), 2, true)
		draw_set_transform(Vector2.ZERO)
	draw_set_transform(Vector2.ZERO)
	if str(spec.get("projectile", "")) == "arrow":
		draw_polyline(PackedVector2Array([p + Vector2(21, -39) * scale_factor, p + Vector2(31, -23) * scale_factor, p + Vector2(21, -5) * scale_factor]), GOLD, 3)
		draw_line(p + Vector2(21, -39) * scale_factor, p + Vector2(21, -5) * scale_factor, WARM, 1)
	var name_y: float = (-39 if kind == "rat" else (-48 if kind == "boar" or kind == "spider" else -67)) * scale_factor
	_text_center(p + Vector2(0, name_y), str(enemy.get("name", "Przeciwnik")), Color("edbe9d") if kind == "boss" else Color("b8c4b9"), 12)
	_health_bar(p + Vector2(0, name_y + 7), 55 * scale_factor, float(enemy.get("hp", 1)), float(enemy.get("max_hp", 1)), Color("c77868"))

func _shadow(p: Vector2, size: Vector2) -> void:
	draw_set_transform(p + Vector2(0, 3), 0, Vector2(1, size.y / size.x))
	draw_circle(Vector2.ZERO, size.x, Color(0.025, 0.075, 0.09, 0.36))
	draw_set_transform(Vector2.ZERO)

func _health_bar(p: Vector2, width: float, hp: float, max_hp: float, color: Color) -> void:
	var ratio: float = clampf(hp / maxf(max_hp, 1), 0, 1)
	draw_rect(Rect2(p - Vector2(width * 0.5 + 1, 1), Vector2(width + 2, 5)), Color("172f35"))
	draw_rect(Rect2(p - Vector2(width * 0.5, 0), Vector2(width * ratio, 3)), color)

func _text_center(p: Vector2, value: String, color: Color, font_size: int) -> void:
	var width: float = _font.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string_outline(_font, p - Vector2(width * 0.5, 0), value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, 3, Color(0.05, 0.13, 0.16, 0.9))
	draw_string(_font, p - Vector2(width * 0.5, 0), value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)

func _class_color(class_id: String) -> Color:
	match class_id:
		"knight": return Color("739ecc")
		"paladin": return Color("d3ac48")
		"mage": return Color("a078d6")
		"druid": return Color("52ae63")
	return Color("438d92")

func _draw_npcs() -> void:
	var own: Dictionary = _local_player()
	for npc: Dictionary in world_data.get("npcs", []):
		if int(npc.get("floor", 0)) != int(own.get("floor", 0)) or Vector2(npc["x"], npc["y"]).distance_to(get_local_position()) > 1200:
			continue
		var p: Vector2 = Vector2(float(npc.get("x",0)),float(npc.get("y",0)))
		var id: String = str(npc.get("id",""))
		var cloth: Color = Color("4d83b3") if id == "strazniczka" else (Color("c2944e") if id == "kartograf" else Color("68a45c"))
		_shadow(p,Vector2(17,7))
		draw_rect(Rect2(p+Vector2(-10,-7),Vector2(8,10)),Color("594b3a"))
		draw_rect(Rect2(p+Vector2(3,-7),Vector2(8,10)),Color("594b3a"))
		draw_rect(Rect2(p+Vector2(-11,-30),Vector2(22,24)),cloth.darkened(0.2))
		draw_rect(Rect2(p+Vector2(-8,-30),Vector2(13,24)),cloth)
		draw_rect(Rect2(p+Vector2(-15,-26),Vector2(5,13)),cloth.lightened(0.1))
		draw_rect(Rect2(p+Vector2(10,-26),Vector2(5,13)),cloth.lightened(0.1))
		draw_rect(Rect2(p+Vector2(-8,-46),Vector2(16,16)),Color("e6ba8e"))
		draw_rect(Rect2(p+Vector2(-10,-48),Vector2(20,6)),Color("5e4b39"))
		draw_rect(Rect2(p+Vector2(-5,-38),Vector2(2,2)),INK)
		draw_rect(Rect2(p+Vector2(4,-38),Vector2(2,2)),INK)
		draw_line(p+Vector2(-11,-12),p+Vector2(11,-12),GOLD,3)
		if id == "kartograf":
			draw_rect(Rect2(p+Vector2(9,-24),Vector2(14,16)),Color("f1deb1"))
			draw_line(p+Vector2(12,-19),p+Vector2(19,-16),Color("748d67"),2)
		else:
			draw_line(p+Vector2(20,1),p+Vector2(20,-44),Color("8a6841"),3)
			draw_colored_polygon(PackedVector2Array([p+Vector2(16,-43),p+Vector2(20,-53),p+Vector2(24,-43)]),Color("dae2cf"))
		_text_center(p+Vector2(0,-61),str(npc.get("name","Wędrowiec")),Color("ffe190"),13)
		var marker: String = ""
		for quest: Dictionary in own.get("quests", []):
			if str(quest.get("npc_id","")) != id:
				continue
			var status: String = str(quest.get("status",""))
			if status == "ready":
				marker = "?"
				break
			if status == "available":
				marker = "!"
		if not marker.is_empty():
			_text_center(p+Vector2(0,-83+sin(_clock*3)*2),marker,Color("fff08a"),24)
		if p.distance_to(get_local_position()) <= float(npc.get("radius",150)):
			_text_center(p+Vector2(0,24),"E · Rozmowa",Color("fff0bd"),12)

func _draw_speech(player: Dictionary, p: Vector2) -> void:
	var text: String = str(player.get("speech_text", ""))
	if text.is_empty() or float(player.get("speech_until",0)) <= _server_time:
		return
	var lines: Array[String] = []
	var line: String = ""
	for word: String in text.substr(0,160).split(" "):
		var remaining: String = word
		while remaining.length() > 31:
			if not line.is_empty():
				lines.append(line)
				line = ""
			lines.append(remaining.substr(0,31))
			remaining = remaining.substr(31)
		if not line.is_empty() and (line + " " + remaining).length() > 31:
			lines.append(line)
			line = remaining
		else:
			line += (" " if not line.is_empty() else "") + remaining
	if not line.is_empty():
		lines.append(line)
	for i: int in range(lines.size()):
		_text_center(p+Vector2(0,-95-(lines.size()-1-i)*18),lines[i],Color("ffe875"),15)

func _draw_effects() -> void:
	for effect: Dictionary in _effects.values():
		if int(effect.get("floor", 0)) != int(_local.get("floor", 0)):
			continue
		var duration: float = maxf(0.01,float(effect.get("duration",0.32)))
		var t: float = clampf((_server_time-float(effect.get("time",0)))/duration,0,1)
		var origin: Vector2 = Vector2(float(effect.get("x",0)),float(effect.get("y",0)))
		var target: Vector2 = Vector2(float(effect.get("target_x",origin.x)),float(effect.get("target_y",origin.y)))
		var kind: String = str(effect.get("kind","magic_bolt"))
		var radius: float = float(effect.get("radius",0))
		if kind == "danger_zone":
			var tint: Color = _enemy_element_color(str(effect.get("element", "stone")))
			draw_circle(target, radius, Color(tint, 0.12))
			draw_arc(target, radius, 0, TAU, 56, Color(tint, 0.9), 3)
			draw_arc(target, maxf(2, radius * t), -PI / 2, -PI / 2 + TAU * t, 48, Color("fff1c9"), 2)
			if effect.get("special", false):
				_text_center(target, "UNIK!", GOLD, 13)
		elif kind == "enemy_impact":
			var tint: Color = _enemy_element_color(str(effect.get("element", "stone")))
			draw_arc(origin, maxf(2, radius * (0.3 + 0.7 * t)), 0, TAU, 48, Color(tint, 1 - t), 5)
		elif kind.begins_with("enemy_"):
			var tint: Color = _enemy_element_color(kind.trim_prefix("enemy_"))
			var pos: Vector2 = origin.lerp(target, t) + Vector2(0, -18)
			if kind == "enemy_stone":
				pos.y -= sin(t * PI) * 65
				draw_rect(Rect2(pos - Vector2(8, 7), Vector2(17, 15)), Color("939182"))
				draw_rect(Rect2(pos - Vector2(7, 7), Vector2(12, 5)), GOLD)
			elif kind in ["enemy_arrow", "enemy_feather"]:
				var direction: Vector2 = (target - origin).normalized()
				draw_line(pos - direction * 20, pos + direction * 8, tint, 3)
				draw_line(pos + direction.rotated(0.7) * 6, pos + direction * 12, WARM, 2)
				draw_line(pos + direction.rotated(-0.7) * 6, pos + direction * 12, WARM, 2)
			else:
				draw_line(origin.lerp(target, maxf(0, t - 0.13)) + Vector2(0, -18), pos, Color(tint, 0.5), 6)
				draw_circle(pos, 15, Color(tint, 0.2))
				draw_circle(pos, 7, tint)
				draw_circle(pos, 3, WARM)
		elif kind in ["ice_ring", "haste"]:
			var tint: Color = Color("a7eaff") if kind == "ice_ring" else Color("d1efb4")
			var ring: float = maxf(20, radius * t)
			draw_arc(origin, ring, 0, TAU, 64, Color(tint, 1.0 - t), 4)
			for i: int in range(16):
				var pos: Vector2 = origin + Vector2.from_angle(i * TAU / 16) * ring
				draw_rect(Rect2(pos - Vector2(2, 5), Vector2(4, 10)), Color(tint, 1.0 - t))
		elif kind == "fire_ring":
			var ring: float = maxf(18,radius*minf(1,t*2.8))
			var fade: float = 1.0-t
			draw_circle(origin,ring,Color(1,0.35,0.05,0.075*fade))
			draw_arc(origin,ring,0,TAU,96,Color(1,0.47,0.10,fade),6)
			draw_arc(origin,ring*0.91,0,TAU,96,Color(1,0.88,0.3,fade*0.7),3)
			for i: int in range(32):
				var angle: float = i*TAU/32+t*0.25
				var p: Vector2 = origin+Vector2.from_angle(angle)*ring
				var height: float = 17+sin(t*25+i*2)*8
				draw_colored_polygon(PackedVector2Array([p+Vector2(-8,3),p+Vector2(-5,-10),p+Vector2(2,-height-10),p+Vector2(5,-8),p+Vector2(9,3)]),Color(1,0.32,0.04,fade))
				draw_colored_polygon(PackedVector2Array([p+Vector2(-4,2),p+Vector2(0,-height*0.7),p+Vector2(5,2)]),Color(1,0.88,0.24,fade))
		elif kind == "bulwark" or kind == "heal":
			var center: Vector2 = target if kind == "heal" else origin
			var tint: Color = Color("86ed98") if kind == "heal" else Color("8bc8f0")
			draw_arc(center,maxf(30,radius)*(0.6+t*0.4),0,TAU,48,Color(tint,1-t),4)
			for i: int in range(8):
				var p: Vector2 = center+Vector2.from_angle(i*TAU/8+t)*maxf(24,radius*0.6)+Vector2(0,-t*30)
				draw_line(p+Vector2(-4,0),p+Vector2(4,0),Color(tint,1-t),2)
				draw_line(p+Vector2(0,-4),p+Vector2(0,4),Color(tint,1-t),2)
		elif kind == "sword":
			var angle: float = (target-origin).angle()
			draw_arc(origin+Vector2(0,-16),42+t*16,angle-0.9+t,angle+0.7+t,20,Color(1,0.93,0.60,1-t),5)
		else:
			# Frozen cast coordinates keep projectiles aimed at the actual target while walking.
			var a: Vector2 = origin+Vector2(0,-24)
			var b: Vector2 = target+Vector2(0,-18)
			var p: Vector2 = a.lerp(b,t)
			var direction: Vector2 = (b-a).normalized()
			if direction.is_zero_approx():
				direction = Vector2.RIGHT
			if kind == "arrow" or kind == "piercing_arrow":
				var color: Color = Color("ffe285") if kind == "piercing_arrow" else Color("f5e9bd")
				draw_line(p-direction*24,p,color,3)
				var side: Vector2 = direction.orthogonal()
				draw_colored_polygon(PackedVector2Array([p+direction*6,p-direction*4+side*5,p-direction*4-side*5]),color)
				if kind == "piercing_arrow":
					draw_line(a.lerp(b,maxf(0,t-0.24)),p,Color(1,0.8,0.3,0.4),7)
			else:
				var color: Color = Color("76ef9b") if kind == "nature_bolt" else Color("bd9dff")
				draw_line(a.lerp(b,maxf(0,t-0.2)),p,Color(color,0.35),10)
				draw_circle(p,11,Color(color,0.2))
				draw_circle(p,6,color)
				draw_circle(p+Vector2(-1,-1),3,Color("fff2d0"))

func _draw_mill_blades() -> void:
	if int(_local.get("floor", 0)) != 0:
		return
	for obstacle: Dictionary in _mills:
		if str(obstacle.get("type", "")) != "mill":
			continue
		var p: Vector2 = Vector2(float(obstacle.get("x", 0))+float(obstacle.get("w", 0))*0.5,float(obstacle.get("y", 0))+float(obstacle.get("h", 0))*0.5-35)
		for i: int in range(4):
			var axis: Vector2 = Vector2.from_angle(_clock*0.45+i*TAU/4)
			var side: Vector2 = axis.orthogonal()
			draw_line(p,p+axis*52,Color("72563b"),4)
			draw_colored_polygon(PackedVector2Array([p+axis*16,p+axis*48,p+axis*48+side*12,p+axis*16+side*12]),Color("e8d3a3"))
			for step: int in range(3):
				draw_line(p+axis*(20+step*11),p+axis*(20+step*11)+side*12,Color("a88a60"),2)
		draw_circle(p,6,Color("a88755"))

func _draw_winged_enemy(enemy: Dictionary, p: Vector2, spec: Dictionary) -> void:
	var body: Color = Color(str(spec.get("color", "c28291")))
	var scale_value: float = float(spec.get("size", 1))
	draw_set_transform(p, 0, Vector2.ONE * scale_value)
	for side: int in [-1, 1]:
		draw_colored_polygon(PackedVector2Array([Vector2(side * 9, -30), Vector2(side * 56, -68), Vector2(side * 38, -15)]), body.darkened(0.2))
		draw_rect(Rect2(side * 12 - 5, -1, 10, 13), body.darkened(0.3))
	draw_rect(Rect2(-17, -39, 34, 39), body)
	draw_rect(Rect2(-12, -33, 24, 22), body.lightened(0.25))
	draw_rect(Rect2(-13, -64, 26, 26), body)
	draw_rect(Rect2(-18, -69, 6, 14), GOLD)
	draw_rect(Rect2(12, -69, 6, 14), GOLD)
	draw_rect(Rect2(-7, -55, 4, 4), Color("fff09b"))
	draw_rect(Rect2(4, -55, 4, 4), Color("fff09b"))
	draw_set_transform(Vector2.ZERO)
	_text_center(p + Vector2(0, -88 * scale_value), str(enemy.get("name", "")), GOLD, 13)
	draw_rect(Rect2(p + Vector2(-24, -80 * scale_value), Vector2(48, 5)), Color("453540"))
	draw_rect(Rect2(p + Vector2(-23, -79 * scale_value), Vector2(46 * float(enemy["hp"]) / float(enemy["max_hp"]), 3)), Color("e18a70"))

func _enemy_element_color(element: String) -> Color:
	var colors: Dictionary = {"stone":"d5bf8a", "arrow":"f5d48d", "venom":"b4dd68", "fire":"ff9856", "ice":"9ae1f6", "shadow":"ce9ee7", "arcane":"9ccaf2", "feather":"e3d9bd"}
	return Color(str(colors.get(element, "efbd8c")))

func _draw_mountain(c: Node2D, rect: Rect2) -> void:
	var p: Vector2 = rect.position
	var w: float = rect.size.x
	var h: float = rect.size.y
	c.draw_colored_polygon(PackedVector2Array([p+Vector2(0,h),p+Vector2(w*0.08,h*0.18),p+Vector2(w*0.33,-h*0.65),p+Vector2(w*0.54,h*0.05),p+Vector2(w*0.74,-h*0.25),p+Vector2(w,h*0.3),p+Vector2(w,h)]),Color("727d78"))
	c.draw_colored_polygon(PackedVector2Array([p+Vector2(w*0.08,h*0.18),p+Vector2(w*0.33,-h*0.65),p+Vector2(w*0.41,h*0.6),p+Vector2(0,h)]),Color("a5ac99"))
	c.draw_polyline(PackedVector2Array([p+Vector2(w*0.33,-h*0.6),p+Vector2(w*0.54,h*0.08),p+Vector2(w*0.7,h*0.18)]),Color("d0cab0"),3)
	for i: int in range(5):
		c.draw_line(p+Vector2(w*0.42,i*h*0.18),p+Vector2(w*0.88,i*h*0.18+10),Color("535f5c"),2)

func _draw_habitat(c: Node2D, camp: Dictionary) -> void:
	var p: Vector2 = Vector2(camp["x"], camp["y"])
	var deco: String = str(camp.get("decoration", "den"))
	if deco == "camp":
		c.draw_circle(p, 15, Color("79593b"))
		c.draw_circle(p, 7, Color("edb566"))
		for off: Vector2 in [Vector2(-82,18), Vector2(101,-28)]:
			c.draw_rect(Rect2(p+off+Vector2(-22,-45),Vector2(44,25)),Color("443e35"))
			c.draw_colored_polygon(PackedVector2Array([p+off+Vector2(-26,-45),p+off+Vector2(0,-80),p+off+Vector2(26,-45)]),Color("ac9465"))
		c.draw_rect(Rect2(p+Vector2(-75,52),Vector2(51,16)),Color("89683e"))
		for dx: int in [-70,-32]:
			c.draw_circle(p+Vector2(dx,72),10,Color("594832"))
			c.draw_circle(p+Vector2(dx,72),5,Color("bd965b"))
	elif deco == "web":
		for off: Vector2 in [Vector2(-75,12),Vector2(25,-50),Vector2(82,30)]:
			for i: int in range(8):
				c.draw_line(p+off,p+off+Vector2.from_angle(i*TAU/8)*40,Color("d8dfbd88"),1)
			for r: int in [12,24,39]:
				c.draw_arc(p+off,r,0,TAU,16,Color("e2e3c099"),1)
	elif deco == "den":
		c.draw_circle(p,35,Color("665b45"))
		c.draw_circle(p+Vector2(3,-2),25,Color("2d382a"))
		for off: Vector2 in [Vector2(-55,24),Vector2(35,-13),Vector2(6,44)]:
			c.draw_line(p+off+Vector2(-14,0),p+off+Vector2(17,-7),Color("c7b685"),3)
	elif deco in ["crypt", "ruin"]:
		for off: Vector2 in [Vector2(-67,-34),Vector2(25,11),Vector2(76,-42),Vector2(-12,49)]:
			c.draw_rect(Rect2(p+off+Vector2(-14,-31),Vector2(28,36)),Color("838b82"))
			c.draw_rect(Rect2(p+off+Vector2(-12,-34),Vector2(24,8)),Color("c4c4ac"))
			c.draw_line(p+off+Vector2(0,-25),p+off+Vector2(0,-7),Color("585e59"),3)
			c.draw_line(p+off+Vector2(-6,-19),p+off+Vector2(6,-19),Color("585e59"),2)
	elif deco == "reeds":
		c.draw_circle(p,44,Color("507f75"))
		for i: int in range(15):
			var off: Vector2 = Vector2(sin(i*7)*66,cos(i*3)*38)
			c.draw_line(p+off,p+off+Vector2(-3,-32),Color("63774b"),2)
			c.draw_rect(Rect2(p+off+Vector2(-5,-36),Vector2(5,10)),Color("b59a65"))
	elif deco in ["rift", "crystals"]:
		for off: Vector2 in [Vector2(-57,-14),Vector2(31,-21),Vector2(5,29)]:
			c.draw_colored_polygon(PackedVector2Array([p+off+Vector2(-11,0),p+off+Vector2(-5,-48),p+off+Vector2(7,-64),p+off+Vector2(17,-9)]),Color("bd7aca") if deco=="rift" else Color("aae3e7"))
			c.draw_line(p+off+Vector2(7,-58),p+off+Vector2(7,-9),WARM,2)
	else:
		if deco == "quarry":
			for i: int in range(3, -1, -1):
				c.draw_circle(p + Vector2(0, i * 7), 96 - i * 14, Color("949d88") if i % 2 else Color("bac0a4"))
			for i: int in range(4):
				c.draw_rect(Rect2(p + Vector2(-17, 35 + i * 10), Vector2(34, 7)), Color("c9c5a6"))
		for off: Vector2 in [Vector2(-57,0),Vector2(45,-23),Vector2(15,37)]:
			c.draw_circle(p+off,20,Color("797c73"))
			c.draw_rect(Rect2(p+off+Vector2(-17,-14),Vector2(28,6)),Color("c0bc9f"))
		if deco == "bones":
			for i: int in range(6):
				c.draw_line(p+Vector2(-35+i*11,-10),p+Vector2(-32+i*11,16),WARM,4)
	if not str(camp.get("name", "")).is_empty():
		_map_label(c,p+Vector2(0,-108),str(camp["name"]),GOLD)

func _draw_wild_enemy(enemy: Dictionary, p: Vector2, spec: Dictionary) -> void:
	var size: float = float(spec.get("size", 1))
	var kind: String = str(spec.get("appearance", "ghoul"))
	var body: Color = Color(str(spec.get("color", "#9d967a")))
	var facing: Array = enemy.get("facing", [1,0])
	var flip: float = -1 if float(facing[0]) < 0 else 1
	_shadow(p,Vector2(26,9)*size)
	draw_set_transform(p,0,Vector2(size*flip,size))
	if kind == "bear":
		draw_rect(Rect2(-24,-30,43,29),body.darkened(0.3))
		draw_rect(Rect2(-22,-35,38,25),body)
		draw_rect(Rect2(-18,-33,18,6),body.lightened(0.18))
		draw_rect(Rect2(9,-37,24,25),body)
		draw_rect(Rect2(13,-42,6,8),body.darkened(0.15))
		draw_rect(Rect2(27,-41,6,7),body.darkened(0.15))
		draw_rect(Rect2(24,-23,15,8),Color("c2a27b"))
		draw_rect(Rect2(35,-23,5,5),Color("382f2a"))
		draw_rect(Rect2(26,-31,3,3),Color("292b27"))
		for x: int in [-19,10]:
			draw_rect(Rect2(x,-3,9,14),body.darkened(0.35))
			draw_rect(Rect2(x+2,9,10,3),WARM)
	elif kind == "harpy":
		for side: int in [-1,1]:
			draw_colored_polygon(PackedVector2Array([Vector2(side*6,-27),Vector2(side*46,-54+sin(_clock*6)*7),Vector2(side*34,-12),Vector2(side*8,-4)]),Color("797e89"))
			for i: int in range(4):
				draw_line(Vector2(side*(17+i*6),-18),Vector2(side*(22+i*6),-39),Color("c8c3b3"),2)
		draw_rect(Rect2(-9,-34,19,31),body)
		draw_rect(Rect2(-8,-49,18,17),Color("d7b598"))
		draw_rect(Rect2(-12,-53,25,9),Color("656d7d"))
		draw_rect(Rect2(5,-40,10,4),GOLD)
		for x: int in [-7,6]:
			draw_polyline(PackedVector2Array([Vector2(x,-4),Vector2(x,9),Vector2(x+8,11)]),GOLD,3)
	elif kind == "scorpion":
		for side: int in [-1,1]:
			for i: int in range(3):
				draw_polyline(PackedVector2Array([Vector2(side*9,-13+i*6),Vector2(side*24,-19+i*8),Vector2(side*30,-8+i*7)]),Color("86613b"),3)
			draw_polyline(PackedVector2Array([Vector2(side*9,1),Vector2(side*22,10),Vector2(side*30,2)]),body,6)
		draw_rect(Rect2(-13,-24,27,25),body)
		for i: int in range(4):
			draw_rect(Rect2(-11,-22+i*6,23,2),body.darkened(0.2))
		draw_polyline(PackedVector2Array([Vector2(0,-23),Vector2(-13,-41),Vector2(-10,-58),Vector2(3,-64),Vector2(13,-56)]),body,7)
		draw_rect(Rect2(9,-57,5,11),Color("594235"))
	else:
		for x: int in [-12,5]:
			draw_rect(Rect2(x,-6,9,15),Color("665441"))
		draw_rect(Rect2(-18,-36,36,34),body)
		draw_rect(Rect2(-14,-33,14,21),body.lightened(0.15))
		draw_rect(Rect2(-22,-32,8,27),body)
		draw_rect(Rect2(16,-32,8,25),body)
		draw_rect(Rect2(-13,-59,27,24),body)
		if str(enemy.get("kind", "")) == "cyclops":
			draw_rect(Rect2(-7,-50,16,7),WARM)
			draw_rect(Rect2(-1,-50,4,6),Color("43352a"))
		else:
			draw_rect(Rect2(-7,-49,4,4),GOLD)
			draw_rect(Rect2(4,-49,4,4),GOLD)
		draw_rect(Rect2(-8,-40,16,3),Color("574333"))
		if kind == "cyclops":
			draw_line(Vector2(24,-5),Vector2(30,-47),Color("765333"),6)
			draw_rect(Rect2(22,-54,18,18),Color("a18456"))
		else:
			draw_rect(Rect2(-18,-25,36,14),Color("786673"))
			for side: int in [-1,1]:
				for i: int in range(3):
					draw_rect(Rect2(side*23+i*2,-8,1,8),WARM)
	draw_set_transform(Vector2.ZERO)
	_text_center(p+Vector2(0,-82*size),str(enemy.get("name","")),WARM,12)
	_health_bar(p+Vector2(0,-82*size+8),50,float(enemy["hp"]),float(enemy["max_hp"]),Color("e87955"))


func _draw_waterways(c: Node2D, view: Rect2) -> void:
	var water: Array = _static_index.query("waterways", view, 0)
	for layer: Array in [[22, "b9bb77"], [10, "62a890"], [0, "449ead"], [-28, "438fa6"]]:
		for river: Dictionary in water:
			var a: Vector2 = Vector2(river["a"][0], river["a"][1])
			var b: Vector2 = Vector2(river["b"][0], river["b"][1])
			var width: float = float(river["width"]) + float(layer[0])
			var color: Color = Color(str(layer[1]))
			c.draw_line(a, b, color, width)
			c.draw_circle(a, width * 0.5, color)
			c.draw_circle(b, width * 0.5, color)
	for river: Dictionary in water:
		var mid: Vector2 = (Vector2(river["a"][0], river["a"][1]) + Vector2(river["b"][0], river["b"][1])) * 0.5
		for offset: int in [-40, 0, 40]:
			c.draw_line(mid + Vector2(offset - 10, 0), mid + Vector2(offset + 12, -2), Color("a0d5c8"), 2)
	for bridge: Dictionary in _static_index.query("bridges", view, 0):
		var a: Vector2 = Vector2(bridge["a"][0], bridge["a"][1])
		var b: Vector2 = Vector2(bridge["b"][0], bridge["b"][1])
		var tangent: Vector2 = (b - a).normalized()
		var normal: Vector2 = Vector2(-tangent.y, tangent.x)
		c.draw_line(a, b, Color("685336"), 148)
		c.draw_line(a, b, Color("bc9255"), 140)
		for distance: int in range(0, ceili(a.distance_to(b)), 12):
			var p: Vector2 = a + tangent * distance
			c.draw_line(p - normal * 65, p + normal * 65, Color("e0b574"), 2)
		for side: int in [-1, 1]:
			c.draw_line(a + normal * 69 * side, b + normal * 69 * side, Color("795b35"), 5)

func _draw_cliff(c: Node2D, rect: Rect2, edge_only: bool = false) -> void:
	var face: float = rect.end.y if edge_only else rect.end.y - 48
	if not edge_only:
		c.draw_rect(Rect2(rect.position + Vector2(8, 12), rect.size), Color(0.2, 0.27, 0.22, 0.4))
		c.draw_rect(rect, Color("899083"))
		c.draw_rect(Rect2(rect.position + Vector2(5, 5), rect.size - Vector2(10, 52)), Color("aaa895"))
		for x: int in range(int(rect.position.x) + 12, int(rect.end.x) - 12, 49):
			for y: int in range(int(rect.position.y) + 12, int(rect.end.y) - 60, 42):
				c.draw_line(Vector2(x, y), Vector2(minf(rect.end.x - 8, x + 31), y), Color("c4bea4"), 2)
	c.draw_rect(Rect2(Vector2(rect.position.x, face), Vector2(rect.size.x, 48)), Color("646e69"))
	c.draw_line(Vector2(rect.position.x, face), Vector2(rect.end.x, face), Color("d1c8a9"), 5)
	for y: int in range(int(face) + 10, int(face) + 46, 12):
		c.draw_line(Vector2(rect.position.x + 3, y), Vector2(rect.end.x - 3, y + 2), Color("92978a"), 3)
	for x: int in range(int(rect.position.x) + 16, int(rect.end.x), 57):
		c.draw_polyline(PackedVector2Array([Vector2(x, face + 5), Vector2(x - 5, face + 22), Vector2(x + 3, face + 43)]), Color("485850"), 2)
	if edge_only:
		c.draw_rect(rect, Color("dbcfaa"), false, 3)

func _draw_site(c: Node2D, site: Dictionary, p: Vector2) -> void:
	var action: String = str(site["action"])
	var tint: Color = Color("b9e5d5") if action == "wind" else Color("cab1ef") if action == "ward" else GOLD
	c.draw_circle(p + Vector2(0, 4), 30, Color(0.2, 0.27, 0.22, 0.4))
	if action == "cache":
		c.draw_rect(Rect2(p + Vector2(-26, -19), Vector2(52, 34)), Color("654837"))
		c.draw_rect(Rect2(p + Vector2(-25, -30), Vector2(50, 15)), Color("b58a4e"))
		c.draw_rect(Rect2(p + Vector2(-24, -17), Vector2(48, 28)), Color("9f7844"))
		for dx: int in [-18, 14]:
			c.draw_rect(Rect2(p + Vector2(dx, -29), Vector2(5, 39)), Color("e2bd70"))
		c.draw_rect(Rect2(p + Vector2(-5, -9), Vector2(10, 12)), Color("e7c87b"))
	elif action == "spring":
		c.draw_circle(p, 33, Color("c4c5a2"))
		c.draw_circle(p + Vector2(0, -2), 26, Color("5aa9b4"))
		c.draw_arc(p + Vector2(0, -3), 17, 0, PI, 16, Color("9ddacc"), 4)
	else:
		c.draw_rect(Rect2(p + Vector2(-19, -10), Vector2(38, 19)), Color("7e8278"))
		c.draw_rect(Rect2(p + Vector2(-12, -49), Vector2(24, 44)), Color("a7aa97"))
		c.draw_rect(Rect2(p + Vector2(-9, -46), Vector2(4, 31)), Color("d4ceb3"))
		_map_label(c, p + Vector2(0, -26), "≈" if action == "wind" else "◇", tint)
	_map_label(c, p + Vector2(0, -64), str(site["name"]), tint)
	_map_label(c, p + Vector2(0, 32), "E · użyj poza walką", tint)
