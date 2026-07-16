extends Node3D
class_name ManamaSouqVerticalSlice

const LAYOUT_PATH := "res://asset_lab/runtime/manama_souq_layout_v1.json"
const FULL_MANIFEST_PATH := "res://asset_lab/runtime/full_asset_matrix_manifest.json"
const PlayerControllerScript := preload("res://scripts/player_controller.gd")
const VehicleControllerScript := preload("res://scripts/vehicle.gd")
const HUDScene := preload("res://scenes/karak_delivery_hud.tscn")

var _layout_loader: ManamaSouqLayoutLoader
var _layout_report: Dictionary = {}
var _population_report: Dictionary = {}
var _mission_points: Dictionary = {}
var _player = null
var _mission_vehicle = null
var _mission: KarakDeliveryMission
var _population: SouqPopulationController
var _hud: KarakDeliveryHUD
var _district_root: Node3D
var _population_root: Node3D
var _last_vehicle: Node3D
var _ready_complete := false
var _mission_reward_applied := false
var _qa_mode := false
var _qa_elapsed := 0.0
var _qa_completion_printed := false
var _target_marker: MeshInstance3D


func _ready() -> void:
	_build_environment()
	_create_named_runtime_nodes()
	_layout_loader = ManamaSouqLayoutLoader.new()
	var layout := _layout_loader.load_layout(LAYOUT_PATH, FULL_MANIFEST_PATH)
	if layout.is_empty():
		push_error("Manama Souq layout failed: %s" % _layout_loader.last_error)
		return
	_mission_points = _layout_loader.get_mission_points()
	_spawn_player()
	await get_tree().process_frame
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		camera = _create_fallback_camera()
	_layout_report = _layout_loader.instantiate_layout(_district_root, camera, "balanced")
	if _layout_report.is_empty():
		push_error("Manama Souq assets failed: %s" % _layout_loader.last_error)
		return
	_spawn_mission_vehicle()
	_spawn_population()
	_spawn_hud()
	_build_mission_markers()
	_start_mission()
	_qa_mode = bool(ProjectSettings.get_setting("bahrain_brick/qa_auto_mission", false))
	_ready_complete = true
	_emit_ready()


func _process(delta: float) -> void:
	if not _ready_complete:
		return
	_update_mission_from_world()
	_update_target_marker()
	if _qa_mode:
		_run_qa_traversal(maxf(delta, 0.0))


func _create_named_runtime_nodes() -> void:
	_district_root = Node3D.new()
	_district_root.name = "District"
	add_child(_district_root)
	var player_spawn := Marker3D.new()
	player_spawn.name = "PlayerSpawn"
	add_child(player_spawn)
	var vehicle_spawn := Marker3D.new()
	vehicle_spawn.name = "MissionVehicleSpawn"
	add_child(vehicle_spawn)
	_population_root = Node3D.new()
	_population_root.name = "Population"
	add_child(_population_root)
	var mission_root := Node.new()
	mission_root.name = "Mission"
	add_child(mission_root)
	var hud_anchor := Node.new()
	hud_anchor.name = "HUD"
	add_child(hud_anchor)


func _build_environment() -> void:
	var environment_node := WorldEnvironment.new()
	environment_node.name = "SouqWorldEnvironment"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.24, 0.48, 0.70, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.93, 0.84, 0.67, 1.0)
	environment.ambient_light_energy = 0.82
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment_node.environment = environment
	add_child(environment_node)

	var sun := DirectionalLight3D.new()
	sun.name = "LateAfternoonSun"
	sun.rotation_degrees = Vector3(-48.0, -32.0, 0.0)
	sun.light_color = Color(1.0, 0.78, 0.56, 1.0)
	sun.light_energy = 1.28
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 150.0
	add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.name = "SkyFill"
	fill.rotation_degrees = Vector3(-25.0, 145.0, 0.0)
	fill.light_color = Color(0.48, 0.65, 0.92, 1.0)
	fill.light_energy = 0.30
	fill.shadow_enabled = false
	add_child(fill)

	var ground_body := StaticBody3D.new()
	ground_body.name = "DistrictGround"
	var ground_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(220.0, 220.0)
	ground_mesh.mesh = plane
	var ground_material := StandardMaterial3D.new()
	ground_material.albedo_color = Color(0.48, 0.39, 0.27, 1.0)
	ground_material.roughness = 0.94
	ground_mesh.material_override = ground_material
	ground_body.add_child(ground_mesh)
	var ground_collision := CollisionShape3D.new()
	var ground_shape := BoxShape3D.new()
	ground_shape.size = Vector3(220.0, 0.4, 220.0)
	ground_collision.shape = ground_shape
	ground_collision.position.y = -0.22
	ground_body.add_child(ground_collision)
	add_child(ground_body)
	_build_road_surface()
	_build_boundary_colliders()


func _build_road_surface() -> void:
	var road_material := StandardMaterial3D.new()
	road_material.albedo_color = Color(0.11, 0.12, 0.13, 1.0)
	road_material.roughness = 0.90
	for record in [
		{"name": "SouqMainRoad", "position": Vector3(-14.0, 0.03, -5.0), "size": Vector3(145.0, 0.08, 13.0), "rotation": 0.18},
		{"name": "WaterfrontApproach", "position": Vector3(45.0, 0.035, -44.0), "size": Vector3(90.0, 0.08, 12.0), "rotation": -0.55},
		{"name": "CafeAccess", "position": Vector3(-64.0, 0.04, 43.0), "size": Vector3(72.0, 0.08, 11.0), "rotation": 1.48},
	]:
		var road := MeshInstance3D.new()
		road.name = str(record["name"])
		var box := BoxMesh.new()
		box.size = record["size"]
		road.mesh = box
		road.position = record["position"]
		road.rotation.y = float(record["rotation"])
		road.material_override = road_material
		add_child(road)


func _build_boundary_colliders() -> void:
	var boundaries := [
		{"position": Vector3(-110.5, 2.0, 0.0), "size": Vector3(1.0, 4.0, 222.0)},
		{"position": Vector3(110.5, 2.0, 0.0), "size": Vector3(1.0, 4.0, 222.0)},
		{"position": Vector3(0.0, 2.0, -110.5), "size": Vector3(222.0, 4.0, 1.0)},
		{"position": Vector3(0.0, 2.0, 110.5), "size": Vector3(222.0, 4.0, 1.0)},
	]
	for index in range(boundaries.size()):
		var body := StaticBody3D.new()
		body.name = "DistrictBoundary_%d" % index
		body.position = boundaries[index]["position"]
		var collision := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = boundaries[index]["size"]
		collision.shape = shape
		body.add_child(collision)
		add_child(body)


func _spawn_player() -> void:
	_player = CharacterBody3D.new()
	_player.name = "Player"
	_player.set_script(PlayerControllerScript)
	_player.position = _mission_points.get("player_spawn", Vector3(-82.0, 1.0, 65.0))
	_player.set("is_local", true)
	_player.set("multiplayer_id", 1)
	add_child(_player)
	var marker := get_node("PlayerSpawn") as Marker3D
	marker.position = _player.position


func _spawn_mission_vehicle() -> void:
	_mission_vehicle = VehicleBody3D.new()
	_mission_vehicle.name = "MissionVehicle"
	_mission_vehicle.set_script(VehicleControllerScript)
	_mission_vehicle.position = _mission_points.get("vehicle_spawn", Vector3(-58.0, 0.6, 48.0))
	_mission_vehicle.rotation_degrees.y = 92.0
	_mission_vehicle.set_meta("car_index", 0)
	_mission_vehicle.set_meta("car_color", Color(0.78, 0.14, 0.08, 1.0))
	_mission_vehicle.set_meta("karak_delivery_vehicle", true)
	var collision := CollisionShape3D.new()
	collision.name = "ChassisCollision"
	var shape := BoxShape3D.new()
	shape.size = Vector3(1.6, 0.8, 3.2)
	collision.shape = shape
	collision.position.y = 0.55
	_mission_vehicle.add_child(collision)
	add_child(_mission_vehicle)
	var marker := get_node("MissionVehicleSpawn") as Marker3D
	marker.position = _mission_vehicle.position


func _spawn_population() -> void:
	_population = SouqPopulationController.new()
	_population.name = "SouqPopulationController"
	_population_root.add_child(_population)
	var population_contract := _layout_loader.get_population_contract()
	var pedestrians := int(population_contract.get("pedestrians", 12))
	var traffic := int(population_contract.get("traffic", 6))
	if not _population.configure(_layout_loader.get_bounds(), _layout_loader.get_traffic_route(), pedestrians, traffic, 1409):
		push_error("Souq population configuration failed")
		return
	_population_report = _population.spawn_all(_population_root)


func _spawn_hud() -> void:
	_hud = HUDScene.instantiate() as KarakDeliveryHUD
	if _hud == null:
		push_error("Karak Delivery HUD failed to instantiate")
		return
	_hud.name = "KarakDeliveryHUD"
	add_child(_hud)
	_hud.replay_requested.connect(_reset_for_replay)


func _start_mission() -> void:
	_mission = KarakDeliveryMission.new()
	_mission.name = "KarakDeliveryMission"
	get_node("Mission").add_child(_mission)
	if not _mission.configure(_mission_points, 250, 300.0):
		push_error("Karak Delivery mission configuration failed")
		return
	_mission.mission_completed.connect(_on_mission_completed)
	_mission.mission_failed.connect(_on_mission_failed)
	if _hud != null:
		_hud.bind_mission(_mission, _player)
	if not _mission.start(_player, _mission_vehicle):
		push_error("Karak Delivery mission failed to start")


func _update_mission_from_world() -> void:
	if _mission == null or _player == null or _mission_vehicle == null:
		return
	var current_vehicle: Node3D = _player.current_vehicle
	match _mission.current_state:
		KarakDeliveryMission.MissionState.WALK_TO_CAFE:
			_mission.advance_from_player_position(_player.global_position)
		KarakDeliveryMission.MissionState.COLLECT_ORDER:
			if _player.global_position.distance_to(_mission.get_current_target()) <= 3.5 and _interaction_pressed():
				if _mission.notify_order_collected() and _hud != null:
					_hud.set_status_message("Karak order collected", 1.5)
		KarakDeliveryMission.MissionState.ENTER_VEHICLE:
			if current_vehicle == _mission_vehicle:
				_mission.notify_vehicle_entered(_mission_vehicle)
		KarakDeliveryMission.MissionState.DRIVE_TO_WATERFRONT:
			var drive_position := _mission_vehicle.global_position if current_vehicle == _mission_vehicle else _player.global_position
			_mission.advance_from_player_position(drive_position)
		KarakDeliveryMission.MissionState.EXIT_VEHICLE:
			if _last_vehicle == _mission_vehicle and current_vehicle == null:
				_mission.notify_vehicle_exited()
		KarakDeliveryMission.MissionState.DELIVER_ORDER:
			if _player.global_position.distance_to(_mission.get_current_target()) <= 3.5 and _interaction_pressed():
				_mission.advance_from_player_position(_player.global_position)
	_last_vehicle = current_vehicle


func _interaction_pressed() -> bool:
	return Input.is_action_just_pressed("enter_vehicle") or TouchInput.consume_interact()


func _reset_for_replay() -> void:
	if _mission == null or _player == null or _mission_vehicle == null:
		return
	if _player.current_vehicle != null:
		if _player.current_vehicle.has_method("remove_driver"):
			_player.current_vehicle.remove_driver()
		_player.current_vehicle = null
	_player.global_position = _mission_points.get("player_spawn", Vector3(-82.0, 1.0, 65.0))
	_player.velocity = Vector3.ZERO
	_mission_vehicle.global_position = _mission_points.get("vehicle_spawn", Vector3(-58.0, 0.6, 48.0))
	_mission_vehicle.linear_velocity = Vector3.ZERO
	_mission_vehicle.angular_velocity = Vector3.ZERO
	_mission_vehicle.rotation_degrees = Vector3(0.0, 92.0, 0.0)
	_last_vehicle = null
	_mission_reward_applied = false
	_qa_elapsed = 0.0
	_qa_completion_printed = false
	if not _mission.restart():
		push_error("Karak Delivery replay failed")
	if _hud != null:
		_hud.bind_mission(_mission, _player)


func _build_mission_markers() -> void:
	_target_marker = MeshInstance3D.new()
	_target_marker.name = "MissionTargetMarker"
	var mesh := CylinderMesh.new()
	mesh.top_radius = 1.5
	mesh.bottom_radius = 1.5
	mesh.height = 0.16
	_target_marker.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(1.0, 0.72, 0.08, 0.78)
	material.emission_enabled = true
	material.emission = Color(1.0, 0.42, 0.04, 1.0)
	material.emission_energy_multiplier = 1.8
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_target_marker.material_override = material
	add_child(_target_marker)


func _update_target_marker() -> void:
	if _target_marker == null or _mission == null:
		return
	_target_marker.visible = _mission.current_state not in [KarakDeliveryMission.MissionState.COMPLETED, KarakDeliveryMission.MissionState.FAILED]
	_target_marker.global_position = _mission.get_current_target() + Vector3(0.0, 0.10, 0.0)
	_target_marker.rotation.y += 0.012


func _on_mission_completed(reward_coins: int, _elapsed_seconds: float) -> void:
	if _mission_reward_applied:
		return
	_mission_reward_applied = true
	if GameManager != null:
		GameManager.add_coins(reward_coins)


func _on_mission_failed(reason: String) -> void:
	if _hud != null:
		_hud.set_status_message(reason, 3.0)


func _emit_ready() -> void:
	var asset_count := int(_layout_report.get("placement_count", 0))
	print("BAHRAIN_BRICK_SOUQ_SLICE_READY assets=%d pedestrians=12 traffic=6" % asset_count)


func _run_qa_traversal(delta: float) -> void:
	if _mission == null or _player == null or _mission_vehicle == null:
		return
	_qa_elapsed += delta
	match _mission.current_state:
		KarakDeliveryMission.MissionState.WALK_TO_CAFE:
			_player.global_position = _player.global_position.move_toward(_mission_points["cafe_collection"] + Vector3(0.0, 1.0, 0.0), delta * 7.0)
		KarakDeliveryMission.MissionState.COLLECT_ORDER:
			_mission.notify_order_collected()
		KarakDeliveryMission.MissionState.ENTER_VEHICLE:
			_player.current_vehicle = _mission_vehicle
			_mission_vehicle.set_driver(_player)
			_mission.notify_vehicle_entered(_mission_vehicle)
			_mission_vehicle.freeze = true
		KarakDeliveryMission.MissionState.DRIVE_TO_WATERFRONT:
			var destination: Vector3 = _mission_points["waterfront_dropoff"] + Vector3(0.0, 0.6, 0.0)
			_mission_vehicle.global_position = _mission_vehicle.global_position.move_toward(destination, delta * 9.0)
			_player.global_position = _mission_vehicle.global_position
		KarakDeliveryMission.MissionState.EXIT_VEHICLE:
			_mission_vehicle.remove_driver()
			_player.current_vehicle = null
			_player.global_position = _mission_vehicle.global_position + Vector3(2.0, 0.5, 0.0)
			_mission.notify_vehicle_exited()
		KarakDeliveryMission.MissionState.DELIVER_ORDER:
			_player.global_position = _mission_points["waterfront_dropoff"] + Vector3(0.0, 1.0, 0.0)
			_mission.advance_from_player_position(_player.global_position)
		KarakDeliveryMission.MissionState.COMPLETED:
			if not _qa_completion_printed:
				_qa_completion_printed = true
				print("BAHRAIN_BRICK_SOUQ_QA_TRAVERSAL_COMPLETE")


func _create_fallback_camera() -> Camera3D:
	var camera := Camera3D.new()
	camera.name = "FallbackCamera"
	camera.current = true
	camera.position = Vector3(-78.0, 7.0, 76.0)
	camera.look_at(Vector3(-65.0, 2.0, 50.0), Vector3.UP)
	add_child(camera)
	return camera


func is_slice_ready() -> bool:
	return _ready_complete


func get_layout_report() -> Dictionary:
	return _layout_report.duplicate(true)


func get_population_report() -> Dictionary:
	return _population_report.duplicate(true)


func get_player_node():
	return _player


func get_mission_vehicle():
	return _mission_vehicle


func get_mission() -> KarakDeliveryMission:
	return _mission


func set_runtime_processing_enabled(enabled: bool) -> void:
	set_process(enabled)
