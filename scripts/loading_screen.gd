extends Control
## Staged loading screen between the studio splash and the interactive main menu.

const NEXT_SCENE := "res://scenes/main_menu.tscn"
const MILESTONES := [
	{"label": "Loading Bahrain skyline", "resource": "res://assets/splash_screen.png"},
	{"label": "Preparing brick materials", "resource": "res://scripts/ui/bahrain_theme.gd"},
	{"label": "Connecting gameplay systems", "resource": "res://scripts/game_manager.gd"},
	{"label": "Finalizing menu", "resource": NEXT_SCENE},
]
const TIPS := [
	"Explore Manama to discover missions and hidden brick rewards.",
	"Visit the Souq, Bahrain Fort, and the waterfront skyline.",
	"Choose Pearl Diver, Street Racer, or Sky Pilot before entering the world.",
	"Use quality settings to balance reflections and performance on mobile.",
]

var _progress: ProgressBar
var _status: Label
var _percent: Label
var _tip: Label
var _transitioned := false

func _ready() -> void:
	_build_ui()
	call_deferred("_run_milestones")

func _build_ui() -> void:
	var background := TextureRect.new()
	background.texture = load("res://assets/splash_screen.png")
	background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background.set_anchors_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)
	move_child(background, 0)

	var top_shade := ColorRect.new()
	top_shade.color = Color(0.01, 0.025, 0.06, 0.52)
	top_shade.anchor_left = 0.0
	top_shade.anchor_top = 0.0
	top_shade.anchor_right = 1.0
	top_shade.anchor_bottom = 0.56
	top_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(top_shade)

	var lower_shade := ColorRect.new()
	lower_shade.color = Color(0.006, 0.009, 0.018, 0.82)
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

	var layout := VBoxContainer.new()
	layout.set_anchors_preset(Control.PRESET_FULL_RECT)
	layout.offset_left = 80
	layout.offset_top = 64
	layout.offset_right = -80
	layout.offset_bottom = -48
	layout.alignment = BoxContainer.ALIGNMENT_CENTER
	layout.add_theme_constant_override("separation", 12)
	safe_area.add_child(layout)

	var spacer_top := Control.new()
	spacer_top.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(spacer_top)

	var title_row := HBoxContainer.new()
	title_row.alignment = BoxContainer.ALIGNMENT_CENTER
	title_row.add_theme_constant_override("separation", 18)
	layout.add_child(title_row)

	var bahrain := Label.new()
	bahrain.text = "BAHRAIN"
	bahrain.add_theme_font_size_override("font_size", BahrainTheme.title_size(get_viewport_rect().size))
	bahrain.add_theme_color_override("font_color", BahrainTheme.TEXT)
	bahrain.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.95))
	bahrain.add_theme_constant_override("outline_size", 10)
	title_row.add_child(bahrain)

	var brick := Label.new()
	brick.text = "BRICK"
	brick.add_theme_font_size_override("font_size", BahrainTheme.title_size(get_viewport_rect().size))
	brick.add_theme_color_override("font_color", BahrainTheme.RED)
	brick.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.95))
	brick.add_theme_constant_override("outline_size", 10)
	title_row.add_child(brick)

	var subtitle_panel := PanelContainer.new()
	subtitle_panel.add_theme_stylebox_override("panel", BahrainTheme.panel_style(Color(0.02, 0.025, 0.035, 0.9), BahrainTheme.GOLD, 10))
	layout.add_child(subtitle_panel)

	var subtitle := Label.new()
	subtitle.text = "OPEN WORLD SANDBOX"
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 20)
	subtitle.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	subtitle_panel.add_child(subtitle)

	var spacer_middle := Control.new()
	spacer_middle.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(spacer_middle)

	var loading_panel := PanelContainer.new()
	loading_panel.custom_minimum_size = Vector2(860, 210)
	loading_panel.add_theme_stylebox_override("panel", BahrainTheme.panel_style(BahrainTheme.PANEL, BahrainTheme.GOLD, 18))
	layout.add_child(loading_panel)

	var loading_content := VBoxContainer.new()
	loading_content.add_theme_constant_override("separation", 12)
	loading_panel.add_child(loading_content)

	var header_row := HBoxContainer.new()
	loading_content.add_child(header_row)

	_status = Label.new()
	_status.text = "Preparing Bahrain Brick"
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_status.add_theme_font_size_override("font_size", 22)
	_status.add_theme_color_override("font_color", BahrainTheme.TEXT)
	header_row.add_child(_status)

	_percent = Label.new()
	_percent.text = "0%"
	_percent.add_theme_font_size_override("font_size", 22)
	_percent.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	header_row.add_child(_percent)

	_progress = ProgressBar.new()
	_progress.min_value = 0.0
	_progress.max_value = 100.0
	_progress.value = 0.0
	_progress.show_percentage = false
	_progress.custom_minimum_size = Vector2(0, 30)
	var progress_background := StyleBoxFlat.new()
	progress_background.bg_color = Color(0.04, 0.05, 0.065, 0.96)
	progress_background.set_corner_radius_all(12)
	progress_background.set_border_width_all(2)
	progress_background.border_color = Color(1, 1, 1, 0.16)
	_progress.add_theme_stylebox_override("background", progress_background)
	var progress_fill := StyleBoxFlat.new()
	progress_fill.bg_color = BahrainTheme.GOLD
	progress_fill.set_corner_radius_all(10)
	progress_fill.shadow_color = Color(1.0, 0.65, 0.08, 0.45)
	progress_fill.shadow_size = 8
	_progress.add_theme_stylebox_override("fill", progress_fill)
	loading_content.add_child(_progress)

	_tip = Label.new()
	_tip.text = TIPS[0]
	_tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_tip.add_theme_font_size_override("font_size", 16)
	_tip.add_theme_color_override("font_color", BahrainTheme.TEXT_MUTED)
	loading_content.add_child(_tip)

	var brand := Label.new()
	brand.text = "ZANABAL GAMING  •  LEGENDS ARE BRICK"
	brand.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand.add_theme_font_size_override("font_size", 14)
	brand.add_theme_color_override("font_color", Color(1, 1, 1, 0.68))
	layout.add_child(brand)

func _run_milestones() -> void:
	for index in range(MILESTONES.size()):
		var milestone: Dictionary = MILESTONES[index]
		var resource_path := String(milestone["resource"])
		_status.text = String(milestone["label"])
		_tip.text = TIPS[index % TIPS.size()]
		if not ResourceLoader.exists(resource_path):
			_show_load_error(resource_path)
			return
		ResourceLoader.load(resource_path)
		var progress_value := float(index + 1) / float(MILESTONES.size()) * 100.0
		var tween := create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(_progress, "value", progress_value, 0.28)
		_percent.text = "%d%%" % int(progress_value)
		await tween.finished
		await get_tree().create_timer(0.14).timeout

	await get_tree().process_frame
	if not _transitioned:
		_transitioned = true
		GameManager.transition_to(NEXT_SCENE)

func _show_load_error(resource_path: String) -> void:
	_status.text = "Unable to prepare the game"
	_status.add_theme_color_override("font_color", BahrainTheme.RED)
	_tip.text = "Missing required resource: %s" % resource_path
	push_error("LoadingScreen: required resource unavailable: %s" % resource_path)
