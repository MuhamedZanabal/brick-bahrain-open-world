extends Node

# Extended mission system — original 7 + 8 new = 15 missions total
var missions: Array[Dictionary] = []
var active_mission_idx: int = -1
var mission_timer: float = 0.0
var mission_target_pos: Vector3 = Vector3.ZERO
var mission_progress: int = 0
var mission_target_count: int = 0
var mission_checkpoints: Array[Vector3] = []
var current_checkpoint_idx: int = 0
var hud_label: Label

signal mission_started(mission_name: String)
signal mission_completed(mission_name: String, reward: int)
signal mission_failed(mission_name: String)

func _ready() -> void:
	_setup_missions()
	add_to_group("mission_system")

func _setup_missions() -> void:
	# === ORIGINAL 7 MISSIONS ===
	missions.append({
		"id": "f1_race",
		"name": "F1 Grand Prix",
		"type": "race",
		"desc": "Complete a lap around the Bahrain International Circuit",
		"reward": 100,
		"position": Vector3(0, 0, 120),
		"checkpoints": _generate_circuit_checkpoints()
	})
	missions.append({
		"id": "souk_treasure",
		"name": "Souk Treasure Hunt",
		"type": "collection",
		"desc": "Find 10 hidden coins in the Manama Souk",
		"reward": 50,
		"position": Vector3(0, 0, -40),
		"target_count": 10
	})
	missions.append({
		"id": "fort_expedition",
		"name": "Bahrain Fort Expedition",
		"type": "exploration",
		"desc": "Reach the top of Bahrain Fort and scan the surroundings",
		"reward": 75,
		"position": Vector3(-80, 0, 60)
	})
	missions.append({
		"id": "causeway_sprint",
		"name": "Causeway Sprint",
		"type": "race",
		"desc": "Race across the King Fahd Causeway",
		"reward": 80,
		"position": Vector3(-120, 0, -30),
		"checkpoints": [Vector3(-120, 1, -30), Vector3(-180, 1, -30), Vector3(-240, 1, -30), Vector3(-260, 1, -30)]
	})
	missions.append({
		"id": "skyline_explore",
		"name": "Skyline Explorer",
		"type": "exploration",
		"desc": "Visit all 5 major towers in the Manama skyline",
		"reward": 60,
		"position": Vector3(20, 0, 10),
		"target_count": 5
	})
	missions.append({
		"id": "desert_run",
		"name": "Desert Run",
		"type": "race",
		"desc": "Time trial through the desert to the Tree of Life",
		"reward": 70,
		"position": Vector3(100, 0, 100),
		"checkpoints": [Vector3(100, 1, 100), Vector3(80, 1, 120), Vector3(60, 1, 140), Vector3(50, 1, 160)]
	})
	missions.append({
		"id": "marina_drift",
		"name": "Marina Drift Challenge",
		"type": "collection",
		"desc": "Collect 8 flags along the Marina Beach",
		"reward": 65,
		"position": Vector3(-60, 0, 80),
		"target_count": 8
	})

	# === 8 NEW MISSIONS ===
	missions.append({
		"id": "pearl_diving",
		"name": "Pearl Diving Expedition",
		"type": "timed_collection",
		"desc": "Collect 10 pearls in 2 minutes at the Marina",
		"reward": 120,
		"position": Vector3(-60, 0, 80),
		"target_count": 10,
		"time_limit": 120.0
	})
	missions.append({
		"id": "police_escape",
		"name": "Police Chase Escape",
		"type": "survival",
		"desc": "Survive a 3-star wanted level for 60 seconds",
		"reward": 100,
		"position": Vector3(0, 0, 0),
		"time_limit": 60.0,
		"required_wanted": 3
	})
	missions.append({
		"id": "property_acquisition",
		"name": "First Property",
		"type": "objective",
		"desc": "Buy your first property at Amwaj Islands",
		"reward": 50,
		"position": Vector3(140, 0, -50),
		"target_count": 1
	})
	missions.append({
		"id": "taxi_job",
		"name": "Taxi Driver Job",
		"type": "transport",
		"desc": "Drive 3 NPCs to their destinations",
		"reward": 90,
		"position": Vector3(5, 0, -45),
		"target_count": 3
	})
	missions.append({
		"id": "drift_competition",
		"name": "BIC Drift Competition",
		"type": "score",
		"desc": "Score 1000 drift points at the Bahrain International Circuit",
		"reward": 110,
		"position": Vector3(0, 0, 120),
		"target_count": 1000
	})
	missions.append({
		"id": "night_causeway",
		"name": "Night Causeway Race",
		"type": "race",
		"desc": "Race across the Causeway at night",
		"reward": 130,
		"position": Vector3(-120, 0, -30),
		"checkpoints": [Vector3(-120, 1, -30), Vector3(-200, 1, -30), Vector3(-260, 1, -30), Vector3(-200, 1, -20), Vector3(-120, 1, -20)],
		"requires_night": true
	})
	missions.append({
		"id": "sandstorm_survival",
		"name": "Sandstorm Survival",
		"type": "survival",
		"desc": "Find shelter and survive a sandstorm",
		"reward": 85,
		"position": Vector3(0, 0, 0),
		"time_limit": 90.0,
		"requires_storm": true
	})
	missions.append({
		"id": "team_race",
		"name": "Team Race 2v2v2",
		"type": "multiplayer_race",
		"desc": "Compete in a 6-player team race (requires multiplayer)",
		"reward": 200,
		"position": Vector3(0, 0, 120),
		"checkpoints": _generate_circuit_checkpoints(),
		"requires_multiplayer": true
	})

func _generate_circuit_checkpoints() -> Array[Vector3]:
	var checkpoints: Array[Vector3] = []
	var center: Vector3 = Vector3(0, 0, 140)
	for i in range(8):
		var angle: float = (float(i) / 8.0) * TAU
		checkpoints.append(center + Vector3(cos(angle) * 40, 1, sin(angle) * 30))
	return checkpoints

func _process(delta: float) -> void:
	if active_mission_idx >= 0:
		_update_active_mission(delta)

func _update_active_mission(delta: float) -> void:
	var mission: Dictionary = missions[active_mission_idx]
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return

	var mission_type: String = mission["type"]

	# Timer for timed missions
	if mission.has("time_limit"):
		mission_timer -= delta
		if mission_timer <= 0:
			_fail_mission(mission)
			return

	match mission_type:
		"race":
			_update_race_mission(player, mission)
		"collection":
			_update_collection_mission(player, mission)
		"exploration":
			_update_exploration_mission(player, mission)
		"timed_collection":
			_update_timed_collection_mission(player, mission)
		"survival":
			_update_survival_mission(player, mission, delta)
		"objective":
			_update_objective_mission(player, mission)
		"transport":
			_update_transport_mission(player, mission)
		"score":
			_update_score_mission(player, mission)
		"multiplayer_race":
			_update_race_mission(player, mission)

func _update_race_mission(player: Node3D, mission: Dictionary) -> void:
	if mission.has("checkpoints") and current_checkpoint_idx < mission["checkpoints"].size():
		var cp: Vector3 = mission["checkpoints"][current_checkpoint_idx]
		var dist: float = player.global_position.distance_to(cp)
		if dist < 5.0:
			current_checkpoint_idx += 1
			if current_checkpoint_idx >= mission["checkpoints"].size():
				_complete_mission(mission)
			else:
				mission_target_pos = mission["checkpoints"][current_checkpoint_idx]
				_update_hud(mission)

func _update_collection_mission(player: Node3D, mission: Dictionary) -> void:
	# Check for coin/flag pickup near mission area
	var coins: int = 0
	if player.has_meta("coin_count"):
		coins = int(player.get_meta("coin_count"))
	if mission_progress >= int(mission.get("target_count", 10)):
		_complete_mission(mission)

func _update_exploration_mission(player: Node3D, mission: Dictionary) -> void:
	var dist: float = player.global_position.distance_to(mission["position"])
	if dist < 5.0:
		mission_progress += 1
		if mission_progress >= 1:
			_complete_mission(mission)

func _update_timed_collection_mission(player: Node3D, mission: Dictionary) -> void:
	# Collect pearls (use coins as proxy)
	if mission_progress >= int(mission.get("target_count", 10)):
		_complete_mission(mission)

func _update_survival_mission(player: Node3D, mission: Dictionary, delta: float) -> void:
	# Check conditions
	if mission.has("required_wanted"):
		var wanted: Node = get_tree().get_first_node_in_group("wanted_level")
		if wanted and wanted.has_method("get_level"):
			if wanted.get_level() >= int(mission["required_wanted"]):
				mission_progress += 1
				# Progress counts as time survived
	if mission.has("requires_storm"):
		var weather: Node = get_tree().get_first_node_in_group("weather_system")
		if weather and weather.has_method("is_storm"):
			if weather.is_storm():
				mission_progress += 1

	# Check time-based survival
	if mission.has("time_limit") and mission_progress > 0:
		# mission_timer is already counting down in main update
		if mission_timer > 0:
			# Still surviving
			_update_hud(mission)
		else:
			_complete_mission(mission)

func _update_objective_mission(player: Node3D, mission: Dictionary) -> void:
	# Check if player owns a property
	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	if save_mgr and save_mgr.has_method("get_owned_properties"):
		if save_mgr.get_owned_properties().size() >= int(mission.get("target_count", 1)):
			_complete_mission(mission)

func _update_transport_mission(player: Node3D, mission: Dictionary) -> void:
	# Check if player has reached destination with NPC
	# Simplified: check distance to mission position
	var dist: float = player.global_position.distance_to(mission["position"])
	if dist < 5.0:
		mission_progress += 1
		mission["position"] = _get_random_transport_destination()
		if mission_progress >= int(mission.get("target_count", 3)):
			_complete_mission(mission)
		else:
			_update_hud(mission)

func _update_score_mission(player: Node3D, mission: Dictionary) -> void:
	# Drift score — check if player is drifting
	var vehicle: Node3D = get_tree().get_first_node_in_group("player_vehicle")
	if vehicle and vehicle is RigidBody3D:
		var vel: Vector3 = vehicle.linear_velocity
		var angular: Vector3 = vehicle.angular_velocity
		if vel.length() > 10 and angular.length() > 1.0:
			mission_progress += int(vel.length() * angular.length() * 0.1)
			if mission_progress >= int(mission.get("target_count", 1000)):
				_complete_mission(mission)

func _get_random_transport_destination() -> Vector3:
	var destinations: Array[Vector3] = [
		Vector3(80, 0, 60),    # City Center
		Vector3(-60, 0, 80),   # Marina
		Vector3(0, 0, -40),    # Souk
		Vector3(30, 0, 20),    # Financial Harbour
	]
	return destinations[randi() % destinations.size()]

func start_mission(idx: int) -> void:
	if idx < 0 or idx >= missions.size():
		return
	if active_mission_idx >= 0:
		return  # Already have an active mission

	var mission: Dictionary = missions[idx]

	# Check requirements
	if mission.has("requires_night"):
		var dnc: Node = get_tree().get_first_node_in_group("day_night_cycle")
		if dnc and dnc.has_method("is_night"):
			if not dnc.is_night():
				_show_message("This mission can only be done at night!")
				return

	if mission.has("requires_storm"):
		var weather: Node = get_tree().get_first_node_in_group("weather_system")
		if weather and weather.has_method("is_storm"):
			if not weather.is_storm():
				_show_message("This mission requires a sandstorm!")
				return

	if mission.has("requires_multiplayer"):
		var mp: Node = get_tree().get_first_node_in_group("multiplayer_manager")
		if mp and mp.has_method("get_player_count"):
			if mp.get_player_count() < 2:
				_show_message("This mission requires multiplayer!")
				return

	active_mission_idx = idx
	mission_progress = 0
	current_checkpoint_idx = 0
	mission_timer = float(mission.get("time_limit", 0.0))
	mission_target_count = int(mission.get("target_count", 0))

	if mission.has("checkpoints"):
		mission_target_pos = mission["checkpoints"][0]
	else:
		mission_target_pos = mission["position"]

	# Set required wanted level for police escape
	if mission.has("required_wanted"):
		var wanted: Node = get_tree().get_first_node_in_group("wanted_level")
		if wanted and wanted.has_method("increase_level"):
			wanted.increase_level(int(mission["required_wanted"]))

	mission_started.emit(mission["name"])
	_show_message("Mission Started: %s" % mission["name"])
	_update_hud(mission)

func _complete_mission(mission: Dictionary) -> void:
	var reward: int = int(mission["reward"])
	var mission_name: String = mission["name"]

	# Award coins
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player:
		var current_coins: int = int(player.get_meta("coin_count", 0))
		player.set_meta("coin_count", current_coins + reward)

	# Save progress
	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	if save_mgr and save_mgr.has_method("complete_mission"):
		save_mgr.complete_mission(mission["id"])

	# Report to server
	var auth_server: Node = get_tree().get_first_node_in_group("authoritative_server")
	if auth_server and auth_server.has_method("report_mission_complete"):
		auth_server.report_mission_complete(mission["id"])

	mission_completed.emit(mission_name, reward)
	_show_message("Mission Complete! +%d coins" % reward)

	active_mission_idx = -1
	mission_progress = 0

func _fail_mission(mission: Dictionary) -> void:
	mission_failed.emit(mission["name"])
	_show_message("Mission Failed: %s" % mission["name"])
	active_mission_idx = -1
	mission_progress = 0

func _update_hud(mission: Dictionary) -> void:
	# HUD is handled by the main HUD system
	pass

func _show_message(msg: String) -> void:
	print("MissionManager: %s" % msg)

func get_active_mission() -> Dictionary:
	if active_mission_idx >= 0:
		return missions[active_mission_idx]
	return {}

func get_active_missions() -> Array:
	if active_mission_idx >= 0:
		return [missions[active_mission_idx]]
	return []

func get_all_missions() -> Array[Dictionary]:
	return missions

func get_mission_count() -> int:
	return missions.size()

func get_nearest_mission(player_pos: Vector3) -> int:
	var nearest_idx: int = -1
	var nearest_dist: float = 9999.0
	for i in range(missions.size()):
		var pos: Vector3 = missions[i]["position"]
		var dist: float = player_pos.distance_to(pos)
		if dist < nearest_dist:
			nearest_dist = dist
			nearest_idx = i
	return nearest_idx

func get_mission_timer() -> float:
	return mission_timer

func get_mission_progress() -> int:
	return mission_progress

func add_progress(amount: int) -> void:
	mission_progress += amount
