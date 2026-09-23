extends RefCounted
## Same 33px road width and ellipse tests as the authoritative server.
var cells: Dictionary = {}
var world: Dictionary = {}
const BIOMES: Dictionary = {"forest":"forest", "swamp":"mud", "desert":"sand", "snow":"snow", "lava":"ash", "obsidian":"ash", "mountain":"stone", "ruins":"stone"}

func build(data: Dictionary) -> void:
	world = data
	cells.clear()
	for road: Array in data.get("roads", []):
		for i: int in range(1, road.size()):
			var a: Vector2 = Vector2(road[i - 1][0], road[i - 1][1])
			var b: Vector2 = Vector2(road[i][0], road[i][1])
			_insert({"road":true, "a":a, "b":b}, Rect2(a, Vector2.ZERO).expand(b).grow(34))
	for patch: Dictionary in data.get("terrain", []):
		_insert({"road":false, "patch":patch}, Rect2(patch["x"], patch["y"], patch["w"], patch["h"]))

func _insert(entry: Dictionary, rect: Rect2) -> void:
	for x: int in range(floori(rect.position.x / 512), floori(rect.end.x / 512) + 1):
		for y: int in range(floori(rect.position.y / 512), floori(rect.end.y / 512) + 1):
			var key: Vector2i = Vector2i(x, y)
			if not cells.has(key):
				cells[key] = []
			cells[key].append(entry)

func at(point: Vector2, floor_id: int = 0) -> String:
	if floor_id != 0:
		return "stone"
	for city: Dictionary in world.get("cities", []):
		if point.distance_to(Vector2(city["x"], city["y"])) < 205:
			return "stone"
	var entries: Array = cells.get(Vector2i(floori(point.x / 512), floori(point.y / 512)), [])
	for entry: Dictionary in entries:
		if entry["road"]:
			var a: Vector2 = entry["a"]
			var b: Vector2 = entry["b"]
			var delta: Vector2 = b - a
			var q: float = clampf((point - a).dot(delta) / maxf(1, delta.length_squared()), 0, 1)
			if point.distance_to(a + delta * q) <= 33:
				return "path"
	for i: int in range(entries.size() - 1, -1, -1):
		var entry: Dictionary = entries[i]
		if not entry["road"]:
			var patch: Dictionary = entry["patch"]
			var rx: float = float(patch["w"]) / 2
			var ry: float = float(patch["h"]) / 2
			if pow((point.x - float(patch["x"]) - rx) / rx, 2) + pow((point.y - float(patch["y"]) - ry) / ry, 2) <= 1:
				return str(patch["kind"])
	if point.x < 3200 and point.y < 2304:
		if point.x > 1720 and point.x < 2220 and point.y > 1370:
			return "mud"
		if point.x > 2250:
			return "stone"
		if point.y < 900 and point.x < 1400:
			return "forest"
		return "grass"
	for region: Dictionary in world.get("regions", []):
		if Rect2(region["x"], region["y"], region["w"], region["h"]).has_point(point):
			return str(BIOMES.get(region.get("biome", ""), "grass"))
	return "grass"
