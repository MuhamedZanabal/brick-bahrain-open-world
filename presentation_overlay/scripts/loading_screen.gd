extends Control
const TARGET="res://scenes/world.tscn"
const TIPS=["Use the left joystick to move.","Drag the right side to rotate the camera.","Tap Jump to clear low obstacles.","Approach glowing markers to start missions.","Pause can resume play or return to the menu."]
var progress_bar:ProgressBar
var percent_label:Label
var status_label:Label
var tip_label:Label
var displayed:=0.0
var elapsed:=0.0
var requested:=false
var evidence_mode:=false

func _ready() -> void:
	GameManager.current_state=GameManager.GameState.LOADING
	evidence_mode="--presentation-test" in OS.get_cmdline_user_args()
	_build_ui()
	if not evidence_mode:
		var err:=ResourceLoader.load_threaded_request(TARGET,"",true)
		requested=err==OK
		if not requested: _show_error("Unable to start world loading.")

func _build_ui() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); BahrainUI.background(self,"res://assets/ui/runtime/loading_background.svg")
	var shade:=ColorRect.new(); shade.color=Color(0,0,0,0.25); shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); shade.mouse_filter=Control.MOUSE_FILTER_IGNORE; add_child(shade)
	var title:=BahrainUI.title("BAHRAIN BRICK",64); title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER; title.position=Vector2(0,95); title.size=Vector2(1920,85); add_child(title)
	var box:=PanelContainer.new(); box.set_anchors_preset(Control.PRESET_CENTER_BOTTOM); box.position=Vector2(-620,-280); box.size=Vector2(1240,220); box.add_theme_stylebox_override("panel",BahrainUI.panel()); add_child(box)
	var stack:=VBoxContainer.new(); stack.add_theme_constant_override("separation",14); box.add_child(stack)
	status_label=Label.new(); status_label.text="Preparing Bahrain Brick…"; status_label.add_theme_font_size_override("font_size",24); stack.add_child(status_label)
	progress_bar=ProgressBar.new(); progress_bar.max_value=100; progress_bar.show_percentage=false; progress_bar.custom_minimum_size=Vector2(1100,34); stack.add_child(progress_bar)
	percent_label=Label.new(); percent_label.text="0%"; percent_label.horizontal_alignment=HORIZONTAL_ALIGNMENT_RIGHT; percent_label.add_theme_font_size_override("font_size",22); stack.add_child(percent_label)
	tip_label=Label.new(); tip_label.text="Tip: "+TIPS[0]; tip_label.add_theme_font_size_override("font_size",20); tip_label.add_theme_color_override("font_color",Color(1,0.82,0.2)); stack.add_child(tip_label)

func _process(delta:float) -> void:
	if evidence_mode or not requested: return
	elapsed+=delta; tip_label.text="Tip: "+TIPS[int(elapsed/4.0)%TIPS.size()]
	var values:Array=[]; var state:=ResourceLoader.load_threaded_get_status(TARGET,values)
	var target:=displayed
	if values.size()>0: target=maxf(displayed,float(values[0])*100.0)
	displayed=move_toward(displayed,target,delta*40.0); _set_progress(displayed)
	if state==ResourceLoader.THREAD_LOAD_LOADED:
		_set_progress(100.0); await get_tree().process_frame
		var packed:=ResourceLoader.load_threaded_get(TARGET) as PackedScene
		if packed: get_tree().change_scene_to_packed(packed)
		else: _show_error("World loading completed without a valid scene.")
	elif state==ResourceLoader.THREAD_LOAD_FAILED or elapsed>75.0: _show_error("World loading failed. Return to the menu and try again.")

func _set_progress(value:float) -> void:
	displayed=maxf(displayed,clampf(value,0,100)); progress_bar.value=displayed; percent_label.text="%d%%"%int(displayed)
	status_label.text="Loading world…" if displayed<100 else "Ready"

func set_test_progress(value:float) -> void:
	evidence_mode=true; _set_progress(value)

func _show_error(message:String) -> void:
	requested=false; status_label.text=message
	var back:=BahrainUI.make_button("Main Menu",Color(0.72,0.22,0.18),Vector2(260,55)); back.pressed.connect(func(): GameManager.back_to_menu()); get_child(get_child_count()-1).get_child(0).add_child(back)
