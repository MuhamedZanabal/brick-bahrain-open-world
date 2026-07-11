extends CanvasLayer
## HUD - In-game heads-up display
## Layout matches the Brick Bahrain reference concept art:
## top-left logo + mission card, health/energy bars, top-right coins/gems + pause,
## minimap with location/time, bottom-left virtual joystick, bottom-right action
## buttons, bottom-center hotbar.

var player: CharacterBody3D
var mission_system: Node

var health_bar_fill: ColorRect
var energy_bar_fill: ColorRect
var coin_label: Label
var gem_label: Label
var mission_title_label: Label
var mission_desc_label: Label
var minimap: Control
var location_label: Label
var time_label: Label
var notification_label: Label
var notification_timer: float = 0.0
var gems: int = 250  # placeholder secondary currency for HUD parity

func _ready() -> void:
	_build_ui()

func _s() -> float:
	# UI scale factor based on viewport vs 1280x720 reference design
	var vp := get_viewport().get_visible_rect().size
	return clamp(min(vp.x / 1280.0, vp.y / 720.0), 0.6, 1.6)

func _build_ui() -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var s := _s()
	
	# ── Top-left: Logo card ──
	var logo_panel := Panel.new()
	logo_panel.position = Vector2(12 * s, 12 * s)
	logo_panel.size = Vector2(190 * s, 60 * s)
	var logo_style := StyleBoxFlat.new()
	logo_style.bg_color = Color(0.08, 0.08, 0.1, 0.55)
	logo_style.corner_radius_top_left = 8
	logo_style.corner_radius_top_right = 8
	logo_style.corner_radius_bottom_left = 8
	logo_style.corner_radius_bottom_right = 8
	logo_style.border_width_left = 3
	logo_style.border_color = Color(0.8, 0.15, 0.15)
	logo_panel.add_theme_stylebox_override("panel", logo_style)
	add_child(logo_panel)
	
	var logo_title := Label.new()
	logo_title.text = "BRICK BAHRAIN"
	logo_title.add_theme_font_size_override("font_size", int(20 * s))
	logo_title.add_theme_color_override("font_color", Color(0.95, 0.75, 0.1))
	logo_title.position = Vector2(10 * s, 6 * s)
	logo_title.size = Vector2(170 * s, 26 * s)
	logo_panel.add_child(logo_title)
	
	var logo_sub := Label.new()
	logo_sub.text = "OPEN WORLD SANDBOX"
	logo_sub.add_theme_font_size_override("font_size", int(11 * s))
	logo_sub.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))
	logo_sub.position = Vector2(10 * s, 34 * s)
	logo_sub.size = Vector2(170 * s, 18 * s)
	logo_panel.add_child(logo_sub)
	
	# ── Health + Energy bars (top, next to logo) ──
	var bars_x := 12 * s + 190 * s + 12 * s
	var bars_w: float = min(220 * s, vp_size.x - bars_x - 12 * s)
	
	var health_bg := ColorRect.new()
	health_bg.color = Color(0.15, 0.05, 0.05, 0.7)
	health_bg.position = Vector2(bars_x, 14 * s)
	health_bg.size = Vector2(bars_w, 18 * s)
	add_child(health_bg)
	health_bar_fill = ColorRect.new()
	health_bar_fill.color = Color(0.85, 0.15, 0.15)
	health_bar_fill.position = health_bg.position + Vector2(2, 2)
	health_bar_fill.size = Vector2(bars_w - 4, 14 * s)
	add_child(health_bar_fill)
	var health_label := Label.new()
	health_label.text = "100/100"
	health_label.add_theme_font_size_override("font_size", int(11 * s))
	health_label.add_theme_color_override("font_color", Color(1, 1, 1))
	health_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	health_label.position = health_bg.position
	health_label.size = health_bg.size
	health_label.name = "HealthText"
	add_child(health_label)
	
	var energy_bg := ColorRect.new()
	energy_bg.color = Color(0.05, 0.15, 0.05, 0.7)
	energy_bg.position = Vector2(bars_x, 36 * s)
	energy_bg.size = Vector2(bars_w, 18 * s)
	add_child(energy_bg)
	energy_bar_fill = ColorRect.new()
	energy_bar_fill.color = Color(0.25, 0.8, 0.25)
	energy_bar_fill.position = energy_bg.position + Vector2(2, 2)
	energy_bar_fill.size = Vector2(bars_w - 4, 14 * s)
	add_child(energy_bar_fill)
	var energy_label := Label.new()
	energy_label.text = "100/100"
	energy_label.add_theme_font_size_override("font_size", int(11 * s))
	energy_label.add_theme_color_override("font_color", Color(1, 1, 1))
	energy_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	energy_label.position = energy_bg.position
	energy_label.size = energy_bg.size
	energy_label.name = "EnergyText"
	add_child(energy_label)
	
	# ── Mission card (below logo) ──
	var mission_panel := Panel.new()
	mission_panel.position = Vector2(12 * s, 78 * s)
	mission_panel.size = Vector2(280 * s, 56 * s)
	var mission_style := StyleBoxFlat.new()
	mission_style.bg_color = Color(0.05, 0.1, 0.2, 0.7)
	mission_style.corner_radius_top_left = 8
	mission_style.corner_radius_top_right = 8
	mission_style.corner_radius_bottom_left = 8
	mission_style.corner_radius_bottom_right = 8
	mission_style.border_width_left = 3
	mission_style.border_color = Color(0.2, 0.6, 0.9)
	mission_panel.add_theme_stylebox_override("panel", mission_style)
	add_child(mission_panel)
	
	mission_title_label = Label.new()
	mission_title_label.text = "NEW MISSION"
	mission_title_label.add_theme_font_size_override("font_size", int(13 * s))
	mission_title_label.add_theme_color_override("font_color", Color(1.0, 0.75, 0.15))
	mission_title_label.position = Vector2(10 * s, 6 * s)
	mission_title_label.size = Vector2(260 * s, 18 * s)
	mission_panel.add_child(mission_title_label)
	
	mission_desc_label = Label.new()
	mission_desc_label.text = "Press Q near a mission marker to begin"
	mission_desc_label.add_theme_font_size_override("font_size", int(12 * s))
	mission_desc_label.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))
	mission_desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	mission_desc_label.position = Vector2(10 * s, 26 * s)
	mission_desc_label.size = Vector2(260 * s, 26 * s)
	mission_panel.add_child(mission_desc_label)
	
	# ── Top-right: Coins / Gems / Pause ──
	var currency_panel := Panel.new()
	var cw := 230 * s
	currency_panel.position = Vector2(vp_size.x - cw - 12 * s, 12 * s)
	currency_panel.size = Vector2(cw, 40 * s)
	var currency_style := StyleBoxFlat.new()
	currency_style.bg_color = Color(0.08, 0.08, 0.1, 0.6)
	currency_style.corner_radius_top_left = 8
	currency_style.corner_radius_top_right = 8
	currency_style.corner_radius_bottom_left = 8
	currency_style.corner_radius_bottom_right = 8
	currency_panel.add_theme_stylebox_override("panel", currency_style)
	add_child(currency_panel)
	
	coin_label = Label.new()
	coin_label.text = "🟨 0"
	coin_label.add_theme_font_size_override("font_size", int(16 * s))
	coin_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.0))
	coin_label.position = Vector2(10 * s, 8 * s)
	coin_label.size = Vector2(95 * s, 24 * s)
	currency_panel.add_child(coin_label)
	
	gem_label = Label.new()
	gem_label.text = "🔷 250"
	gem_label.add_theme_font_size_override("font_size", int(16 * s))
	gem_label.add_theme_color_override("font_color", Color(0.3, 0.7, 1.0))
	gem_label.position = Vector2(110 * s, 8 * s)
	gem_label.size = Vector2(90 * s, 24 * s)
	currency_panel.add_child(gem_label)
	
	var pause_btn := Button.new()
	pause_btn.text = "II"
	pause_btn.custom_minimum_size = Vector2(34 * s, 34 * s)
	pause_btn.position = Vector2(vp_size.x - 34 * s - 12 * s, 12 * s)
	pause_btn.add_theme_font_size_override("font_size", int(14 * s))
	pause_btn.pressed.connect(_on_pause_pressed)
	add_child(pause_btn)
	
	# ── Minimap (top-right, below currency) ──
	var map_size := 150 * s
	minimap = Control.new()
	minimap.position = Vector2(vp_size.x - map_size - 12 * s, 58 * s)
	minimap.size = Vector2(map_size, map_size)
	minimap.name = "Minimap"
	add_child(minimap)
	
	var minimap_bg := ColorRect.new()
	minimap_bg.color = Color(0.12, 0.16, 0.12, 0.9)
	minimap_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	minimap_bg.name = "Bg"
	minimap.add_child(minimap_bg)
	
	var minimap_border := Control.new()
	minimap_border.set_anchors_preset(Control.PRESET_FULL_RECT)
	minimap_border.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var border_style := StyleBoxFlat.new()
	border_style.bg_color = Color(0, 0, 0, 0)
	border_style.border_width_left = 2
	border_style.border_width_right = 2
	border_style.border_width_top = 2
	border_style.border_width_bottom = 2
	border_style.border_color = Color(0.85, 0.75, 0.35)
	border_style.corner_radius_top_left = 6
	border_style.corner_radius_top_right = 6
	border_style.corner_radius_bottom_left = 6
	border_style.corner_radius_bottom_right = 6
	minimap_border.add_theme_stylebox_override("panel", border_style)
	minimap.add_child(minimap_border)
	
	# Location / time bar under minimap
	var loc_bar := Panel.new()
	loc_bar.position = Vector2(vp_size.x - map_size - 12 * s, 58 * s + map_size + 4 * s)
	loc_bar.size = Vector2(map_size, 24 * s)
	var loc_style := StyleBoxFlat.new()
	loc_style.bg_color = Color(0.08, 0.08, 0.1, 0.75)
	loc_style.corner_radius_top_left = 6
	loc_style.corner_radius_top_right = 6
	loc_style.corner_radius_bottom_left = 6
	loc_style.corner_radius_bottom_right = 6
	loc_bar.add_theme_stylebox_override("panel", loc_style)
	add_child(loc_bar)
	
	location_label = Label.new()
	location_label.text = "MANAMA"
	location_label.add_theme_font_size_override("font_size", int(11 * s))
	location_label.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))
	location_label.position = Vector2(8 * s, 3 * s)
	location_label.size = Vector2(90 * s, 18 * s)
	loc_bar.add_child(location_label)
	
	time_label = Label.new()
	time_label.text = "12:30 PM"
	time_label.add_theme_font_size_override("font_size", int(11 * s))
	time_label.add_theme_color_override("font_color", Color(0.9, 0.8, 0.5))
	time_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	time_label.position = Vector2(map_size - 80 * s, 3 * s)
	time_label.size = Vector2(72 * s, 18 * s)
	loc_bar.add_child(time_label)
	
	# Single player tag
	var mode_label := Label.new()
	mode_label.text = "● %s" % ("SINGLE PLAYER" if GameManager.current_mode == GameManager.GameMode.SINGLE_PLAYER else "MULTIPLAYER")
	mode_label.add_theme_font_size_override("font_size", int(12 * s))
	mode_label.add_theme_color_override("font_color", Color(0.6, 0.9, 0.6))
	mode_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	mode_label.position = Vector2(vp_size.x - map_size - 12 * s, 58 * s + map_size + 32 * s)
	mode_label.size = Vector2(map_size, 20 * s)
	add_child(mode_label)
	
	# ── Bottom-left: Virtual joystick ──
	var joystick := VirtualJoystick.new()
	joystick.position = Vector2(30 * s, vp_size.y - 190 * s)
	add_child(joystick)
	
	# ── Bottom-right: Action buttons (sprint / interact / jump) ──
	var btn_size := 56 * s
	var action_x := vp_size.x - btn_size - 24 * s
	
	var btn_jump := _make_round_button("⬆", action_x, vp_size.y - 190 * s, btn_size, Color(0.15, 0.15, 0.18, 0.75))
	btn_jump.pressed.connect(func(): TouchInput.request_jump())
	add_child(btn_jump)
	
	var btn_interact := _make_round_button("✋", action_x, vp_size.y - 130 * s, btn_size, Color(0.15, 0.15, 0.18, 0.75))
	btn_interact.pressed.connect(func(): TouchInput.request_interact())
	add_child(btn_interact)
	
	var btn_sprint := _make_round_button("🏃", action_x, vp_size.y - 70 * s, btn_size, Color(0.15, 0.15, 0.18, 0.75))
	btn_sprint.button_down.connect(func(): TouchInput.set_sprint(true))
	btn_sprint.button_up.connect(func(): TouchInput.set_sprint(false))
	add_child(btn_sprint)
	
	# ── Bottom-center: Hotbar ──
	var hotbar := HBoxContainer.new()
	var hb_w := 340 * s
	hotbar.position = Vector2(vp_size.x / 2 - hb_w / 2, vp_size.y - 60 * s)
	hotbar.size = Vector2(hb_w, 50 * s)
	hotbar.add_theme_constant_override("separation", int(6 * s))
	add_child(hotbar)
	
	var hotbar_items := [
		{"icon": "🧱", "count": ""},
		{"icon": "🚗", "count": "1"},
		{"icon": "🎲", "count": "1"},
		{"icon": "🟥", "count": "30"},
		{"icon": "🟨", "count": "30"},
		{"icon": "🟦", "count": "30"},
	]
	for item in hotbar_items:
		var slot := _make_hotbar_slot(item["icon"], item["count"], 48 * s)
		hotbar.add_child(slot)
	
	# ── Notification (center-top, temporary) ──
	notification_label = Label.new()
	notification_label.text = ""
	notification_label.add_theme_font_size_override("font_size", int(22 * s))
	notification_label.add_theme_color_override("font_color", Color(1.0, 0.9, 0.3))
	notification_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notification_label.position = Vector2(0, 140 * s)
	notification_label.size = Vector2(vp_size.x, 35 * s)
	notification_label.visible = false
	add_child(notification_label)
	
	# Connect signals
	GameManager.coins_changed.connect(func(amount): coin_label.text = "🟨 %d" % amount)
	GameManager.player_count_changed.connect(func(count):
		var mode_str = "SINGLE PLAYER" if GameManager.current_mode == GameManager.GameMode.SINGLE_PLAYER else "MULTIPLAYER"
		mode_label.text = "● %s (%d)" % [mode_str, count]
	)
	
	if mission_system:
		_connect_mission_signals()

func _make_round_button(icon_text: String, x: float, y: float, sz: float, bg_color: Color) -> Button:
	var btn := Button.new()
	btn.text = icon_text
	btn.custom_minimum_size = Vector2(sz, sz)
	btn.position = Vector2(x, y)
	btn.add_theme_font_size_override("font_size", int(sz * 0.4))
	var style := StyleBoxFlat.new()
	style.bg_color = bg_color
	style.corner_radius_top_left = int(sz / 2)
	style.corner_radius_top_right = int(sz / 2)
	style.corner_radius_bottom_left = int(sz / 2)
	style.corner_radius_bottom_right = int(sz / 2)
	style.border_width_left = 2
	style.border_width_right = 2
	style.border_width_top = 2
	style.border_width_bottom = 2
	style.border_color = Color(1, 1, 1, 0.3)
	btn.add_theme_stylebox_override("normal", style)
	var style_pressed := style.duplicate()
	style_pressed.bg_color = bg_color.lightened(0.2)
	btn.add_theme_stylebox_override("pressed", style_pressed)
	return btn

func _make_hotbar_slot(icon_text: String, count: String, sz: float) -> Panel:
	var slot := Panel.new()
	slot.custom_minimum_size = Vector2(sz, sz)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.1, 0.12, 0.75)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_left = 6
	style.corner_radius_bottom_right = 6
	style.border_width_left = 1
	style.border_width_right = 1
	style.border_width_top = 1
	style.border_width_bottom = 1
	style.border_color = Color(1, 1, 1, 0.2)
	slot.add_theme_stylebox_override("panel", style)
	
	var icon_label := Label.new()
	icon_label.text = icon_text
	icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	icon_label.add_theme_font_size_override("font_size", int(sz * 0.4))
	slot.add_child(icon_label)
	
	if count != "":
		var count_label := Label.new()
		count_label.text = count
		count_label.add_theme_font_size_override("font_size", int(sz * 0.22))
		count_label.add_theme_color_override("font_color", Color(1, 1, 1))
		count_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		count_label.position = Vector2(0, sz - sz * 0.28)
		count_label.size = Vector2(sz - 4, sz * 0.26)
		slot.add_child(count_label)
	
	return slot

func _on_pause_pressed() -> void:
	get_tree().paused = not get_tree().paused

func _connect_mission_signals() -> void:
	mission_system.objective_updated.connect(func(text):
		notification_label.text = text
		notification_label.visible = true
		notification_timer = 3.0
	)
	mission_system.mission_completed_signal.connect(func(m):
		notification_label.text = "Mission Complete! +%d coins" % m.get("reward_coins", 0)
		notification_label.visible = true
		notification_timer = 4.0
	)
	mission_system.mission_failed.connect(func(m):
		notification_label.text = "Mission Failed!"
		notification_label.visible = true
		notification_timer = 3.0
	)

func update_hud(p: CharacterBody3D, ms: Node) -> void:
	player = p
	mission_system = ms
	
	# Update mission tracker
	if mission_system and mission_system.mission_active:
		mission_title_label.text = "MISSION: " + mission_system.active_mission.get("name", "").to_upper()
		var obj_text: String = mission_system.get_current_objective_text()
		var time_left: float = mission_system.get_time_remaining()
		if time_left > 0:
			obj_text += "  (%.0fs)" % time_left
		mission_desc_label.text = obj_text
	else:
		mission_title_label.text = "NEW MISSION"
		mission_desc_label.text = "Press Q near a mission marker to begin"
	
	# Update health/energy bars
	if player and player.has_method("get") :
		var cur_health: float = player.get("health") if player.get("health") != null else 100.0
		var cur_energy: float = player.get("energy") if player.get("energy") != null else 100.0
		var health_pct: float = clamp(cur_health / 100.0, 0.0, 1.0)
		var energy_pct: float = clamp(cur_energy / 100.0, 0.0, 1.0)
		
		var health_text := get_node_or_null("HealthText") as Label
		var energy_text := get_node_or_null("EnergyText") as Label
		
		if health_bar_fill and health_text:
			var bg_w: float = health_text.size.x
			health_bar_fill.size.x = max(0.0, (bg_w - 4) * health_pct)
			health_text.text = "%d/100" % int(cur_health)
		if energy_bar_fill and energy_text:
			var bg_w2: float = energy_text.size.x
			energy_bar_fill.size.x = max(0.0, (bg_w2 - 4) * energy_pct)
			energy_text.text = "%d/100" % int(cur_energy)

func _process(delta: float) -> void:
	# Notification timer
	if notification_timer > 0:
		notification_timer -= delta
		if notification_timer <= 0:
			notification_label.visible = false
	
	# Update time-of-day label from day/night cycle if available
	var dn_nodes := get_tree().get_nodes_in_group("day_night_cycle")
	if dn_nodes.size() > 0 and dn_nodes[0].has_method("get_time_string"):
		time_label.text = dn_nodes[0].get_time_string()
	
	# Draw minimap
	_draw_minimap()

func _draw_minimap() -> void:
	if not minimap:
		return
	
	# Build the draw node ONCE and reuse it — creating/freeing a new Control
	# every frame caused stale-node draw errors (matches the correct pattern
	# already used in virtual_joystick.gd).
	var draw_node: Control = minimap.get_node_or_null("DrawNode")
	if not draw_node:
		draw_node = Control.new()
		draw_node.name = "DrawNode"
		draw_node.set_anchors_preset(Control.PRESET_FULL_RECT)
		draw_node.mouse_filter = Control.MOUSE_FILTER_IGNORE
		minimap.add_child(draw_node)
		draw_node.draw.connect(_on_minimap_draw)
	draw_node.queue_redraw()

func _on_minimap_draw() -> void:
	var draw: Control = minimap.get_node("DrawNode") as Control
	if not draw:
		return
	
	var map_size: float = minimap.size.x
	var center := Vector2(map_size / 2.0, map_size / 2.0)
	var scale := map_size / 500.0  # world to minimap scale
	
	# Draw landmarks
	for landmark in LandmarkGenerator.landmarks:
		var pos: Vector3 = landmark["pos"]
		var mp := center + Vector2(pos.x * scale, pos.z * scale)
		if mp.distance_to(center) < map_size / 2.0 - 4:
			draw.draw_circle(mp, 3, Color(0.6, 0.5, 0.3))
	
	# Draw player position
	if player:
		var ppos: Vector2 = center + Vector2(player.global_position.x * scale, player.global_position.z * scale)
		ppos.x = clamp(ppos.x, 5, map_size - 5)
		ppos.y = clamp(ppos.y, 5, map_size - 5)
		draw.draw_circle(ppos, 4, Color(0.2, 0.8, 0.3))
		var angle: float = atan2(-player.velocity.x, -player.velocity.z) if player.velocity.length() > 0.1 else 0.0
		var dir: Vector2 = Vector2(sin(angle), -cos(angle)) * 6
		draw.draw_line(ppos, ppos + dir, Color(0.2, 0.8, 0.3), 2)
