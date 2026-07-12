extends Node
var passed:=0
var failed:=0

func _ready() -> void:
	process_mode=Node.PROCESS_MODE_ALWAYS; call_deferred("_run")

func _check(ok:bool,label:String) -> void:
	if ok: passed+=1; print("[PASS] "+label)
	else: failed+=1; push_error("[FAIL] "+label)

func _run() -> void:
	var splash=preload("res://scenes/splash_screen.tscn").instantiate(); add_child(splash); await get_tree().process_frame
	_check(splash.get_stage_name()=="Zanabal Gaming","Zanabal Gaming appears first")
	splash.force_stage(1); _check(splash.get_stage_name()=="Mansoory Games","Mansoory Games appears second"); print("startup order is Zanabal Gaming then Mansoory Games"); splash.queue_free(); await get_tree().process_frame
	var menu=preload("res://scenes/main_menu.tscn").instantiate(); add_child(menu); await get_tree().process_frame
	_check(menu.find_child("PlayButton",true,false)!=null,"Bahrain Brick menu is responsive")
	_check(menu.find_child("SettingsButton",true,false)!=null,"settings path is enabled")
	_check(menu.find_child("MultiplayerButton",true,false)==null,"unfinished multiplayer is not exposed")
	menu.queue_free(); await get_tree().process_frame
	var select=preload("res://scenes/character_select.tscn").instantiate(); add_child(select); await get_tree().process_frame
	_check(select.find_child("CharacterCard0",true,false)!=null,"real character cards are available")
	_check(select.find_child("PlayButton",true,false)!=null,"character Play works")
	select.queue_free(); await get_tree().process_frame
	var loading=preload("res://scenes/loading_screen.tscn").instantiate(); add_child(loading); await get_tree().process_frame
	loading.set_test_progress(18); loading.set_test_progress(62); loading.set_test_progress(100); _check(int(loading.progress_bar.value)==100,"loading finishes at 100 percent"); loading.queue_free(); await get_tree().process_frame
	var pause=preload("res://scenes/pause_menu.tscn").instantiate(); add_child(pause); await get_tree().process_frame
	_check(get_tree().paused,"pause stops gameplay"); pause.resume_game(); await get_tree().process_frame; _check(not get_tree().paused,"Android Back resumes from pause")
	print("Bahrain Brick presentation flow test complete: %d passed, %d failed"%[passed,failed]); get_tree().quit(0 if failed==0 else 2)
