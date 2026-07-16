extends SceneTree

const SliceScene := preload("res://scenes/manama_souq_vertical_slice.tscn")


func _initialize() -> void:
	ProjectSettings.set_setting("bahrain_brick/qa_auto_mission", false)
	call_deferred("_run")


func _run() -> void:
	var slice := SliceScene.instantiate() as ManamaSouqVerticalSlice
	_require(slice != null, "ManamaSouqVerticalSlice scene root type mismatch")
	root.add_child(slice)
	for _frame in range(900):
		if slice.is_slice_ready():
			break
		await process_frame
	_require(slice.is_slice_ready(), "slice did not become ready")
	slice.set_runtime_processing_enabled(false)

	var layout := slice.get_layout_report()
	var population := slice.get_population_report()
	_require(int(layout.get("placement_count", -1)) == 35, "layout placement count mismatch")
	_require(int(layout.get("architecture_count", -1)) == 31, "architecture count mismatch")
	_require(int(layout.get("commercial_count", -1)) == 4, "commercial count mismatch")
	_require(int(population.get("pedestrian_count", -1)) == 12, "population pedestrian count mismatch")
	_require(int(population.get("traffic_count", -1)) == 6, "population traffic count mismatch")
	_require(get_nodes_in_group("souq_pedestrians").size() == 12, "souq_pedestrians group mismatch")
	_require(get_nodes_in_group("souq_traffic").size() == 6, "souq_traffic group mismatch")

	var player = slice.get_player_node()
	var mission_vehicle = slice.get_mission_vehicle()
	var mission: KarakDeliveryMission = slice.get_mission()
	_require(player != null and player.name == "Player", "player missing")
	_require(mission_vehicle != null and mission_vehicle.name == "MissionVehicle", "MissionVehicle missing")
	_require(mission != null and mission.name == "KarakDeliveryMission", "KarakDeliveryMission missing")
	_require(mission.current_state == KarakDeliveryMission.MissionState.WALK_TO_CAFE, "mission did not start")
	_require(get_nodes_in_group("vehicles").has(mission_vehicle), "mission vehicle not in vehicles group")
	_require(get_nodes_in_group("player").has(player), "player not in player group")
	_require(root.get_viewport().get_camera_3d() != null, "current camera missing")
	for node_name in ["District", "PlayerSpawn", "MissionVehicleSpawn", "Population", "Mission", "HUD"]:
		_require(slice.get_node_or_null(node_name) != null, "runtime node missing: %s" % node_name)

	print("MANAMA_SOUQ_SLICE_RUNTIME_PASS assets=35 pedestrians=12 traffic=6")
	quit(0)


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
