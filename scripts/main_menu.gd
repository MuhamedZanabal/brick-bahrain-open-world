extends Control
## Reference-matched Bahrain Brick main menu built from native responsive controls.

var _dialog: AcceptDialog

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.MENU
	_build_ui()

func _build_ui() -> void:
	var background := TextureRect.new()
	background.name = "WaterfrontBackground"
	background.texture = load("res://assets/splash_screen.png")
	background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background.set_anchors_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)
	move_child(background, 0)

	var right_gradient := Gradient.new()
	right_gradient.set_color(0, Color(0.01, 0.015, 0.025, 0.08))
	right_gradient.set_color(1, Color(0.008, 0.012, 0.02, 0.9))
	var right_texture := GradientTexture2D.new()
	right_texture.gradient = right_gradient
	right_texture.fill_from = Vector2(0.38, 0.5)
	right_texture.fill_to = Vector2(1.0, 0.5)
	var right_shade := TextureRect.new()
	right_shade.texture = right_texture
	right_shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	right_shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	right_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(right_shade)

	var bottom_gradient := Gradient.new()
	bottom_gradient.set_color(0, Color(0.01, 0.015, 0.025, 0.0))
	bottom_gradient.set_color(1, Color(0.005, 0.008, 0.014, 0.82))
	var bottom_texture := GradientTexture2D.new()
	bottom_texture.gradient = bottom_gradient
	bottom_texture.fill_from = Vector2(0.5, 0.46)
	bottom_texture.fill_to = Vector2(0.5, 1.0)
	var bottom_shade := TextureRect.new()
	bottom_shade.texture = bottom_texture
	bottom_shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bottom_shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	bottom_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bottom_shade)

	var safe_area := get_node_or_null("SafeArea") as MarginContainer
	if safe_area == null:
		safe_area = SafeAreaRoot.new()
		safe_area.name = "SafeArea"
		safe_area.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(safe_area)

	_build_hero_region(safe_area)
	_build_menu_region(safe_area)
	_build_profile_region(safe_area)
	_build_footer_region(safe_area)

func _build_hero_region(parent: Control) -> void:
	var hero := VBoxContainer.new()
	hero.name = "HeroRegion"
	hero.anchor_left = 0.045
	hero.anchor_top = 0.08
	hero.anchor_right = 0.58
	hero.anchor_bottom = 0.62
	hero.offset_left = 0
	hero.offset_top = 0
	hero.offset_right = 0
	hero.offset_bottom = 0
	hero.alignment = BoxContainer.ALIGNMENT_CENTER
	hero.add_theme_constant_override("separation", 0)
	parent.add_child(hero)

	var crest := TextureRect.new()
	crest.texture = load("res://assets/app_icon.png")
	crest.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	crest.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	crest.custom_minimum_size = Vector2(110, 110)
	crest.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hero.add_child(crest)

	var bahrain := Label.new()
	bahrain.text = "BAHRAIN"
	bahrain.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bahrain.add_theme_font_size_override("font_size", BahrainTheme.title_size(get_viewport_rect().size))
	bahrain.add_theme_color_override("font_color", BahrainTheme.TEXT)
	bahrain.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.96))
	bahrain.add_theme_constant_override("outline_size", 11)
	hero.add_child(bahrain)

	var brick := Label.new()
	brick.text = "BRICK"
	brick.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brick.add_theme_font_size_override("font_size", int(BahrainTheme.title_size(get_viewport_rect().size) * 0.9))
	brick.add_theme_color_override("font_color", BahrainTheme.RED)
	brick.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.96))
	brick.add_theme_constant_override("outline_size", 11)
	hero.add_child(brick)

	var plaque := PanelContainer.new()
	plaque.custom_minimum_size = Vector2(390, 54)
	plaque.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.018, 0.025, 0.036, 0.92), BahrainTheme.GOLD, 10))
	hero.add_child(plaque)
	var subtitle := Label.new()
	subtitle.text = "OPEN WORLD SANDBOX"
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 20)
	subtitle.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	plaque.add_child(subtitle)

	var location := Label.new()
	location.text = "MANAMA  •  KINGDOM OF BAHRAIN"
	location.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	location.add_theme_font_size_override("font_size", 15)
	location.add_theme_color_override("font_color", Color(1, 1, 1, 0.78))
	location.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	location.add_theme_constant_override("outline_size", 4)
	hero.add_child(location)

func _build_menu_region(parent: Control) -> void:
	var panel := PanelContainer.new()
	panel.name = "ActionMenu"
	panel.anchor_left = 0.72
	panel.anchor_top = 0.055
	panel.anchor_right = 0.975
	panel.anchor_bottom = 0.87
	panel.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.015, 0.022, 0.034, 0.9), Color(1, 1, 1, 0.16), 20))
	parent.add_child(panel)

	var stack := VBoxContainer.new()
	stack.alignment = BoxContainer.ALIGNMENT_CENTER
	stack.add_theme_constant_override("separation", 8)
	panel.add_child(stack)

	var play_button := _create_menu_button("Play", BahrainTheme.GREEN, ">")
	var character_button := _create_menu_button("Character Select", BahrainTheme.ORANGE, "◆")
	var multiplayer_button := _create_menu_button("Multiplayer", BahrainTheme.BLUE, "◎")
	var missions_button := _create_menu_button("Missions", BahrainTheme.PURPLE, "+")
	var settings_button := _create_menu_button("Settings", BahrainTheme.GOLD, "⚙")
	var credits_button := _create_menu_button("Credits", BahrainTheme.CYAN, "★")
	var exit_button := _create_menu_button("Exit", BahrainTheme.RED, "←")

	for button in [play_button, character_button, multiplayer_button, missions_button, settings_button, credits_button, exit_button]:
		stack.add_child(button)

	play_button.pressed.connect(func(): GameManager.start_singleplayer())
	character_button.pressed.connect(func(): GameManager.show_character_select())
	multiplayer_button.pressed.connect(_show_multiplayer_dialog)
	missions_button.pressed.connect(_show_mission_preview)
	settings_button.pressed.connect(_show_settings_preview)
	credits_button.pressed.connect(_show_credits)
	exit_button.pressed.connect(func(): get_tree().quit())

func _build_profile_region(parent: Control) -> void:
	var profile := PanelContainer.new()
	profile.name = "PlayerProfile"
	profile.anchor_left = 0.035
	profile.anchor_top = 0.765
	profile.anchor_right = 0.38
	profile.anchor_bottom = 0.955
	profile.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.012, 0.02, 0.032, 0.9), Color(1, 1, 1, 0.18), 16))
	parent.add_child(profile)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	profile.add_child(row)

	var crest := TextureRect.new()
	crest.texture = load("res://assets/app_icon.png")
	crest.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	crest.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	crest.custom_minimum_size = Vector2(88, 88)
	crest.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(crest)

	var details := VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 4)
	row.add_child(details)

	var player_name := Label.new()
	player_name.text = "BRICK BAHRAIN"
	player_name.add_theme_font_size_override("font_size", 21)
	player_name.add_theme_color_override("font_color", BahrainTheme.TEXT)
	details.add_child(player_name)

	var level_row := HBoxContainer.new()
	details.add_child(level_row)
	var level := Label.new()
	level.text = "LEVEL 12"
	level.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	level.add_theme_font_size_override("font_size", 15)
	level.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	level_row.add_child(level)
	var coins := Label.new()
	coins.text = "GOLD  %s" % _format_number(SaveManager.get_coins())
	coins.add_theme_font_size_override("font_size", 15)
	coins.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	level_row.add_child(coins)

	var progress := ProgressBar.new()
	progress.min_value = 0
	progress.max_value = 100
	progress.value = 64
	progress.show_percentage = false
	progress.custom_minimum_size = Vector2(0, 16)
	var background_style := StyleBoxFlat.new()
	background_style.bg_color = Color(0.08, 0.09, 0.11, 0.95)
	background_style.set_corner_radius_all(8)
	progress.add_theme_stylebox_override("background", background_style)
	var fill_style := StyleBoxFlat.new()
	fill_style.bg_color = BahrainTheme.GOLD
	fill_style.set_corner_radius_all(8)
	progress.add_theme_stylebox_override("fill", fill_style)
	details.add_child(progress)

func _build_footer_region(parent: Control) -> void:
	var footer := HBoxContainer.new()
	footer.name = "FooterActions"
	footer.anchor_left = 0.735
	footer.anchor_top = 0.89
	footer.anchor_right = 0.97
	footer.anchor_bottom = 0.97
	footer.alignment = BoxContainer.ALIGNMENT_END
	footer.add_theme_constant_override("separation", 10)
	parent.add_child(footer)
	for item in [["D", "Community"], ["IG", "Instagram"], ["TT", "TikTok"], ["YT", "YouTube"], ["X", "Updates"]]:
		var button := _create_footer_button(String(item[0]), String(item[1]))
		footer.add_child(button)

func _create_menu_button(label: String, color: Color, icon_text: String) -> Button:
	var button := Button.new()
	button.text = "%s  %s" % [icon_text, label]
	button.custom_minimum_size = Vector2(330, 58)
	button.add_theme_font_size_override("font_size", 23)
	button.add_theme_color_override("font_color", BahrainTheme.TEXT)
	button.add_theme_color_override("font_hover_color", Color.WHITE)
	button.add_theme_stylebox_override("normal", BahrainTheme.button_style(color))
	button.add_theme_stylebox_override("hover", BahrainTheme.button_style(color.lightened(0.08)))
	button.add_theme_stylebox_override("pressed", BahrainTheme.button_style(color, true))
	return button

func _create_footer_button(label: String, tooltip: String) -> Button:
	var button := Button.new()
	button.text = label
	button.tooltip_text = tooltip
	button.custom_minimum_size = Vector2(48, 48)
	button.add_theme_font_size_override("font_size", 14)
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color(0.035, 0.045, 0.065, 0.9)
	normal.border_color = Color(1, 1, 1, 0.28)
	normal.set_border_width_all(2)
	normal.set_corner_radius_all(24)
	button.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = BahrainTheme.GOLD.darkened(0.35)
	hover.border_color = BahrainTheme.GOLD_LIGHT
	button.add_theme_stylebox_override("hover", hover)
	button.pressed.connect(func(): _show_info_dialog(tooltip, "%s channels will be linked in a later production integration." % tooltip))
	return button

func _show_multiplayer_dialog() -> void:
	var dialog := AcceptDialog.new()
	dialog.title = "Multiplayer"
	dialog.dialog_text = "Choose how you want to enter Bahrain."
	dialog.ok_button_text = "Cancel"
	dialog.add_button("Host Game", true, "host")
	dialog.add_button("Join Game", true, "join")
	dialog.custom_action.connect(func(action: StringName):
		dialog.hide()
		if action == &"host":
			GameManager.start_multiplayer_host()
		elif action == &"join":
			GameManager.start_multiplayer_client()
	)
	add_child(dialog)
	dialog.popup_centered(Vector2i(640, 320))

func _show_mission_preview() -> void:
	var text := "GRAND PRIX CIRCUIT\nRace the Bahrain International Circuit.\n\n"
	text += "SOUQ TREASURE HUNT\nFind hidden gems in Manama Souq.\n\n"
	text += "FORT EXPEDITION\nExplore Bahrain Fort and recover lost bricks.\n\n"
	text += "CAUSEWAY SPRINT\nRace toward the King Fahd Causeway."
	_show_info_dialog("Missions", text)

func _show_settings_preview() -> void:
	var settings := SaveManager.get_settings()
	var text := "Quality: %s\nBrightness: %d%%\nField of View: %d°\n\n" % [
		String(settings.get("quality", "medium")).capitalize(),
		int(float(settings.get("brightness", 0.8)) * 100.0),
		int(float(settings.get("field_of_view", 75.0))),
	]
	text += "The full interactive graphics, controls, audio, and gameplay settings panel is delivered in the pause/settings slice."
	_show_info_dialog("Settings", text)

func _show_credits() -> void:
	_show_info_dialog("Credits", "BAHRAIN BRICK\nAn open-world brick sandbox by Zanabal Gaming.\n\nBuilt with Godot Engine.\nLegends are brick.")

func _show_info_dialog(title: String, text: String) -> void:
	if is_instance_valid(_dialog):
		_dialog.queue_free()
	_dialog = AcceptDialog.new()
	_dialog.title = title
	_dialog.dialog_text = text
	_dialog.ok_button_text = "Close"
	add_child(_dialog)
	_dialog.popup_centered(Vector2i(720, 480))

func _format_number(value: int) -> String:
	var text := str(max(value, 0))
	var output := ""
	while text.length() > 3:
		output = "," + text.right(3) + output
		text = text.left(text.length() - 3)
	return text + output
