extends Node
## GameManager - Autoload singleton
## Manages global game state, character selection, multiplayer mode, and scene transitions

signal player_count_changed(count: int)
signal mission_completed(mission_id: String)
signal coins_changed(amount: int)

enum GameState { MENU, CHARACTER_SELECT, LOADING, IN_WORLD, PAUSED }
enum GameMode { SINGLE_PLAYER, MULTIPLAYER_HOST, MULTIPLAYER_CLIENT }

const MAIN_MENU_SCENE := "res://scenes/main_menu.tscn"
const CHARACTER_SELECT_SCENE := "res://scenes/character_select.tscn"
const LOADING_SCENE := "res://scenes/loading_screen.tscn"
const WORLD_SCENE := "res://scenes/world.tscn"
const APPROVED_CHARACTER_INDICES := [3, 5, 4]

var current_state: GameState = GameState.MENU
var current_mode: GameMode = GameMode.SINGLE_PLAYER
var selected_character_index: int = 0
var player_name: String = "Player1"
var coins: int = 0
var completed_missions: Array[String] = []
var connected_players: int = 1

## Transition guard — prevents multiple scene changes from rapid touch events
var _transitioning: bool = false

func _ready() -> void:
	add_to_group("game_manager")

# Character roster data
var characters: Array[Dictionary] = [
	{
		"model_path": "res://assets/characters_kit/Casual2_Male.gltf",
		"name": "Speed Racer",
		"description": "Former F1 pit crew member. Faster driving, nitro boost.",
		"body_color": Color(0.85, 0.1, 0.1),
		"head_color": Color(1.0, 0.8, 0.6),
		"hair_color": Color(0.1, 0.1, 0.1),
		"ability": "nitro",
		"speed_mult": 1.3,
		"jump_mult": 1.0,
		"icon": "R"
	},
	{
		"model_path": "res://assets/characters_kit/Kimono_Male.gltf",
		"name": "Souk Merchant",
		"description": "Bahraini trader. Better coin rewards, trade skills.",
		"body_color": Color(0.9, 0.7, 0.2),
		"head_color": Color(0.75, 0.55, 0.35),
		"hair_color": Color(0.15, 0.1, 0.05),
		"ability": "trade",
		"speed_mult": 1.0,
		"jump_mult": 1.0,
		"icon": "S"
	},
	{
		"model_path": "res://assets/characters_kit/Cowboy_Male.gltf",
		"name": "Fort Explorer",
		"description": "Archaeologist. Higher jump, faster sprint, exploration bonus.",
		"body_color": Color(0.2, 0.5, 0.8),
		"head_color": Color(0.8, 0.6, 0.4),
		"hair_color": Color(0.3, 0.2, 0.1),
		"ability": "explore",
		"speed_mult": 1.1,
		"jump_mult": 1.4,
		"icon": "E"
	},
	{
		"model_path": "res://assets/characters_kit/Worker_Male.gltf",
		"name": "Pearl Diver",
		"description": "Traditional diver. Swim speed boost, underwater breathing.",
		"body_color": Color(0.1, 0.4, 0.6),
		"head_color": Color(0.7, 0.5, 0.3),
		"hair_color": Color(0.05, 0.05, 0.03),
		"ability": "dive",
		"speed_mult": 1.0,
		"jump_mult": 1.1,
		"icon": "P"
	},
	{
		"model_path": "res://assets/characters_kit/Suit_Male.gltf",
		"name": "Sky Pilot",
		"description": "Bahrain International pilot. Vehicle handling master, air control.",
		"body_color": Color(0.3, 0.3, 0.35),
		"head_color": Color(0.9, 0.7, 0.5),
		"hair_color": Color(0.2, 0.15, 0.1),
		"ability": "pilot",
		"speed_mult": 1.15,
		"jump_mult": 1.2,
		"icon": "A"
	},
	{
		"model_path": "res://assets/characters_kit/Casual3_Male.gltf",
		"name": "Street Racer",
		"description": "Underground racer. Drift king, stunt bonus, night vision.",
		"body_color": Color(0.4, 0.1, 0.5),
		"head_color": Color(0.65, 0.45, 0.3),
		"hair_color": Color(0.05, 0.05, 0.05),
		"ability": "drift",
		"speed_mult": 1.25,
		"jump_mult": 1.05,
		"icon": "D"
	}
]

func get_character(index: int) -> Dictionary:
	if index < 0 or index >= characters.size():
		return characters[0]
	return characters[index]

func get_selected_character() -> Dictionary:
	return get_character(selected_character_index)

func get_approved_characters() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for index in APPROVED_CHARACTER_INDICES:
		result.append(characters[index])
	return result

func add_coins(amount: int) -> void:
	coins += amount
	coins_changed.emit(coins)

func spend_coins(amount: int) -> bool:
	if coins >= amount:
		coins -= amount
		coins_changed.emit(coins)
		return true
	return false

func complete_mission(mission_id: String) -> void:
	if not mission_id in completed_missions:
		completed_missions.append(mission_id)
		mission_completed.emit(mission_id)

func set_player_count(count: int) -> void:
	connected_players = count
	player_count_changed.emit(count)

## Transition with guard — ignores re-entry while a transition is in progress
func transition_to(scene_path: String) -> void:
	if _transitioning:
		push_warning("GameManager: transition already in progress, ignoring duplicate request")
		return
	_transitioning = true
	current_state = GameState.LOADING
	call_deferred("_do_transition", scene_path)

func _do_transition(scene_path: String) -> void:
	var err := get_tree().change_scene_to_file(scene_path)
	if err != OK:
		push_error("GameManager: failed to change scene to %s (error %d)" % [scene_path, err])
	_transitioning = false

func show_main_menu() -> void:
	transition_to(MAIN_MENU_SCENE)

func show_character_select() -> void:
	transition_to(CHARACTER_SELECT_SCENE)

func show_loading_screen() -> void:
	transition_to(LOADING_SCENE)

func start_singleplayer() -> void:
	current_mode = GameMode.SINGLE_PLAYER
	show_character_select()

func start_multiplayer_host() -> void:
	current_mode = GameMode.MULTIPLAYER_HOST
	show_character_select()

func start_multiplayer_client() -> void:
	current_mode = GameMode.MULTIPLAYER_CLIENT
	show_character_select()

func enter_world() -> void:
	transition_to(WORLD_SCENE)

func back_to_menu() -> void:
	show_main_menu()
