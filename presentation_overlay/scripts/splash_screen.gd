extends Control

const SCREENS := [
	{"name": "Zanabal Gaming", "subtitle": "Building worlds, brick by brick", "asset": "res://assets/ui/runtime/splash_zanabal.svg", "accent": Color(0.95, 0.69, 0.20)},
	{"name": "Mansoory Games", "subtitle": "Play. Create. Inspire.", "asset": "res://assets/ui/runtime/splash_mansoory.svg", "accent": Color(0.20, 0.82, 0.93)},
]

var stage := 0
var elapsed := 0.0
var advancing := false
var title_label: Label
var subtitle_label: Label
var background_node: TextureRect
var accent_line: ColorRect
var capture_mode := false

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	capture_mode = "--presentation-test" in OS.get_cmdline_user_args()
	_build()
	_show_stage(0)

func _build() -> void:
	background_node = TextureRect.new()
	background_node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background_node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background_node.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background_node)

	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.18)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)

	var center := VBoxContainer.new()
	center.set_anchors_preset(Control.PRESET_CENTER)
	center.position = Vector2(-390, -105)
	center.size = Vector2(780, 210)
	center.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_theme_constant_override("separation", 14)
	add_child(center)

	title_label = BahrainUI.title("", 70, Color.WHITE)
	title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center.add_child(title_label)

	accent_line = ColorRect.new()
	accent_line.custom_minimum_size = Vector2(300, 5)
	center.add_child(accent_line)

	subtitle_label = Label.new()
	subtitle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle_label.add_theme_font_size_override("font_size", 24)
	subtitle_label.add_theme_color_override("font_color", Color(0.92, 0.94, 1))
	center.add_child(subtitle_label)

	var skip := Label.new()
	skip.text = "Tap to continue"
	skip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	skip.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	skip.position = Vector2(-200, -62)
	skip.size = Vector2(400, 30)
	skip.add_theme_font_size_override("font_size", 16)
	skip.modulate = Color(1, 1, 1, 0.58)
	add_child(skip)

func _show_stage(index: int) -> void:
	stage = clampi(index, 0, SCREENS.size() - 1)
	var data: Dictionary = SCREENS[stage]
	background_node.texture = load(data.asset)
	title_label.text = data.name
	subtitle_label.text = data.subtitle
	accent_line.color = data.accent
	elapsed = 0.0
	advancing = false
	modulate.a = 0.0
	create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT).tween_property(self, "modulate:a", 1.0, 0.42)

func _process(delta: float) -> void:
	if capture_mode or advancing:
		return
	elapsed += delta
	if elapsed >= 2.35:
		_advance()

func _unhandled_input(event: InputEvent) -> void:
	if capture_mode or elapsed < 0.75:
		return
	if (event is InputEventScreenTouch and event.pressed) or (event is InputEventMouseButton and event.pressed):
		_advance()

func _advance() -> void:
	if advancing:
		return
	advancing = true
	var tween := create_tween()
	tween.tween_property(self, "modulate:a", 0.0, 0.38)
	await tween.finished
	if stage + 1 < SCREENS.size():
		_show_stage(stage + 1)
	else:
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

func force_stage(index: int) -> void:
	_show_stage(index)
	modulate.a = 1.0

func get_stage_name() -> String:
	return str(SCREENS[stage].name)
