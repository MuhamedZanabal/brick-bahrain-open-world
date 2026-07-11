extends Control
## CharacterSelect - Character roster selection screen
## Shows all playable minifigures with their stats and abilities
## Mobile-responsive: scales UI based on viewport size

var selected_index: int = 0
var character_preview: SubViewportContainer
var preview_camera: Camera3D
var preview_world: Node3D
var info_label: RichTextLabel
var name_label: Label
var stats_container: VBoxContainer

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.CHARACTER_SELECT
	GameManager.selected_character_index = 0
	_build_ui()
	_update_preview()

func _get_scale() -> float:
	# Scale UI based on screen size — base design is 1280x720
	var vp := get_viewport().get_visible_rect().size
	return min(vp.x / 1280.0, vp.y / 720.0) * 1.2  # slight upscale for readability

func _build_ui() -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var s := _get_scale()
	
	# Background — same Zanabal Gaming artwork as main menu/splash, darkened for readability
	var bg_tex := TextureRect.new()
	var tex := load("res://assets/splash_screen.png")
	if tex:
		bg_tex.texture = tex
		bg_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		bg_tex.stretch_mode = TextureRect.STRETCH_SCALE
	bg_tex.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg_tex)

	var bg_dim := ColorRect.new()
	bg_dim.color = Color(0.05, 0.05, 0.06, 0.62)
	bg_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg_dim)
	
	# Title
	var title := Label.new()
	title.text = "SELECT YOUR CHARACTER"
	title.add_theme_font_size_override("font_size", int(36 * s))
	title.add_theme_color_override("font_color", Color(1.0, 0.8, 0.0))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 20 * s)
	title.size = Vector2(vp_size.x, 50 * s)
	add_child(title)
	
	# Character preview (3D viewport on the left)
	var pv_w := 400 * s
	var pv_h := 400 * s
	character_preview = SubViewportContainer.new()
	character_preview.position = Vector2(40 * s, 90 * s)
	character_preview.size = Vector2(pv_w, pv_h)
	character_preview.stretch = true
	add_child(character_preview)
	
	var sub_vp := SubViewport.new()
	sub_vp.size = Vector2(400, 400)
	sub_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	character_preview.add_child(sub_vp)
	
	# 3D scene for preview
	preview_world = Node3D.new()
	sub_vp.add_child(preview_world)
	
	# Camera
	preview_camera = Camera3D.new()
	preview_camera.position = Vector3(0, 1.5, 4)
	preview_world.add_child(preview_camera)  # must be added to the tree BEFORE look_at
	preview_camera.look_at(Vector3(0, 1, 0))
	
	# Light
	var light := DirectionalLight3D.new()
	light.rotation = Vector3(deg_to_rad(-45), deg_to_rad(30), 0)
	light.light_energy = 1.5
	preview_world.add_child(light)
	
	var hemi := DirectionalLight3D.new()
	hemi.light_energy = 0.5
	preview_world.add_child(hemi)
	
	# Platform
	var platform := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 1.5
	cyl.bottom_radius = 1.5
	cyl.height = 0.2
	platform.mesh = cyl
	var pmat := StandardMaterial3D.new()
	pmat.albedo_color = Color(0.3, 0.3, 0.35)
	platform.material_override = pmat
	platform.position = Vector3(0, 0, 0)
	preview_world.add_child(platform)
	
	# Character info panel (right side) — position responsively
	var panel_x := 40 * s + pv_w + 20 * s
	var panel_w := vp_size.x - panel_x - 20 * s
	if panel_w < 200 * s:
		# On narrow screens, put info below the preview
		panel_x = 40 * s
		panel_w = vp_size.x - 80 * s
	
	info_label = RichTextLabel.new()
	info_label.position = Vector2(panel_x, 90 * s)
	info_label.size = Vector2(panel_w, 150 * s)
	info_label.add_theme_font_size_override("normal_font_size", int(16 * s))
	info_label.add_theme_color_override("default_color", Color(0.9, 0.9, 0.9))
	info_label.bbcode_enabled = true
	add_child(info_label)
	
	# Name label
	name_label = Label.new()
	name_label.add_theme_font_size_override("font_size", int(26 * s))
	name_label.add_theme_color_override("font_color", Color(1.0, 0.9, 0.3))
	name_label.position = Vector2(panel_x, 250 * s)
	name_label.size = Vector2(panel_w, 40 * s)
	add_child(name_label)
	
	# Stats
	stats_container = VBoxContainer.new()
	stats_container.position = Vector2(panel_x, 300 * s)
	stats_container.size = Vector2(panel_w, 100 * s)
	stats_container.add_theme_constant_override("separation", int(6 * s))
	add_child(stats_container)
	
	# Character grid (bottom)
	var grid := GridContainer.new()
	grid.columns = 6
	grid.position = Vector2(40 * s, vp_size.y - 180 * s)
	grid.size = Vector2(vp_size.x - 80 * s, 80 * s)
	grid.add_theme_constant_override("h_separation", int(8 * s))
	grid.add_theme_constant_override("v_separation", int(8 * s))
	add_child(grid)
	_grid = grid
	
	for i in range(GameManager.characters.size()):
		var char_btn := _create_char_button(i, s)
		grid.add_child(char_btn)
	
	# Navigation buttons
	var btn_container := HBoxContainer.new()
	btn_container.position = Vector2(vp_size.x / 2 - 130 * s, vp_size.y - 90 * s)
	btn_container.size = Vector2(260 * s, 45 * s)
	btn_container.add_theme_constant_override("separation", int(20 * s))
	add_child(btn_container)
	
	var btn_prev := Button.new()
	btn_prev.text = "< Prev"
	btn_prev.custom_minimum_size = Vector2(110 * s, 40 * s)
	btn_prev.add_theme_font_size_override("font_size", int(14 * s))
	btn_prev.pressed.connect(func(): _change_selection(-1))
	btn_container.add_child(btn_prev)
	
	var btn_next := Button.new()
	btn_next.text = "Next >"
	btn_next.custom_minimum_size = Vector2(110 * s, 40 * s)
	btn_next.add_theme_font_size_override("font_size", int(14 * s))
	btn_next.pressed.connect(func(): _change_selection(1))
	btn_container.add_child(btn_next)
	
	# Start button — large and prominent
	var btn_start := Button.new()
	btn_start.text = "ENTER BAHRAIN"
	btn_start.custom_minimum_size = Vector2(250 * s, 50 * s)
	btn_start.add_theme_font_size_override("font_size", int(18 * s))
	btn_start.position = Vector2(vp_size.x / 2 - 125 * s, vp_size.y - 35 * s)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.2, 0.6, 0.3)
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_left = 8
	style.corner_radius_bottom_right = 8
	btn_start.add_theme_stylebox_override("normal", style)
	var style_h := StyleBoxFlat.new()
	style_h.bg_color = Color(0.25, 0.7, 0.35)
	style_h.corner_radius_top_left = 8
	style_h.corner_radius_top_right = 8
	style_h.corner_radius_bottom_left = 8
	style_h.corner_radius_bottom_right = 8
	btn_start.add_theme_stylebox_override("hover", style_h)
	btn_start.pressed.connect(func(): GameManager.enter_world())
	add_child(btn_start)
	
	# Back button
	var btn_back := Button.new()
	btn_back.text = "Back"
	btn_back.custom_minimum_size = Vector2(90 * s, 35 * s)
	btn_back.add_theme_font_size_override("font_size", int(14 * s))
	btn_back.position = Vector2(15 * s, 15 * s)
	btn_back.pressed.connect(func(): GameManager.back_to_menu())
	add_child(btn_back)
	
	# Name input
	var name_edit := LineEdit.new()
	name_edit.text = GameManager.player_name
	name_edit.placeholder_text = "Enter your name"
	name_edit.position = Vector2(panel_x, 55 * s)
	name_edit.size = Vector2(180 * s, 30 * s)
	name_edit.add_theme_font_size_override("font_size", int(14 * s))
	name_edit.text_changed.connect(func(t): GameManager.player_name = t)
	add_child(name_edit)

func _create_char_button(index: int, s: float) -> Button:
	var btn := Button.new()
	var char_data := GameManager.characters[index]
	btn.text = char_data.name
	btn.custom_minimum_size = Vector2(140 * s, 40 * s)
	btn.add_theme_font_size_override("font_size", int(11 * s))
	btn.pressed.connect(func(): _select_character(index))
	
	if index == selected_index:
		var style := StyleBoxFlat.new()
		style.bg_color = Color(0.3, 0.4, 0.6)
		style.border_width_bottom = 3
		style.border_color = Color(1, 0.8, 0)
		btn.add_theme_stylebox_override("normal", style)
	
	return btn

func _select_character(index: int) -> void:
	selected_index = index
	GameManager.selected_character_index = index
	_update_preview()
	_rebuild_grid()

func _change_selection(dir: int) -> void:
	selected_index = (selected_index + dir + GameManager.characters.size()) % GameManager.characters.size()
	GameManager.selected_character_index = selected_index
	_update_preview()
	_rebuild_grid()

var _grid: GridContainer

func _rebuild_grid() -> void:
	if _grid == null:
		return
	
	for child in _grid.get_children():
		child.queue_free()
	
	var s := _get_scale()
	for i in range(GameManager.characters.size()):
		_grid.add_child(_create_char_button(i, s))

func _update_preview() -> void:
	# Clear old preview
	for child in preview_world.get_children():
		if child is not Camera3D and child is not DirectionalLight3D and not child.name.begins_with("Platform"):
			child.queue_free()
	
	# Create new character preview — real animated model if available,
	# otherwise fall back to a procedural brick minifigure.
	var char_data := GameManager.get_character(selected_index)
	var model_path: String = char_data.get("model_path", "")
	var fig: Node3D = BrickFactory.load_character_model(model_path)
	if fig == null:
		fig = BrickFactory.create_minifigure(char_data)
	else:
		var anim_player: AnimationPlayer = fig.get_meta("anim_player", null)
		var anim_prefix: String = fig.get_meta("anim_prefix", "")
		if anim_player and anim_player.has_animation(anim_prefix + "Idle"):
			anim_player.play(anim_prefix + "Idle")
	fig.position = Vector3(0, 0.1, 0)
	fig.rotation.y = PI  # face the preview camera
	preview_world.add_child(fig)
	
	# Update info
	name_label.text = char_data.name
	info_label.text = "[i]%s[/i]" % char_data.description
	
	# Stats
	for child in stats_container.get_children():
		child.queue_free()
	
	var s := _get_scale()
	var speed_bar := _create_stat_bar("Speed", char_data.speed_mult, s)
	stats_container.add_child(speed_bar)
	
	var jump_bar := _create_stat_bar("Jump", char_data.jump_mult, s)
	stats_container.add_child(jump_bar)
	
	var ability_label := Label.new()
	ability_label.text = "Special: %s" % _ability_name(char_data.ability)
	ability_label.add_theme_font_size_override("font_size", int(14 * s))
	ability_label.add_theme_color_override("font_color", Color(1, 0.8, 0.2))
	stats_container.add_child(ability_label)

func _create_stat_bar(stat_name: String, value: float, s: float) -> HBoxContainer:
	var container := HBoxContainer.new()
	
	var label := Label.new()
	label.text = stat_name + ":"
	label.custom_minimum_size = Vector2(70 * s, 22 * s)
	label.add_theme_font_size_override("font_size", int(14 * s))
	label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	container.add_child(label)
	
	var bar := ProgressBar.new()
	bar.min_value = 0.8
	bar.max_value = 1.5
	bar.value = value
	bar.custom_minimum_size = Vector2(130 * s, 22 * s)
	bar.show_percentage = false
	container.add_child(bar)
	
	var val_label := Label.new()
	val_label.text = "x%.1f" % value
	val_label.add_theme_font_size_override("font_size", int(12 * s))
	val_label.add_theme_color_override("font_color", Color(0.9, 0.9, 0.3))
	container.add_child(val_label)
	
	return container

func _ability_name(ability: String) -> String:
	match ability:
		"nitro": return "Nitro Boost (faster vehicles)"
		"trade": return "Merchant (bonus coins)"
		"explore": return "Explorer (higher jump, faster sprint)"
		"dive": return "Pearl Diver (swim speed, underwater)"
		"pilot": return "Pilot (vehicle handling master)"
		"drift": return "Street Racer (drift king, stunt bonus)"
		_: return ability

func _process(delta: float) -> void:
	# Rotate the preview character
	for child in preview_world.get_children():
		if child.name == "Model":
			child.rotation.y += delta * 0.5
