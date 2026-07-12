extends VBoxContainer
signal close_requested

func _ready() -> void:
	name="SettingsPanel"; add_theme_constant_override("separation",16); _build()

func _build() -> void:
	var title:=BahrainUI.title("SETTINGS",44); title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER; add_child(title)
	var quality_label:=Label.new(); quality_label.text="Graphics quality"; quality_label.add_theme_font_size_override("font_size",22); add_child(quality_label)
	var quality:=OptionButton.new(); quality.name="QualityOption"; quality.add_item("Low"); quality.add_item("Medium"); quality.add_item("High"); quality.select(clampi(int(GameManager.get_setting("graphics_quality",1)),0,2)); quality.item_selected.connect(func(i): QualityManager.set_profile(int(i))); quality.custom_minimum_size=Vector2(600,54); add_child(quality)
	_add_slider("Music volume","music_volume",float(GameManager.get_setting("music_volume",0.75)))
	_add_slider("Sound effects","sfx_volume",float(GameManager.get_setting("sfx_volume",0.85)))
	var controls:=Label.new(); controls.text="CONTROLS\nLeft joystick: move • Right side drag: camera • Jump: leap\nAct: interact • Exit: leave vehicle • Pause: open this menu"; controls.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; controls.add_theme_font_size_override("font_size",19); controls.custom_minimum_size=Vector2(650,125); add_child(controls)
	var close:=BahrainUI.make_button("Back",Color(0.23,0.48,0.76),Vector2(320,58)); close.pressed.connect(func(): close_requested.emit()); add_child(close)

func _add_slider(label_text:String,key:String,value:float) -> void:
	var row:=HBoxContainer.new(); row.add_theme_constant_override("separation",18); add_child(row)
	var label:=Label.new(); label.text=label_text; label.custom_minimum_size=Vector2(220,50); label.add_theme_font_size_override("font_size",21); row.add_child(label)
	var slider:=HSlider.new(); slider.name=key; slider.min_value=0; slider.max_value=1; slider.step=0.01; slider.value=value; slider.custom_minimum_size=Vector2(400,50); slider.value_changed.connect(func(v): GameManager.set_setting(key,float(v))); row.add_child(slider)
