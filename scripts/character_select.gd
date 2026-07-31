extends Control
## Three-role Bahrain Brick character selection with one bounded 3D preview viewport.

const ROLE_NAMES := ["Pearl Diver", "Street Racer", "Sky Pilot"]
const ROLE_MARKERS := ["SHELL", "CHECKERED FLAG", "AIRCRAFT"]
const ROLE_DESCRIPTIONS := [
	"Explores the deep blue for rare pearls and hidden treasures.",
	"Rules the streets with speed, skill, and unmistakable style.",
	"Takes to the skies and navigates Bahrain from a new horizon.",
]

var selected_role: int = 0
var _role_cards: Array[Button] = []
var _preview_world: Node3D
var _preview_model: Node3D
var _preview_name: Label
var _preview_description: Label

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.CHARACTER_SELECT
	var saved_index := SaveManager.get_selected_character()
	selected_role = clamp(GameManager.APPROVED_CHARACTER_INDICES.find(saved_index), 0, 2)
	_build_ui()
	_select_role(selected_role)

func _build_ui() -> void:
	var background := TextureRect.new()
	background.texture = load("res://assets/splash_screen.png")
	background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background.set_anchors_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)
	move_child(background, 0)

	var shade := ColorRect.new()
	shade.color = Color(0.008, 0.015, 0.028, 0.58)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)

	var lower_shade := ColorRect.new()
	lower_shade.color = Color(0.006, 0.01, 0.018, 0.62)
	lower_shade.anchor_left = 0.0
	lower_shade.anchor_top = 0.56
	lower_shade.anchor_right = 1.0
	lower_shade.anchor_bottom = 1.0
	lower_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(lower_shade)

	var safe_area := get_node_or_null("SafeArea") as MarginContainer
	if safe_area == null:
		safe_area = SafeAreaRoot.new()
		safe_area.name = "SafeArea"
		safe_area.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(safe_area)

	var content := safe_area.get_node_or_null("Content") as Control
	if content == null:
		content = Control.new()
		content.name = "Content"
		content.set_anchors_preset(Control.PRESET_FULL_RECT)
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		safe_area.add_child(content)

	_build_header(content)
	_build_preview(content)
	_build_role_cards(content)
	_build_navigation(content)

func _build_header(parent: Control) -> void:
	var header := VBoxContainer.new()
	header.anchor_left = 0.17
	header.anchor_top = 0.025
	header.anchor_right = 0.83
	header.anchor_bottom = 0.18
	header.alignment = BoxContainer.ALIGNMENT_CENTER
	header.add_theme_constant_override("separation", 2)
	parent.add_child(header)

	var title := Label.new()
	title.text = "BAHRAIN BRICK"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", int(BahrainTheme.title_size(get_viewport_rect().size) * 0.64))
	title.add_theme_color_override("font_color", BahrainTheme.TEXT)
	title.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.95))
	title.add_theme_constant_override("outline_size", 9)
	header.add_child(title)

	var plaque := PanelContainer.new()
	plaque.custom_minimum_size = Vector2(360, 42)
	plaque.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.02, 0.028, 0.04, 0.94), BahrainTheme.GOLD, 9))
	header.add_child(plaque)
	var subtitle := Label.new()
	subtitle.text = "CHARACTER SELECT"
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 18)
	subtitle.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	plaque.add_child(subtitle)

func _build_preview(parent: Control) -> void:
	var panel := PanelContainer.new()
	panel.name = "SharedPreviewPanel"
	panel.anchor_left = 0.31
	panel.anchor_top = 0.18
	panel.anchor_right = 0.69
	panel.anchor_bottom = 0.61
	panel.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.015, 0.025, 0.04, 0.84), Color(1, 1, 1, 0.2), 20))
	parent.add_child(panel)

	var layout := HBoxContainer.new()
	layout.add_theme_constant_override("separation", 18)
	panel.add_child(layout)

	var preview_container := SubViewportContainer.new()
	preview_container.stretch = true
	preview_container.custom_minimum_size = Vector2(390, 310)
	preview_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	preview_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(preview_container)

	var sub_viewport := SubViewport.new()
	sub_viewport.size = Vector2i(520, 420)
	sub_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sub_viewport.transparent_bg = true
	preview_container.add_child(sub_viewport)

	_preview_world = Node3D.new()
	_preview_world.name = "PreviewWorld"
	sub_viewport.add_child(_preview_world)

	var camera := Camera3D.new()
	camera.position = Vector3(0, 1.6, 4.4)
	_preview_world.add_child(camera)
	camera.look_at(Vector3(0, 1.05, 0))

	var key_light := DirectionalLight3D.new()
	key_light.rotation = Vector3(deg_to_rad(-42), deg_to_rad(28), 0)
	key_light.light_color = Color(1.0, 0.82, 0.58)
	key_light.light_energy = 1.7
	key_light.shadow_enabled = false
	_preview_world.add_child(key_light)

	var fill_light := DirectionalLight3D.new()
	fill_light.rotation = Vector3(deg_to_rad(20), deg_to_rad(210), 0)
	fill_light.light_color = Color(0.38, 0.58, 1.0)
	fill_light.light_energy = 0.8
	fill_light.shadow_enabled = false
	_preview_world.add_child(fill_light)

	var platform := MeshInstance3D.new()
	platform.name = "Podium"
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = 1.45
	cylinder.bottom_radius = 1.6
	cylinder.height = 0.25
	platform.mesh = cylinder
	platform.position = Vector3(0, 0.03, 0)
	var platform_material := StandardMaterial3D.new()
	platform_material.albedo_color = BahrainTheme.GOLD.darkened(0.42)
	platform_material.metallic = 0.55
	platform_material.roughness = 0.24
	platform.material_override = platform_material
	_preview_world.add_child(platform)

	var info := VBoxContainer.new()
	info.custom_minimum_size = Vector2(280, 0)
	info.alignment = BoxContainer.ALIGNMENT_CENTER
	info.add_theme_constant_override("separation", 12)
	layout.add_child(info)

	_preview_name = Label.new()
	_preview_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_preview_name.add_theme_font_size_override("font_size", 30)
	_preview_name.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	info.add_child(_preview_name)

	_preview_description = Label.new()
	_preview_description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_preview_description.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_preview_description.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_preview_description.custom_minimum_size = Vector2(260, 110)
	_preview_description.add_theme_font_size_override("font_size", 17)
	_preview_description.add_theme_color_override("font_color", BahrainTheme.TEXT_MUTED)
	info.add_child(_preview_description)

	var hint := Label.new()
	hint.text = "SELECT A PODIUM BELOW"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 13)
	hint.add_theme_color_override("font_color", Color(1, 1, 1, 0.58))
	info.add_child(hint)

func _build_role_cards(parent: Control) -> void:
	var cards := HBoxContainer.new()
	cards.name = "RolePodiums"
	cards.anchor_left = 0.055
	cards.anchor_top = 0.635
	cards.anchor_right = 0.945
	cards.anchor_bottom = 0.87
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 22)
	parent.add_child(cards)

	var approved := GameManager.get_approved_characters()
	for role_index in range(approved.size()):
		var role: Dictionary = approved[role_index]
		var button := Button.new()
		button.name = "Role%d" % role_index
		button.text = "%s\n%s\n%s" % [ROLE_MARKERS[role_index], ROLE_NAMES[role_index], ROLE_DESCRIPTIONS[role_index]]
		button.custom_minimum_size = Vector2(360, 165)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.add_theme_font_size_override("font_size", 17)
		button.add_theme_color_override("font_color", BahrainTheme.TEXT)
		button.add_theme_color_override("font_hover_color", Color.WHITE)
		button.tooltip_text = String(role.get("description", ROLE_DESCRIPTIONS[role_index]))
		button.pressed.connect(func(index := role_index): _select_role(index))
		cards.add_child(button)
		_role_cards.append(button)

func _build_navigation(parent: Control) -> void:
	var back_button := Button.new()
	back_button.text = "←  Back"
	back_button.anchor_left = 0.045
	back_button.anchor_top = 0.89
	back_button.anchor_right = 0.19
	back_button.anchor_bottom = 0.97
	back_button.add_theme_font_size_override("font_size", 20)
	back_button.add_theme_stylebox_override("normal", BahrainTheme.button_style(Color(0.12, 0.15, 0.2, 0.96)))
	back_button.add_theme_stylebox_override("hover", BahrainTheme.button_style(Color(0.18, 0.22, 0.3, 0.98)))
	back_button.add_theme_stylebox_override("pressed", BahrainTheme.button_style(Color(0.12, 0.15, 0.2, 0.96), true))
	back_button.pressed.connect(func(): GameManager.show_main_menu())
	parent.add_child(back_button)

	var play_button := Button.new()
	play_button.text = ">  Play"
	play_button.anchor_left = 0.405
	play_button.anchor_top = 0.89
	play_button.anchor_right = 0.595
	play_button.anchor_bottom = 0.97
	play_button.add_theme_font_size_override("font_size", 24)
	play_button.add_theme_stylebox_override("normal", BahrainTheme.button_style(BahrainTheme.GREEN))
	play_button.add_theme_stylebox_override("hover", BahrainTheme.button_style(BahrainTheme.GREEN.lightened(0.08)))
	play_button.add_theme_stylebox_override("pressed", BahrainTheme.button_style(BahrainTheme.GREEN, true))
	play_button.pressed.connect(_play_selected)
	parent.add_child(play_button)

func _select_role(role_index: int) -> void:
	selected_role = clamp(role_index, 0, 2)
	GameManager.selected_character_index = GameManager.APPROVED_CHARACTER_INDICES[selected_role]
	SaveManager.set_selected_character(GameManager.selected_character_index, false)
	_refresh_selection_state()
	_update_preview()

func _refresh_selection_state() -> void:
	for index in range(_role_cards.size()):
		var button := _role_cards[index]
		var color := _role_color(index)
		var normal := BahrainTheme.button_style(color.darkened(0.22))
		var hover := BahrainTheme.button_style(color.darkened(0.08))
		if index == selected_role:
			normal.border_color = BahrainTheme.GOLD_LIGHT
			normal.set_border_width_all(4)
			hover.border_color = BahrainTheme.GOLD_LIGHT
			hover.set_border_width_all(4)
		button.add_theme_stylebox_override("normal", normal)
		button.add_theme_stylebox_override("hover", hover)
		button.add_theme_stylebox_override("pressed", BahrainTheme.button_style(color, true))
		button.pivot_offset = button.size * 0.5
		var target_scale := Vector2(1.04, 1.04) if index == selected_role else Vector2.ONE
		create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT).tween_property(button, "scale", target_scale, 0.16)

func _update_preview() -> void:
	if _preview_model and is_instance_valid(_preview_model):
		_preview_model.queue_free()
		_preview_model = null

	var character_index: int = GameManager.APPROVED_CHARACTER_INDICES[selected_role]
	var character_data := GameManager.get_character(character_index)
	var model_path := String(character_data.get("model_path", ""))
	var figure: Node3D = BrickFactory.load_character_model(model_path)
	if figure == null:
		figure = BrickFactory.create_minifigure(character_data)
	else:
		var animation_player: AnimationPlayer = figure.get_meta("anim_player", null)
		var animation_prefix := String(figure.get_meta("anim_prefix", ""))
		if animation_player and animation_player.has_animation(animation_prefix + "Idle"):
			animation_player.play(animation_prefix + "Idle")
	figure.position = Vector3(0, 0.17, 0)
	figure.rotation.y = PI
	_preview_world.add_child(figure)
	_preview_model = figure

	_preview_name.text = ROLE_NAMES[selected_role]
	_preview_description.text = ROLE_DESCRIPTIONS[selected_role]

func _play_selected() -> void:
	SaveManager.set_selected_character(GameManager.selected_character_index, true)
	GameManager.enter_world()

func _role_color(role_index: int) -> Color:
	match role_index:
		0:
			return BahrainTheme.BLUE
		1:
			return BahrainTheme.RED
		2:
			return BahrainTheme.GOLD
		_:
			return BahrainTheme.PANEL_SOFT

func _process(delta: float) -> void:
	if _preview_model and is_instance_valid(_preview_model):
		_preview_model.rotation.y += delta * 0.35
