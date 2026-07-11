extends Control
## SplashScreen - Zanabal Gaming splash/boot screen shown before the main menu

var progress_bar_fill: ColorRect
var progress_pct: float = 0.0
var status_label: Label
var loading_messages: Array[String] = [
	"PREPARING GROVE STREET",
	"POLISHING BRICKS",
	"LOADING MANAMA SKYLINE",
	"FUELING VEHICLES",
	"SPAWNING NPCS",
	"TUNING RADIO STATIONS",
	"ALMOST READY"
]
var message_idx: int = 0
var min_display_time: float = 3.0
var elapsed: float = 0.0
var ready_to_advance: bool = false

func _ready() -> void:
	_build_ui()
	set_process(true)

func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)

	# Background image (the splash artwork)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/splash_screen.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	# Dark overlay for readability at the bottom
	var overlay := ColorRect.new()
	overlay.color = Color(0, 0, 0, 0.35)
	overlay.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	overlay.position.y = -140
	overlay.size = Vector2(get_viewport().get_visible_rect().size.x, 140)
	add_child(overlay)

	# Progress bar background
	var bar_bg := ColorRect.new()
	bar_bg.color = Color(0.1, 0.1, 0.1, 0.8)
	bar_bg.position = Vector2(40, get_viewport().get_visible_rect().size.y - 90)
	bar_bg.size = Vector2(get_viewport().get_visible_rect().size.x - 80, 24)
	add_child(bar_bg)

	# Progress bar fill
	progress_bar_fill = ColorRect.new()
	progress_bar_fill.color = Color(1.0, 0.75, 0.1)
	progress_bar_fill.position = bar_bg.position + Vector2(2, 2)
	progress_bar_fill.size = Vector2(0, 20)
	add_child(progress_bar_fill)

	# Status label
	status_label = Label.new()
	status_label.text = "LOADING... [0%%] | %s | POWERED BY BRICKS" % loading_messages[0]
	status_label.add_theme_font_size_override("font_size", 16)
	status_label.add_theme_color_override("font_color", Color(1, 1, 1))
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.position = Vector2(0, get_viewport().get_visible_rect().size.y - 55)
	status_label.size = Vector2(get_viewport().get_visible_rect().size.x, 30)
	add_child(status_label)

	# Studio credit
	var credit := Label.new()
	credit.text = "ZANABAL GAMING — LEGENDS ARE BRICK"
	credit.add_theme_font_size_override("font_size", 13)
	credit.add_theme_color_override("font_color", Color(0.85, 0.75, 0.4))
	credit.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	credit.position = Vector2(0, get_viewport().get_visible_rect().size.y - 25)
	credit.size = Vector2(get_viewport().get_visible_rect().size.x, 20)
	add_child(credit)

func _process(delta: float) -> void:
	elapsed += delta

	# Animate progress bar over min_display_time seconds
	progress_pct = clamp(elapsed / min_display_time, 0.0, 1.0)
	var bar_width: float = get_viewport().get_visible_rect().size.x - 84
	progress_bar_fill.size.x = bar_width * progress_pct

	# Cycle loading messages
	var new_idx: int = int(progress_pct * (loading_messages.size() - 1))
	if new_idx != message_idx:
		message_idx = new_idx

	status_label.text = "LOADING... [%d%%] | %s | POWERED BY BRICKS" % [int(progress_pct * 100), loading_messages[message_idx]]

	if elapsed >= min_display_time and not ready_to_advance:
		ready_to_advance = true
		_go_to_main_menu()

func _go_to_main_menu() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")

func _input(event: InputEvent) -> void:
	# Allow tapping/clicking to skip once minimum time has passed
	if ready_to_advance:
		return
	if event is InputEventScreenTouch and event.pressed:
		elapsed = min_display_time
	elif event is InputEventMouseButton and event.pressed:
		elapsed = min_display_time
