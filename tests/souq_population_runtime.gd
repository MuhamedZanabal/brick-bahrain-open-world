extends SceneTree

const PopulationScript := preload("res://scripts/souq_population_controller.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var population_root := Node3D.new()
	population_root.name = "PopulationRuntimeRoot"
	root.add_child(population_root)
	var controller: SouqPopulationController = PopulationScript.new()
	controller.name = "SouqPopulationControllerRuntime"
	population_root.add_child(controller)
	var route: Array[Vector3] = [
		Vector3(-80.0, 0.0, 55.0),
		Vector3(-20.0, 0.0, 45.0),
		Vector3(55.0, 0.0, 0.0),
		Vector3(70.0, 0.0, -70.0),
		Vector3(0.0, 0.0, -70.0),
		Vector3(-55.0, 0.0, -10.0),
		Vector3(-80.0, 0.0, 55.0),
	]
	var bounds := AABB(Vector3(-110.0, -4.0, -110.0), Vector3(220.0, 80.0, 220.0))
	_require(controller.configure(bounds, route, 12, 6, 1409), "configure failed")
	var report := controller.spawn_all(population_root)
	_require(int(report.get("pedestrian_count", -1)) == 12, "pedestrian_count mismatch")
	_require(int(report.get("traffic_count", -1)) == 6, "traffic_count mismatch")
	_require(controller.spawn_all(population_root).is_empty(), "duplicate population spawn was accepted")
	await process_frame
	await process_frame
	var counts := controller.get_population_counts()
	_require(int(counts.get("pedestrian_count", -1)) == 12, "runtime pedestrian count mismatch")
	_require(int(counts.get("traffic_count", -1)) == 6, "runtime traffic count mismatch")
	_require(get_nodes_in_group("souq_pedestrians").size() == 12, "souq_pedestrians group mismatch")
	_require(get_nodes_in_group("souq_traffic").size() == 6, "souq_traffic group mismatch")
	for pedestrian: Node3D in controller.get_pedestrians():
		_require(bounds.has_point(pedestrian.global_position), "pedestrian outside bounds")
	for vehicle: Node3D in controller.get_traffic():
		_require(bounds.has_point(vehicle.global_position), "traffic outside bounds")
	print("SOUQ_POPULATION_RUNTIME_PASS pedestrian_count=12 traffic_count=6")
	quit(0)


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
