extends SceneTree

const LoaderScript := preload("res://scripts/manama_souq_layout_loader.gd")
const LAYOUT_PATH := "res://asset_lab/runtime/manama_souq_layout_v1.json"
const FULL_MANIFEST_PATH := "res://asset_lab/runtime/full_asset_matrix_manifest.json"


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var root_node := Node3D.new()
	root_node.name = "ManamaSouqLayoutRuntimeRoot"
	root.add_child(root_node)
	var camera := Camera3D.new()
	camera.name = "RuntimeCamera"
	camera.current = true
	camera.position = Vector3(0.0, 48.0, 95.0)
	root_node.add_child(camera)

	var loader: ManamaSouqLayoutLoader = LoaderScript.new()
	var layout := loader.load_layout(LAYOUT_PATH, FULL_MANIFEST_PATH)
	_require(not layout.is_empty(), "layout failed to load: %s" % loader.last_error)
	var result := loader.instantiate_layout(root_node, camera, "balanced")
	_require(not result.is_empty(), "layout failed to instantiate: %s" % loader.last_error)
	_require(int(result.get("placement_count", -1)) == 35, "placement_count mismatch: %s" % result)
	_require(int(result.get("architecture_count", -1)) == 31, "architecture_count mismatch: %s" % result)
	_require(int(result.get("commercial_count", -1)) == 4, "commercial_count mismatch: %s" % result)
	var zone_counts := result.get("zone_counts", {}) as Dictionary
	for zone_name in ["cafe_start", "souq_lane", "vehicle_route", "waterfront_delivery"]:
		_require(root_node.get_node_or_null(zone_name) != null, "zone missing: %s" % zone_name)
		_require(zone_counts.has(zone_name), "zone count missing: %s" % zone_name)
	_require(int(zone_counts.get("cafe_start", -1)) == 5, "cafe_start count mismatch")
	_require(int(zone_counts.get("souq_lane", -1)) == 23, "souq_lane count mismatch")
	_require(int(zone_counts.get("vehicle_route", -1)) == 0, "vehicle_route count mismatch")
	_require(int(zone_counts.get("waterfront_delivery", -1)) == 7, "waterfront_delivery count mismatch")
	_require((result.get("loaded_asset_ids", []) as Array).size() == 35, "loaded asset ID count mismatch")
	_require(loader.get_mission_points().size() == 5, "mission point count mismatch")
	_require(loader.get_traffic_route().size() == 13, "traffic route count mismatch")
	var population := loader.get_population_contract()
	_require(int(population.get("pedestrians", -1)) == 12, "pedestrian contract mismatch")
	_require(int(population.get("traffic", -1)) == 6, "traffic contract mismatch")
	var bounds := loader.get_bounds()
	_require(is_equal_approx(bounds.size.x, 220.0) and is_equal_approx(bounds.size.z, 220.0), "layout bounds mismatch")

	print("MANAMA_SOUQ_LAYOUT_RUNTIME_PASS placements=35 architecture=31 commercial=4")
	quit(0)


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
