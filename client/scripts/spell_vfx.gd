extends RefCounted
## Procedural visuals use the exact authoritative polygons/circles, not guessed radii.
static func point(value: Array) -> Vector2:
	return Vector2(float(value[0]), float(value[1]))

static func missile_point(a: Vector2, b: Vector2, t: float, index: int, total: int = 3) -> Vector2:
	var bend: Array[float] = [-96.0, 32.0, 105.0]
	var direction: Vector2 = (b - a).normalized()
	if direction.is_zero_approx():
		direction = Vector2.RIGHT
	var curve: float = bend[index % 3] if total <= 3 else -150.0 + 300.0 * index / maxf(1, total - 1)
	curve *= minf(1, a.distance_to(b) / 130.0)
	var control: Vector2 = (a + b) * 0.5 + Vector2(-direction.y, direction.x) * curve + Vector2(0, -18)
	return (1 - t) * (1 - t) * a + 2 * (1 - t) * t * control + t * t * b

static func burst(h: Node2D, center: Vector2, t: float, tint: Color, frost: bool = false) -> void:
	for i: int in range(15):
		var direction: Vector2 = Vector2.from_angle(i * TAU / 15.0 + t)
		var a: Vector2 = center + direction * (4 + t * 25)
		var b: Vector2 = a + direction * (5 + (i % 4) * 3)
		h.draw_line(a, b, Color(tint, 1 - t), 2.5, true)
		if frost:
			h.draw_line(a - direction.orthogonal() * 3, a + direction.orthogonal() * 3, Color.WHITE, 1, true)

static func beam(h: Node2D, a: Vector2, b: Vector2, tint: Color, core: Color, t: float, frost: bool = false) -> void:
	var alpha: float = maxf(0, sin(PI * t))
	h.draw_line(a, b, Color(tint, alpha * 0.25), 19, true)
	h.draw_line(a, b, Color(tint, alpha), 7, true)
	h.draw_line(a, b, Color(core, alpha), 2.5, true)
	var normal: Vector2 = (b - a).normalized().orthogonal()
	for i: int in range(12):
		var c: Vector2 = a.lerp(b, fmod(i / 12.0 + t * 2, 1.0))
		h.draw_line(c, c + normal * sin(i * 2.6 + t * 13) * 12, Color(core, alpha * 0.65), 1.5, true)
	burst(h, b, fmod(t * 2, 1.0), core, frost)

static func draw(h: Node2D, effect: Dictionary, t: float, now: float) -> void:
	var visual: Dictionary = effect.get("visual", {})
	var colors: Array = visual.get("colors", ["#648bdb", "#aaceff", "#ffffff"])
	var tint: Color = Color(str(colors[0]))
	var light: Color = Color(str(colors[1]))
	var core: Color = Color(str(colors[2]))
	var a: Vector2 = Vector2(float(effect.get("x", 0)), float(effect.get("y", 0))) + Vector2(0, -20)
	var b: Vector2 = Vector2(float(effect.get("target_x", a.x)), float(effect.get("target_y", a.y))) + Vector2(0, -20)
	var style: String = str(visual.get("style", "projectile"))
	var key: String = str(effect.get("spell_id", ""))
	var area: Dictionary = effect.get("area", {})
	if not area.is_empty() and style != "chain":
		var persistent: bool = effect.get("persistent", false)
		var alpha: float = 0.72 + sin(now * 3) * 0.15 if persistent else sin(PI * minf(0.98, t))
		for polygon: Array in area.get("polygons", []):
			var points: PackedVector2Array = PackedVector2Array()
			for pos: Array in polygon:
				points.append(point(pos))
			if points.size() < 3:
				continue
			h.draw_colored_polygon(points, Color(tint, alpha * 0.21))
			points.append(points[0])
			h.draw_polyline(points, Color(light, alpha), 2, true)
			# Lines inside the polygon remain bounded by authoritative vertices.
			var center: Vector2 = Vector2.ZERO
			for pos: Array in polygon:
				center += point(pos) / float(polygon.size())
			for i: int in range(polygon.size()):
				var corner: Vector2 = point(polygon[i])
				h.draw_line(center, center.lerp(corner, 0.75 + sin(now * 4 + i) * 0.12), Color(light, alpha * 0.4), 2, true)
		if area.get("shape", "") == "cone":
			var origin: Vector2 = point(area.get("origin", [0, 0]))
			var direction: Vector2 = point(area.get("direction", [1, 0]))
			var length: float = float(area.get("length", 0))
			for i: int in range(13):
				var end: Vector2 = origin + direction * length + direction.orthogonal() * (i / 12.0 - 0.5) * length
				h.draw_line(origin, origin.lerp(end, minf(1, t * 1.9)), Color(light, alpha * 0.45), 4, true)
		elif area.get("shape", "") == "line":
			var origin: Vector2 = point(area.get("origin", [0, 0]))
			beam(h, origin, origin + point(area.get("direction", [1, 0])) * float(area.get("length", 0)), tint, core, t)
		for circle: Array in area.get("circles", []):
			var center: Vector2 = Vector2(circle[0], circle[1])
			var radius: float = float(circle[2])
			h.draw_circle(center, radius, Color(tint, alpha * 0.13))
			h.draw_arc(center, radius, 0, TAU, 64, Color(light, alpha), 2, true)
			for i: int in range(28):
				var angle: float = i * 2.39996 + sin(now + i) * 0.07
				var c: Vector2 = center + Vector2.from_angle(angle) * sqrt((i + 0.5) / 28.0) * radius * 0.9
				h.draw_line(c, c + Vector2(0, -8 - 5 * sin(now * 4 + i)), Color(light, alpha * 0.7), 2, true)
			if key == "moonbeam":
				h.draw_line(center + Vector2(0, -150), center, Color(core, alpha * 0.2), radius * 1.4, true)
			elif key == "meteor_swarm":
				var pos: Vector2 = center + Vector2(-80, -120) * (1 - minf(1, t / 0.58))
				h.draw_line(pos + Vector2(-32, -48), pos, Color(tint, alpha), 15, true)
				h.draw_circle(pos, 18, Color(light, alpha))
			elif not persistent:
				h.draw_arc(center, maxf(1, radius * minf(1, t * 1.7)), 0, TAU, 64, Color(core, (1 - t) * 0.7), 3, true)
		return
	if style == "missiles":
		var progress: float = minf(1, t / 0.75)
		var count: int = clampi(int(effect.get("shots", 3)), 1, 11)
		for i: int in range(count):
			var trail: PackedVector2Array = PackedVector2Array()
			for j: int in range(12):
				trail.append(missile_point(a, b, maxf(0, progress - (11 - j) * 0.013), i, count))
			h.draw_polyline(trail, Color(tint, 0.35), 10, true)
			h.draw_polyline(trail, light, 3, true)
			if progress < 1:
				var pos: Vector2 = missile_point(a, b, progress, i, count)
				h.draw_circle(pos, 13, Color(tint, 0.3))
				h.draw_circle(pos, 6, light)
				h.draw_circle(pos, 2.5, core)
			else:
				burst(h, b, (t - 0.75) / 0.25, core)
	elif style == "vines":
		draw_vines(h, b + Vector2(0, 20), now, 1.0, sin(PI * t))
	elif style == "mark":
		draw_mark(h, b + Vector2(0, 20), now, 1.0, sin(PI * t))
	elif style == "beam":
		for i: int in range(int(effect.get("shots", 1))):
			beam(h, a + Vector2(0, (i - (int(effect.get("shots", 1)) - 1) / 2.0) * 7), b, tint, core, t, key == "ray_of_frost")
	elif style == "chain":
		beam(h, a, b, tint, core, t)
		for target: Dictionary in effect.get("targets", []):
			var c: Vector2 = Vector2(target.get("x", 0), target.get("y", 0)) + Vector2(0, -20)
			if c.distance_to(b) > 1:
				beam(h, b, c, tint, core, t)
	elif style == "projectile":
		var progress: float = minf(1, t / 0.7)
		var pos: Vector2 = a.lerp(b, progress)
		h.draw_line(a.lerp(b, maxf(0, progress - 0.18)), pos, Color(tint, 0.4), 10, true)
		h.draw_circle(pos, 9, light)
		h.draw_circle(pos, 3, core)
		if progress >= 1:
			burst(h, b, minf(1, (t - 0.7) / 0.3), light)
	else:
		var radius: float = 24 + t * 20
		h.draw_arc(b + Vector2(0, 20), radius, 0, TAU, 48, Color(light, 1 - t), 3, true)
		if key == "shield" or key == "mage_armor":
			var shield: PackedVector2Array = PackedVector2Array([b + Vector2(-21, -24), b + Vector2(21, -24), b + Vector2(18, 11), b + Vector2(0, 29), b + Vector2(-18, 11), b + Vector2(-21, -24)])
			h.draw_colored_polygon(shield, Color(tint, (1 - t) * 0.2))
			h.draw_polyline(shield, Color(core, 1 - t), 3, true)
		elif style == "heal":
			for i: int in range(8):
				var pos: Vector2 = b + Vector2.from_angle(i * TAU / 8) * radius + Vector2(0, -t * 30)
				h.draw_line(pos - Vector2(4, 0), pos + Vector2(4, 0), Color(light, 1 - t), 2, true)
				h.draw_line(pos - Vector2(0, 4), pos + Vector2(0, 4), Color(light, 1 - t), 2, true)
		else:
			burst(h, b, t, light)

static func draw_mark(h: Node2D, center: Vector2, now: float, size: float = 1.0, alpha: float = 1.0) -> void:
	var c: Vector2 = center + Vector2(0, -49 * size)
	h.draw_arc(c, 10 * size, 0, TAU, 28, Color(0.93, 0.78, 0.41, alpha), 2, true)
	for i: int in range(4):
		var direction: Vector2 = Vector2.from_angle(i * TAU / 4)
		h.draw_line(c + direction * 6.5 * size, c + direction * 14.5 * size, Color(1.0, 0.94, 0.67, alpha), 2, true)
	h.draw_arc(center, 18 * size, 0, TAU, 32, Color(0.93, 0.78, 0.41, alpha * (0.25 + 0.1 * sin(now * 3))), 1.5, true)

static func draw_vines(h: Node2D, center: Vector2, now: float, size: float = 1.0, alpha: float = 1.0) -> void:
	for side: int in [-1, 1]:
		var points: PackedVector2Array = PackedVector2Array()
		for j: int in range(15):
			var t: float = j / 14.0
			points.append(center + Vector2(side * (13 + sin(t * 9 + now * 1.5) * 5), -t * 37) * size)
		h.draw_polyline(points, Color(0.09, 0.25, 0.17, alpha), 6 * size, true)
		h.draw_polyline(points, Color(0.40, 0.72, 0.34, alpha), 3 * size, true)
		for j: int in range(3, 14, 4):
			var a: Vector2 = points[j]
			h.draw_colored_polygon(PackedVector2Array([a, a + Vector2(side * 9, -10) * size, a + Vector2(side * 7, 1) * size]), Color(0.76, 0.92, 0.54, alpha))

static func draw_statuses(h: Node2D, statuses: Array, center: Vector2, now: float, size: float = 1.0) -> void:
	var marked: bool = false
	var ensnared: bool = false
	size = clampf(size, 0.7, 2.2)
	for status: Dictionary in statuses:
		if str(status.get("id", "")) in ["concentration", "ensnaring_ready"]:
			continue
		if status.get("id", "") == "sap":
			h.draw_arc(center + Vector2(0, -62) * size, 11 * size, 0, TAU, 12, Color("e7c276"), 2, true)
		if status.get("id", "") == "prone":
			h.draw_arc(center + Vector2(0, 2), 20 * size, 0, TAU, 20, Color("e9c987"), 2, true)
		if status.get("spell_id", "") == "hunters_mark" and not marked:
			draw_mark(h, center, now, size)
			marked = true
		if status.get("spell_id", "") == "ensnaring_strike" and status.get("id", "") == "restrained" and not ensnared:
			draw_vines(h, center, now, size)
			ensnared = true


static func draw_fighter(h: Node2D, effect: Dictionary, t: float) -> void:
	var center: Vector2 = Vector2(float(effect.get("target_x", effect.get("x", 0))), float(effect.get("target_y", effect.get("y", 0))))
	var key: String = str(effect.get("mastery", ""))
	var color: Color = Color(0.96, 0.80, 0.46, 1.0 - t)
	if key == "surge":
		for i: int in range(3):
			h.draw_arc(center + Vector2(0, -20), 20 + i * 10 + 20 * t, -2.5 + i * 0.2, 1.0 + i * 0.4, 24, color, 3, true)
	elif key == "sap":
		h.draw_arc(center + Vector2(0, -52), 9 + 20 * t, 0, TAU, 18, color, 2, true)
	elif key == "graze":
		h.draw_line(center + Vector2(-26 + 25 * t, -44), center + Vector2(20, -8), Color(0.85, 0.91, 0.85, 1.0 - t), 3, true)
	else:
		for i: int in range(10):
			var a: float = TAU * i / 10.0
			h.draw_circle(center + Vector2(cos(a), sin(a) * 0.4) * (8 + t * 38), 2 + (1-t)*2, color)
