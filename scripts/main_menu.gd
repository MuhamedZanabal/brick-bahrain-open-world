extends Control
## MainMenu - Title screen with game mode selection
## Mobile-responsive: scales UI based on viewport size
## Background now uses the official Zanabal Gaming splash artwork for visual consistency
## with the splash screen and app icon, instead of a flat color.

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.MENU
	_build_ui()

func _get_scale() -> float:
	var vp := get_viewport().get_visible_rect().size
	return clamp(min(vp.x / 1280.0, vp.y / 720.0) * 1.3, 0.6, 2.0)

func _build_ui() -> void:
	var vp := get_viewport().get_visible_rect().size
	var s := _get_scale()

	# Full screen background — the actual Zanabal Gaming artwork, covering the whole screen
	var bg_tex := TextureRect.new()
	var tex := load("res://assets/splash_screen.png")
	if tex:
		bg_tex.texture = tex
		bg_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		bg_tex.stretch_mode = TextureRect.STRETCH_SCALE
	bg_tex.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg_tex)

	# Dark gradient overlay (top lighter, bottom darker) so text/buttons stay readable
	# over busy artwork — built from two stacked ColorRects for a cheap vertical gradient feel.
	var overlay_top := ColorRect.new()
	overlay_top.color = Color(0.05, 0.04, 0.03, 0.35)
	overlay_top.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(overlay_top)

	var overlay_bottom := ColorRect.new()
	overlay_bottom.color = Color(0.02, 0.02, 0.02, 0.55)
	overlay_bottom.position = Vector2(0, vp.y * 0.42)
	overlay_bottom.size = Vector2(vp.x, vp.y * 0.58)
	add_child(overlay_bottom)

	# Small dragon crest logo (cropped app icon) above the title for brand consistency
	var logo_tex := load("res://assets/app_icon.png")
	if logo_tex:
		var logo := TextureRect.new()
		logo.texture = logo_tex
		logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		var logo_size := 64 * s
		logo.position = Vector2(vp.x / 2 - logo_size / 2, 10 * s)
		logo.size = Vector2(logo_size, logo_size)
		add_child(logo)

	# Title
	var title := Label.new()
	title.text = "BRICK BAHRAIN"
	title.add_theme_font_size_override("font_size", int(56 * s))
	title.add_theme_color_override("font_color", Color(1.0, 0.8, 0.0))
	title.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	title.add_theme_constant_override("outline_size", int(6 * s))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 78 * s)
	title.size = Vector2(vp.x, 70 * s)
	add_child(title)

	# Subtitle
	var subtitle := Label.new()
	subtitle.text = "Open World Sandbox"
	subtitle.add_theme_font_size_override("font_size", int(22 * s))
	subtitle.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))
	subtitle.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	subtitle.add_theme_constant_override("outline_size", int(4 * s))
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.position = Vector2(0, 148 * s)
	subtitle.size = Vector2(vp.x, 30 * s)
	add_child(subtitle)

	# Version / brand tag
	var ver := Label.new()
	ver.text = "Zanabal Gaming — Legends Are Brick — v1.0.0 Mobile Edition"
	ver.add_theme_font_size_override("font_size", int(13 * s))
	ver.add_theme_color_override("font_color", Color(0.75, 0.75, 0.75))
	ver.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	ver.add_theme_constant_override("outline_size", int(3 * s))
	ver.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ver.position = Vector2(0, 180 * s)
	ver.size = Vector2(vp.x, 20 * s)
	add_child(ver)

	# Button container — centered, scaled
	var container := VBoxContainer.new()
	var btn_w := 300 * s
	container.position = Vector2(vp.x / 2 - btn_w / 2, 236 * s)
	container.size = Vector2(btn_w, 380 * s)
	container.add_theme_constant_override("separation", int(12 * s))
	add_child(container)

	# Buttons
	var btn_single := _create_button("Single Player", Color(0.2, 0.6, 0.3), s)
	btn_single.pressed.connect(func(): GameManager.start_singleplayer())
	container.add_child(btn_single)

	var btn_host := _create_button("Host Multiplayer", Color(0.2, 0.4, 0.7), s)
	btn_host.pressed.connect(func(): GameManager.start_multiplayer_host())
	container.add_child(btn_host)

	var btn_join := _create_button("Join Multiplayer", Color(0.5, 0.3, 0.6), s)
	btn_join.pressed.connect(func(): GameManager.start_multiplayer_client())
	container.add_child(btn_join)

	var btn_missions := _create_button("Mission List Preview", Color(0.6, 0.5, 0.2), s)
	btn_missions.pressed.connect(_show_mission_preview)
	container.add_child(btn_missions)

	var btn_exit := _create_button("Exit", Color(0.6, 0.2, 0.2), s)
	btn_exit.pressed.connect(func(): get_tree().quit())
	container.add_child(btn_exit)

	# Info text at bottom
	var info := Label.new()
	info.text = "Explore Bahrain — from Manama skyline to F1 circuit\nBuilt entirely from bricks. Drive. Race. Discover. Play together."
	info.add_theme_font_size_override("font_size", int(14 * s))
	info.add_theme_color_override("font_color", Color(0.75, 0.75, 0.75))
	info.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	info.add_theme_constant_override("outline_size", int(3 * s))
	info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	info.position = Vector2(0, vp.y - 70 * s)
	info.size = Vector2(vp.x, 50 * s)
	add_child(info)

func _create_button(text: String, color: Color, s: float) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(300 * s, 50 * s)
	btn.add_theme_font_size_override("font_size", int(18 * s))

	var style_normal := StyleBoxFlat.new()
	style_normal.bg_color = color
	style_normal.corner_radius_top_left = 8
	style_normal.corner_radius_top_right = 8
	style_normal.corner_radius_bottom_left = 8
	style_normal.corner_radius_bottom_right = 8
	style_normal.content_margin_left = 20
	style_normal.content_margin_right = 20
	style_normal.content_margin_top = 10
	style_normal.content_margin_bottom = 10
	style_normal.shadow_size = 4
	style_normal.shadow_color = Color(0, 0, 0, 0.5)
	btn.add_theme_stylebox_override("normal", style_normal)

	var style_hover := StyleBoxFlat.new()
	style_hover.bg_color = color.lightened(0.15)
	style_hover.corner_radius_top_left = 8
	style_hover.corner_radius_top_right = 8
	style_hover.corner_radius_bottom_left = 8
	style_hover.corner_radius_bottom_right = 8
	style_hover.content_margin_left = 20
	style_hover.content_margin_right = 20
	style_hover.content_margin_top = 10
	style_hover.content_margin_bottom = 10
	style_hover.shadow_size = 6
	style_hover.shadow_color = Color(0, 0, 0, 0.6)
	btn.add_theme_stylebox_override("hover", style_hover)

	var style_pressed := StyleBoxFlat.new()
	style_pressed.bg_color = color.darkened(0.2)
	style_pressed.corner_radius_top_left = 8
	style_pressed.corner_radius_top_right = 8
	style_pressed.corner_radius_bottom_left = 8
	style_pressed.corner_radius_bottom_right = 8
	btn.add_theme_stylebox_override("pressed", style_pressed)

	return btn

func _show_mission_preview() -> void:
	# Simple popup with mission list
	var popup := AcceptDialog.new()
	popup.title = "Available Missions"
	var text := "Race: Grand Prix Circuit — Lap the F1 track (500 coins)\n"
	text += "Collection: Souk Treasure Hunt — Find hidden gems (300 coins)\n"
	text += "Exploration: Fort Expedition — Explore Bahrain Fort (400 coins)\n"
	text += "Time Trial: Causeway Sprint — Race the King Fahd Causeway (350 coins)\n"
	text += "Exploration: Skyline Explorer — Visit Manama landmarks (250 coins)\n"
	text += "Collection: Desert Run — Reach Tree of Life (200 coins)\n"
	text += "Time Trial: Marina Drift — Sprint to Amwaj Islands (300 coins)"
	popup.dialog_text = text
	popup.size = Vector2(500, 300)
	add_child(popup)
	popup.popup_centered()
