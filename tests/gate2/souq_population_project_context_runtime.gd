extends Node

const PopulationScript := preload("res://scripts/souq_population_controller.gd")


func _ready() -> void:
	call_deferred("_run")


func _run() -> void:
	var factory := get_node_or_null("/root/BrickFactory")
	_require(factory != null, "BrickFactory autoload is unavailable in project context")
	_require(factory.has_method("create_brick_car"), "BrickFactory.create_brick_car is unavailable")

	var population_root := Node3D.new()
	population_root.name = "PopulationProjectContextRoot"
	add_child(population_root)
	var controller: SouqPopulationController = PopulationScript.new()
	controller.name = "SouqPopulationControllerProjectContext"
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
	await get_tree().process_frame
	await get_tree().process_frame
	var counts := controller.get_population_counts()
	_require(int(counts.get("pedestrian_count", -1)) == 12, "runtime pedestrian count mismatch")
	_require(int(counts.get("traffic_count", -1)) == 6, "runtime traffic count mismatch")
	_require(get_tree().get_nodes_in_group("souq_pedestrians").size() == 12, "souq_pedestrians group mismatch")
	_require(get_tree().get_nodes_in_group("souq_traffic").size() == 6, "souq_traffic group mismatch")
	for pedestrian: Node3D in controller.get_pedestrians():
		_require(bounds.has_point(pedestrian.global_position), "pedestrian outside bounds")
	for vehicle: Node3D in controller.get_traffic():
		_require(bounds.has_point(vehicle.global_position), "traffic outside bounds")
		var model := vehicle.get_node_or_null("TrafficCarModel")
		_require(model != null, "BrickFactory vehicle model missing")
		_require(model.get_child_count() > 0, "BrickFactory vehicle model is empty")
	print("SOUQ_POPULATION_PROJECT_CONTEXT_PASS pedestrian_count=12 traffic_count=6 brick_factory=resolved")
	get_tree().quit(0)


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	get_tree().quit(1)
