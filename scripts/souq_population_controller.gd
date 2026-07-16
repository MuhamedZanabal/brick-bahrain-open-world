extends Node
class_name SouqPopulationController

const DEFAULT_PEDESTRIAN_COUNT := 12
const DEFAULT_TRAFFIC_COUNT := 6
const DEFAULT_SEED := 1409
const TRAFFIC_SPEED_MIN := 4.2
const TRAFFIC_SPEED_MAX := 6.4

const PEDESTRIAN_COLORS := [
	Color(0.80, 0.18, 0.12),
	Color(0.10, 0.36, 0.72),
	Color(0.86, 0.62, 0.08),
	Color(0.15, 0.58, 0.28),
	Color(0.56, 0.24, 0.66),
	Color(0.80, 0.42, 0.12),
]

const TRAFFIC_COLORS := [
	Color(0.76, 0.08, 0.08),
	Color(0.08, 0.26, 0.64),
	Color(0.88, 0.88, 0.82),
	Color(0.12, 0.12, 0.14),
	Color(0.72, 0.54, 0.08),
	Color(0.18, 0.54, 0.42),
]

var _bounds := AABB()
var _traffic_route: Array[Vector3] = []
var _pedestrian_count := DEFAULT_PEDESTRIAN_COUNT
var _traffic_count := DEFAULT_TRAFFIC_COUNT
var _seed := DEFAULT_SEED
var _rng := RandomNumberGenerator.new()
var _configured := false
var _spawned := false
var _pedestrians: Array[Node3D] = []
var _traffic: Array[Node3D] = []


func configure(bounds: AABB, traffic_route: Array[Vector3], pedestrian_count: int = 12, traffic_count: int = 6, seed: int = 1409) -> bool:
	if bounds.size.x <= 0.0 or bounds.size.z <= 0.0:
		push_error("SouqPopulationController: invalid bounds")
		return false
	if traffic_route.size() < 4 or not traffic_route[0].is_equal_approx(traffic_route[-1]):
		push_error("SouqPopulationController: traffic_route must be closed")
		return false
	if pedestrian_count <= 0 or traffic_count <= 0:
		push_error("SouqPopulationController: population counts must be positive")
		return false
	_bounds = bounds
	_traffic_route = traffic_route.duplicate()
	_pedestrian_count = pedestrian_count
	_traffic_count = traffic_count
	_seed = seed
	_rng.seed = seed
	_configured = true
	return true


func spawn_all(root: Node3D) -> Dictionary:
	if _spawned:
		return {}
	if not _configured or root == null:
		return {}
	var pedestrian_root := Node3D.new()
	pedestrian_root.name = "SouqPedestrians"
	root.add_child(pedestrian_root)
	var traffic_root := Node3D.new()
	traffic_root.name = "SouqTraffic"
	root.add_child(traffic_root)

	for index in range(_pedestrian_count):
		var pedestrian := NPCPedestrian.new()
		pedestrian.name = "SouqPedestrian_%02d" % index
		pedestrian.npc_name = "Souq Visitor %02d" % (index + 1)
		pedestrian.npc_color = PEDESTRIAN_COLORS[index % PEDESTRIAN_COLORS.size()]
		pedestrian.walk_radius = 7.0 + float(index % 3) * 1.5
		pedestrian.home_position = _pedestrian_spawn_position(index)
		pedestrian.model_path = ""
		pedestrian.add_to_group("souq_pedestrians")
		pedestrian_root.add_child(pedestrian)
		pedestrian.global_position = pedestrian.home_position
		_pedestrians.append(pedestrian)

	var route_segment_count := _traffic_route.size() - 1
	for index in range(_traffic_count):
		var traffic_vehicle := Node3D.new()
		traffic_vehicle.name = "SouqTraffic_%02d" % index
		traffic_vehicle.add_to_group("souq_traffic")
		var route_index := int(floor(float(index) * float(route_segment_count) / float(_traffic_count))) % route_segment_count
		var target_index := (route_index + 1) % route_segment_count
		traffic_vehicle.set_meta("route_index", route_index)
		traffic_vehicle.set_meta("target_index", target_index)
		traffic_vehicle.set_meta("speed_mps", _rng.randf_range(TRAFFIC_SPEED_MIN, TRAFFIC_SPEED_MAX))
		traffic_vehicle.set_meta("seed", _seed + index)
		traffic_vehicle.position = _traffic_route[route_index] + Vector3(0.0, 0.45, 0.0)
		var car := BrickFactory.create_brick_car(TRAFFIC_COLORS[index % TRAFFIC_COLORS.size()], Color(0.10, 0.12, 0.15))
		car.name = "TrafficCarModel"
		car.scale = Vector3(0.88, 0.88, 0.88)
		traffic_vehicle.add_child(car)
		traffic_root.add_child(traffic_vehicle)
		_traffic.append(traffic_vehicle)

	_spawned = true
	set_process(true)
	return {
		"pedestrian_count": _pedestrians.size(),
		"traffic_count": _traffic.size(),
		"pedestrian_group": "souq_pedestrians",
		"traffic_group": "souq_traffic",
		"seed": _seed,
	}


func _process(delta: float) -> void:
	if not _spawned:
		return
	_update_traffic(maxf(delta, 0.0))
	_enforce_bounds()


func get_pedestrians() -> Array[Node3D]:
	return _pedestrians.duplicate()


func get_traffic() -> Array[Node3D]:
	return _traffic.duplicate()


func get_population_counts() -> Dictionary:
	return {
		"pedestrian_count": _pedestrians.size(),
		"traffic_count": _traffic.size(),
	}


func _pedestrian_spawn_position(index: int) -> Vector3:
	var lane := index % 3
	var row := index / 3
	var x := -43.0 + float(row) * 14.0 + _rng.randf_range(-1.5, 1.5)
	var z := 24.0 + float(lane) * 12.0 + _rng.randf_range(-1.25, 1.25)
	return _clamp_to_bounds(Vector3(x, 0.0, z))


func _update_traffic(delta: float) -> void:
	var route_segment_count := _traffic_route.size() - 1
	for traffic_vehicle: Node3D in _traffic:
		if not is_instance_valid(traffic_vehicle):
			continue
		var route_index := int(traffic_vehicle.get_meta("route_index", 0))
		var target_index := int(traffic_vehicle.get_meta("target_index", 1))
		var target := _traffic_route[target_index] + Vector3(0.0, 0.45, 0.0)
		var offset := target - traffic_vehicle.position
		offset.y = 0.0
		var distance := offset.length()
		if distance <= 1.25:
			route_index = target_index
			target_index = (target_index + 1) % route_segment_count
			traffic_vehicle.set_meta("route_index", route_index)
			traffic_vehicle.set_meta("target_index", target_index)
			target = _traffic_route[target_index] + Vector3(0.0, 0.45, 0.0)
			offset = target - traffic_vehicle.position
			offset.y = 0.0
			distance = offset.length()
		if distance > 0.001:
			var direction := offset / distance
			var speed := float(traffic_vehicle.get_meta("speed_mps", TRAFFIC_SPEED_MIN))
			traffic_vehicle.position += direction * minf(speed * delta, distance)
			traffic_vehicle.look_at(traffic_vehicle.position + direction, Vector3.UP)


func _enforce_bounds() -> void:
	for pedestrian: Node3D in _pedestrians:
		if is_instance_valid(pedestrian) and not _bounds.has_point(pedestrian.global_position):
			pedestrian.global_position = _clamp_to_bounds(pedestrian.global_position)
	for traffic_vehicle: Node3D in _traffic:
		if is_instance_valid(traffic_vehicle) and not _bounds.has_point(traffic_vehicle.global_position):
			traffic_vehicle.global_position = _clamp_to_bounds(traffic_vehicle.global_position)


func _clamp_to_bounds(position: Vector3) -> Vector3:
	var minimum := _bounds.position
	var maximum := _bounds.end
	return Vector3(
		clampf(position.x, minimum.x + 0.5, maximum.x - 0.5),
		maxf(position.y, 0.0),
		clampf(position.z, minimum.z + 0.5, maximum.z - 0.5)
	)
