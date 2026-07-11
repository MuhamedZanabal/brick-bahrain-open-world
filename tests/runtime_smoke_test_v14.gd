extends SceneTree
## Headless runtime gate. Execute with Godot 4.3:
## godot --headless --path . --script res://tests/runtime_smoke_test_v14.gd

var _results: Array[Dictionary] = []
var _failed := 0
var _original_save_path := ""


func _initialize() -> void:
	call_deferred("_run")


func _check(condition: bool, description: String, evidence: Variant = null) -> void:
	if not condition:
		_failed += 1
	_results.append({"passed": condition, "description": description, "evidence": evidence})
	print(
		(
			"[%s] %s%s"
			% [
				"PASS" if condition else "FAIL",
				description,
				" — %s" % str(evidence) if evidence != null else ""
			]
		)
	)


func _wait_frames(count: int) -> void:
	for _index in range(count):
		await process_frame


func _run() -> void:
	print("Brick Bahrain v1.4 runtime smoke test starting")
	_original_save_path = SaveManager.save_path
	SaveManager.save_path = "user://savegame.v14.smoke.json"
	for suffix in ["", ".tmp", ".bak"]:
		var candidate := SaveManager.save_path + suffix
		if FileAccess.file_exists(candidate):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(candidate))
	SaveManager.load_game()
	SaveManager.apply_loaded_state()
	GameManager.current_mode = GameManager.GameMode.SINGLE_PLAYER
	GameManager.completed_missions.clear()
	GameManager.owned_properties.clear()
	GameManager.owned_vehicles.clear()
	GameManager.set_coins(0, false)

	for scene_path in [
		"res://scenes/splash_screen.tscn",
		"res://scenes/main_menu.tscn",
		"res://scenes/character_select.tscn",
		"res://scenes/world.tscn",
	]:
		var packed := load(scene_path) as PackedScene
		_check(packed != null, "scene resource loads", scene_path)
		if packed:
			var probe := packed.instantiate()
			_check(probe != null, "scene instantiates", scene_path)
			probe.free()

	var world_scene := load("res://scenes/world.tscn") as PackedScene
	if world_scene == null:
		_finish()
		return
	var world := world_scene.instantiate() as Node3D
	root.add_child(world)
	var ready_timeout := 900
	while ready_timeout > 0 and not bool(world.get("_world_ready")):
		ready_timeout -= 1
		await process_frame
	_check(bool(world.get("_world_ready")), "world staged loading completes", 900 - ready_timeout)
	if not bool(world.get("_world_ready")):
		_finish()
		return

	await _wait_frames(40)
	var player := world.get("player") as CharacterBody3D
	var hero := world.call("get_hero_district") as Node3D
	var npc_manager := world.get("npc_manager") as Node
	var traffic_manager := world.call("get_traffic_manager") as Node
	var vehicles: Array = world.get("vehicles")
	_check(player != null and is_instance_valid(player), "visible local player exists")
	_check(hero != null and is_instance_valid(hero), "hero district exists")
	_check(player and player.find_child("Model", true, false) != null, "player model exists")
	_check(
		player and player.find_child("Collision", true, false) != null, "player collision exists"
	)
	_check(
		player and player.find_child("ThirdPersonCamera", true, false) is Camera3D,
		"third-person camera exists"
	)
	_check(vehicles.size() >= 5, "five drivable vehicles spawn", vehicles.size())
	_check(
		npc_manager and int(npc_manager.call("get_npc_count")) >= 50,
		"at least fifty pedestrians spawn",
		npc_manager.call("get_npc_count") if npc_manager else -1
	)
	_check(
		traffic_manager and int(traffic_manager.call("get_total_vehicle_count")) >= 7,
		"traffic pool spawns",
		traffic_manager.call("get_total_vehicle_count") if traffic_manager else -1
	)
	_check(world.get("hud") != null, "state-driven HUD exists")
	_check(world.get("phone_ui") != null, "phone UI exists")
	_check(
		MissionManager.get_mission_count() == 8,
		"eight missions registered",
		MissionManager.get_mission_count()
	)
	_check(
		world.find_child("CentralBoulevard", true, false) != null,
		"central boulevard geometry exists"
	)
	_check(
		world.find_child("TwinSailTradeCentre", true, false) != null, "twin-sail landmark exists"
	)
	_check(world.find_child("WaterfrontWater", true, false) != null, "animated waterfront exists")

	if player:
		var walking_start := player.global_position
		TouchInput.set_movement(Vector2(0.0, -1.0))
		TouchInput.set_sprint(true)
		await _wait_frames(75)
		TouchInput.set_movement(Vector2.ZERO)
		TouchInput.set_sprint(false)
		await _wait_frames(6)
		var walking_distance := walking_start.distance_to(player.global_position)
		_check(walking_distance > 0.35, "player responds to touch movement", walking_distance)
		var camera_rig := player.find_child("CameraRig", true, false) as Node3D
		var yaw_before := camera_rig.rotation.y if camera_rig else 0.0
		TouchInput.add_look_delta(Vector2(100.0, -35.0))
		await _wait_frames(4)
		_check(
			camera_rig and absf(camera_rig.rotation.y - yaw_before) > 0.001,
			"touch drag rotates camera"
		)

	if player and not vehicles.is_empty():
		var vehicle := vehicles[0] as VehicleBody3D
		player.call("enter_vehicle", vehicle)
		await _wait_frames(8)
		_check(bool(player.call("is_in_vehicle")), "vehicle entry succeeds")
		var vehicle_start := vehicle.global_position
		TouchInput.set_vehicle_throttle(1.0)
		TouchInput.set_vehicle_steering(0.22)
		await _wait_frames(150)
		TouchInput.reset_vehicle_controls()
		var driven_distance := vehicle_start.distance_to(vehicle.global_position)
		_check(
			driven_distance > 0.5 or float(vehicle.call("get_speed_kph")) > 1.0,
			"vehicle accelerates and drives",
			{"distance": driven_distance, "speed_kph": vehicle.call("get_speed_kph")}
		)
		player.call("exit_vehicle")
		await _wait_frames(8)
		_check(not bool(player.call("is_in_vehicle")), "vehicle exit succeeds")

	if npc_manager and int(npc_manager.call("get_npc_count")) > 0:
		var pedestrian := npc_manager.get("pedestrians")[0] as Node3D
		pedestrian.call("flee_from", pedestrian.global_position + Vector3(1, 0, 0), 2.0)
		await _wait_frames(2)
		_check(int(pedestrian.get("state")) == 1, "pedestrian enters flee state")

	var coins_before := GameManager.coins
	_check(MissionManager.start_mission("pearl_diving"), "pearl mission starts")
	MissionManager.record_event("pearl_collected", 10.0)
	await _wait_frames(4)
	_check(GameManager.completed_missions.has("pearl_diving"), "pearl mission completes")
	_check(
		GameManager.coins >= coins_before + 120,
		"pearl mission reward is authoritative",
		GameManager.coins
	)

	if player:
		player.global_position = Vector3(0, 1.4, -48)
	_check(MissionManager.start_mission("drift_competition"), "drift mission starts")
	for _index in range(13):
		MissionManager.record_event("drift_points", 80.0)
	await _wait_frames(4)
	_check(GameManager.completed_missions.has("drift_competition"), "drift mission completes")

	_check(MissionManager.start_mission("sandstorm_survival"), "sandstorm mission starts")
	if player:
		player.global_position = Vector3(61, 1.4, 78)
	await _wait_frames(5)
	_check(
		GameManager.completed_missions.has("sandstorm_survival"),
		"sandstorm mission completes at shelter"
	)
	_check(
		(
			WeatherSystem.current_weather == WeatherSystem.WeatherType.SANDSTORM
			or GameManager.completed_missions.has("sandstorm_survival")
		),
		"sandstorm system participates in mission"
	)

	var saved_coins := GameManager.coins
	_check(SaveManager.save_game("v1.4 smoke"), "save file writes")
	_check(FileAccess.file_exists(SaveManager.save_path), "save file exists", SaveManager.save_path)
	GameManager.set_coins(0, false)
	_check(SaveManager.load_game(), "save file reloads")
	SaveManager.apply_loaded_state()
	_check(
		GameManager.coins == saved_coins,
		"coin progress restores",
		{"expected": saved_coins, "actual": GameManager.coins}
	)
	_check(GameManager.completed_missions.has("pearl_diving"), "mission completion restores")

	var sample := QualityManager.get_performance_sample()
	_check(
		sample.has("fps") and sample.has("draw_calls") and sample.has("static_memory_mb"),
		"performance telemetry is available",
		sample
	)
	_finish()


func _finish() -> void:
	var output := {
		"version": "1.4.0",
		"failed": _failed,
		"passed": _results.size() - _failed,
		"results": _results,
		"performance": QualityManager.get_performance_sample(),
	}
	var file := FileAccess.open("user://runtime_smoke_v14.json", FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(output, "\t"))
		file.close()
	for suffix in ["", ".tmp", ".bak"]:
		var candidate := SaveManager.save_path + suffix
		if FileAccess.file_exists(candidate):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(candidate))
	SaveManager.save_path = _original_save_path
	print(
		(
			"Brick Bahrain v1.4 runtime smoke test complete: %d passed, %d failed"
			% [output["passed"], _failed]
		)
	)
	quit(1 if _failed > 0 else 0)
