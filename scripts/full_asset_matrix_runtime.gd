extends "res://scripts/asset_lab_runtime.gd"

const FULL_MATRIX_MANIFEST := "res://asset_lab/runtime/full_asset_matrix_manifest.json"

var _active_profile: String = "balanced"
var _manifest: Dictionary = {}


func _ready() -> void:
	for district_name in DISTRICTS:
		var district := Node3D.new()
		district.name = district_name
		add_child(district)
	_manifest = _load_full_matrix_manifest()
	_active_profile = GoldenMasterQuality.normalize_profile(
		str(ProjectSettings.get_setting("bahrain_brick/asset_quality", "balanced"))
	)
	_instantiate_architecture_matrix()
	_instantiate_commercial_matrix()
	_instantiate_family(get_node("VillaDistrict") as Node3D, VILLA_ASSETS, Vector3(-92.0, 0.0, 74.0))
	_instantiate_family(get_node("RoadNetwork") as Node3D, ROAD_ASSETS, _district_origin("RoadNetwork"))
	_instantiate_family(get_node("StreetPropSpawner") as Node3D, STREET_PROP_ASSETS, _district_origin("StreetPropSpawner"))
	_instantiate_clean_room_assets()
	_load_mobile_shader()
	print("BAHRAIN_BRICK_FULL_MATRIX_READY profile=%s architecture=%d commercial=%d" % [
		_active_profile,
		int(_manifest.get("architecture_asset_count", 0)),
		int(_manifest.get("commercial_asset_count", 0)),
	])
	print("BAHRAIN BRICK GAME ASSET LAB READY")


func _load_full_matrix_manifest() -> Dictionary:
	if not FileAccess.file_exists(FULL_MATRIX_MANIFEST):
		push_error("Full asset matrix manifest missing: %s" % FULL_MATRIX_MANIFEST)
		return {}
	var file := FileAccess.open(FULL_MATRIX_MANIFEST, FileAccess.READ)
	if file == null:
		push_error("Full asset matrix manifest could not be opened")
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_error("Full asset matrix manifest is invalid JSON")
		return {}
	var manifest := parsed as Dictionary
	if int(manifest.get("architecture_asset_count", -1)) != 48:
		push_error("Full asset matrix architecture count is not 48")
		return {}
	if int(manifest.get("commercial_asset_count", -1)) != 4:
		push_error("Full asset matrix commercial count is not 4")
		return {}
	return manifest


func _instantiate_architecture_matrix() -> void:
	var camera := get_viewport().get_camera_3d()
	var hysteresis := float(_manifest.get("lod_hysteresis_m", 4.0))
	var records: Array = _manifest.get("assets", [])
	for index in range(records.size()):
		var record: Dictionary = records[index]
		var family := str(record.get("family", ""))
		var district_name := _district_for_family(family)
		var district := get_node(district_name) as Node3D
		var lod_instance := GoldenMasterLODInstance.new()
		if not lod_instance.configure(record, _active_profile, camera, hysteresis):
			push_error("Full matrix runtime failed for %s" % str(record.get("asset_id", "unknown")))
			continue
		var column := index % 8
		var row := index / 8
		lod_instance.position = _district_origin(district_name) + Vector3(column * 7.5, 0.0, row * 9.0)
		lod_instance.set_meta("full_matrix", true)
		district.add_child(lod_instance)


func _instantiate_commercial_matrix() -> void:
	var records: Array = _manifest.get("commercial", [])
	var district := get_node("CommercialDistrict") as Node3D
	for index in range(records.size()):
		var record: Dictionary = records[index]
		_instantiate_verified_scene(
			district,
			str(record.get("path", "")),
			_district_origin("CommercialDistrict"),
			index
		)


func _district_for_family(family: String) -> String:
	match family:
		"traditional":
			return "TraditionalDistrict"
		"souq":
			return "SouqDistrict"
		"waterfront":
			return "WaterfrontDistrict"
		_:
			push_error("Unknown full-matrix family: %s" % family)
			return "TraditionalDistrict"
