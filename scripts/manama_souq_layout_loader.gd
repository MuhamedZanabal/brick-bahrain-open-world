extends RefCounted
class_name ManamaSouqLayoutLoader

const EXPECTED_SCHEMA := "bahrain-brick-manama-souq-layout-v1"
const SUPPORTED_SCHEMA_VERSION := 1
const REQUIRED_ZONES := ["cafe_start", "souq_lane", "vehicle_route", "waterfront_delivery"]
const REQUIRED_FAMILY_COUNTS := {
	"traditional": 8,
	"souq": 12,
	"waterfront": 5,
	"commercial": 4,
}

var _layout: Dictionary = {}
var _full_manifest: Dictionary = {}
var _architecture_by_id: Dictionary = {}
var _commercial_by_id: Dictionary = {}
var _hysteresis_m: float = 4.0
var _loaded: bool = false
var last_error: String = ""


func load_layout(path: String, full_manifest_path: String) -> Dictionary:
	_reset()
	var layout_variant: Variant = _read_json(path)
	if not layout_variant is Dictionary:
		return _reject("layout JSON is missing or invalid")
	var manifest_variant: Variant = _read_json(full_manifest_path)
	if not manifest_variant is Dictionary:
		return _reject("full matrix manifest is missing or invalid")
	_layout = layout_variant as Dictionary
	_full_manifest = manifest_variant as Dictionary
	if not _validate_layout_header():
		return {}
	if not _index_full_manifest():
		return {}
	if not _validate_placements():
		return {}
	_hysteresis_m = maxf(float(_full_manifest.get("lod_hysteresis_m", 4.0)), 0.0)
	_loaded = true
	return _layout.duplicate(true)


func instantiate_layout(root: Node3D, camera: Camera3D, profile: String) -> Dictionary:
	if not _loaded or root == null or camera == null:
		last_error = "layout must be loaded before instantiation"
		return {}
	var normalized_profile: String = GoldenMasterQuality.normalize_profile(profile)
	var zones: Dictionary = _ensure_zones(root)
	var placements: Array = _layout.get("placements", [])
	var sorted_placements: Array = placements.duplicate(true)
	sorted_placements.sort_custom(
		func(a: Dictionary, b: Dictionary) -> bool:
			return str(a.get("placement_id", "")) < str(b.get("placement_id", ""))
	)
	var architecture_count: int = 0
	var commercial_count: int = 0
	var zone_counts: Dictionary = {}
	var loaded_asset_ids: Array[String] = []
	for zone_name: String in REQUIRED_ZONES:
		zone_counts[zone_name] = 0
	for placement_variant: Variant in sorted_placements:
		var placement: Dictionary = placement_variant as Dictionary
		var family: String = str(placement.get("family", ""))
		var asset_id: String = str(placement.get("asset_id", ""))
		var zone_name: String = str(placement.get("zone", ""))
		var zone: Node3D = zones.get(zone_name) as Node3D
		if zone == null:
			last_error = "required zone missing during instantiation: %s" % zone_name
			return {}
		var instance: Node3D
		if family == "commercial":
			var commercial_record: Dictionary = _commercial_by_id.get(asset_id, {}) as Dictionary
			var commercial_path: String = str(commercial_record.get("path", ""))
			if not ResourceLoader.exists(commercial_path, "PackedScene"):
				last_error = "commercial scene missing: %s" % commercial_path
				return {}
			var packed: PackedScene = ResourceLoader.load(commercial_path, "PackedScene") as PackedScene
			if packed == null:
				last_error = "commercial scene is not PackedScene: %s" % commercial_path
				return {}
			instance = packed.instantiate() as Node3D
			if instance == null:
				last_error = "commercial scene root is not Node3D: %s" % commercial_path
				return {}
			commercial_count += 1
		else:
			var manifest_record: Dictionary = _architecture_by_id.get(asset_id, {}) as Dictionary
			var lod_instance: GoldenMasterLODInstance = GoldenMasterLODInstance.new()
			if not lod_instance.configure(manifest_record, normalized_profile, camera, _hysteresis_m):
				last_error = "LOD configuration failed for %s" % asset_id
				return {}
			instance = lod_instance
			architecture_count += 1
		_apply_placement(instance, placement)
		instance.set_meta("placement_id", str(placement.get("placement_id", "")))
		instance.set_meta("manama_souq_zone", zone_name)
		instance.set_meta("source_asset_id", asset_id)
		instance.set_meta("asset_profile", normalized_profile)
		zone.add_child(instance)
		zone_counts[zone_name] = int(zone_counts.get(zone_name, 0)) + 1
		loaded_asset_ids.append(asset_id)
	return {
		"placement_count": architecture_count + commercial_count,
		"architecture_count": architecture_count,
		"commercial_count": commercial_count,
		"zone_counts": zone_counts,
		"loaded_asset_ids": loaded_asset_ids,
		"profile": normalized_profile,
	}


func get_mission_points() -> Dictionary:
	var result: Dictionary = {}
	var points: Dictionary = _layout.get("mission_points", {}) as Dictionary
	for key: String in points:
		result[key] = _vector3(points[key])
	return result


func get_traffic_route() -> Array[Vector3]:
	var result: Array[Vector3] = []
	var route: Array = _layout.get("traffic_route", [])
	for value: Variant in route:
		result.append(_vector3(value))
	return result


func get_population_contract() -> Dictionary:
	return (_layout.get("population", {}) as Dictionary).duplicate(true)


func get_bounds() -> AABB:
	var bounds: Dictionary = _layout.get("bounds", {}) as Dictionary
	var minimum: Vector3 = Vector3(
		float(bounds.get("min_x", -110.0)),
		-4.0,
		float(bounds.get("min_z", -110.0))
	)
	return AABB(minimum, Vector3(220.0, 80.0, 220.0))


func _validate_layout_header() -> bool:
	if str(_layout.get("schema", "")) != EXPECTED_SCHEMA or int(_layout.get("schema_version", -1)) != SUPPORTED_SCHEMA_VERSION:
		_reject("unsupported layout schema")
		return false
	if str(_layout.get("parent_authority", "")) != "fc8f00182f97c39015610d6603fa7c9c44364c5d":
		_reject("layout parent authority mismatch")
		return false
	var bounds: Dictionary = _layout.get("bounds", {}) as Dictionary
	if float(bounds.get("max_x", 0.0)) - float(bounds.get("min_x", 0.0)) != 220.0 or float(bounds.get("max_z", 0.0)) - float(bounds.get("min_z", 0.0)) != 220.0:
		_reject("layout bounds are not 220m x 220m")
		return false
	var zones: Array = _layout.get("zones", [])
	for required_zone: String in REQUIRED_ZONES:
		if not required_zone in zones:
			_reject("required zone missing: %s" % required_zone)
			return false
	return true


func _index_full_manifest() -> bool:
	var architecture: Array = _full_manifest.get("assets", [])
	var commercial: Array = _full_manifest.get("commercial", [])
	if int(_full_manifest.get("architecture_asset_count", -1)) != 48 or architecture.size() != 48:
		_reject("full matrix architecture authority is not 48")
		return false
	if int(_full_manifest.get("commercial_asset_count", -1)) != 4 or commercial.size() != 4:
		_reject("full matrix commercial authority is not 4")
		return false
	for record_variant: Variant in architecture:
		var record: Dictionary = record_variant as Dictionary
		var asset_id: String = str(record.get("asset_id", ""))
		if asset_id.is_empty() or _architecture_by_id.has(asset_id):
			_reject("duplicate or empty architecture asset ID")
			return false
		_architecture_by_id[asset_id] = record
	for record_variant: Variant in commercial:
		var record: Dictionary = record_variant as Dictionary
		var asset_id: String = str(record.get("asset_id", ""))
		if asset_id.is_empty() or _commercial_by_id.has(asset_id):
			_reject("duplicate or empty commercial asset ID")
			return false
		_commercial_by_id[asset_id] = record
	return true


func _validate_placements() -> bool:
	var placements: Array = _layout.get("placements", [])
	var seen: Dictionary = {}
	var counts: Dictionary = {}
	var commercial_ids: Dictionary = {}
	var bounds: Dictionary = _layout.get("bounds", {}) as Dictionary
	for placement_variant: Variant in placements:
		if not placement_variant is Dictionary:
			_reject("placement record is not a Dictionary")
			return false
		var placement: Dictionary = placement_variant as Dictionary
		var placement_id: String = str(placement.get("placement_id", ""))
		if placement_id.is_empty() or seen.has(placement_id):
			_reject("duplicate placement_id: %s" % placement_id)
			return false
		seen[placement_id] = true
		var family: String = str(placement.get("family", ""))
		var asset_id: String = str(placement.get("asset_id", ""))
		if family == "commercial":
			if not _commercial_by_id.has(asset_id):
				_reject("asset missing from full matrix manifest: %s" % asset_id)
				return false
			commercial_ids[asset_id] = true
		else:
			if not _architecture_by_id.has(asset_id):
				_reject("asset missing from full matrix manifest: %s" % asset_id)
				return false
			var record: Dictionary = _architecture_by_id[asset_id] as Dictionary
			if str(record.get("family", "")) != family:
				_reject("placement family does not match full matrix manifest: %s" % asset_id)
				return false
		var zone_name: String = str(placement.get("zone", ""))
		if not zone_name in REQUIRED_ZONES:
			_reject("required zone missing from placement: %s" % zone_name)
			return false
		var position: Vector3 = _vector3(placement.get("position", []))
		if position.x < float(bounds.get("min_x", 0.0)) or position.x > float(bounds.get("max_x", 0.0)) or position.z < float(bounds.get("min_z", 0.0)) or position.z > float(bounds.get("max_z", 0.0)):
			_reject("placement outside layout bounds: %s" % placement_id)
			return false
		counts[family] = int(counts.get(family, 0)) + 1
	for family: String in REQUIRED_FAMILY_COUNTS:
		if int(counts.get(family, 0)) < int(REQUIRED_FAMILY_COUNTS[family]):
			_reject("required family count not met: %s" % family)
			return false
	if commercial_ids.size() != 4:
		_reject("commercial asset closure is not four")
		return false
	return true


func _ensure_zones(root: Node3D) -> Dictionary:
	var zones: Dictionary = {}
	for zone_name: String in REQUIRED_ZONES:
		var node: Node3D = root.get_node_or_null(zone_name) as Node3D
		if node == null:
			node = Node3D.new()
			node.name = zone_name
			root.add_child(node)
		zones[zone_name] = node
	return zones


func _apply_placement(instance: Node3D, placement: Dictionary) -> void:
	instance.name = str(placement.get("placement_id", "placement"))
	instance.position = _vector3(placement.get("position", []))
	instance.rotation_degrees = _vector3(placement.get("rotation_degrees", []))
	instance.scale = _vector3(placement.get("scale", [1.0, 1.0, 1.0]))


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		last_error = "file missing: %s" % path
		return null
	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		last_error = "file could not be opened: %s" % path
		return null
	return JSON.parse_string(file.get_as_text())


func _vector3(value: Variant) -> Vector3:
	if not value is Array or (value as Array).size() != 3:
		return Vector3.ZERO
	var parts: Array = value as Array
	return Vector3(float(parts[0]), float(parts[1]), float(parts[2]))


func _reject(message: String) -> Dictionary:
	last_error = message
	push_error("ManamaSouqLayoutLoader: %s" % message)
	_loaded = false
	return {}


func _reset() -> void:
	_layout.clear()
	_full_manifest.clear()
	_architecture_by_id.clear()
	_commercial_by_id.clear()
	_hysteresis_m = 4.0
	_loaded = false
	last_error = ""
