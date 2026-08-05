extends Control
## Branded studio splash shown before the staged Bahrain Brick loading screen.

const NEXT_SCENE := "res://scenes/loading_screen.tscn"
const MIN_DISPLAY_SECONDS := 2.2
const AUTO_ADVANCE_SECONDS := 3.4

var _elapsed := 0.0
var _transitioned := false
var _branding: Control

func _ready() -> void:
	_build_ui()
	_animate_branding()

func _build_ui() -> void:
	var background := TextureRect.new()
	background.name = "Background"
	background.texture = load("res://assets/splash_screen.png")
	background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background.set_anchors_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)
	move_child(background, 0)

	var shade := ColorRect.new()
	shade.name = "CinematicShade"
	shade.color = Color(0.008, 0.018, 0.04, 0.58)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	move_child(shade, 1)

	var vignette := ColorRect.new()
	vignette.name = "LowerShade"
	vignette.color = Color(0.005, 0.008, 0.015, 0.34)
	vignette.anchor_left = 0.0
	vignette.anchor_top = 0.48
	vignette.anchor_right = 1.0
	vignette.anchor_bottom = 1.0
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(vignette)

	var safe_area := get_node_or_null("SafeArea") as MarginContainer
	if safe_area == null:
		safe_area = SafeAreaRoot.new()
		safe_area.name = "SafeArea"
		safe_area.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(safe_area)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	safe_area.add_child(center)

	_branding = VBoxContainer.new()
	_branding.name = "Branding"
	_branding.custom_minimum_size = Vector2(700, 420)
	_branding.alignment = BoxContainer.ALIGNMENT_CENTER
	_branding.add_theme_constant_override("separation", 18)
	_branding.modulate.a = 0.0
	_branding.scale = Vector2(0.9, 0.9)
	center.add_child(_branding)

	var crest := TextureRect.new()
	crest.name = "StudioCrest"
	crest.texture = load("res://assets/app_icon.png")
	crest.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	crest.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	crest.custom_minimum_size = Vector2(170, 170)
	crest.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_branding.add_child(crest)

	var studio := Label.new()
	studio.text = "ZANABAL GAMING"
	studio.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	studio.add_theme_font_size_override("font_size", 58)
	studio.add_theme_color_override("font_color", BahrainTheme.GOLD_LIGHT)
	studio.add_theme_color_override("font_outline_color", Color(0.01, 0.01, 0.015, 0.95))
	studio.add_theme_constant_override("outline_size", 9)
	_branding.add_child(studio)

	var divider := HSeparator.new()
	divider.custom_minimum_size = Vector2(520, 2)
	_branding.add_child(divider)

	var motto := Label.new()
	motto.text = "BUILDING LEGENDS, BRICK BY BRICK"
	motto.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	motto.add_theme_font_size_override("font_size", 22)
	motto.add_theme_color_override("font_color", BahrainTheme.TEXT)
	motto.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	motto.add_theme_constant_override("outline_size", 5)
	_branding.add_child(motto)

	var hint := Label.new()
	hint.name = "SkipHint"
	hint.text = "TAP TO CONTINUE"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 15)
	hint.add_theme_color_override("font_color", Color(1, 1, 1, 0.62))
	hint.modulate.a = 0.0
	hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hint.position = Vector2(-120, -56)
	hint.size = Vector2(240, 30)
	add_child(hint)

func _animate_branding() -> void:
	if _branding == null:
		return
	var tween := create_tween()
	tween.set_parallel(true)
	tween.set_trans(Tween.TRANS_QUAD)
	tween.set_ease(Tween.EASE_OUT)
	tween.tween_property(_branding, "modulate:a", 1.0, 0.75)
	tween.tween_property(_branding, "scale", Vector2.ONE, 0.9).set_trans(Tween.TRANS_BACK)
	var hint := get_node_or_null("SkipHint") as Label
	if hint:
		var hint_tween := create_tween()
		hint_tween.tween_interval(MIN_DISPLAY_SECONDS)
		hint_tween.tween_property(hint, "modulate:a", 1.0, 0.35)

func _process(delta: float) -> void:
	if _transitioned:
		return
	_elapsed += delta
	if _elapsed >= AUTO_ADVANCE_SECONDS:
		_go_next()

func _input(event: InputEvent) -> void:
	if _transitioned or _elapsed < MIN_DISPLAY_SECONDS:
		return
	if event is InputEventScreenTouch and event.pressed:
		_go_next()
	elif event is InputEventMouseButton and event.pressed:
		_go_next()
	elif event is InputEventKey and event.pressed:
		_go_next()

func _go_next() -> void:
	if _transitioned:
		return
	_transitioned = true
	GameManager.transition_to(NEXT_SCENE)
