extends Control

var modal: PanelContainer

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.MENU
	_build_ui()

func _build_ui() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	BahrainUI.background(self, "res://assets/ui/runtime/main_menu_background.svg")

	var veil := ColorRect.new()
	veil.color = Color(0.015, 0.025, 0.045, 0.30)
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(veil)

	var brand := VBoxContainer.new()
	brand.position = Vector2(70, 72)
	brand.size = Vector2(700, 260)
	brand.add_theme_constant_override("separation", 4)
	add_child(brand)

	brand.add_child(BahrainUI.title("BAHRAIN BRICK", 76, Color(1, 0.83, 0.18)))
	var subtitle := Label.new()
	subtitle.text = "OPEN WORLD SANDBOX"
	subtitle.add_theme_font_size_override("font_size", 25)
	subtitle.add_theme_color_override("font_color", Color(0.82, 0.93, 1))
	brand.add_child(subtitle)

	var studio := Label.new()
	studio.text = "A Zanabal Gaming × Mansoory Games production"
	studio.add_theme_font_size_override("font_size", 17)
	studio.modulate = Color(1, 1, 1, 0.72)
	brand.add_child(studio)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER_RIGHT)
	panel.position = Vector2(-455, -270)
	panel.size = Vector2(395, 540)
	panel.add_theme_stylebox_override("panel", BahrainUI.panel())
	add_child(panel)

	var buttons := VBoxContainer.new()
	buttons.add_theme_constant_override("separation", 13)
	panel.add_child(buttons)
	_add_button(buttons, "Play", Color(0.20, 0.68, 0.31), func(): GameManager.start_singleplayer())
	_add_button(buttons, "Character Select", Color(0.91, 0.55, 0.12), func(): GameManager.start_singleplayer())
	_add_button(buttons, "Settings", Color(0.20, 0.50, 0.82), _show_settings)
	_add_button(buttons, "Credits", Color(0.48, 0.30, 0.76), _show_credits)
	_add_button(buttons, "Exit", Color(0.76, 0.20, 0.18), func(): get_tree().quit())

	var note := Label.new()
	note.text = "Single-player build • Landscape Android QA"
	note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	note.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	note.position = Vector2(-350, -50)
	note.size = Vector2(700, 28)
	note.modulate = Color(1, 1, 1, 0.66)
	add_child(note)

func _add_button(parent: VBoxContainer, text: String, color: Color, callback: Callable) -> void:
	var button := BahrainUI.make_button(text, color, Vector2(340, 65))
	button.pressed.connect(callback)
	parent.add_child(button)

func _show_settings() -> void:
	_close_modal()
	modal = PanelContainer.new()
	modal.name = "SettingsModal"
	modal.set_anchors_preset(Control.PRESET_CENTER)
	modal.position = Vector2(-410, -300)
	modal.size = Vector2(820, 600)
	modal.add_theme_stylebox_override("panel", BahrainUI.panel())
	add_child(modal)
	var settings := preload("res://scripts/settings_panel.gd").new()
	modal.add_child(settings)
	settings.close_requested.connect(_close_modal)

func _show_credits() -> void:
	_close_modal()
	modal = PanelContainer.new()
	modal.name = "CreditsModal"
	modal.set_anchors_preset(Control.PRESET_CENTER)
	modal.position = Vector2(-380, -260)
	modal.size = Vector2(760, 520)
	modal.add_theme_stylebox_override("panel", BahrainUI.panel())
	add_child(modal)
	var box := VBoxContainer.new()
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	box.add_theme_constant_override("separation", 18)
	modal.add_child(box)
	var title := BahrainUI.title("BAHRAIN BRICK", 48)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	for line in ["Zanabal Gaming — Studio", "Mansoory Games — Co-development", "Godot Engine 4.3", "Original Bahrain-inspired modular brick world"]:
		var label := Label.new()
		label.text = line
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 22)
		box.add_child(label)
	var close := BahrainUI.make_button("Back", Color(0.22, 0.48, 0.75), Vector2(280, 58))
	close.pressed.connect(_close_modal)
	box.add_child(close)

func _close_modal() -> void:
	if is_instance_valid(modal):
		modal.queue_free()
	modal = null
