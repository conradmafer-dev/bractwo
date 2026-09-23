extends Node
## Server-authoritative native client: class, equipment, parties and deliberate PvP.
const WORLD_SCRIPT = preload("res://scripts/world_view.gd")
const PAD_SCRIPT = preload("res://scripts/input_pad.gd")
const MINIMAP_SCRIPT = preload("res://scripts/minimap.gd")
const CLASS_IDS: Array[String] = ["knight", "paladin", "mage", "druid"]
const CLASS_NAMES: Dictionary = {"knight":"Rycerz", "paladin":"Paladyn", "mage":"Mag", "druid":"Druid"}
const CLASS_DESCRIPTIONS: Dictionary = {
	"knight":"Miecz i wysoka wytrzymałość. Umiejętność osłania i przyciąga potwory.",
	"paladin":"Łuk i walka dystansowa. Umiejętność wykonuje mocniejszy strzał.",
	"mage":"Kostur i obrażenia magiczne. Umiejętność trafia pobliskie potwory.",
	"druid":"Kostur i wsparcie. Umiejętność leczy ciebie oraz pobliską drużynę."
}
const SLOT_NAMES: Dictionary = {"weapon":"Broń", "armor":"Pancerz", "ring":"Pierścień", "trophy":"Trofeum"}
const PAPER: Color = Color("eee6ce")
const GOLD: Color = Color("dabb79")
const GREEN: Color = Color("8ed6b5")
const RED: Color = Color("e99b8a")

var socket: WebSocketPeer
var world_view: Node2D
var local_id: String = ""
var state: Dictionary = {}
var world_data: Dictionary = {}
var progression = preload("res://scripts/expansion_panel.gd").new()
var navigation_goal: Dictionary = {}
var player: Dictionary = {}
var login_panel: Control
var hud: Control
var endpoint: LineEdit
var username: LineEdit
var password: LineEdit
var class_select: OptionButton
var class_description: Label
var login_status: Label
var connect_button: Button
var create_button: Button
var stats_label: Label
var hp_bar: ProgressBar
var mana_bar: ProgressBar
var xp_bar: ProgressBar
var vital_label: Label
var event_label: Label
var status_label: Label
var hint_label: Label
var target_label: Label
var feed: Label
var chat_field: LineEdit
var pad: Control
var ability_button: Button
var health_button: Button
var mana_button: Button
var attack_button: Button
var safety_button: Button
var safety_confirm: ConfirmationDialog
var inventory_panel: PanelContainer
var inventory_list: VBoxContainer
var inventory_stats: Label
var equipment_list: VBoxContainer
var legacy_row: HBoxContainer
var legacy_select: OptionButton
var legacy_button: Button
var shop_label: Label
var buy_health: Button
var buy_mana: Button
var journal_panel: PanelContainer
var journal_list: VBoxContainer
var quest_tracker: Label
var minimap: Control
var last_journal_key: String = ""
var party_panel: PanelContainer
var party_list: VBoxContainer
var party_summary: Label
var pvp_rules_label: Label
var invite_label: Label
var accept_invite: Button
var leave_party: Button
var pending_invite_id: String = ""
var pending_invite_name: String = ""
var selected_target: String = ""
var selected_enemy: String = ""
var fps_label: Label
var fps_elapsed: float = 0.0
var battle_panel: PanelContainer
var battle_list: VBoxContainer
var battle_buttons: Dictionary = {}
var last_inventory_key: String = ""
var last_players_key: String = ""
var register_requested: bool = false
var hello_sent: bool = false
var connecting: bool = false
var connection_started: float = 0.0
var input_elapsed: float = 0.0
var attack_elapsed: float = 0.0
var attack_held: bool = false
var app_focused: bool = true
var notices: Array[String] = []

func _ready() -> void:
	_bind_keys()
	world_view = WORLD_SCRIPT.new()
	add_child(world_view)
	var canvas: CanvasLayer = CanvasLayer.new()
	add_child(canvas)
	var root: Control = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = _theme()
	canvas.add_child(root)
	_build_login(root)
	_build_hud(root)
	_build_inventory()
	_build_party()
	_build_journal()
	progression.setup(self)
	safety_confirm = ConfirmationDialog.new()
	safety_confirm.title = "Odblokować atakowanie graczy?"
	safety_confirm.dialog_text = "Atak wymaga wybrania konkretnej postaci.\nNieuzasadniona agresja i zabójstwa powodują kary.\nOsada i początkujący pozostają chronieni."
	safety_confirm.ok_button_text = "Odblokuj PvP"
	safety_confirm.cancel_button_text = "Zostaw blokadę"
	safety_confirm.confirmed.connect(func() -> void: _send({"type":"pvp_safety", "enabled":false}))
	root.add_child(safety_confirm)
	_load_preferences()
	if OS.has_feature("web"):
		var browser_url = JavaScriptBridge.eval("(location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'")
		if browser_url is String:
			endpoint.text = browser_url

func _bind_keys() -> void:
	var bindings: Dictionary = {"walk_up":[KEY_W, KEY_UP], "walk_down":[KEY_S, KEY_DOWN], "walk_left":[KEY_A, KEY_LEFT], "walk_right":[KEY_D, KEY_RIGHT], "strike":[KEY_SPACE]}
	for action in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in bindings[action]:
			var event: InputEventKey = InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)

func _style(color: Color, border: Color, radius: int = 10) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(radius)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	return style

func _theme() -> Theme:
	var theme: Theme = Theme.new()
	theme.default_font_size = 16
	for kind: String in ["Label", "Button", "LineEdit", "OptionButton"]:
		theme.set_color("font_color", kind, PAPER)
	theme.set_color("font_placeholder_color", "LineEdit", Color("849f97"))
	theme.set_color("caret_color", "LineEdit", GOLD)
	theme.set_stylebox("panel", "PanelContainer", _style(Color(0.035,0.09,0.10,0.97), Color("36534c")))
	for kind: String in ["Button", "OptionButton"]:
		theme.set_stylebox("normal", kind, _style(Color("203d39"), Color("4d7161")))
		theme.set_stylebox("hover", kind, _style(Color("31584b"), GOLD))
		theme.set_stylebox("pressed", kind, _style(Color("3e6c59"), GREEN))
		theme.set_stylebox("disabled", kind, _style(Color("14282a"), Color("2c403d")))
		theme.set_color("font_disabled_color", kind, Color("7d9288"))
	theme.set_stylebox("normal", "LineEdit", _style(Color("0b191d"), Color("38594f")))
	theme.set_stylebox("focus", "LineEdit", _style(Color("11292a"), GOLD))
	theme.set_stylebox("background", "ProgressBar", _style(Color("1c3435"), Color("34554b"), 4))
	theme.set_stylebox("fill", "ProgressBar", _style(Color("87b991"), Color("87b991"), 4))
	return theme

func _label(text: String, font_size: int = 16, color: Color = PAPER) -> Label:
	var result: Label = Label.new()
	result.text = text
	result.add_theme_font_size_override("font_size", font_size)
	result.add_theme_color_override("font_color", color)
	return result

func _wrap_label(text: String, font_size: int = 16, color: Color = PAPER) -> Label:
	var result: Label = _label(text, font_size, color)
	result.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	result.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return result

func _button(text: String, callback: Callable) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.custom_minimum_size.y = 44
	button.focus_mode = Control.FOCUS_NONE
	button.pressed.connect(callback)
	return button

func _class_options() -> OptionButton:
	var select: OptionButton = OptionButton.new()
	select.custom_minimum_size.y = 44
	select.focus_mode = Control.FOCUS_NONE
	for id: String in CLASS_IDS:
		select.add_item(str(CLASS_NAMES[id]))
	return select

func _build_login(root: Control) -> void:
	login_panel = Control.new()
	login_panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(login_panel)
	var shade: ColorRect = ColorRect.new()
	shade.color = Color(0.025,0.065,0.073,0.94)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	login_panel.add_child(shade)
	var center: CenterContainer = CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	login_panel.add_child(center)
	var panel: PanelContainer = PanelContainer.new()
	panel.custom_minimum_size = Vector2(580, 0)
	center.add_child(panel)
	var box: VBoxContainer = VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	panel.add_child(box)
	box.add_child(_label("BRACTWO · POGRANICZE", 30, GOLD))
	box.add_child(_label("WIELKI KONTYNENT 0.4  /  WSPÓLNY OTWARTY ŚWIAT", 14, GREEN))
	box.add_child(_label("Cztery klasy · rozwój bez limitu poziomu · loot · drużyny · PvP", 15))
	box.add_child(_label("Adres serwera", 13, GREEN))
	endpoint = LineEdit.new()
	endpoint.text = "ws://127.0.0.1:8080/ws"
	endpoint.custom_minimum_size.y = 44
	box.add_child(endpoint)
	username = LineEdit.new()
	username.placeholder_text = "Nazwa postaci (3–20 znaków)"
	username.max_length = 20
	username.custom_minimum_size.y = 44
	box.add_child(username)
	password = LineEdit.new()
	password.placeholder_text = "Hasło (co najmniej 8 znaków)"
	password.secret = true
	password.max_length = 128
	password.custom_minimum_size.y = 44
	box.add_child(password)
	password.text_submitted.connect(func(_value: String) -> void: _connect(false))
	var class_row: HBoxContainer = HBoxContainer.new()
	class_row.add_child(_label("Klasa nowej postaci:"))
	class_select = _class_options()
	class_select.name = "RegistrationClass"
	class_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	class_row.add_child(class_select)
	box.add_child(class_row)
	class_description = _wrap_label(str(CLASS_DESCRIPTIONS["knight"]), 14, GREEN)
	class_description.custom_minimum_size = Vector2(540, 40)
	box.add_child(class_description)
	class_select.item_selected.connect(func(index: int) -> void: class_description.text = str(CLASS_DESCRIPTIONS[CLASS_IDS[index]]))
	box.add_child(_label("Wybór klasy jest trwały. Logowanie zachowuje istniejącą klasę.", 13))
	var row: HBoxContainer = HBoxContainer.new()
	box.add_child(row)
	connect_button = _button("Wejdź do świata", func() -> void: _connect(false))
	connect_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(connect_button)
	create_button = _button("Utwórz postać", func() -> void: _connect(true))
	create_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(create_button)
	login_status = _wrap_label("Uruchom serwer z paczki, potem utwórz postać.", 14, GREEN)
	login_status.custom_minimum_size = Vector2(540, 38)
	box.add_child(login_status)
	box.add_child(_label("WASD: ruch · Spacja: atak · F: magia · E: rozmowa · J: zadania", 13))
	box.add_child(_label("Postęp zapisuje serwer. Przez internet używaj wss:// z TLS.", 13, Color("a7b8a6")))

func _bar(color: Color, height: float) -> ProgressBar:
	var bar: ProgressBar = ProgressBar.new()
	bar.custom_minimum_size.y = height
	bar.show_percentage = false
	var fill: StyleBoxFlat = _style(color, color, 3)
	fill.content_margin_top = 0
	fill.content_margin_bottom = 0
	bar.add_theme_stylebox_override("fill", fill)
	var back: StyleBoxFlat = _style(Color("1c3435"), Color("34554b"), 3)
	back.content_margin_top = 0
	back.content_margin_bottom = 0
	bar.add_theme_stylebox_override("background", back)
	return bar

func _build_hud(root: Control) -> void:
	hud = Control.new()
	hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.hide()
	root.add_child(hud)
	var top: PanelContainer = PanelContainer.new()
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 12
	top.offset_right = -12
	top.offset_top = 10
	top.offset_bottom = 118
	hud.add_child(top)
	var top_row: HBoxContainer = HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 20)
	top.add_child(top_row)
	var identity: VBoxContainer = VBoxContainer.new()
	identity.custom_minimum_size.x = 460
	top_row.add_child(identity)
	stats_label = _label("Podróżnik", 18, GOLD)
	stats_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	identity.add_child(stats_label)
	vital_label = _label("HP · Mana", 13)
	identity.add_child(vital_label)
	var bars: HBoxContainer = HBoxContainer.new()
	identity.add_child(bars)
	hp_bar = _bar(Color("87b991"), 9)
	hp_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bars.add_child(hp_bar)
	mana_bar = _bar(Color("75aeda"), 9)
	mana_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bars.add_child(mana_bar)
	xp_bar = _bar(GOLD, 5)
	identity.add_child(xp_bar)
	var status: VBoxContainer = VBoxContainer.new()
	status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_row.add_child(status)
	event_label = _label("BRACTWO · POGRANICZE", 15, GREEN)
	status.add_child(event_label)
	status_label = _label("Ochrona osady", 14)
	status.add_child(status_label)
	target_label = _label("Cel: potwory w zasięgu", 13, GREEN)
	status.add_child(target_label)
	fps_label = _label("— FPS", 12, PAPER)
	fps_label.custom_minimum_size.x = 64
	fps_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top_row.add_child(fps_label)
	top_row.add_child(_button("Wyjdź", _disconnect))
	hint_label = _label("", 14, GREEN)
	hint_label.position = Vector2(22, 128)
	hud.add_child(hint_label)
	var tracker_panel: PanelContainer = PanelContainer.new()
	tracker_panel.position = Vector2(14, 156)
	tracker_panel.custom_minimum_size = Vector2(380, 88)
	tracker_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(tracker_panel)
	quest_tracker = _wrap_label("J · Dziennik wypraw", 14, GOLD)
	quest_tracker.custom_minimum_size.x = 354
	quest_tracker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tracker_panel.add_child(quest_tracker)
	minimap = MINIMAP_SCRIPT.new()
	minimap.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	minimap.offset_left = -236
	minimap.offset_right = -14
	minimap.offset_top = 156
	minimap.offset_bottom = 316
	hud.add_child(minimap)
	battle_panel = PanelContainer.new()
	battle_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	battle_panel.offset_left = -236
	battle_panel.offset_right = -14
	battle_panel.offset_top = 325
	battle_panel.offset_bottom = 480
	hud.add_child(battle_panel)
	battle_list = VBoxContainer.new()
	battle_list.add_theme_constant_override("separation", 2)
	battle_panel.add_child(battle_list)
	battle_panel.hide()
	var notice_panel: PanelContainer = PanelContainer.new()
	notice_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	notice_panel.offset_left = 188
	notice_panel.offset_right = 664
	notice_panel.offset_top = -176
	notice_panel.offset_bottom = -12
	hud.add_child(notice_panel)
	var notice_box: VBoxContainer = VBoxContainer.new()
	notice_panel.add_child(notice_box)
	feed = _wrap_label("Witaj na Pograniczu.", 14)
	feed.custom_minimum_size = Vector2(430, 94)
	feed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	feed.clip_text = true
	notice_box.add_child(feed)
	chat_field = LineEdit.new()
	chat_field.placeholder_text = "Enter: wiadomość do graczy…"
	chat_field.max_length = 160
	chat_field.text_submitted.connect(_chat)
	chat_field.focus_entered.connect(_stop_controls)
	notice_box.add_child(chat_field)
	pad = PAD_SCRIPT.new()
	pad.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	pad.offset_left = 12
	pad.offset_right = 172
	pad.offset_top = -172
	pad.offset_bottom = -12
	hud.add_child(pad)
	var actions: VBoxContainer = VBoxContainer.new()
	actions.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	actions.offset_left = -588
	actions.offset_right = -12
	actions.offset_top = -221
	actions.offset_bottom = -12
	actions.add_theme_constant_override("separation", 6)
	hud.add_child(actions)
	var menus: HBoxContainer = HBoxContainer.new()
	actions.add_child(menus)
	menus.add_child(_button("I · Plecak", _toggle_inventory))
	menus.add_child(_button("P · Gracze", _toggle_party))
	menus.add_child(_button("J · Zadania", _toggle_journal))
	menus.add_child(_button("K · Księga", func() -> void: progression.toggle()))
	safety_button = _button("PvP zablokowane", _toggle_safety)
	safety_button.name = "PvpSafety"
	safety_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	menus.add_child(safety_button)
	var spellbar: HBoxContainer = HBoxContainer.new()
	actions.add_child(spellbar)
	spellbar.add_child(_button("3 · Leczenie", func() -> void: _send({"type":"cast", "spell_id":"mend"})))
	spellbar.add_child(_button("4 · Pośpiech", func() -> void: _send({"type":"cast", "spell_id":"haste"})))
	spellbar.add_child(_button("5 · Czar", func() -> void: _cast_level(30)))
	spellbar.add_child(_button("6 · Mistrz", func() -> void: _cast_level(80)))
	spellbar.add_child(_button("7 · Runa", func() -> void: _send({"type":"rune_use", "rune_id":"fire"})))
	var utilities: HBoxContainer = HBoxContainer.new()
	actions.add_child(utilities)
	health_button = _button("1 · Życie", func() -> void: _best_potion("health_potion"))
	health_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	utilities.add_child(health_button)
	mana_button = _button("2 · Mana", func() -> void: _best_potion("mana_potion"))
	mana_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	utilities.add_child(mana_button)
	utilities.add_child(_button("E · Rozmowa", _interact_nearby))
	var combat: HBoxContainer = HBoxContainer.new()
	actions.add_child(combat)
	ability_button = _button("F · Umiejętność", func() -> void: _send({"type":"ability"}))
	ability_button.name = "ClassAbility"
	ability_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	combat.add_child(ability_button)
	attack_button = _button("SPACJA · ATAK", _attack)
	attack_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	attack_button.button_down.connect(func() -> void: attack_held = true)
	attack_button.button_up.connect(func() -> void: attack_held = false)
	combat.add_child(attack_button)
	_add_notice("Strażniczka w osadzie szuka pomocy. E: rozmowa · J: dziennik · Enter: czat.")

func _window(title: String) -> PanelContainer:
	var panel: PanelContainer = PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	panel.offset_left = -676
	panel.offset_right = -12
	panel.offset_top = 150
	panel.offset_bottom = 530
	hud.add_child(panel)
	var box: VBoxContainer = VBoxContainer.new()
	panel.add_child(box)
	var heading: HBoxContainer = HBoxContainer.new()
	box.add_child(heading)
	var label: Label = _label(title, 19, GOLD)
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	heading.add_child(label)
	heading.add_child(_button("Zamknij", func() -> void: panel.hide()))
	panel.hide()
	return panel

func _build_inventory() -> void:
	inventory_panel = _window("PLECAK I WYPOSAŻENIE")
	inventory_panel.name = "InventoryPanel"
	inventory_panel.offset_bottom = 704
	var box: VBoxContainer = inventory_panel.get_child(0)
	inventory_stats = _wrap_label("", 14, GREEN)
	box.add_child(inventory_stats)
	legacy_row = HBoxContainer.new()
	legacy_row.add_child(_label("Klasa postaci z 0.1:", 14))
	legacy_select = _class_options()
	legacy_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	legacy_row.add_child(legacy_select)
	legacy_button = _button("Wybierz na stałe", func() -> void: _send({"type":"choose_class", "class_id":CLASS_IDS[legacy_select.selected]}))
	legacy_row.add_child(legacy_button)
	box.add_child(legacy_row)
	equipment_list = VBoxContainer.new()
	box.add_child(equipment_list)
	shop_label = _wrap_label("", 13, GREEN)
	box.add_child(shop_label)
	var shop: HBoxContainer = HBoxContainer.new()
	box.add_child(shop)
	buy_health = _button("Kup miksturę życia", func() -> void: _send({"type":"buy", "item":"health_potion"}))
	buy_health.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shop.add_child(buy_health)
	buy_mana = _button("Kup miksturę many", func() -> void: _send({"type":"buy", "item":"mana_potion"}))
	buy_mana.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shop.add_child(buy_mana)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.custom_minimum_size.y = 100
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	inventory_list = VBoxContainer.new()
	inventory_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(inventory_list)

func _build_party() -> void:
	party_panel = _window("GRACZE · DRUŻYNA · CEL PvP")
	party_panel.name = "PlayersPanel"
	party_panel.offset_bottom = 704
	var box: VBoxContainer = party_panel.get_child(0)
	party_summary = _wrap_label("", 14, GREEN)
	box.add_child(party_summary)
	var invite_row: HBoxContainer = HBoxContainer.new()
	box.add_child(invite_row)
	invite_label = _wrap_label("Brak zaproszenia.", 14)
	invite_row.add_child(invite_label)
	accept_invite = _button("Dołącz", func() -> void: _send({"type":"party_accept", "leader_id":pending_invite_id}))
	invite_row.add_child(accept_invite)
	var party_actions: HBoxContainer = HBoxContainer.new()
	box.add_child(party_actions)
	leave_party = _button("Opuść drużynę", func() -> void: _send({"type":"party_leave"}))
	party_actions.add_child(leave_party)
	party_actions.add_child(_button("Wyczyść cel PvP", func() -> void: _select_target("")))
	box.add_child(_wrap_label("Cel PvP wskazujesz ręcznie. Blokada ataków nie chroni przed cudzą agresją. F: potwory / leczenie; druid nie leczy sojusznika walczącego z graczem.", 13, Color("b6c5b3")))
	pvp_rules_label = _wrap_label("", 13, RED)
	box.add_child(pvp_rules_label)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.custom_minimum_size.y = 90
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	party_list = VBoxContainer.new()
	party_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(party_list)

func _connect(create: bool) -> void:
	if connecting:
		return
	var url: String = endpoint.text.strip_edges()
	if not (url.begins_with("ws://") or url.begins_with("wss://")):
		login_status.text = "Adres musi zaczynać się od ws:// lub wss://."
		return
	if username.text.strip_edges().length() < 3 or password.text.length() < 8:
		login_status.text = "Podaj nazwę (min. 3 znaki) i hasło (min. 8 znaków)."
		return
	_save_preferences()
	register_requested = create
	hello_sent = false
	connecting = true
	connect_button.disabled = true
	create_button.disabled = true
	connection_started = Time.get_ticks_msec() / 1000.0
	socket = WebSocketPeer.new()
	# The continent catalogue is ~2.4 MB; the default 64 KiB cannot receive it.
	socket.inbound_buffer_size = 8 * 1024 * 1024
	var error: Error = socket.connect_to_url(url)
	if error != OK:
		_fail("Nie można otworzyć połączenia: " + error_string(error))
	else:
		login_status.text = "Łączenie ze światem…"

func _process(delta: float) -> void:
	_poll_socket()
	fps_elapsed += delta
	if fps_elapsed >= 0.5:
		fps_elapsed = 0.0
		fps_label.text = "%d FPS" % Engine.get_frames_per_second()
	if local_id.is_empty():
		return
	input_elapsed += delta
	attack_elapsed += delta
	var typing: bool = get_viewport().gui_get_focus_owner() is LineEdit
	if input_elapsed >= 0.05:
		input_elapsed = 0.0
		var movement: Vector2 = Vector2.ZERO
		if app_focused and not typing and not _menu_open():
			movement = Input.get_vector("walk_left", "walk_right", "walk_up", "walk_down")
			if pad.vector.length() > movement.length():
				movement = pad.vector
		_send({"type":"input", "x":movement.x, "y":movement.y})
	if attack_elapsed >= 0.22 and app_focused and not typing and not _menu_open() and (attack_held or Input.is_action_pressed("strike")):
		attack_elapsed = 0.0
		_attack()

func _poll_socket() -> void:
	if socket == null:
		return
	socket.poll()
	var ready: int = socket.get_ready_state()
	if ready == WebSocketPeer.STATE_OPEN:
		if not hello_sent:
			hello_sent = true
			_send({"type":"hello", "name":username.text.strip_edges(), "password":password.text, "create":register_requested, "class_id":CLASS_IDS[class_select.selected], "compact_state":true})
		while socket != null and socket.get_available_packet_count() > 0:
			var raw: String = socket.get_packet().get_string_from_utf8()
			var parsed = JSON.parse_string(raw)
			if parsed is Dictionary:
				_handle_message(parsed)
	elif ready == WebSocketPeer.STATE_CLOSED:
		_fail("Połączenie zakończone. Możesz zalogować się ponownie.")
	if connecting and Time.get_ticks_msec() / 1000.0 - connection_started > 12.0:
		_fail("Serwer nie odpowiedział. Sprawdź adres i czy jest uruchomiony.")

func _handle_message(data: Dictionary) -> void:
	match str(data.get("type", "")):
		"welcome":
			local_id = str(data.get("id", ""))
			player = {}
			selected_enemy = ""
			selected_target = ""
			world_view.selected_enemy = ""
			world_view.selected_target = ""
			world_data = data.get("world", {})
			navigation_goal = {}
			progression.signature = ""
			progression.panel.hide()
			world_view.local_id = local_id
			world_view.set_world(world_data)
			connecting = false
			password.clear()
			login_panel.hide()
			hud.show()
			get_viewport().gui_release_focus()
		"state":
			if bool(data.get("owner_delta", false)):
				var entries: Array = data.get("players", [])
				for i: int in range(entries.size()):
					if str(entries[i].get("id", "")) == local_id:
						var merged: Dictionary = player.duplicate()
						merged.merge(entries[i], true)
						entries[i] = merged
			state = data
			world_view.set_state(data)
			_update_hud()
		"party_invite":
			pending_invite_id = str(data.get("leader_id", ""))
			pending_invite_name = str(data.get("name", "Gracz"))
			_add_notice(pending_invite_name + " zaprasza do drużyny. P → Dołącz.")
			last_players_key = ""
			_refresh_party()
		"notice":
			_add_notice(str(data.get("text", "")))
		"chat":
			_add_notice(str(data.get("name", "")) + ": " + str(data.get("text", "")))
		"error":
			if local_id.is_empty():
				_fail(str(data.get("text", "Nie udało się zalogować.")))
			else:
				_add_notice(str(data.get("text", "Nie można wykonać tej czynności.")))

func _send(data: Dictionary) -> void:
	if not selected_enemy.is_empty() and str(data.get("type", "")) in ["ability", "rune_use"]:
		data = data.duplicate()
		data["enemy_id"] = selected_enemy
	if socket != null and socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		socket.send_text(JSON.stringify(data))

func _fail(message: String) -> void:
	if socket != null:
		socket.close()
	socket = null
	connecting = false
	hello_sent = false
	local_id = ""
	attack_held = false
	selected_target = ""
	pending_invite_id = ""
	pending_invite_name = ""
	state = {}
	player = {}
	world_view.selected_target = ""
	world_view.set_state({})
	last_inventory_key = ""
	last_players_key = ""
	pad.reset()
	inventory_panel.hide()
	party_panel.hide()
	journal_panel.hide()
	chat_field.clear()
	last_journal_key = ""
	safety_confirm.hide()
	hud.hide()
	login_panel.show()
	connect_button.disabled = false
	create_button.disabled = false
	login_status.text = message

func _disconnect() -> void:
	_send({"type":"input", "x":0, "y":0})
	_fail("Wylogowano. Postęp zapisuje serwer; podczas walki postać pozostaje zagrożona.")

func _update_hud() -> void:
	player = _find_player(local_id)
	if player.is_empty():
		return
	var class_id: String = str(player.get("class_id", "knight"))
	stats_label.text = "%s · %s · poz. %d · %d zł" % [player.get("name", ""), player.get("profession", CLASS_NAMES.get(class_id, class_id)), int(player.get("level", 1)), int(player.get("gold", 0))]
	hp_bar.max_value = maxf(1, float(player.get("max_hp", 100)))
	hp_bar.value = float(player.get("hp", 100))
	mana_bar.max_value = maxf(1, float(player.get("max_mana", 1)))
	mana_bar.value = float(player.get("mana", 0))
	xp_bar.max_value = maxf(1, float(player.get("xp_next", 100)))
	xp_bar.value = float(player.get("xp", 0))
	vital_label.text = "HP %d/%d  Mana %d/%d  XP %d/%d  Ruch %.1f" % [int(hp_bar.value), int(hp_bar.max_value), int(mana_bar.value), int(mana_bar.max_value), int(xp_bar.value), int(xp_bar.max_value), float(player.get("speed", 100))]
	vital_label.text += " · Piętro %s%d" % ["+" if int(player.get("floor", 0)) > 0 else "", int(player.get("floor", 0))]
	if float(player.get("wind_remaining", 0)) > 0:
		vital_label.text += " · Wiatr +15%"
	if float(player.get("ward_remaining", 0)) > 0:
		vital_label.text += " · Osłona −12% PvE"
	vital_label.text += " · " + str(world_data.get("surfaces", {}).get(player.get("surface", "grass"), {}).get("name", "Trawa")) + (" · Premium test" if player.get("premium_demo", false) else "")
	var online: int = 0
	for entry: Dictionary in state.get("players", []):
		if not bool(entry.get("disconnected", false)):
			online += 1
	event_label.text = "POGRANICZE · online %d · ATK %d · Pancerz %d" % [online, int(player.get("attack", 0)), int(player.get("armor", 0))]
	var skull: String = str(player.get("skull", "none"))
	var skull_text: String = "Bez czaszki"
	if skull == "white":
		skull_text = "Biała czaszka %ds" % int(ceil(float(player.get("skull_remaining", 0))))
	elif skull == "red":
		skull_text = "Czerwona czaszka %dm" % int(ceil(float(player.get("skull_remaining", 0)) / 60.0))
	var combat: int = int(ceil(float(player.get("combat_remaining", 0))))
	var pvp_combat: int = int(ceil(float(player.get("pvp_combat_remaining", 0))))
	var combat_text: String = " · Walka PvP %ds — osada zamknięta" % pvp_combat if pvp_combat > 0 else (" · Walka %ds" % combat if combat > 0 else (" · Osada chroniona" if _in_town() else " · Poza osadą"))
	status_label.text = skull_text + combat_text
	status_label.add_theme_color_override("font_color", RED if skull != "none" or combat > 0 else PAPER)
	var rules: Dictionary = world_data.get("pvp_rules", {})
	if int(player.get("level", 1)) < int(rules.get("min_level", 8)):
		status_label.text += " · Ochrona poziomu"
	status_label.tooltip_text = "Nieuzasadnione zabójstwa: %d / %d w ostatnich 24 h" % [int(player.get("unjust_kills", 0)), int(rules.get("red_kills", 3))]
	var safe: bool = bool(player.get("pvp_safety", true))
	safety_button.text = "PvP: blokada ataku" if safe else "PvP: atak odblokowany"
	safety_button.add_theme_color_override("font_color", GREEN if safe else RED)
	var target: Dictionary = _find_enemy(selected_enemy) if not selected_enemy.is_empty() else _find_player(selected_target)
	if not target.is_empty() and (float(target.get("hp", 0)) <= 0 or int(target.get("floor", 0)) != int(player.get("floor", 0))):
		target = {}
	if target.is_empty() or not bool(player.get("alive", true)):
		selected_target = ""
		selected_enemy = ""
		world_view.selected_target = ""
		world_view.selected_enemy = ""
	if not selected_enemy.is_empty():
		target_label.text = "Cel: %s · %d/%d HP" % [target.get("name", ""), int(target.get("hp", 0)), int(target.get("max_hp", 1))]
		attack_button.text = "SPACJA · WYBRANY POTWÓR"
	else:
		target_label.text = "Cel: potwory w zasięgu" if selected_target.is_empty() else "Cel PvP: %s%s" % [target.get("name", "?"), " · ATAK ZABLOKOWANY" if safe else ""]
		attack_button.text = "SPACJA · POTWORY" if selected_target.is_empty() else "SPACJA · CEL PvP"
	target_label.add_theme_color_override("font_color", GREEN if selected_target.is_empty() else RED)
	_refresh_battle_list()
	var potions: Dictionary = player.get("potions", {})
	health_button.text = "1 · Życie ×%d" % _potion_count("health_potion")
	mana_button.text = "2 · Mana ×%d" % _potion_count("mana_potion")
	var potion_cooldown: float = float(player.get("potion_cooldown", 0))
	health_button.disabled = _potion_count("health_potion") <= 0 or not bool(player.get("alive", true)) or potion_cooldown > 0
	var potion_metadata: Dictionary = world_data.get("potions", {})
	health_button.tooltip_text = "Odnawia %d HP · wspólny czas odnowienia mikstur: %ds" % [int(potion_metadata.get("health_potion", {}).get("restore", 0)), int(ceil(potion_cooldown))]
	mana_button.tooltip_text = "Odnawia %d many · wspólny czas odnowienia mikstur: %ds" % [int(potion_metadata.get("mana_potion", {}).get("restore", 0)), int(ceil(potion_cooldown))]
	mana_button.disabled = _potion_count("mana_potion") <= 0 or not bool(player.get("alive", true)) or potion_cooldown > 0
	var cooldown: float = float(player.get("ability_cooldown", 0))
	ability_button.text = "F · " + str(player.get("ability_name", "Umiejętność")) + (" (%ds)" % int(ceil(cooldown)) if cooldown > 0 else "")
	var class_spec: Dictionary = world_data.get("classes", {}).get(class_id, {})
	var ability_cost: int = int(class_spec.get("ability_cost", 0))
	ability_button.disabled = cooldown > 0 or not bool(player.get("alive", true)) or float(player.get("mana", 0)) < ability_cost
	ability_button.tooltip_text = "Koszt: %d many. Umiejętności ofensywne trafiają wyłącznie potwory. Druid leczy drużynę poza walką PvP." % ability_cost
	if not bool(player.get("alive", true)):
		hint_label.text = "Pokonano cię. Za chwilę wrócisz do osady z karą za śmierć."
	elif not bool(player.get("class_chosen", true)):
		hint_label.text = "Postać z wersji 0.1: wybierz stałą klasę w osadzie (I → wybór klasy)."
	elif not _nearest_npc().is_empty() and not _merchant_is_nearest():
		hint_label.text = "E · " + str(_nearest_npc().get("name", "Rozmowa")) + " · J: dziennik wypraw · Enter: powiedz coś"
	elif _near_merchant():
		hint_label.text = "E · Kupiec: kup mikstury, sprzedaj łupy · I: załóż sprzęt · P: zaproś graczy"
	else:
		hint_label.text = "J: dziennik i kierunek wyprawy · Enter: czat · F: umiejętność · 1/2: mikstury"
	if str(player.get("party_id", "")) == pending_invite_id and not pending_invite_id.is_empty():
		pending_invite_id = ""
		pending_invite_name = ""
	if inventory_panel.visible:
		_refresh_inventory()
	if party_panel.visible:
		_refresh_party()
	progression.refresh()
	_refresh_tracker()
	minimap.set_data(world_data, state, local_id)
	if journal_panel.visible:
		_refresh_journal()

func _find_player(id: String) -> Dictionary:
	for candidate: Dictionary in state.get("players", []):
		if str(candidate.get("id", "")) == id:
			return candidate
	return {}

func _in_town() -> bool:
	for zone: Dictionary in world_data.get("safe_zones", [world_data.get("safe_zone", {})]):
		if _near_point(zone):
			return true
	return false

func _near_point(point: Dictionary) -> bool:
	return int(player.get("floor", 0)) == int(point.get("floor", 0)) and Vector2(float(player.get("x", 0)), float(player.get("y", 0))).distance_to(Vector2(float(point.get("x", 0)), float(point.get("y", 0)))) <= float(point.get("radius", 150))

func _near_merchant() -> bool:
	if _near_point(world_data.get("merchant", {"x":680, "y":1180})):
		return true
	return not progression.near_service("merchant").is_empty()

func _merchant_data() -> Dictionary:
	var nearby: Dictionary = progression.near_service("merchant")
	return nearby if not nearby.is_empty() else world_data.get("merchant", {})

func _toggle_inventory() -> void:
	progression.panel.hide()
	inventory_panel.visible = not inventory_panel.visible
	party_panel.hide()
	journal_panel.hide()
	_stop_controls()
	attack_held = false
	if inventory_panel.visible:
		_refresh_inventory()

func _toggle_party() -> void:
	progression.panel.hide()
	party_panel.visible = not party_panel.visible
	inventory_panel.hide()
	journal_panel.hide()
	_stop_controls()
	attack_held = false
	if party_panel.visible:
		_refresh_party()

func _merchant() -> void:
	_send({"type":"interact"})
	inventory_panel.show()
	party_panel.hide()
	journal_panel.hide()
	_stop_controls()
	_refresh_inventory()

func _clear_children(parent: Node) -> void:
	for child: Node in parent.get_children():
		parent.remove_child(child)
		child.queue_free()

func _item_by_uid(uid: String) -> Dictionary:
	for item: Dictionary in player.get("inventory", []):
		if str(item.get("uid", "")) == uid:
			return item
	return {}

func _item_equipped(uid: String) -> bool:
	var equipment: Dictionary = player.get("equipment", {})
	return equipment.values().has(uid)

func _item_usable(item: Dictionary) -> bool:
	if str(item.get("slot", "")) == "trophy":
		return false
	var classes: Array = item.get("class_ids", [])
	return int(player.get("level", 1)) >= int(item.get("min_level", 1)) and (classes.is_empty() or classes.has(str(player.get("class_id", "knight"))))

func _item_details(item: Dictionary) -> String:
	var classes: Array[String] = []
	for class_id in item.get("class_ids", []):
		classes.append(str(CLASS_NAMES.get(str(class_id), class_id)))
	var details: String = "%s · ATK +%d · Pancerz +%d · poz. %d" % [SLOT_NAMES.get(str(item.get("slot", "")), "Sprzęt"), int(item.get("attack", 0)), int(item.get("armor", 0)), int(item.get("min_level", 1))]
	if not classes.is_empty():
		details += " · " + "/".join(classes)
	details += " · " + str(world_data.get("rarities", {}).get(item.get("rarity", "common"), "Pospolity"))
	if str(item.get("slot", "")) == "trophy":
		return "Trofeum · " + str(item.get("description", "Na sprzedaż"))
	return details

func _refresh_inventory() -> void:
	var inventory: Array = player.get("inventory", [])
	var equipment: Dictionary = player.get("equipment", {})
	var near: bool = _near_merchant()
	var trading: bool = near and float(player.get("combat_remaining", 0)) <= 0 and bool(player.get("alive", true))
	var key: String = JSON.stringify([inventory, equipment, player.get("gold", 0), player.get("level", 1), player.get("attack", 0), player.get("armor", 0), player.get("class_id", "knight"), player.get("class_chosen", true), _in_town(), near, trading])
	if key == last_inventory_key:
		return
	last_inventory_key = key
	inventory_stats.text = "ATK %d · Pancerz %d · Złoto %d · Przedmioty %d/%d" % [int(player.get("attack", 0)), int(player.get("armor", 0)), int(player.get("gold", 0)), inventory.size(), int(world_data.get("inventory_cap", 40))]
	legacy_row.visible = not bool(player.get("class_chosen", true))
	legacy_button.disabled = not _in_town()
	legacy_button.tooltip_text = "Jednorazowy wybór klasy — tylko w osadzie."
	_clear_children(equipment_list)
	for slot: String in ["weapon", "armor", "ring"]:
		var uid: String = str(equipment.get(slot, ""))
		var item: Dictionary = _item_by_uid(uid)
		var row: HBoxContainer = HBoxContainer.new()
		equipment_list.add_child(row)
		var label: Label = _wrap_label(str(SLOT_NAMES[slot]) + ": " + str(item.get("name", "puste")), 14, GOLD)
		row.add_child(label)
		var remove: Button = _button("Zdejmij", func() -> void: _send({"type":"unequip", "slot":slot}))
		remove.custom_minimum_size.y = 32
		remove.disabled = uid.is_empty()
		row.add_child(remove)
	shop_label.text = "Kupiec w zasięgu · kup mikstury lub sprzedaj niezałożony sprzęt." if trading else ("Zakończ walkę, aby odpocząć i handlować." if near else "Handel dostępny przy kupcu w osadzie.")
	buy_health.disabled = not trading
	buy_mana.disabled = not trading
	var merchant: Dictionary = _merchant_data()
	var prices: Dictionary = merchant.get("prices", {})
	buy_health.text = "Kup życie" + (" · %d zł" % int(prices["health_potion"]) if prices.has("health_potion") else "")
	buy_mana.text = "Kup manę" + (" · %d zł" % int(prices["mana_potion"]) if prices.has("mana_potion") else "")
	_clear_children(inventory_list)
	if inventory.is_empty():
		inventory_list.add_child(_label("Brak sprzętu. Potwory mogą upuścić nowe przedmioty.", 14))
	for item: Dictionary in inventory:
		var uid: String = str(item.get("uid", ""))
		var equipped: bool = _item_equipped(uid)
		var row: HBoxContainer = HBoxContainer.new()
		inventory_list.add_child(row)
		var info: VBoxContainer = VBoxContainer.new()
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(info)
		info.add_child(_wrap_label(str(item.get("name", "Przedmiot")) + (" · założone" if equipped else ""), 15, GOLD if equipped else PAPER))
		info.add_child(_wrap_label(_item_details(item), 12, GREEN if _item_usable(item) else RED))
		var equip: Button = _button("Załóż", func() -> void: _send({"type":"equip", "uid":uid}))
		equip.disabled = equipped or not _item_usable(item)
		row.add_child(equip)
		equip.visible = str(item.get("slot", "")) != "trophy"
		var sell: Button = _button("Sprzedaj\n%d zł" % int(item.get("value", 0)), func() -> void: _send({"type":"sell", "uid":uid}))
		sell.disabled = equipped or not trading
		sell.add_theme_font_size_override("font_size", 13)
		sell.tooltip_text = "Sprzedaje ten przedmiot kupcowi. Założony sprzęt trzeba najpierw zdjąć."
		row.add_child(sell)

func _refresh_party() -> void:
	var entries: Array = []
	for candidate: Dictionary in state.get("players", []):
		entries.append([candidate.get("id", ""), candidate.get("name", ""), candidate.get("level", 1), candidate.get("class_id", ""), candidate.get("party_id", ""), candidate.get("skull", "none"), candidate.get("disconnected", false)])
	var key: String = JSON.stringify([entries, player.get("party_id", ""), player.get("party_members", []), pending_invite_id, pending_invite_name, selected_target])
	if key == last_players_key:
		return
	last_players_key = key
	var rules: Dictionary = world_data.get("pvp_rules", {})
	pvp_rules_label.text = "PvP od poziomu %d, poza osadą. Biała czaszka po agresji: %ds. %d nieuzasadnione zabójstwa / 24 h: czerwona czaszka na 24 h.\nŚmierć: −%d%% złota i −%d%% bieżącego XP. Czerwona czaszka: −%d%% złota i −%d%% XP oraz 1 niezałożony przedmiot. Bez utraty poziomu.\nPodczas walki PvP nie wejdziesz do osady. Rozłączenie w walce nie chroni postaci." % [int(rules.get("min_level", 8)), int(rules.get("white_seconds", 120)), int(rules.get("red_kills", 3)), int(float(rules.get("normal_gold_loss", 0.05))*100), int(float(rules.get("normal_xp_loss", 0.10))*100), int(float(rules.get("red_gold_loss", 0.20))*100), int(float(rules.get("red_xp_loss", 0.20))*100)]
	var party_id: String = str(player.get("party_id", ""))
	var members: Array = player.get("party_members", [])
	var party_rules: Dictionary = world_data.get("party_rules", {})
	party_summary.text = "Solo · zaproś gracza, aby dzielić doświadczenie w pobliżu." if party_id.is_empty() else "Drużyna %d/%d · dzielenie XP w promieniu %d, poziomy maks. %d:1; indywidualny loot." % [members.size(), int(party_rules.get("max_members", 4)), int(party_rules.get("range", 650)), int(party_rules.get("max_level_ratio", 3))]
	invite_label.text = "Zaprasza: " + pending_invite_name if not pending_invite_id.is_empty() else "Brak zaproszenia."
	accept_invite.disabled = pending_invite_id.is_empty() or not party_id.is_empty()
	leave_party.disabled = party_id.is_empty()
	_clear_children(party_list)
	var others: int = 0
	for candidate: Dictionary in state.get("players", []):
		var id: String = str(candidate.get("id", ""))
		if id == local_id:
			continue
		others += 1
		var row: HBoxContainer = HBoxContainer.new()
		party_list.add_child(row)
		var name_text: String = "%s · %s · poz. %d" % [candidate.get("name", ""), CLASS_NAMES.get(str(candidate.get("class_id", "")), "?"), int(candidate.get("level", 1))]
		var skull: String = str(candidate.get("skull", "none"))
		if skull != "none":
			name_text += " · " + ("CZERWONA CZASZKA" if skull == "red" else "biała czaszka")
		if bool(candidate.get("disconnected", false)):
			name_text += " · rozłączony"
		if members.has(id):
			name_text += " · w drużynie"
		row.add_child(_wrap_label(name_text, 14, RED if skull != "none" else PAPER))
		var invite: Button = _button("Zaproś", func() -> void: _send({"type":"party_invite", "target_id":id}))
		invite.disabled = members.has(id) or bool(candidate.get("disconnected", false)) or (not party_id.is_empty() and party_id != local_id)
		row.add_child(invite)
		var target: Button = _button("Wybrany cel" if selected_target == id else "Cel PvP", func() -> void: _select_target(id))
		target.add_theme_color_override("font_color", RED)
		row.add_child(target)
	if others == 0:
		party_list.add_child(_wrap_label("Nie ma innych graczy. Możesz samodzielnie polować i rozwijać postać.", 14))

func _toggle_safety() -> void:
	attack_held = false
	if bool(player.get("pvp_safety", true)):
		var rules: Dictionary = world_data.get("pvp_rules", {})
		safety_confirm.dialog_text = "Atak wymaga wybrania konkretnej postaci.\nNieuzasadniona agresja: biała czaszka.\n%d nieuzasadnione zabójstwa / 24 h: czerwona czaszka i surowsza kara śmierci.\nPvP od poziomu %d, poza chronioną osadą." % [int(rules.get("red_kills", 3)), int(rules.get("min_level", 8))]
		safety_confirm.popup_centered(Vector2i(620, 240))
	else:
		_send({"type":"pvp_safety", "enabled":true})
		_select_target("")

func _select_target(id: String) -> void:
	selected_enemy = ""
	world_view.selected_enemy = ""
	selected_target = id
	world_view.selected_target = id
	attack_held = false
	last_players_key = ""
	if not id.is_empty():
		_add_notice("Wybrano cel PvP: " + str(_find_player(id).get("name", "?")) + ". Spacja zaatakuje go po odblokowaniu PvP.")
	_update_hud()

func _attack() -> void:
	if local_id.is_empty() or not bool(player.get("alive", true)):
		return
	if not selected_enemy.is_empty():
		_send({"type":"attack", "enemy_id":selected_enemy})
	elif selected_target.is_empty():
		_send({"type":"attack"})
	elif not bool(player.get("pvp_safety", true)):
		_send({"type":"attack", "target_id":selected_target})
	else:
		_add_notice("Atak PvP zablokowany. Odblokuj PvP albo wyczyść cel w panelu P.")

func _chat(message: String) -> void:
	if not message.strip_edges().is_empty():
		_send({"type":"chat", "text":message.strip_edges()})
	chat_field.clear()
	chat_field.release_focus()

func _add_notice(message: String) -> void:
	if not notices.is_empty() and notices.back() == message:
		return
	notices.append(message)
	while notices.size() > 4:
		notices.pop_front()
	feed.text = "\n".join(notices)

func _find_enemy(id: String) -> Dictionary:
	for enemy: Dictionary in state.get("enemies", []):
		if str(enemy.get("id", "")) == id:
			return enemy
	return {}

func _select_enemy(id: String) -> void:
	var enemy: Dictionary = _find_enemy(id)
	if enemy.is_empty() or float(enemy.get("hp", 0)) <= 0 or int(enemy.get("floor", 0)) != int(player.get("floor", 0)):
		return
	selected_enemy = id
	selected_target = ""
	world_view.selected_enemy = id
	world_view.selected_target = ""
	get_viewport().gui_release_focus()
	_update_hud()

func _refresh_battle_list() -> void:
	var enemies: Array = []
	var here: Vector2 = Vector2(player.get("x", 0), player.get("y", 0))
	for enemy: Dictionary in state.get("enemies", []):
		var point: Vector2 = Vector2(enemy.get("x", 0), enemy.get("y", 0))
		if float(enemy.get("hp", 0)) > 0 and int(enemy.get("floor", 0)) == int(player.get("floor", 0)) and (here.distance_to(point) < 500 or str(enemy["id"]) == selected_enemy):
			enemies.append(enemy)
	enemies.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		if (str(a["id"]) == selected_enemy) != (str(b["id"]) == selected_enemy):
			return str(a["id"]) == selected_enemy
		return here.distance_squared_to(Vector2(a["x"], a["y"])) < here.distance_squared_to(Vector2(b["x"], b["y"])))
	if enemies.size() > 4:
		enemies.resize(4)
	var present: Dictionary = {}
	for i: int in range(enemies.size()):
		var enemy: Dictionary = enemies[i]
		var id: String = str(enemy["id"])
		present[id] = true
		var button: Button = battle_buttons.get(id)
		if button == null:
			button = _button("", func() -> void: _select_enemy(id))
			button.custom_minimum_size = Vector2(200, 28)
			button.add_theme_font_size_override("font_size", 12)
			button.clip_text = true
			button.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			battle_buttons[id] = button
			battle_list.add_child(button)
		button.text = "%s%s · %d%%" % ["▸ " if id == selected_enemy else "", enemy.get("name", ""), int(float(enemy["hp"]) / maxf(1, float(enemy["max_hp"])) * 100)]
		button.add_theme_color_override("font_color", RED if id == selected_enemy else PAPER)
		if button.get_index() != i:
			battle_list.move_child(button, i)
	for id: String in battle_buttons.keys():
		if not present.has(id):
			battle_buttons[id].queue_free()
			battle_buttons.erase(id)
	battle_panel.visible = not enemies.is_empty() and not _menu_open()

func _unhandled_input(event: InputEvent) -> void:
	if local_id.is_empty() or _menu_open() or not bool(player.get("alive", true)):
		return
	var point: Vector2
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		point = event.position
	elif event is InputEventScreenTouch and event.pressed:
		point = event.position
	else:
		return
	var hit: Dictionary = world_view.pick_actor(point)
	if not hit.is_empty():
		if hit["kind"] == "enemies":
			_select_enemy(hit["id"])
		else:
			_select_target(hit["id"])
		get_viewport().set_input_as_handled()

func _input(event: InputEvent) -> void:
	# Handle Enter before GUI shortcuts, including a focused HUD button or chat field.
	if local_id.is_empty() or not event is InputEventKey or not event.pressed or event.echo:
		return
	var key: int = event.physical_keycode if event.physical_keycode != 0 else event.keycode
	if key == KEY_ENTER or key == KEY_KP_ENTER:
		if safety_confirm.visible:
			return
		if chat_field.has_focus():
			_chat(chat_field.text)
		elif not get_viewport().gui_get_focus_owner() is LineEdit:
			_stop_controls()
			chat_field.grab_focus()
		get_viewport().set_input_as_handled()
	elif key == KEY_ESCAPE and chat_field.has_focus():
		chat_field.clear()
		chat_field.release_focus()
		get_viewport().set_input_as_handled()

func _unhandled_key_input(event: InputEvent) -> void:
	if local_id.is_empty() or not event is InputEventKey or not event.pressed or event.echo:
		return
	if get_viewport().gui_get_focus_owner() is LineEdit or safety_confirm.visible:
		return
	match event.physical_keycode:
		KEY_E:
			_interact_nearby()
		KEY_F:
			if not _menu_open():
				_send({"type":"ability"})
		KEY_1:
			_best_potion("health_potion")
		KEY_2:
			_best_potion("mana_potion")
		KEY_I:
			_toggle_inventory()
		KEY_P:
			_toggle_party()
		KEY_K:
			progression.toggle()
		KEY_3:
			_send({"type":"cast", "spell_id":"mend"})
		KEY_4:
			_send({"type":"cast", "spell_id":"haste"})
		KEY_5:
			_cast_level(30)
		KEY_6:
			_cast_level(80)
		KEY_7:
			_send({"type":"rune_use", "rune_id":"fire"})
		KEY_J:
			_toggle_journal()
		KEY_ESCAPE:
			progression.panel.hide()
			inventory_panel.hide()
			party_panel.hide()
			journal_panel.hide()
			_select_target("")

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		app_focused = false
		attack_held = false
		if is_instance_valid(pad):
			pad.reset()
		_send({"type":"input", "x":0, "y":0})
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN:
		app_focused = true
	elif what == NOTIFICATION_WM_CLOSE_REQUEST:
		_send({"type":"input", "x":0, "y":0})
		if socket != null:
			socket.close()

func _load_preferences() -> void:
	var config: ConfigFile = ConfigFile.new()
	if config.load("user://preferences.cfg") == OK:
		endpoint.text = str(config.get_value("connection", "url", endpoint.text))
		username.text = str(config.get_value("connection", "name", ""))

func _save_preferences() -> void:
	var config: ConfigFile = ConfigFile.new()
	config.set_value("connection", "url", endpoint.text.strip_edges())
	config.set_value("connection", "name", username.text.strip_edges())
	config.save("user://preferences.cfg")

func _stop_controls() -> void:
	attack_held = false
	if is_instance_valid(pad):
		pad.reset()
	_send({"type":"input", "x":0, "y":0})

func _menu_open() -> bool:
	return safety_confirm.visible or inventory_panel.visible or party_panel.visible or journal_panel.visible or progression.panel.visible

func _nearest_npc() -> Dictionary:
	var here: Vector2 = Vector2(float(player.get("x", -1000)), float(player.get("y", -1000)))
	var best: Dictionary = {}
	var distance: float = INF
	for npc: Dictionary in world_data.get("npcs", []):
		var d: float = here.distance_to(Vector2(float(npc.get("x", 0)), float(npc.get("y", 0))))
		if int(player.get("floor", 0)) == int(npc.get("floor", 0)) and d <= float(npc.get("radius", 150)) and d < distance:
			distance = d
			best = npc
	return best

func _npc_by_id(id: String) -> Dictionary:
	for npc: Dictionary in world_data.get("npcs", []):
		if str(npc.get("id", "")) == id:
			return npc
	return {}

func _npc_in_range(id: String) -> bool:
	var npc: Dictionary = _npc_by_id(id)
	var here: Vector2 = Vector2(float(player.get("x", -1000)), float(player.get("y", -1000)))
	return not npc.is_empty() and int(npc.get("floor", 0)) == int(player.get("floor", 0)) and bool(player.get("alive", true)) and here.distance_to(Vector2(float(npc.get("x", 0)), float(npc.get("y", 0)))) <= float(npc.get("radius", 150))

func _merchant_is_nearest() -> bool:
	if not _near_merchant():
		return false
	var npc: Dictionary = _nearest_npc()
	if npc.is_empty():
		return true
	var merchant: Dictionary = _merchant_data()
	var here: Vector2 = Vector2(float(player.get("x", 0)), float(player.get("y", 0)))
	var merchant_distance: float = here.distance_to(Vector2(float(merchant.get("x", 680)), float(merchant.get("y", 1180))))
	var npc_distance: float = here.distance_to(Vector2(float(npc.get("x", 0)), float(npc.get("y", 0))))
	return merchant_distance < npc_distance

func _interact_nearby() -> void:
	for stair: Dictionary in world_data.get("stairs", []):
		if _near_point(stair):
			_send({"type":"descend"})
			return
	for site: Dictionary in world_data.get("pois", []):
		if _near_point(site):
			_send({"type":"interact"})
			return
	var nearest: Dictionary = _nearest_npc()
	if not str(nearest.get("service", "")).is_empty():
		progression.show_book("Rozwój" if nearest.get("service", "") == "master" else "Usługi")
		return
	var npc: Dictionary = _nearest_npc()
	if _merchant_is_nearest():
		_merchant()
	elif not npc.is_empty():
		journal_panel.show()
		inventory_panel.hide()
		party_panel.hide()
		_stop_controls()
		last_journal_key = ""
		_refresh_journal()
	else:
		_add_notice("Podejdź do postaci w osadzie. J: dziennik pokazuje cele i ich kierunek.")

func _build_journal() -> void:
	journal_panel = _window("DZIENNIK WYPRAW · ZADANIA I ODKRYCIA")
	journal_panel.name = "JournalPanel"
	journal_panel.offset_bottom = 704
	var box: VBoxContainer = journal_panel.get_child(0)
	box.add_child(_wrap_label("Przyjmuj i odbieraj zadania u zleceniodawcy (E). Odkrycia zapisują się podczas podróży. Rozwój i nagrody przechowuje serwer.", 14, GREEN))
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size.y = 360
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	box.add_child(scroll)
	journal_list = VBoxContainer.new()
	journal_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	journal_list.add_theme_constant_override("separation", 10)
	scroll.add_child(journal_list)

func _toggle_journal() -> void:
	progression.panel.hide()
	journal_panel.visible = not journal_panel.visible
	inventory_panel.hide()
	party_panel.hide()
	_stop_controls()
	if journal_panel.visible:
		last_journal_key = ""
		_refresh_journal()

func _direction_to(point: Dictionary) -> String:
	if int(point.get("floor", 0)) != int(player.get("floor", 0)):
		return "Piętro %d · szukaj schodów" % int(point.get("floor", 0))
	if not point.has("x") or not point.has("y"):
		return ""
	var delta: Vector2 = Vector2(float(point["x"]) - float(player.get("x", 0)), float(point["y"]) - float(player.get("y", 0)))
	var direction: String = "blisko"
	if delta.length() > 80:
		var vertical: String = "północ" if delta.y < 0 else "południe"
		var horizontal: String = "zachód" if delta.x < 0 else "wschód"
		direction = horizontal if absf(delta.x) > absf(delta.y) * 2 else (vertical if absf(delta.y) > absf(delta.x) * 2 else vertical + " / " + horizontal)
	return "%s · %d kroków" % [direction, int(delta.length() / 32.0)]

func _objective_location(objective: Dictionary) -> Dictionary:
	if objective.has("x") and objective.has("y"):
		return objective
	if str(objective.get("type", "")) == "discover":
		for landmark: Dictionary in world_data.get("landmarks", []):
			if str(landmark.get("id", "")) == str(objective.get("target", "")):
				return landmark
	else:
		var best: Dictionary = {}
		var distance: float = INF
		var here: Vector2 = Vector2(float(player.get("x", 0)), float(player.get("y", 0)))
		for enemy: Dictionary in state.get("enemies", []):
			if str(enemy.get("kind", "")) != str(objective.get("target", "")):
				continue
			var d: float = here.distance_to(Vector2(float(enemy.get("x", 0)), float(enemy.get("y", 0))))
			if d < distance:
				distance = d
				best = enemy
		return best if not best.is_empty() else objective
	return {}

func _refresh_tracker() -> void:
	for site: Dictionary in world_data.get("pois", []):
		if _near_point(site):
			var remaining: int = int(player.get("site_cooldowns", {}).get(site["id"], 0))
			quest_tracker.text = str(site["name"]) + "\n" + ("Odnowienie: %d s" % remaining if remaining > 0 else "E · użyj")
			return
	if not navigation_goal.is_empty():
		quest_tracker.text = str(navigation_goal.get("label", "Cel")) + "\n" + _direction_to(navigation_goal) + " · usuń w Atlasie [K]"
		return
	var tracked: Dictionary = {}
	for wanted: String in ["ready", "active", "available"]:
		for quest: Dictionary in player.get("quests", []):
			if str(quest.get("status", "")) == wanted:
				tracked = quest
				break
		if not tracked.is_empty():
			break
	if tracked.is_empty():
		quest_tracker.text = "J · DZIENNIK WYPRAW\nPoznane miejsca: %d/%d\nSzukaj łupów, rozwijaj postać i zbierz drużynę." % [player.get("discoveries", []).size(), world_data.get("landmarks", []).size()]
		return
	var lines: Array[String] = ["J · " + str(tracked.get("title", "Wyprawa"))]
	var status: String = str(tracked.get("status", ""))
	if status == "active":
		for objective: Dictionary in tracked.get("objectives", []):
			if int(objective.get("count", 0)) < int(objective.get("required", 1)):
				lines.append("%s %d/%d" % [objective.get("label", "Cel"), int(objective.get("count", 0)), int(objective.get("required", 1))])
				lines.append(_direction_to(_objective_location(objective)))
				break
	else:
		var npc: Dictionary = _npc_by_id(str(tracked.get("npc_id", "")))
		lines.append(("Odbierz nagrodę: " if status == "ready" else "Porozmawiaj: ") + str(npc.get("name", "Zleceniodawca")))
		lines.append(_direction_to(npc))
	quest_tracker.text = "\n".join(lines)

func _refresh_journal() -> void:
	var in_range: Array[bool] = []
	for quest: Dictionary in player.get("quests", []):
		in_range.append(_npc_in_range(str(quest.get("npc_id", ""))))
	var key: String = JSON.stringify([player.get("quests", []), player.get("discoveries", []), in_range])
	if key == last_journal_key:
		return
	last_journal_key = key
	_clear_children(journal_list)
	var statuses: Dictionary = {"locked":"Dalsza wyprawa", "available":"Do przyjęcia", "active":"W toku", "ready":"Nagroda czeka", "claimed":"Ukończone"}
	for quest: Dictionary in player.get("quests", []):
		var id: String = str(quest.get("id", ""))
		var status: String = str(quest.get("status", "locked"))
		var color: Color = GOLD if status == "ready" else (GREEN if status == "active" or status == "available" else Color("9aa998"))
		journal_list.add_child(_wrap_label(str(quest.get("title", "Zadanie")) + " · " + str(statuses.get(status, status)), 17, color))
		journal_list.add_child(_wrap_label(str(quest.get("description", "")), 13))
		for objective: Dictionary in quest.get("objectives", []):
			journal_list.add_child(_wrap_label("%s: %d/%d" % [objective.get("label", "Cel"), int(objective.get("count", 0)), int(objective.get("required", 1))], 14, color))
		var reward: Dictionary = quest.get("reward", {})
		var reward_text: String = "Nagroda: %d XP · %d zł" % [int(reward.get("xp", 0)), int(reward.get("gold", 0))]
		if reward.has("item"):
			var item_id: String = str(reward["item"])
			if item_id.begins_with("class_weapon_"):
				item_id = str(player.get("class_id", "knight")) + "_weapon_" + item_id.get_slice("_", 2)
			reward_text += " · " + str(world_data.get("items", {}).get(item_id, {}).get("name", "przedmiot"))
		for potion_id: String in reward.get("potions", {}):
			reward_text += " · %d × %s" % [int(reward["potions"][potion_id]), "mikstura życia" if potion_id == "health_potion" else "mikstura many"]
		journal_list.add_child(_wrap_label(reward_text, 13, GOLD))
		var npc: Dictionary = _npc_by_id(str(quest.get("npc_id", "")))
		journal_list.add_child(_wrap_label("Zleceniodawca: " + str(npc.get("name", "?")), 13, GREEN))
		if status == "available" or status == "ready":
			var command: String = "quest_claim" if status == "ready" else "quest_accept"
			var action: Button = _button("Odbierz nagrodę" if status == "ready" else "Przyjmij zadanie", func() -> void: _send({"type":command, "quest_id":id}))
			action.disabled = not _npc_in_range(str(quest.get("npc_id", "")))
			action.tooltip_text = "Podejdź do zleceniodawcy, aby porozmawiać."
			journal_list.add_child(action)
	journal_list.add_child(_label("ODKRYTE MIEJSCA", 17, GOLD))
	var discoveries: Array = player.get("discoveries", [])
	for landmark: Dictionary in world_data.get("landmarks", []):
		var known: bool = discoveries.has(str(landmark.get("id", "")))
		journal_list.add_child(_wrap_label(("✓ " if known else "◇ ") + str(landmark.get("name", "Miejsce")), 15, GREEN if known else PAPER))
		journal_list.add_child(_wrap_label(str(landmark.get("description", "")) if known else "Odwiedź to miejsce, aby poznać jego historię i dostać nagrodę.", 13))

func _cast_level(level: int) -> void:
	for id: String in world_data.get("spells", {}):
		var spell: Dictionary = world_data["spells"][id]
		if int(spell["min_level"]) == level and spell.get("class_ids", []).has(player.get("class_id", "")):
			_send({"type":"cast", "spell_id":id})
			return

func _best_potion(prefix: String) -> void:
	var best: String = prefix
	var restore: int = 0
	for id: String in world_data.get("potions", {}):
		var spec: Dictionary = world_data["potions"][id]
		if id.begins_with(prefix) and int(player.get("potions", {}).get(id, 0)) > 0 and int(player.get("level", 1)) >= int(spec.get("min_level", 1)) and int(spec["restore"]) > restore:
			best = id
			restore = int(spec["restore"])
	_send({"type":"potion", "item":best})

func _potion_count(prefix: String) -> int:
	var count: int = 0
	for key: String in player.get("potions", {}):
		if key.begins_with(prefix):
			count += int(player["potions"][key])
	return count
