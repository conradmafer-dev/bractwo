extends RefCounted
## Lightweight original artwork; positions and status lifetimes come from the server.
static func polygon(h: Node2D, p: Vector2, offsets: Array, tint: Color) -> void:
	var points: PackedVector2Array = PackedVector2Array()
	for pair: Array in offsets:
		points.append(p + Vector2(float(pair[0]), float(pair[1])))
	h.draw_colored_polygon(points, tint)

static func actor(h: Node2D, e: Dictionary, p: Vector2, now: float) -> bool:
	var kind: String = str(e.get("kind", ""))
	if kind not in ["owl", "cat", "black_bear"]:
		return false
	h.draw_circle(p + Vector2(0, 5), 14, Color(0.1, 0.18, 0.14, 0.22))
	if kind == "owl":
		var q: Vector2 = p + Vector2(0, -20 + sin(now * 4) * 2)
		var flap: float = sin(now * 10) * 8
		polygon(h, q, [[-9,-6],[-33,-10-flap],[-27,3-flap],[-6,8]], Color("829298"))
		polygon(h, q, [[9,-6],[33,-10-flap],[27,3-flap],[6,8]], Color("a9b6b6"))
		h.draw_circle(q, 12, Color("bec6b8"))
		h.draw_circle(q + Vector2(0, -7), 13, Color("637586"))
		for dx: int in [-6, 6]:
			h.draw_circle(q + Vector2(dx, -8), 6, Color("efe0b4"))
			h.draw_circle(q + Vector2(dx, -8), 2, Color("14232c"))
		polygon(h, q, [[-3,-2],[3,-2],[0,3]], Color("d8aa5e"))
	elif kind == "cat":
		h.draw_rect(Rect2(p + Vector2(-15,-13), Vector2(28,15)), Color("b4ac9c"))
		for dx: int in [-12, 7]:
			h.draw_line(p + Vector2(dx, -2), p + Vector2(dx, 8), Color("62686b"), 4)
		h.draw_circle(p + Vector2(14, -18), 10, Color("ccbea0"))
		polygon(h, p, [[5,-22],[6,-32],[13,-25],[21,-32],[24,-19]], Color("ccbea0"))
		h.draw_circle(p + Vector2(19,-20), 2, Color("274e34"))
		h.draw_arc(p + Vector2(-20,-16), 10, 0, 4, 12, Color("b4ac9c"), 4, true)
	else:
		for dx: int in [-17, 15]:
			h.draw_rect(Rect2(p + Vector2(dx,-9), Vector2(9,19)), Color("28362d"))
		h.draw_circle(p + Vector2(-2,-18), 24, Color("3a463f"))
		h.draw_circle(p + Vector2(20,-26), 17, Color("48524a"))
		h.draw_circle(p + Vector2(13,-40), 6, Color("303e34"))
		h.draw_circle(p + Vector2(32,-22), 10, Color("b79b73"))
		h.draw_circle(p + Vector2(29,-30), 2, Color("ead79e"))
	return true

static func world(h: Node2D, data: Dictionary, snapshot: Dictionary, local: Dictionary) -> void:
	var pos: Vector2 = Vector2(float(local.get("x", 0)), float(local.get("y", 0)))
	for site: Dictionary in data.get("nature_sites", []):
		var p: Vector2 = Vector2(float(site.get("x",0)), float(site.get("y",0)))
		if int(site.get("floor",0)) != int(local.get("floor",0)) or p.distance_squared_to(pos) > 1210000:
			continue
		var kind: String = str(site.get("kind", ""))
		if kind == "fox":
			h.draw_rect(Rect2(p + Vector2(-16,-15), Vector2(32,17)), Color("bd7e49"))
			h.draw_circle(p + Vector2(17,-20), 10, Color("db9d5a"))
			polygon(h, p, [[9,-24],[9,-34],[16,-26],[24,-33],[26,-19]], Color("c38349"))
			h.draw_rect(Rect2(p + Vector2(21,-17), Vector2(11,5)), Color("ead5ac"))
			h.draw_line(p + Vector2(-12,-8), p + Vector2(-31,-23), Color("c38749"), 8)
		elif kind == "frog":
			h.draw_circle(p + Vector2(0,-4), 10, Color("75964d"))
			for dx: int in [-6,6]:
				h.draw_circle(p + Vector2(dx,-11), 5, Color("a0b471"))
				h.draw_circle(p + Vector2(dx,-12), 2, Color("263926"))
		else:
			polygon(h, p, [[-14,4],[-10,-27],[7,-32],[17,4]], Color("687976"))
			h.draw_line(p + Vector2(1,-24), p + Vector2(1,-3), Color("a8d9a0"), 2)
			h.draw_line(p + Vector2(-6,-19), p + Vector2(1,-12), Color("a8d9a0"), 2)
			h.draw_line(p + Vector2(8,-19), p + Vector2(1,-12), Color("a8d9a0"), 2)
	for alarm: Dictionary in snapshot.get("alarms", []):
		if int(alarm.get("floor",0)) != int(local.get("floor",0)):
			continue
		var p: Vector2 = Vector2(float(alarm["x"]), float(alarm["y"]))
		h.draw_rect(Rect2(p - Vector2(64,64), Vector2(128,128)), Color(0.76,0.67,0.88,0.6), false, 2)

static func statuses(h: Node2D, e: Dictionary, p: Vector2, now: float) -> void:
	var active: bool = not e.get("character_sheet", {}).get("caster", {}).get("channel", {}).is_empty()
	for status: Dictionary in e.get("status_effects", []):
		if str(status.get("id", "")) in ["arcane_channel","ritual_channel"]:
			active = true
	if not active:
		return
	h.draw_arc(p + Vector2(0,4), 25, 0, TAU, 40, Color("a4cfce"), 2, true)
	for i: int in range(6):
		var a: float = now + i * TAU / 6.0
		h.draw_circle(p + Vector2(cos(a)*25, sin(a)*12), 2, Color("e7e7ce"))
