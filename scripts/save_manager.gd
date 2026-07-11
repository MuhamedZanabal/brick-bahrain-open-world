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

func save_game() -> void:
	# Collect current game state
	var game_mgr: Node = get_tree().get_first_node_in_group("game_manager")
	var player: CharacterBody3D = get_tree().get_first_node_in_group("player")

	save_data = {
		"version": 2,
		"timestamp": Time.get_unix_time_from_system(),
		"player": {
			"position": {
				"x": 0.0,
				"y": 1.0,
				"z": 0.0
			},
			"coins": 0,
			"selected_character": 0,
		},
		"unlocked_characters": [0],
		"completed_missions": [],
		"owned_properties": [],
		"owned_vehicles": [],
		"wanted_level": 0,
		"playtime": 0.0,
	}

	if player and player.has_meta("coin_count"):
		save_data["player"]["coins"] = int(player.get_meta("coin_count"))

	if player:
		save_data["player"]["position"] = {
			"x": player.global_position.x,
			"y": player.global_position.y,
			"z": player.global_position.z
		}

	if game_mgr:
		if game_mgr.has_meta("selected_character"):
			save_data["player"]["selected_character"] = int(game_mgr.get_meta("selected_character"))
		if game_mgr.has_meta("unlocked_characters"):
			save_data["unlocked_characters"] = game_mgr.get_meta("unlocked_characters")
		if game_mgr.has_meta("completed_missions"):
			save_data["completed_missions"] = game_mgr.get_meta("completed_missions")
		if game_mgr.has_meta("owned_properties"):
			save_data["owned_properties"] = game_mgr.get_meta("owned_properties")
		if game_mgr.has_meta("owned_vehicles"):
			save_data["owned_vehicles"] = game_mgr.get_meta("owned_vehicles")

	# Write to file
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
	if err != OK:
		push_error("SaveManager: Failed to parse save file: %s" % json.get_error_message())
		save_data = _default_save()
		save_loaded.emit(save_data)
		return false

	save_data = json.data as Dictionary
	print("SaveManager: Game loaded successfully")
	save_loaded.emit(save_data)
	return true

func _default_save() -> Dictionary:
	return {
		"version": 2,
		"timestamp": Time.get_unix_time_from_system(),
		"player": {
			"position": {"x": 0.0, "y": 1.0, "z": 0.0},
			"coins": 0,
			"selected_character": 0,
		},
		"unlocked_characters": [0],
		"completed_missions": [],
		"owned_properties": [],
		"owned_vehicles": [],
		"wanted_level": 0,
		"playtime": 0.0,
	}

func get_coins() -> int:
	if save_data.has("player") and save_data["player"].has("coins"):
		return int(save_data["player"]["coins"])
	return 0

func get_position() -> Vector3:
	if save_data.has("player") and save_data["player"].has("position"):
		var p: Dictionary = save_data["player"]["position"]
		return Vector3(float(p["x"]), float(p["y"]), float(p["z"]))
	return Vector3.ZERO

func get_selected_character() -> int:
	if save_data.has("player") and save_data["player"].has("selected_character"):
		return int(save_data["player"]["selected_character"])
	return 0

func get_completed_missions() -> Array:
	if save_data.has("completed_missions"):
		return save_data["completed_missions"] as Array
	return []

func get_unlocked_characters() -> Array:
	if save_data.has("unlocked_characters"):
		return save_data["unlocked_characters"] as Array
	return [0]

func get_owned_properties() -> Array:
	if save_data.has("owned_properties"):
		return save_data["owned_properties"] as Array
	return []

func get_owned_vehicles() -> Array:
	if save_data.has("owned_vehicles"):
		return save_data["owned_vehicles"] as Array
	return []

func add_coins(amount: int) -> void:
	if not save_data.has("player"):
		save_data["player"] = {}
	var current: int = get_coins()
	save_data["player"]["coins"] = current + amount

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
	# Auto-save on mission complete
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
