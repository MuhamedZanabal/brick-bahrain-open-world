extends Node
const OUT := "res://build/visual_evidence"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("_run")

func _save(name: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	image.resize(1280, 720)
	image.save_png(ProjectSettings.globalize_path(OUT + "/screenshots/" + name + ".png"))

func _clear() -> void:
	for child in get_children():
		child.queue_free()
	await get_tree().process_frame

func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT + "/screenshots"))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT + "/startup_frames"))

	var splash := preload("res://scenes/splash_screen.tscn").instantiate()
	add_child(splash)
	await get_tree().process_frame
	splash.force_stage(0)
	await _save("zanabal_gaming")
	for index in range(18):
		await _frame("startup_frames/frame_%04d.png" % index)
	splash.force_stage(1)
	await _save("mansoory_games")
	for index in range(18, 36):
		await _frame("startup_frames/frame_%04d.png" % index)

	await _clear()
	var menu := preload("res://scenes/main_menu.tscn").instantiate()
	add_child(menu)
	await _save("bahrain_brick_main_menu")
	for index in range(36, 54):
		await _frame("startup_frames/frame_%04d.png" % index)

	await _clear()
	var select := preload("res://scenes/character_select.tscn").instantiate()
	add_child(select)
	await _save("character_selection")

	await _clear()
	var loading := preload("res://scenes/loading_screen.tscn").instantiate()
	add_child(loading)
	loading.set_test_progress(18)
	await _save("loading_18_percent")
	loading.set_test_progress(62)
	await _save("loading_62_percent")
	loading.set_test_progress(100)
	await _save("loading_100_percent")

	await _clear()
	var pause := preload("res://scenes/pause_menu.tscn").instantiate()
	add_child(pause)
	await get_tree().process_frame
	pause.show_settings()
	await _save("pause_and_settings")
	pause.resume_game()
	await _clear()

	var background := TextureRect.new()
	background.texture = load("res://assets/ui/runtime/main_menu_background.svg")
	background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var hud := preload("res://scenes/hud.tscn").instantiate()
	add_child(hud)
	await _save("gameplay_hud")

	print("Bahrain Brick presentation visual evidence complete")
	get_tree().quit(0)

func _frame(relative: String) -> void:
	await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	image.resize(1280, 720)
	image.save_png(ProjectSettings.globalize_path(OUT + "/" + relative))
