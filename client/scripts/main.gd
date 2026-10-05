extends Node
## Server-authoritative native client: class, equipment, parties and deliberate PvP.
const WORLD_SCRIPT = preload("res://scripts/world_view.gd")
const PAD_SCRIPT = preload("res://scripts/input_pad.gd")
const MINIMAP_SCRIPT = preload("res://scripts/minimap.gd")
const CLASS_IDS: Array[String] = ["knight", "ranger", "mage", "druid"]
const CLASS_NAMES: Dictionary = {"knight":"Rycerz", "ranger":"Łowca", "mage":"Czarodziej", "druid":"Druid"}
const CLASS_DESCRIPTIONS: Dictionary = {
	"knight":"Wybór stylu, mistrzostwo broni, kolczuga i tarcza. Drugi oddech bez many.",
	"ranger":"Łuk, I krąg i bezpłatny Znak łowcy od początku; wilk od poziomu 3.",
	"mage":"Różdżka: 1k4. Darmowe sztuczki; I krąg od poziomu 1, II od 3, dalsze co 2.",
	"druid":"Wybór Strażnika lub Mistyka natury; I krąg od 1., wilk i kot od 2. poziomu."
}
const SLOT_NAMES: Dictionary = {"weapon":"Broń", "armor":"Pancerz", "shield":"Tarcza", "ring":"Pierścień", "trophy":"Trofeum"}
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
var level_up_panels = preload("res://scripts/level_up.gd").new()
var fighter_choice = preload("res://scripts/fighter_choice.gd").new()
var caster_choice = preload("res://scripts/caster_choice.gd").new()
var character_sheet = preload("res://scripts/character_sheet.gd").new()
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
var loot_button: Button
var loot_dialog: AcceptDialog
var feed: Label
var chat_field: LineEdit
var pad: Control
var ability_button: Button
var health_button: Button
var mana_button: Button
var attack_button: Button
var combat_roll_label: Label
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
var merchant_tab: String = "buy"
var window_layout = preload("res://scripts/window_layout.gd").new()
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
var hotbar_buttons: Array[Button] = []
var hotbar_page: int = 0
var hotbar_pages: HBoxContainer
var hotbar_page_label: Label
var own_effects_row: HBoxContainer
var target_effects_row: HBoxContainer
var status_strip: VBoxContainer
var effect_dialog: AcceptDialog
var escape_restraint_button: Button
var control_tip: PanelContainer
var tip_dismissed: bool = false
var ranking_label: Label
var ranking_http: HTTPRequest

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
	level_up_panels.setup(self)
	progression.setup(self)
	character_sheet.setup(self)
	fighter_choice.setup(self)
	caster_choice.setup(self)
	safety_confirm = ConfirmationDialog.new()
	safety_confirm.title = "Odblokować atakowanie graczy?"
	safety_confirm.dialog_text = "PvP: broń, czary, obszary i wilk. Uważaj na osoby w obszarze.\nNieuzasadniona agresja i zabójstwa powodują kary.\nOsada i początkujący pozostają chronieni."
	safety_confirm.ok_button_text = "Odblokuj PvP"
	safety_confirm.cancel_button_text = "Zostaw blokadę"
	safety_confirm.confirmed.connect(func() -> void: _send({"type":"pvp_safety", "enabled":false}))
	root.add_child(safety_confirm)
	_load_preferences()
	control_tip.visible = not tip_dismissed
	_setup_ranking()
	window_layout.setup(self)
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
	var login_row: HBoxContainer = HBoxContainer.new()
	login_row.add_theme_constant_override("separation", 20)
	center.add_child(login_row)
	login_row.add_child(panel)
	var ranks: PanelContainer = PanelContainer.new()
	ranks.custom_minimum_size.x = 270
	login_row.add_child(ranks)
	var rank_box: VBoxContainer = VBoxContainer.new()
	ranks.add_child(rank_box)
	rank_box.add_child(_label("RANKING GRACZY", 18, GOLD))
	rank_box.add_child(_label("Poziom / PD · TOP 20", 12, GREEN))
	var rank_scroll: ScrollContainer = ScrollContainer.new()
	rank_scroll.custom_minimum_size = Vector2(244, 390)
	rank_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	rank_box.add_child(rank_scroll)
	ranking_label = _wrap_label("Łączenie z rankingiem…", 14)
	ranking_label.custom_minimum_size.x = 240
	rank_scroll.add_child(ranking_label)
	var box: VBoxContainer = VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	panel.add_child(box)
	box.add_child(_label("BRACTWO · POGRANICZE", 30, GOLD))
	box.add_child(_label("KOŚCI I KRĘGI 0.8.4  /  WSPÓLNY OTWARTY ŚWIAT", 14, GREEN))
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
	var target_row: HBoxContainer = HBoxContainer.new()
	status.add_child(target_row)
	target_row.add_child(target_label)
	loot_button = _button("Łup", _show_target_loot)
	loot_button.hide()
	target_row.add_child(loot_button)
	loot_dialog = AcceptDialog.new()
	loot_dialog.ok_button_text = "Zamknij"
	add_child(loot_dialog)
	# Independent transparent status strip below the top HUD. Only buttons have a background.
	status_strip = VBoxContainer.new()
	status_strip.name = "StatusButtons"
	status_strip.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	status_strip.offset_left = 412
	status_strip.offset_right = -246
	status_strip.offset_top = 128
	status_strip.offset_bottom = 208
	status_strip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(status_strip)
	own_effects_row = _make_effect_row(status_strip)
	target_effects_row = _make_effect_row(status_strip)
	status_strip.hide()
	effect_dialog = AcceptDialog.new()
	effect_dialog.ok_button_text = "Zamknij"
	escape_restraint_button = effect_dialog.add_button("Wyrwij się · akcja", true, "escape_restraint")
	escape_restraint_button.hide()
	effect_dialog.custom_action.connect(func(action: StringName) -> void:
		if action == "escape_restraint":
			var packet: Dictionary = {"type":"escape_restraint"}
			var ally_id: String = str(escape_restraint_button.get_meta("target_id", ""))
			if not ally_id.is_empty():
				packet["target_id"] = ally_id
			_send(packet)
			effect_dialog.hide())
	hud.add_child(effect_dialog)
	fps_label = _label("— FPS", 12, PAPER)
	fps_label.custom_minimum_size.x = 64
	fps_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top_row.add_child(fps_label)
	top_row.add_child(_button("Wyjdź", _disconnect))
	hint_label = _label("", 14, GREEN)
	hint_label.position = Vector2(22, 164)
	hud.add_child(hint_label)
	var tracker_panel: PanelContainer = PanelContainer.new()
	tracker_panel.name = "QuestTracker"
	tracker_panel.position = Vector2(14, 202)
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
	notice_panel.offset_left = 12
	notice_panel.offset_right = 294
	notice_panel.offset_top = -266
	notice_panel.offset_bottom = -152
	hud.add_child(notice_panel)
	var notice_box: VBoxContainer = VBoxContainer.new()
	notice_panel.add_child(notice_box)
	feed = _wrap_label("Witaj na Pograniczu.", 14)
	feed.custom_minimum_size = Vector2(254, 46)
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
	var character_button: Button = _button("C · Karta postaci", func() -> void: character_sheet.toggle())
	character_button.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	character_button.offset_left = -198
	character_button.offset_right = -12
	character_button.offset_top = 14
	character_button.offset_bottom = 54
	hud.add_child(character_button)
	var actions: VBoxContainer = VBoxContainer.new()
	actions.name = "ActionDock"
	actions.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	actions.offset_left = -880
	actions.offset_right = -12
	actions.offset_top = -316
	actions.offset_bottom = -12
	actions.add_theme_constant_override("separation", 6)
	hud.add_child(actions)
	var menus: HBoxContainer = HBoxContainer.new()
	actions.add_child(menus)
	menus.add_child(_button("C · Postać", func() -> void: character_sheet.toggle()))
	menus.add_child(_button("P · Gracze", _toggle_party))
	menus.add_child(_button("J · Zadania", _toggle_journal))
	menus.add_child(_button("K · Czary", func() -> void: character_sheet.toggle("spells")))
	# F keeps its original usage-based action; only its parent and placement change.
	ability_button = _button("F · Umiejętność", func() -> void: _send({"type":"ability"}))
	ability_button.name = "ClassAbility"
	ability_button.custom_minimum_size.x = 164
	ability_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ability_button.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	ability_button.expand_icon = true
	ability_button.add_theme_constant_override("icon_max_width", 22)
	menus.add_child(ability_button)
	menus.add_child(_button("Świat", func() -> void: progression.toggle()))
	safety_button = _button("PvP zablokowane", _toggle_safety)
	safety_button.name = "PvpSafety"
	safety_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	safety_button.custom_minimum_size.x = 128
	safety_button.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	menus.add_child(safety_button)
	for menu: Button in menus.get_children():
		menu.add_theme_font_size_override("font_size", 11)
	var spellbar: GridContainer = GridContainer.new()
	spellbar.columns = 12
	actions.add_child(spellbar)
	for slot: int in range(24):
		var b: Button = _button(_hotbar_key_label(slot), _cast_slot.bind(slot))
		b.custom_minimum_size = Vector2(60, 55)
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 24)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 12)
		b.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		spellbar.add_child(b)
		hotbar_buttons.append(b)
	hotbar_pages = HBoxContainer.new()
	hotbar_pages.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_child(hotbar_pages)
	hotbar_pages.add_child(_button("‹ Page Up", _change_hotbar_page.bind(-1)))
	hotbar_page_label = _label("1/1", 13)
	hotbar_pages.add_child(hotbar_page_label)
	hotbar_pages.add_child(_button("Page Down ›", _change_hotbar_page.bind(1)))
	var utilities: HBoxContainer = HBoxContainer.new()
	actions.add_child(utilities)
	# Potions sit between the left chat panel and both spell rows.
	var potion_strip: VBoxContainer = VBoxContainer.new()
	potion_strip.name = "PotionStrip"
	potion_strip.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	potion_strip.offset_left = -974
	potion_strip.offset_right = -892
	potion_strip.offset_top = -266
	potion_strip.offset_bottom = -152
	potion_strip.add_theme_constant_override("separation", 4)
	potion_strip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(potion_strip)
	health_button = _button("Q · HP", func() -> void: _best_potion("health_potion"))
	mana_button = _button("R · Mana", func() -> void: _best_potion("mana_potion"))
	for potion_button: Button in [health_button, mana_button]:
		potion_button.custom_minimum_size = Vector2(82, 55)
		potion_button.add_theme_font_size_override("font_size", 12)
		potion_strip.add_child(potion_button)
	utilities.add_child(_button("E · Rozmowa", _interact_nearby))
	combat_roll_label = _wrap_label("", 12, GOLD)
	combat_roll_label.custom_minimum_size.y = 32
	combat_roll_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	actions.add_child(combat_roll_label)
	var combat: HBoxContainer = HBoxContainer.new()
	actions.add_child(combat)
	attack_button = _button("SPACJA · ATAK", func() -> void: pass)
	attack_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	attack_button.button_down.connect(func() -> void:
		attack_held = true
		_attack()
	)
	attack_button.button_up.connect(func() -> void: attack_held = false)
	combat.add_child(attack_button)
	control_tip = PanelContainer.new()
	control_tip.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	control_tip.offset_left = 190
	control_tip.offset_top = -77
	control_tip.offset_right = 675
	control_tip.offset_bottom = -16
	hud.add_child(control_tip)
	var tip_row: HBoxContainer = HBoxContainer.new()
	control_tip.add_child(tip_row)
	var tip: Label = _wrap_label("W S A D · ruch     SPACJA · atak\nKliknij cel: autoatak · 1–0, −, = / F1–F12: czary · C: karta", 12, PAPER)
	tip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tip.custom_minimum_size.x = 400
	tip_row.add_child(tip)
	tip_row.add_child(_button("×", func() -> void:
		tip_dismissed = true
		control_tip.hide()
		_save_preferences()))
	_add_notice("Strażniczka w osadzie szuka pomocy.")

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
	window_layout.attach(panel, label)
	panel.hide()
	return panel

func _build_inventory() -> void:
	inventory_panel = _window("KUPIEC")
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
	buy_health = _button("Kupuj", func() -> void: merchant_tab = "buy"; last_inventory_key = ""; _refresh_inventory())
	buy_health.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shop.add_child(buy_health)
	buy_mana = _button("Sprzedaj", func() -> void: merchant_tab = "sell"; last_inventory_key = ""; _refresh_inventory())
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
	box.add_child(_wrap_label("Po odblokowaniu PvP działają broń, czary, obszary i wilk. Wsparcie drużyny w PvP również włącza cię do walki. Blokada ataków nie chroni przed cudzą agresją.", 13, Color("b6c5b3")))
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
	var typing: bool = get_viewport().gui_get_focus_owner() is LineEdit or get_viewport().gui_get_focus_owner() is TextEdit
	if input_elapsed >= 0.05:
		input_elapsed = 0.0
		var movement: Vector2 = Vector2.ZERO
		if app_focused and not typing and not _controls_blocked():
			movement = Input.get_vector("walk_left", "walk_right", "walk_up", "walk_down")
			if pad.vector.length() > movement.length():
				movement = pad.vector
		_send({"type":"input", "x":movement.x, "y":movement.y})
	if attack_elapsed >= 0.22 and app_focused and not typing and not _controls_blocked() and (attack_held or Input.is_action_pressed("strike")):
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
			level_up_panels.reset()
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
		"nature_hint":
			navigation_goal = {"x":data.get("x", 0), "y":data.get("y", 0), "floor":data.get("floor", 0), "label":data.get("name", "Wskazówka")}
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
	var command: String = str(data.get("type", ""))
	if command in ["cast", "ability"]:
		data = data.duplicate()
		var key: String = str(data.get("spell_id", player.get("favorite_spell", "")))
		var spec: Dictionary = _spell_profile(key)
		var friend: Dictionary = _find_player(selected_target) if not selected_target.is_empty() else {}
		var same_party: bool = not str(player.get("party_id", "")).is_empty() and str(friend.get("party_id", "")) == str(player.get("party_id", ""))
		if str(spec.get("targeting", "")) == "ally" and not friend.is_empty() and (str(friend.get("id", "")) == local_id or same_party):
			data["target_id"] = selected_target
		elif str(spec.get("kind", "")) in ["attack", "save", "missiles", "mark", "control", "field"]:
			if not selected_enemy.is_empty():
				data["enemy_id"] = selected_enemy
			elif not selected_target.is_empty():
				data["target_id"] = selected_target
	if not selected_enemy.is_empty() and command == "rune_use":
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
	xp_bar.max_value = maxf(1, float(player.get("xp_next", 300)))
	xp_bar.value = float(player.get("xp", 0))
	vital_label.text = "HP %d/%d  Mana %d/%d  XP %d/%d  Ruch %.1f" % [int(hp_bar.value), int(hp_bar.max_value), int(mana_bar.value), int(mana_bar.max_value), int(player.get("xp_total", player.get("xp", 0))), int(player.get("xp_next_total", player.get("xp_next", 300))), float(player.get("speed", 100))]
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
	event_label.text = "POGRANICZE · online %d · Trafienie +%d · KP %d · %s" % [online, int(player.get("attack_bonus", 0)), int(player.get("armor_class", 10)), str(player.get("damage_dice", ""))]
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
	if int(player.get("level", 1)) < int(rules.get("min_level", 2)):
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
	loot_button.visible = not selected_enemy.is_empty() and not target.is_empty()
	if not selected_enemy.is_empty():
		target_label.text = ("Auto: %s · %d/%d HP · KP %d" if bool(player.get("weapon_auto_attack", true)) else "Cel: %s · %d/%d HP · KP %d") % [target.get("name", ""), int(target.get("hp", 0)), int(target.get("max_hp", 1)), int(target.get("armor_class", 10))]
		attack_button.text = "SPACJA · WYBRANY POTWÓR"
	else:
		target_label.text = "Cel: potwory w zasięgu" if selected_target.is_empty() else "Cel PvP: %s%s" % [target.get("name", "?"), " · ATAK ZABLOKOWANY" if safe else ""]
		attack_button.text = "SPACJA · POTWORY" if selected_target.is_empty() else "SPACJA · CEL PvP"
	var action_remaining: float = float(player.get("action_remaining", 0))
	if action_remaining > 0:
		attack_button.text = "SPACJA · %.1f s" % action_remaining
	attack_button.tooltip_text = ("Iskra różdżki tylko na Spację lub przycisk ataku. Zaznaczenie wybiera cel dla czarów.\n" if not bool(player.get("weapon_auto_attack", true)) else "Zaznaczenie uruchamia autoatak bronią co 3 s.\n") + "Esc odznacza cel. Oczekujący czar ma pierwszeństwo przed następnym atakiem. Atak i czar dzielą akcję; akcja dodatkowa ma własne odnowienie."
	combat_roll_label.text = _combat_summary(player.get("last_roll", {}))
	target_label.add_theme_color_override("font_color", GREEN if selected_target.is_empty() else RED)
	_refresh_battle_list()
	for key: String in ["q", "r"]:
		var template: String = str(player.get("potion_slots", {}).get(key, "health_potion" if key == "q" else "mana_potion"))
		var spec: Dictionary = world_data.get("items", {}).get(template, {})
		var count: int = int(player.get("potions", {}).get(template, 0))
		var b: Button = health_button if key == "q" else mana_button
		b.text = key.to_upper() + " · ×%d" % count
		b.tooltip_text = str(spec.get("name", "Nie przypisano mikstury")) + "\n" + _item_details(spec) + "\nPrzypisanie: C → Ekwipunek."
		var path: String = "res://" + str(spec.get("icon", ""))
		b.icon = load(path) as Texture2D if ResourceLoader.exists(path) else null
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 27)
		b.disabled = count <= 0 or not player.get("alive", true) or float(player.get("potion_cooldown", 0)) > 0 or int(player.get("level", 1)) < int(spec.get("min_level", 1))
	var favorite: String = str(player.get("favorite_spell", ""))
	var ability_spec: Dictionary = _spell_profile(favorite)
	var cooldown: float = float(player.get("spell_cooldowns", {}).get(favorite, 0))
	var ability_cost: int = _spell_mana(favorite, ability_spec)
	var revert: bool = ability_spec.get("kind", "") == "shape" and not str(player.get("form", "")).is_empty()
	var reaction: bool = ability_spec.get("kind", "") == "reaction"
	var weapon_ready: bool = ability_spec.get("kind", "") == "weapon_trigger" and bool(player.get("ensnaring_armed", false))
	var favorite_queue: String = _queued_spell_label(favorite)
	ability_button.text = "F · " + str(ability_spec.get("name", "Czar")) + (" · " + favorite_queue if not favorite_queue.is_empty() else " · GOTOWE" if weapon_ready else " (%ds)" % ceili(cooldown) if cooldown > 0 else "")
	var favorite_icon: String = "res://" + str(ability_spec.get("icon", ""))
	ability_button.icon = load(favorite_icon) as Texture2D if ResourceLoader.exists(favorite_icon) else null
	ability_button.disabled = ability_spec.is_empty() or not bool(player.get("alive", true)) or (not revert and not reaction and not weapon_ready and (cooldown > 0 or float(player.get("mana", 0)) < ability_cost or not str(player.get("form", "")).is_empty()))
	if ability_spec.get("kind", "") == "recovery":
		ability_button.disabled = not preload("res://scripts/caster_sheet.gd").can_recover(player)
	ability_button.tooltip_text = str(ability_spec.get("name", "Czar")) + "\nNajczęściej używany czar w ostatnich 100 udanych użyciach. Koszt: %d many." % ability_cost

	if not bool(player.get("alive", true)):
		hint_label.text = "Pokonano cię. Za chwilę wrócisz do osady z karą za śmierć."
	elif not bool(player.get("class_chosen", true)):
		hint_label.text = "Postać z wersji 0.1: wybierz stałą klasę w osadzie (I → wybór klasy)."
	elif not _nearest_npc().is_empty() and not _merchant_is_nearest():
		hint_label.text = "E · " + str(_nearest_npc().get("name", "Rozmowa")) + " · J: dziennik wypraw · Enter: powiedz coś"
	elif _near_merchant():
		hint_label.text = "E · Kupiec: kup mikstury, sprzedaj łupy · I: załóż sprzęt · P: zaproś graczy"
	else:
		hint_label.text = ""
	if str(player.get("party_id", "")) == pending_invite_id and not pending_invite_id.is_empty():
		pending_invite_id = ""
		pending_invite_name = ""
	if inventory_panel.visible:
		_refresh_inventory()
	if party_panel.visible:
		_refresh_party()
	_update_hotbar()
	_update_statuses(target)
	progression.refresh()
	character_sheet.refresh()
	fighter_choice.refresh()
	caster_choice.refresh()
	level_up_panels.refresh()
	_refresh_tracker()
	window_layout.refresh()
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
	character_sheet.toggle("inventory")

func _toggle_party() -> void:
	character_sheet.panel.hide()
	progression.panel.hide()
	party_panel.visible = not party_panel.visible
	inventory_panel.hide()
	journal_panel.hide()
	attack_held = false
	if party_panel.visible:
		_refresh_party()

func _merchant() -> void:
	_send({"type":"interact"})
	inventory_panel.show()
	party_panel.hide()
	journal_panel.hide()
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
	return str(player.get("form", "")).is_empty() and str(item.get("preview", {}).get("equip_error", "")).is_empty() and int(player.get("level", 1)) >= int(item.get("min_level", 1)) and (classes.is_empty() or classes.has(str(player.get("class_id", "knight"))))

func _item_details(item: Dictionary) -> String:
	var lines: PackedStringArray = PackedStringArray()
	if item.is_empty():
		return ""
	var details: Dictionary = item.get("preview", player.get("item_previews", {}).get(item.get("template", ""), {}))
	var slot: String = str(item.get("slot", ""))
	var damage_names: Dictionary = {"piercing":"kłute", "slashing":"sieczne", "bludgeoning":"obuchowe", "fire":"ogień", "cold":"zimno", "force":"moc", "necrotic":"nekrotyczne", "poison":"trucizna"}
	if slot == "weapon":
		lines.append(str(item.get("weapon_name", "Broń")) + (" · Prosta" if item.get("weapon_category", "") == "simple" else " · Żołnierska" if item.get("weapon_category", "") == "martial" else ""))
		if details.has("attack"):
			var attack_value: int = int(details["attack"])
			lines.append("Atak  1k20" + ("+" if attack_value >= 0 else "") + str(attack_value))
		lines.append("Obrażenia  " + str(details.get("dice", item.get("damage_dice", ""))) + " " + str(damage_names.get(details.get("damage_type", item.get("damage_type", "")), "")))
		if details.has("two_hand_dice"):
			lines.append("Oburącz  " + str(details["two_hand_dice"]))
		elif item.get("two_handed", false):
			lines.append("Dwuręczna")
		if int(details.get("spell_bonus", item.get("spell_bonus", 0))) > 0:
			lines.append("Czary: atak i ST +%d" % int(details.get("spell_bonus", item.get("spell_bonus", 0))))
		if not details.get("proficient", true):
			lines.append("Brak biegłości: −%d do trafienia" % int(details.get("proficiency", 2)))
		if details.get("heavy_penalty", false):
			lines.append("Za mała cecha — utrudnienie")
		if item.has("mastery_name"):
			lines.append("Mistrzostwo  " + str(item["mastery_name"]) + ("" if details.get("mastery_active", false) else " 🔒"))
	elif slot == "potion":
		lines.append("Odnawia " + str(item.get("effect_summary", "")))
		lines.append("Liczba: %d" % int(item.get("quantity", 1)))
	elif slot == "armor":
		lines.append(str({"none":"Szata", "light":"Lekki pancerz", "medium":"Średni pancerz", "heavy":"Ciężki pancerz"}.get(item.get("armor_kind", "none"), "Pancerz")))
		lines.append("Twoja KP  %d" % int(details["ac"]) if details.has("ac") else str(item.get("armor_summary", "")))
		if details.get("armor_penalty", false):
			lines.append("Brak wyszkolenia — bez czarów, utrudnienie Siły/Zręczności")
		if details.get("speed_penalty", false):
			lines.append("Za mała Siła — ruch −10 stóp")
	elif slot == "shield":
		lines.append("Tarcza · +%d KP" % int(item.get("shield_ac", 2)))
		if details.has("ac"):
			lines.append("Twoja KP  %d" % int(details["ac"]))
		if details.get("untrained_shield", false):
			lines.append("Brak wyszkolenia — bez premii KP")
	elif slot == "ring":
		lines.append("Pierścień")
		if int(item.get("ac_bonus", 0)) > 0:
			lines.append("KP +%d" % int(item["ac_bonus"]))
		if int(item.get("attack_bonus", 0)) > 0:
			lines.append("Atak bronią +%d" % int(item["attack_bonus"]))
	var resistance_names: PackedStringArray = PackedStringArray()
	for dtype: String in item.get("resistances", []):
		resistance_names.append(str(damage_names.get(dtype, dtype)))
	if not resistance_names.is_empty():
		lines.append("Odporność: " + ", ".join(resistance_names))
	if int(item.get("min_level", 1)) > 1:
		lines.append("Poziom %d" % int(item["min_level"]))
	var sources: PackedStringArray = PackedStringArray()
	for source: Dictionary in item.get("sources", []):
		sources.append(str(source.get("name", "")))
	if not sources.is_empty():
		lines.append("Zdobyto: " + ", ".join(sources))
	return "\n".join(lines)

func _refresh_inventory() -> void:
	var inventory: Array = player.get("inventory", [])
	var trading: bool = _near_merchant() and float(player.get("combat_remaining", 0)) <= 0 and player.get("alive", true)
	var key: String = JSON.stringify([merchant_tab, inventory, player.get("equipment"), player.get("gold"), player.get("level"), trading])
	if key == last_inventory_key:
		return
	last_inventory_key = key
	inventory_stats.text = "Złoto: %d · Plecak: %d / 40" % [int(player.get("gold", 0)), inventory.size()]
	legacy_row.visible = not bool(player.get("class_chosen", true))
	equipment_list.hide()
	shop_label.text = "Wybierz przedmiot." if trading else "Handel przy kupcu, poza walką."
	buy_health.text = "✓ Kupuj" if merchant_tab == "buy" else "Kupuj"
	buy_mana.text = "✓ Sprzedaj" if merchant_tab == "sell" else "Sprzedaj"
	_clear_children(inventory_list)
	var entries: Array = []
	if merchant_tab == "buy":
		for template: String in world_data.get("items", {}):
			if not world_data["items"][template].has("price"):
				continue
			var entry: Dictionary = world_data.get("items", {}).get(template, {}).duplicate()
			entry["template"] = template
			entry["preview"] = player.get("item_previews", {}).get(template, {})
			entries.append(entry)
	else:
		for entry: Dictionary in inventory:
			if not _item_equipped(str(entry.get("uid", ""))):
				entries.append(entry)
	for item: Dictionary in entries:
		var box: VBoxContainer = VBoxContainer.new()
		inventory_list.add_child(box)
		var label: Label = _wrap_label(str(item.get("name", "")) + (" ×%d" % int(item["quantity"]) if item.has("quantity") else ""), 15, GOLD)
		label.mouse_filter = Control.MOUSE_FILTER_STOP
		label.tooltip_text = _item_details(item)
		box.add_child(label)
		box.add_child(_wrap_label(str(item.get("effect_summary", item.get("damage_dice", ""))), 12, GREEN))
		var actions: HFlowContainer = HFlowContainer.new()
		box.add_child(actions)
		if merchant_tab == "buy":
			var price: int = int(item.get("price", 0))
			var buy: Button = _button("Kup · %d zł" % price, func() -> void: _send({"type":"buy", "item":item["template"]}))
			buy.disabled = not trading or int(player.get("gold", 0)) < price or int(player.get("level", 1)) < int(item.get("min_level", 1))
			actions.add_child(buy)
		else:
			var sell: Button = _button("Sprzedaj 1 · %d zł" % int(item.get("value", 0)), func() -> void: _send({"type":"sell", "uid":item["uid"]}))
			sell.disabled = not trading
			actions.add_child(sell)
			if int(item.get("quantity", 1)) > 1:
				var stack: Button = _button("Sprzedaj stos", func() -> void: _send({"type":"sell", "uid":item["uid"], "quantity":item["quantity"]}))
				stack.disabled = not trading
				actions.add_child(stack)
		inventory_list.add_child(HSeparator.new())
	if entries.is_empty():
		inventory_list.add_child(_wrap_label("Brak przedmiotów do sprzedaży.", 14))

func _refresh_party() -> void:
	var entries: Array = []
	for candidate: Dictionary in state.get("players", []):
		entries.append([candidate.get("id", ""), candidate.get("name", ""), candidate.get("level", 1), candidate.get("class_id", ""), candidate.get("party_id", ""), candidate.get("skull", "none"), candidate.get("disconnected", false)])
	var key: String = JSON.stringify([entries, player.get("party_id", ""), player.get("party_members", []), pending_invite_id, pending_invite_name, selected_target])
	if key == last_players_key:
		return
	last_players_key = key
	var rules: Dictionary = world_data.get("pvp_rules", {})
	pvp_rules_label.text = "PvP od poziomu %d, poza osadą. Biała czaszka po agresji: %ds. %d nieuzasadnione zabójstwa / 24 h: czerwona czaszka na 24 h.\nŚmierć: −%d%% złota i −%d%% bieżącego XP. Czerwona czaszka: −%d%% złota i −%d%% XP oraz 1 niezałożony przedmiot. Bez utraty poziomu.\nPodczas walki PvP nie wejdziesz do osady. Rozłączenie w walce nie chroni postaci." % [int(rules.get("min_level", 2)), int(rules.get("white_seconds", 120)), int(rules.get("red_kills", 3)), int(float(rules.get("normal_gold_loss", 0.05))*100), int(float(rules.get("normal_xp_loss", 0.10))*100), int(float(rules.get("red_gold_loss", 0.20))*100), int(float(rules.get("red_xp_loss", 0.20))*100)]
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
		safety_confirm.dialog_text = "PvP: broń, czary, obszary i wilk. Uważaj na osoby w obszarze.\nNieuzasadniona agresja: biała czaszka.\n%d nieuzasadnione zabójstwa / 24 h: czerwona czaszka i surowsza kara śmierci.\nPvP od poziomu %d, poza chronioną osadą." % [int(rules.get("red_kills", 3)), int(rules.get("min_level", 2))]
		safety_confirm.popup_centered(Vector2i(620, 240))
	else:
		_send({"type":"pvp_safety", "enabled":true})
		_select_target("")

func _select_target(id: String) -> void:
	_send({"type":"select_target", "target_id":id})
	selected_enemy = ""
	world_view.selected_enemy = ""
	selected_target = id
	world_view.selected_target = id
	attack_held = false
	last_players_key = ""
	if not id.is_empty():
		_add_notice("Wybrano cel PvP: " + str(_find_player(id).get("name", "?")) + ". Po odblokowaniu PvP działają autoatak, czary i towarzysz.")
	_update_hud()

func _combat_summary(roll: Dictionary) -> String:
	if roll.get("graze", false):
		return "%s · pudło · Draśnięcie → %s obr." % [roll.get("action", "Atak"), str(roll.get("damage", 0))]
	if str(roll.get("check", "")) == "healing":
		return "%s · %s → +%d" % [roll.get("action", "Leczenie"), roll.get("damage_dice", ""), int(roll.get("healing", 0))]
	if str(roll.get("check", "")) == "automatic":
		return "%s · %s → %d obrażeń" % [roll.get("action", "Czar"), roll.get("damage_dice", ""), int(roll.get("damage", 0))]
	if str(roll.get("check", "")) == "concentration":
		return "Koncentracja: k20 %d + %d / ST %d · %s" % [int(roll.get("roll", 0)), int(roll.get("bonus", 0)), int(roll.get("defense", 10)), "utrzymana" if roll.get("saved", false) else "przerwana"]
	if roll.is_empty():
		return ""
	var die: String = "k20 %d" % int(roll.get("roll", 0))
	if bool(roll.get("disadvantage", false)) or bool(roll.get("advantage", false)):
		die = "k20 %s → %d" % [str(roll.get("rolls", [])), int(roll.get("roll", 0))]
	var save: bool = str(roll.get("check", "")) == "save"
	var result: String = "KRYTYK" if roll.get("critical", false) else "trafienie" if roll.get("hit", false) else "PUDŁO"
	if save:
		result = ("obrona · połowa" if roll.get("save_half", false) else "obrona · brak obrażeń") if roll.get("saved", false) else "nieudana obrona"
	var damage: String = " · %s → %s obr." % [str(roll.get("damage_dice", "")), str(roll.get("damage", 0))] if roll.get("hit", false) else ""
	return "%s: %s + %d = %d / %s %d · %s%s" % [str(roll.get("target_name", "Cel")), die, int(roll.get("bonus", 0)), int(roll.get("total", 0)), "ST" if save else "KP", int(roll.get("defense", 0)), result, damage]

func _attack() -> void:
	if local_id.is_empty() or not app_focused or _controls_blocked() or get_viewport().gui_get_focus_owner() is LineEdit or not bool(player.get("alive", true)) or float(player.get("action_remaining", 0)) > 0:
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
	_send({"type":"select_target", "enemy_id":id})
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
	if is_instance_valid(loot_dialog) and loot_dialog.visible:
		return
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
	if is_instance_valid(loot_dialog) and loot_dialog.visible and event is InputEventKey and event.pressed and event.physical_keycode == KEY_ESCAPE:
		loot_dialog.hide()
		return
	if local_id.is_empty() or not event is InputEventKey or not event.pressed or event.echo:
		return
	if event.ctrl_pressed or event.alt_pressed or event.meta_pressed:
		return
	if get_viewport().gui_get_focus_owner() is LineEdit or get_viewport().gui_get_focus_owner() is TextEdit or safety_confirm.visible:
		return
	match event.physical_keycode:
		KEY_SPACE:
			_attack()
		KEY_E:
			_interact_nearby()
		KEY_F:
			if not _controls_blocked():
				_send({"type":"ability"})
		KEY_Q:
			_best_potion("health_potion")
		KEY_R:
			_best_potion("mana_potion")
		KEY_I:
			_toggle_inventory()
		KEY_P:
			_toggle_party()
		KEY_C:
			character_sheet.toggle()
		KEY_K:
			character_sheet.toggle("spells")
		KEY_PAGEUP:
			_change_hotbar_page(-1)
		KEY_PAGEDOWN:
			_change_hotbar_page(1)
		KEY_1:
			if not _controls_blocked():
				_cast_slot(0)
		KEY_2:
			if not _controls_blocked():
				_cast_slot(1)
		KEY_3:
			if not _controls_blocked():
				_cast_slot(2)
		KEY_4:
			if not _controls_blocked():
				_cast_slot(3)
		KEY_5:
			if not _controls_blocked():
				_cast_slot(4)
		KEY_6:
			if not _controls_blocked():
				_cast_slot(5)
		KEY_7:
			if not _controls_blocked():
				_cast_slot(6)
		KEY_8:
			if not _controls_blocked():
				_cast_slot(7)
		KEY_9:
			if not _controls_blocked():
				_cast_slot(8)
		KEY_0:
			if not _controls_blocked():
				_cast_slot(9)
		KEY_MINUS:
			if not _controls_blocked():
				_cast_slot(10)
		KEY_EQUAL:
			if not _controls_blocked():
				_cast_slot(11)
		KEY_F1:
			if not _controls_blocked():
				_cast_slot(12)
		KEY_F2:
			if not _controls_blocked():
				_cast_slot(13)
		KEY_F3:
			if not _controls_blocked():
				_cast_slot(14)
		KEY_F4:
			if not _controls_blocked():
				_cast_slot(15)
		KEY_F5:
			if not _controls_blocked():
				_cast_slot(16)
		KEY_F6:
			if not _controls_blocked():
				_cast_slot(17)
		KEY_F7:
			if not _controls_blocked():
				_cast_slot(18)
		KEY_F8:
			if not _controls_blocked():
				_cast_slot(19)
		KEY_F9:
			if not _controls_blocked():
				_cast_slot(20)
		KEY_F10:
			if not _controls_blocked():
				_cast_slot(21)
		KEY_F11:
			if not _controls_blocked():
				_cast_slot(22)
		KEY_F12:
			if not _controls_blocked():
				_cast_slot(23)
		KEY_J:
			_toggle_journal()
		KEY_ESCAPE:
			if character_sheet.panel.visible:
				character_sheet.panel.hide()
				return
			progression.panel.hide()
			inventory_panel.hide()
			party_panel.hide()
			journal_panel.hide()
			_select_target("")

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		app_focused = false
		_send({"type":"auto_pause", "paused":true})
		attack_held = false
		if is_instance_valid(pad):
			pad.reset()
		_send({"type":"input", "x":0, "y":0})
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN:
		app_focused = true
		_send({"type":"auto_pause", "paused":false})
	elif what == NOTIFICATION_WM_CLOSE_REQUEST:
		_send({"type":"input", "x":0, "y":0})
		if socket != null:
			socket.close()

func _load_preferences() -> void:
	var config: ConfigFile = ConfigFile.new()
	if config.load("user://preferences.cfg") == OK:
		endpoint.text = str(config.get_value("connection", "url", endpoint.text))
		username.text = str(config.get_value("connection", "name", ""))
		tip_dismissed = bool(config.get_value("ui", "control_tip_dismissed", false))

func _save_preferences() -> void:
	var config: ConfigFile = ConfigFile.new()
	config.set_value("ui", "control_tip_dismissed", tip_dismissed)
	config.set_value("connection", "url", endpoint.text.strip_edges())
	config.set_value("connection", "name", username.text.strip_edges())
	config.save("user://preferences.cfg")

func _stop_controls() -> void:
	attack_held = false
	if is_instance_valid(pad):
		pad.reset()
	_send({"type":"input", "x":0, "y":0})

func _controls_blocked() -> bool:
	return local_id.is_empty() or safety_confirm.visible or not bool(player.get("alive", true))

func _menu_open() -> bool:
	if is_instance_valid(loot_dialog) and loot_dialog.visible:
		return true
	return safety_confirm.visible or inventory_panel.visible or party_panel.visible or journal_panel.visible or progression.panel.visible or character_sheet.panel.visible

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
	if _controls_blocked():
		return
	for window: Control in [progression.panel, journal_panel, inventory_panel]:
		if window.visible:
			window.hide()
			return
	for nature: Dictionary in world_data.get("nature_sites", []):
		if int(nature.get("floor", 0)) == int(player.get("floor", 0)) and Vector2(float(nature.get("x", 0)), float(nature.get("y", 0))).distance_to(Vector2(float(player.get("x", 0)), float(player.get("y", 0)))) <= 110.0:
			_send({"type":"nature_interact", "id":nature.get("id", "")})
			return
	for stair: Dictionary in world_data.get("stairs", []):
		if _near_point(stair):
			_send({"type":"descend"})
			return
	for site: Dictionary in world_data.get("pois", []):
		if _near_point(site):
			_send({"type":"interact"})
			return
	var nearest: Dictionary = _nearest_npc()
	if str(nearest.get("service", "")) == "merchant":
		_merchant()
		return
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
		last_journal_key = ""
		_refresh_journal()
	else:
		progression.show_book("Atlas")

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
	character_sheet.panel.hide()
	progression.panel.hide()
	journal_panel.visible = not journal_panel.visible
	inventory_panel.hide()
	party_panel.hide()
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
		if _spell_gate(spell) == level and spell.get("class_ids", []).has(player.get("class_id", "")):
			_send({"type":"cast", "spell_id":id})
			return

func _best_potion(prefix: String) -> void:
	# Kept as a compatibility method name: never select a stronger potion silently.
	_send({"type":"potion", "slot":"q" if prefix == "health_potion" else "r"})

func _potion_count(prefix: String) -> int:
	var count: int = 0
	for key: String in player.get("potions", {}):
		if key.begins_with(prefix):
			count += int(player["potions"][key])
	return count


func _spell_gate(spec: Dictionary) -> int:
	var cls: String = str(player.get("class_id", ""))
	return int(spec.get("required_level", spec.get("class_levels", {}).get(cls, spec.get("min_level", 1))))

func _cast_slot(slot: int) -> void:
	var bar: Array = player.get("hotbar", [])
	var index: int = hotbar_page * 24 + slot
	if slot >= 0 and slot < 24 and index < bar.size() and not str(bar[index]).is_empty():
		_send({"type":"cast", "spell_id":str(bar[index])})

func _bind_hotbar(index: int, spell_id: String) -> void:
	if index > 0:
		_send({"type":"hotbar", "slot":index - 1, "spell_id":spell_id})

func _spell_profile(key: String) -> Dictionary:
	var spec: Dictionary = world_data.get("spells", {}).get(key, {}).duplicate(true)
	spec.merge(player.get("spell_profiles", {}).get(key, {}), true)
	return spec

func _spell_mana(key: String, spec: Dictionary) -> int:
	var live: Dictionary = player.get("spell_profiles", {}).get(key, spec)
	return 0 if bool(spec.get("recast", false)) and str(player.get("concentration", "")) == key else int(live.get("mana", 0))

func _change_hotbar_page(delta: int) -> void:
	var pages: int = maxi(1, ceili(player.get("hotbar", []).size() / 24.0))
	hotbar_page = posmod(hotbar_page + delta, pages)
	_update_hotbar()

func _queued_spell_label(key: String) -> String:
	if key.is_empty() or str(player.get("queued_spell", "")) != key:
		return ""
	var remaining: float = maxf(0.0, float(player.get("action_remaining", 0)))
	return "Za %.1f s" % remaining if remaining > 0 else "W kolejce"

func _update_hotbar() -> void:
	var bar: Array = player.get("hotbar", [])
	var pages: int = maxi(1, ceili(bar.size() / 24.0))
	hotbar_page = clampi(hotbar_page, 0, pages - 1)
	hotbar_pages.visible = pages > 1
	hotbar_page_label.text = "%d/%d · 1–0, −, = oraz F1–F12" % [hotbar_page + 1, pages]
	for slot: int in range(hotbar_buttons.size()):
		var button: Button = hotbar_buttons[slot]
		var index: int = hotbar_page * 24 + slot
		var key: String = str(bar[index]) if index < bar.size() else ""
		var spec: Dictionary = _spell_profile(key)
		if spec.is_empty():
			button.text = _hotbar_key_label(slot) + "\n—"
			button.icon = null
			button.disabled = true
			continue
		var gate: int = _spell_gate(spec)
		var unlocked: bool = int(player.get("level", 1)) >= gate
		var cd: int = ceili(float(player.get("spell_cooldowns", {}).get(key, 0)))
		var revert: bool = spec.get("kind", "") == "shape" and not str(player.get("form", "")).is_empty()
		var reaction: bool = spec.get("kind", "") == "reaction"
		var detail: String = "poz. %d" % gate if not unlocked else "Powrót" if revert else ("ON" if player.get("shield_armed", false) else "OFF") if reaction else "GOTOWE" if spec.get("kind", "") == "weapon_trigger" and player.get("ensnaring_armed", false) else "%d s" % cd if cd > 0 else "%d MP" % _spell_mana(key, spec)
		var queued: String = _queued_spell_label(key)
		if not queued.is_empty():
			detail = queued
		button.text = "%s\n%s" % [_hotbar_key_label(slot), detail]
		var icon_path: String = "res://" + str(spec.get("icon", ""))
		if ResourceLoader.exists(icon_path):
			button.icon = load(icon_path) as Texture2D
		button.tooltip_text = "%s · poziom %d\n%s\n%s" % [spec.get("name", ""), gate, spec.get("power_summary", ""), spec.get("description", "")]
		button.disabled = not unlocked or not bool(player.get("alive", false)) or (not revert and not reaction and not (spec.get("kind", "") == "weapon_trigger" and player.get("ensnaring_armed", false)) and (cd > 0 or float(player.get("mana", 0)) < _spell_mana(key, spec) or not str(player.get("form", "")).is_empty()))
		if spec.get("kind", "") == "recovery":
			button.disabled = not preload("res://scripts/caster_sheet.gd").can_recover(player)

func _make_effect_row(parent: VBoxContainer) -> HBoxContainer:
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.custom_minimum_size.y = 36
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(scroll)
	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	scroll.add_child(row)
	return row

func _show_effect(button: Button) -> void:
	var effect: Dictionary = button.get_meta("effect", {})
	var other: bool = bool(button.get_meta("is_target", false))
	var ally: Dictionary = _find_player(selected_target) if other else {}
	var same_party: bool = not str(player.get("party_id", "")).is_empty() and player.get("party_id", "") == ally.get("party_id", "other")
	escape_restraint_button.visible = bool(effect.get("escape_action", false)) and (not other or same_party)
	escape_restraint_button.set_meta("target_id", selected_target if other and same_party else "")
	effect_dialog.set_meta("escape_mode", escape_restraint_button.visible)
	escape_restraint_button.text = "Uwolnij sojusznika · akcja" if other else "Wyrwij się · akcja"
	escape_restraint_button.disabled = float(player.get("action_remaining", 0)) > 0
	effect_dialog.title = str(effect.get("name", "Status"))
	effect_dialog.dialog_text = button.tooltip_text
	effect_dialog.popup_centered(Vector2i(470, 180))

func _render_effect_buttons(effects: Array, row: HBoxContainer, is_target: bool) -> void:
	var existing: Dictionary = {}
	for child: Button in row.get_children():
		existing[str(child.get_meta("effect_id", ""))] = child
	var wanted: Dictionary = {}
	for effect: Dictionary in effects:
		var id: String = str(effect.get("id", ""))
		wanted[id] = true
		var button: Button = existing.get(id) as Button
		if button == null:
			button = Button.new()
			button.focus_mode = Control.FOCUS_NONE
			button.custom_minimum_size.y = 30
			button.add_theme_font_size_override("font_size", 11)
			button.set_meta("effect_id", id)
			button.pressed.connect(_show_effect.bind(button))
			row.add_child(button)
		button.set_meta("effect", effect)
		button.set_meta("is_target", is_target)
		var time_text: String = "aktywne"
		if effect.get("remaining") != null:
			var seconds: int = ceili(float(effect.get("remaining", 0)))
			time_text = "%d:%02d · %d r." % [int(seconds / 60.0), seconds % 60, int(effect.get("rounds", 0))]
		var owner: String = "Cel · " if is_target else ""
		button.text = "%s%s %s · %s" % [owner, str(effect.get("icon", "✦")), str(effect.get("name", "")), time_text]
		button.tooltip_text = ("Cel · " if is_target else "Ty · ") + str(effect.get("name", "")) + " · " + time_text + "\n" + str(effect.get("description", ""))
		button.add_theme_color_override("font_color", RED if effect.get("harmful", false) else GREEN)
	for id: String in existing:
		if not wanted.has(id):
			var expired: Button = existing[id] as Button
			row.remove_child(expired)
			expired.queue_free()
	var scroll: ScrollContainer = row.get_parent() as ScrollContainer
	scroll.visible = not effects.is_empty()

func _update_statuses(target: Dictionary) -> void:
	var own: Array = player.get("status_effects", [])
	var other: Array = target.get("status_effects", [])
	_render_effect_buttons(own, own_effects_row, false)
	_render_effect_buttons(other, target_effects_row, true)
	status_strip.visible = not own.is_empty() or not other.is_empty()
	if effect_dialog.visible and effect_dialog.get_meta("escape_mode", false):
		var ally_id: String = str(escape_restraint_button.get_meta("target_id", ""))
		var recipient: Dictionary = player if ally_id.is_empty() else _find_player(ally_id)
		var still_restrained: bool = false
		for state: Dictionary in recipient.get("status_effects", []):
			if state.get("escape_action", false):
				still_restrained = true
		escape_restraint_button.visible = still_restrained
		escape_restraint_button.disabled = float(player.get("action_remaining", 0)) > 0 or not player.get("alive", true)
		if not still_restrained:
			effect_dialog.hide()
	var budget: Dictionary = player.get("mana_budget", {})
	mana_bar.tooltip_text = "Pełna pula: %d many. Wspólna mana." % int(player.get("max_mana", 0))
	var mana_gain: int = int(budget.get("next_level_gain", 0))
	if mana_gain > 0:
		mana_bar.tooltip_text += " Następny poziom: +%d many." % mana_gain
	mana_bar.tooltip_text += " Brak regeneracji w walce. Poza walką: 12 s przerwy po wydaniu many, potem pełna pula w 4 min (20 s w osadzie)."

func _setup_ranking() -> void:
	ranking_http = HTTPRequest.new()
	ranking_http.timeout = 8
	add_child(ranking_http)
	ranking_http.request_completed.connect(_ranking_received)
	endpoint.text_submitted.connect(func(_text: String) -> void: _refresh_ranking())
	endpoint.focus_exited.connect(_refresh_ranking)
	var timer: Timer = Timer.new()
	timer.wait_time = 20
	timer.timeout.connect(_refresh_ranking)
	add_child(timer)
	timer.start()
	_refresh_ranking()

func _refresh_ranking() -> void:
	if not login_panel.visible or not is_instance_valid(ranking_http):return
	var url: String = endpoint.text.strip_edges().replace("wss://", "https://").replace("ws://", "http://")
	url = url.trim_suffix("/ws")
	ranking_http.cancel_request()
	var error: Error = ranking_http.request(url.trim_suffix("/") + "/ranking")
	if error != OK:ranking_label.text = "Ranking niedostępny — sprawdź adres."

func _ranking_received(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		ranking_label.text = "Ranking niedostępny.\nUruchom serwer i sprawdź adres."
		return
	var decoded: Variant = JSON.parse_string(body.get_string_from_utf8())
	if not decoded is Dictionary:return
	var rows: PackedStringArray = PackedStringArray()
	for entry: Dictionary in decoded.get("ranking", []):
		rows.append("%d. %s · %d\n    %s%s" % [int(entry.get("rank", 0)), str(entry.get("name", "")), int(entry.get("level", 1)), str(CLASS_NAMES.get(entry.get("class_id", ""), "")), " · online" if entry.get("online", false) else ""])
	ranking_label.text = "\n\n".join(rows) if not rows.is_empty() else "Świat czeka na pierwszego bohatera."

func _hotbar_key_label(index: int) -> String:
	var slot: int = posmod(index, 24)
	var names: Array[String] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "−", "="]
	var label: String = names[slot] if slot < 12 else "F%d" % (slot - 11)
	return ("%d · " % (int(index / 24.0) + 1) if index >= 24 else "") + label

func _show_target_loot() -> void:
	var target: Dictionary = _find_enemy(selected_enemy)
	if target.is_empty():
		return
	var spec: Dictionary = world_data.get("enemy_types", {}).get(str(target.get("kind", "")), {})
	loot_dialog.title = str(spec.get("name", "Łupy"))
	var rows: PackedStringArray = PackedStringArray()
	for entry: Dictionary in player.get("known_loot", {}).get(str(target.get("kind", "")), []):
		var source: Dictionary = world_data.get("potions", {}) if str(entry.get("kind", "")) == "potion" else world_data.get("items", {})
		var item: Dictionary = source.get(str(entry.get("template", "")), {})
		rows.append(str(item.get("name", "")) + " · " + str(snappedf(float(entry.get("chance", 0)) * 100, 0.01)) + "%")
	rows.append("")
	rows.append("Tylko przedmioty zdobyte przez tę postać z tego gatunku." if rows.size() > 1 else "Nie odkryto jeszcze łupów z tego gatunku.")
	loot_dialog.dialog_text = "\n".join(rows)
	loot_dialog.popup_centered(Vector2i(mini(540, int(get_viewport_rect().size.x) - 24), 360))
