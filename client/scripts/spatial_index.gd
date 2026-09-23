extends RefCounted
## Static scene candidates by cell. Geometry and drawing styles stay unchanged.
const CELL: int = 512
var groups: Dictionary = {}

func build(world: Dictionary) -> void:
	groups.clear()
	for group: String in ["obstacles", "landmarks", "stairs", "hunting_grounds", "waterways", "bridges", "elevations"]:
		var cells: Dictionary = {}
		var order: int = 0
		for item: Dictionary in world.get(group, []):
			var rect: Rect2 = Rect2(float(item["x"]), float(item["y"]), float(item.get("w", 0)), float(item.get("h", 0))).grow(220)
			var record: Dictionary = {"data":item, "rect":rect, "order":order}
			order += 1
			for x: int in range(floori(rect.position.x / CELL), floori(rect.end.x / CELL) + 1):
				for y: int in range(floori(rect.position.y / CELL), floori(rect.end.y / CELL) + 1):
					var key: Vector3i = Vector3i(x, y, int(item.get("floor", 0)))
					if not cells.has(key):
						cells[key] = []
					cells[key].append(record)
		groups[group] = cells

func query(group: String, view: Rect2, floor_id: int) -> Array:
	var found: Dictionary = {}
	var cells: Dictionary = groups.get(group, {})
	for x: int in range(floori(view.position.x / CELL), floori(view.end.x / CELL) + 1):
		for y: int in range(floori(view.position.y / CELL), floori(view.end.y / CELL) + 1):
			for record: Dictionary in cells.get(Vector3i(x, y, floor_id), []):
				if view.intersects(record["rect"]):
					found[record["order"]] = record["data"]
	var keys: Array = found.keys()
	keys.sort()
	var result: Array = []
	for key: int in keys:
		result.append(found[key])
	return result
