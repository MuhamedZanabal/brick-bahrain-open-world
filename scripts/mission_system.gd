extends Node
## MissionSystem - Handles all mission definitions, tracking, and rewards
## Mission types: Race, Collection, Exploration, Time Trial, Stunt

signal mission_started(mission: Dictionary)
signal mission_completed_signal(mission: Dictionary)
signal mission_failed(mission: Dictionary)
signal objective_updated(text: String)

var world: Node3D = null
var active_mission: Dictionary = {}
var mission_timer: float = 0.0
var mission_active: bool = false
var collected_items: int = 0
var target_items: int = 0
var checkpoint_index: int = 0
var race_checkpoints: Array[Vector3] = []

var available_missions: Array[Dictionary] = [
	{
		"id": "race_f1",
		"name": "Grand Prix Circuit",
		"description": "Complete a lap around the Bahrain International Circuit",
		"type": "race",
		"reward_coins": 500,
		"location": Vector3(-50, 0, 130),
		"checkpoints": [
			Vector3(-50, 1, 100), Vector3(-50, 1, 160), Vector3(-30, 1, 180),
			Vector3(10, 1, 180), Vector3(30, 1, 160), Vector3(30, 1, 100),
			Vector3(10, 1, 80), Vector3(-30, 1, 80), Vector3(-50, 1, 100)
		],
		"time_limit": 60.0
	},
	{
		"id": "collect_souk",
		"name": "Souk Treasure Hunt",
		"description": "Find 10 hidden gems in the Manama Souk district",
		"type": "collection",
		"reward_coins": 300,
		"location": Vector3(100, 0, -60),
		"target_count": 10,
		"collect_radius": 30.0,
		"time_limit": 120.0
	},
	{
		"id": "explore_fort",
		"name": "Fort Expedition",
		"description": "Reach the top of Bahrain Fort and explore all towers",
		"type": "exploration",
		"reward_coins": 400,
		"location": Vector3(-60, 0, -110),
		"targets": [
			Vector3(-75, 0, -95), Vector3(-45, 0, -95), 
			Vector3(-75, 0, -125), Vector3(-45, 0, -125),
			Vector3(-60, 5, -110)
		],
		"time_limit": 90.0
	},
	{
		"id": "race_causeway",
		"name": "Causeway Sprint",
		"description": "Race across the King Fahd Causeway as fast as possible",
		"type": "time_trial",
		"reward_coins": 350,
		"location": Vector3(-120, 0, -60),
		"checkpoints": [
			Vector3(-120, 1, -110), Vector3(-115, 1, -90), 
			Vector3(-110, 1, -70), Vector3(-105, 1, -50),
			Vector3(-100, 1, -30)
		],
		"time_limit": 30.0
	},
	{
		"id": "explore_skyline",
		"name": "Skyline Explorer",
		"description": "Visit all major buildings in the Manama skyline",
		"type": "exploration",
		"reward_coins": 250,
		"location": Vector3(120, 0, -100),
		"targets": [
			Vector3(115, 0, -90), Vector3(135, 0, -105),
			Vector3(105, 0, -80), Vector3(110, 0, -70)
		],
		"time_limit": 120.0
	},
	{
		"id": "collect_tree",
		"name": "Desert Run",
		"description": "Reach the Tree of Life and collect 5 desert gems",
		"type": "collection",
		"reward_coins": 200,
		"location": Vector3(-80, 0, 100),
		"target_count": 5,
		"collect_radius": 40.0,
		"time_limit": 60.0
	},
	{
		"id": "race_marina",
		"name": "Marina Drift",
		"description": "Sprint from the Marina to Amwaj Islands",
		"type": "time_trial",
		"reward_coins": 300,
		"location": Vector3(140, 0, -50),
		"checkpoints": [
			Vector3(140, 1, -50), Vector3(150, 1, -80),
			Vector3(155, 1, -110), Vector3(160, 1, -130)
		],
		"time_limit": 25.0
	}
]

func initialize(world_node: Node3D) -> void:
	add_to_group("mission_system")
	world = world_node

func get_available_missions() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for m in available_missions:
		if not m["id"] in GameManager.completed_missions:
			result.append(m)
	return result

func start_mission(mission_id: String) -> bool:
	for m in available_missions:
		if m["id"] == mission_id:
			active_mission = m.duplicate(true)
			mission_active = true
			mission_timer = 0.0
			collected_items = 0
			checkpoint_index = 0
			target_items = m.get("target_count", 0)
			race_checkpoints = m.get("checkpoints", [])
			mission_started.emit(active_mission)
			return true
	return false

func cancel_mission() -> void:
	mission_active = false
	active_mission = {}
	mission_failed.emit(active_mission)

func _process(delta: float) -> void:
	if not mission_active:
		return
	
	mission_timer += delta
	var time_limit: float = active_mission.get("time_limit", 999.0)
	
	# Check time limit
	if mission_timer > time_limit:
		_fail_mission("Time's up!")
		return
	
	# Check mission progress based on type
	match active_mission.get("type"):
		"race", "time_trial":
			_check_race_progress()
		"collection":
			_check_collection_progress()
		"exploration":
			_check_exploration_progress()

func _check_race_progress() -> void:
	if not world or not world.player:
		return
	if checkpoint_index >= race_checkpoints.size():
		return
	
	var next_checkpoint := race_checkpoints[checkpoint_index]
	var player_pos: Vector3 = world.player.global_position
	var dist: float = player_pos.distance_to(next_checkpoint)
	
	if dist < 5.0:
		checkpoint_index += 1
		objective_updated.emit("Checkpoint %d/%d reached!" % [checkpoint_index, race_checkpoints.size()])
		
		if checkpoint_index >= race_checkpoints.size():
			_complete_mission()

func _check_collection_progress() -> void:
	if not world or not world.player:
		return
	# Count coins collected within the mission area
	var loc: Vector3 = active_mission.get("location", Vector3.ZERO)
	var radius: float = active_mission.get("collect_radius", 30.0)
	
	# Check proximity-based collection
	# (uses the coin system already in place, but tracks within mission zone)
	if world.player.global_position.distance_to(loc) < radius + 10:
		# Each time a coin is collected in the zone, increment
		# This is handled via the collectible system + checking GameManager coins delta
		pass
	
	# Simplified: reach the location and stay for the duration
	if world.player.global_position.distance_to(loc) < 5.0:
		collected_items += 1
		objective_updated.emit("Items: %d/%d" % [collected_items, target_items])
		if collected_items >= target_items:
			_complete_mission()

func _check_exploration_progress() -> void:
	if not world or not world.player:
		return
	var targets: Array = active_mission.get("targets", [])
	if checkpoint_index >= targets.size():
		_complete_mission()
		return
	
	var target: Vector3 = targets[checkpoint_index]
	if world.player.global_position.distance_to(target) < 8.0:
		checkpoint_index += 1
		objective_updated.emit("Location %d/%d explored!" % [checkpoint_index, targets.size()])
		if checkpoint_index >= targets.size():
			_complete_mission()

func _complete_mission() -> void:
	mission_active = false
	var reward: int = active_mission.get("reward_coins", 0)
	GameManager.add_coins(reward)
	GameManager.complete_mission(active_mission["id"])
	mission_completed_signal.emit(active_mission)
	active_mission = {}

func _fail_mission(reason: String) -> void:
	mission_active = false
	mission_failed.emit(active_mission)
	active_mission = {}

func get_time_remaining() -> float:
	if not mission_active:
		return 0.0
	var limit: float = active_mission.get("time_limit", 999.0)
	return max(0.0, limit - mission_timer)

func get_current_objective_text() -> String:
	if not mission_active:
		return "No active mission"
	
	var type: String = active_mission.get("type", "")
	match type:
		"race", "time_trial":
			return "Reach checkpoint %d/%d" % [checkpoint_index + 1, race_checkpoints.size()]
		"collection":
			return "Collect items: %d/%d" % [collected_items, target_items]
		"exploration":
			var targets: Array = active_mission.get("targets", [])
			return "Explore location %d/%d" % [checkpoint_index + 1, targets.size()]
	return active_mission.get("description", "")
