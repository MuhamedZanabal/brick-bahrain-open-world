extends Control

var selected_index := 0
var cards: Array[Button] = []
var detail_name: Label
var detail_text: Label

func _ready() -> void:
	GameManager.current_state = GameManager.GameState.CHARACTER_SELECT
	selected_index = clampi(GameManager.selected_character_index, 0, GameManager.characters.size() - 1)
	_build_ui()
	_refresh_selection()

func _build_ui() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	BahrainUI.background(self, "res://assets/ui/runtime/character_select_background.svg", Color(0.72, 0.78, 0.86, 1))
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.28)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)

	var title := BahrainUI.title("CHOOSE YOUR CHARACTER", 52)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 35)
	title.size = Vector2(1920, 75)
	add_child(title)

	var grid := GridContainer.new()
	grid.columns = 3
	grid.position = Vector2(95, 145)
	grid.size = Vector2(1120, 690)
	grid.add_theme_constant_override("h_separation", 18)
	grid.add_theme_constant_override("v_separation", 18)
	add_child(grid)

	for index in GameManager.characters.size():
		var data: Dictionary = GameManager.characters[index]
		var card := BahrainUI.make_button(str(data.name), Color(0.12, 0.36, 0.56), Vector2(350, 190))
		card.name = "CharacterCard%d" % index
		card.add_theme_font_size_override("font_size", 24)
		card.pressed.connect(func(): _select(index))
		grid.add_child(card)
		cards.append(card)

	var info := PanelContainer.new()
	info.position = Vector2(1280, 145)
	info.size = Vector2(540, 600)
	info.add_theme_stylebox_override("panel", BahrainUI.panel())
	add_child(info)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	info.add_child(box)

	detail_name = BahrainUI.title("", 42)
	detail_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(detail_name)
	detail_text = Label.new()
	detail_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail_text.add_theme_font_size_override("font_size", 21)
	detail_text.custom_minimum_size = Vector2(460, 230)
	box.add_child(detail_text)

	var play := BahrainUI.make_button("Play", Color(0.20, 0.68, 0.31), Vector2(450, 70))
	play.pressed.connect(_play)
	box.add_child(play)
	var back := BahrainUI.make_button("Back", Color(0.25, 0.42, 0.62), Vector2(450, 62))
	back.pressed.connect(func(): GameManager.back_to_menu())
	box.add_child(back)

func _select(index: int) -> void:
	selected_index = clampi(index, 0, GameManager.characters.size() - 1)
	GameManager.set_selected_character(selected_index)
	_refresh_selection()

func _refresh_selection() -> void:
	var data: Dictionary = GameManager.get_character(selected_index)
	detail_name.text = str(data.name)
	detail_text.text = "Playable character\n\nMovement speed: %.2fx\nJump strength: %.2fx\n\nSelected character will be used when the world loads." % [float(data.speed_mult), float(data.jump_mult)]
	for index in cards.size():
		cards[index].modulate = Color(1, 0.85, 0.38, 1) if index == selected_index else Color.WHITE

func _play() -> void:
	GameManager.set_selected_character(selected_index)
	SaveManager.request_autosave("character selected", 0.0)
	GameManager.current_state = GameManager.GameState.LOADING
	get_tree().change_scene_to_file("res://scenes/loading_screen.tscn")
