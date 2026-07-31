extends Node

# Save/load system using user://savegame.json
var save_path: String = "user://savegame.json"
var save_data: Dictionary = {}
var autosave_timer: float = 0.0
var autosave_interval: float = 60.0  # Auto-save every 60 seconds

signal save_loaded(data: Dictionary)
signal save_completed()

func _ready() -> void:
	add_to_group("save_manager")
	load_game()

func _process(delta: float) -> void:
	autosave_timer += delta
	if autosave_timer >= autosave_interval:
		autosave_timer = 0.0
		save_game()

func _ensure_schema() -> void:
	var defaults := _default_save()
	if save_data.is_empty():
		save_data = defaults
		return
	for key in defaults:
		if not save_data.has(key):
			save_data[key] = defaults[key]
	if not save_data["player"] is Dictionary:
		save_data["player"] = defaults["player"].duplicate(true)
	for key in defaults["player"]:
		if not save_data["player"].has(key):
			save_data["player"][key] = defaults["player"][key]
	if not save_data["settings"] is Dictionary:
		save_data["settings"] = defaults["settings"].duplicate(true)
	for key in defaults["settings"]:
		if not save_data["settings"].has(key):
			save_data["settings"][key] = defaults["settings"][key]

func save_game() -> void:
	_ensure_schema()
	save_data["version"] = 3
	save_data["timestamp"] = Time.get_unix_time_from_system()

	var game_mgr: Node = get_tree().get_first_node_in_group("game_manager")
	var player: CharacterBody3D = get_tree().get_first_node_in_group("player")

	if player and player.has_meta("coin_count"):
		save_data["player"]["coins"] = int(player.get_meta("coin_count"))

	if player:
		save_data["player"]["position"] = {
			"x": player.global_position.x,
			"y": player.global_position.y,
			"z": player.global_position.z
		}

	if game_mgr:
		var selected: Variant = game_mgr.get("selected_character_index")
		if selected != null:
			save_data["player"]["selected_character"] = int(selected)
		if game_mgr.has_meta("unlocked_characters"):
			save_data["unlocked_characters"] = game_mgr.get_meta("unlocked_characters")
		if game_mgr.has_meta("completed_missions"):
			save_data["completed_missions"] = game_mgr.get_meta("completed_missions")
		if game_mgr.has_meta("owned_properties"):
			save_data["owned_properties"] = game_mgr.get_meta("owned_properties")
		if game_mgr.has_meta("owned_vehicles"):
			save_data["owned_vehicles"] = game_mgr.get_meta("owned_vehicles")

	var file: FileAccess = FileAccess.open(save_path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(save_data, "\t"))
		file.close()
		print("SaveManager: Game saved to %s" % save_path)
		save_completed.emit()
	else:
		push_error("SaveManager: Failed to save game!")

func load_game() -> bool:
	if not FileAccess.file_exists(save_path):
		print("SaveManager: No save file found, starting fresh")
		save_data = _default_save()
		save_loaded.emit(save_data)
		return false

	var file: FileAccess = FileAccess.open(save_path, FileAccess.READ)
	if not file:
		push_error("SaveManager: Failed to open save file")
		save_data = _default_save()
		save_loaded.emit(save_data)
		return false

	var content: String = file.get_as_text()
	file.close()

	var json: JSON = JSON.new()
	var err: int = json.parse(content)
	if err != OK or not json.data is Dictionary:
		push_error("SaveManager: Failed to parse save file: %s" % json.get_error_message())
		save_data = _default_save()
		save_loaded.emit(save_data)
		return false

	save_data = json.data as Dictionary
	_ensure_schema()
	print("SaveManager: Game loaded successfully")
	save_loaded.emit(save_data)
	return true

func _default_save() -> Dictionary:
	return {
		"version": 3,
		"timestamp": Time.get_unix_time_from_system(),
		"player": {
			"position": {"x": 0.0, "y": 1.0, "z": 0.0},
			"coins": 0,
			"selected_character": 0,
		},
		"settings": {
			"quality": "medium",
			"brightness": 0.8,
			"field_of_view": 75.0,
			"camera_shake": true,
			"auto_jump": true,
			"tutorial_hints": true,
		},
		"unlocked_characters": [0],
		"completed_missions": [],
		"owned_properties": [],
		"owned_vehicles": [],
		"wanted_level": 0,
		"playtime": 0.0,
	}

func get_coins() -> int:
	_ensure_schema()
	return int(save_data["player"]["coins"])

func get_position() -> Vector3:
	_ensure_schema()
	var p: Dictionary = save_data["player"]["position"]
	return Vector3(float(p.get("x", 0.0)), float(p.get("y", 1.0)), float(p.get("z", 0.0)))

func get_selected_character() -> int:
	_ensure_schema()
	return int(save_data["player"]["selected_character"])

func set_selected_character(index: int, flush: bool = true) -> void:
	_ensure_schema()
	save_data["player"]["selected_character"] = max(index, 0)
	if flush:
		save_game()

func get_settings() -> Dictionary:
	_ensure_schema()
	return save_data["settings"].duplicate(true)

func set_setting(key: String, value: Variant, flush: bool = true) -> void:
	_ensure_schema()
	if not save_data["settings"].has(key):
		push_warning("SaveManager: registering new setting key %s" % key)
	save_data["settings"][key] = value
	if flush:
		save_game()

func get_completed_missions() -> Array:
	_ensure_schema()
	return save_data["completed_missions"] as Array

func get_unlocked_characters() -> Array:
	_ensure_schema()
	return save_data["unlocked_characters"] as Array

func get_owned_properties() -> Array:
	_ensure_schema()
	return save_data["owned_properties"] as Array

func get_owned_vehicles() -> Array:
	_ensure_schema()
	return save_data["owned_vehicles"] as Array

func add_coins(amount: int) -> void:
	_ensure_schema()
	save_data["player"]["coins"] = get_coins() + amount

func spend_coins(amount: int) -> bool:
	var current: int = get_coins()
	if current >= amount:
		save_data["player"]["coins"] = current - amount
		return true
	return false

func complete_mission(mission_id: String) -> void:
	var completed: Array = get_completed_missions()
	if not completed.has(mission_id):
		completed.append(mission_id)
		save_data["completed_missions"] = completed
	save_game()

func unlock_character(char_id: int) -> void:
	var unlocked: Array = get_unlocked_characters()
	if not unlocked.has(char_id):
		unlocked.append(char_id)
		save_data["unlocked_characters"] = unlocked

func add_property(prop_id: String) -> void:
	var props: Array = get_owned_properties()
	if not props.has(prop_id):
		props.append(prop_id)
		save_data["owned_properties"] = props

func add_vehicle(veh_id: String) -> void:
	var vehs: Array = get_owned_vehicles()
	if not vehs.has(veh_id):
		vehs.append(veh_id)
		save_data["owned_vehicles"] = vehs

func has_save() -> bool:
	return FileAccess.file_exists(save_path)
