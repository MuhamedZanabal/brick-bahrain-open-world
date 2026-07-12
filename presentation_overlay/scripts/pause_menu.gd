extends Control
var settings_panel:Control

func _ready() -> void:
	process_mode=Node.PROCESS_MODE_ALWAYS; set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); get_tree().paused=true; _build()

func _exit_tree() -> void:
	if get_tree(): get_tree().paused=false

func _build() -> void:
	BahrainUI.background(self,"res://assets/ui/runtime/pause_background.svg",Color(0.55,0.62,0.72,1))
	var veil:=ColorRect.new(); veil.color=Color(0,0,0,0.38); veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); veil.mouse_filter=Control.MOUSE_FILTER_IGNORE; add_child(veil)
	var title:=BahrainUI.title("PAUSED",64); title.position=Vector2(90,80); title.size=Vector2(620,80); add_child(title)
	var menu:=PanelContainer.new(); menu.position=Vector2(90,185); menu.size=Vector2(470,650); menu.add_theme_stylebox_override("panel",BahrainUI.panel()); add_child(menu)
	var buttons:=VBoxContainer.new(); buttons.add_theme_constant_override("separation",15); menu.add_child(buttons)
	_add(buttons,"Resume",Color(0.20,0.68,0.31),resume_game)
	_add(buttons,"Settings",Color(0.20,0.50,0.82),show_settings)
	_add(buttons,"Controls",Color(0.48,0.30,0.76),show_settings)
	_add(buttons,"Audio",Color(0.91,0.55,0.12),show_settings)
	_add(buttons,"Main Menu",Color(0.76,0.20,0.18),_main_menu)

func _add(parent:VBoxContainer,text:String,color:Color,callback:Callable) -> void:
	var b:=BahrainUI.make_button(text,color,Vector2(390,70)); b.pressed.connect(callback); parent.add_child(b)

func show_settings() -> void:
	if is_instance_valid(settings_panel): return
	var panel:=PanelContainer.new(); panel.name="PauseSettings"; panel.position=Vector2(650,110); panel.size=Vector2(1080,760); panel.add_theme_stylebox_override("panel",BahrainUI.panel()); add_child(panel); settings_panel=panel
	var settings:=preload("res://scripts/settings_panel.gd").new(); panel.add_child(settings); settings.close_requested.connect(_close_settings)

func resume_game() -> void:
	get_tree().paused=false; queue_free()

func _main_menu() -> void:
	get_tree().paused=false; GameManager.back_to_menu()

func _unhandled_input(event:InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"): resume_game(); get_viewport().set_input_as_handled()

func _close_settings() -> void:
	if is_instance_valid(settings_panel):
		settings_panel.queue_free()
	settings_panel = null
