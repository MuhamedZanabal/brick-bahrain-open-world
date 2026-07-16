extends SceneTree

const MANIFEST_PATH := "res://asset_lab/runtime/golden_master_manifest.json"
const PREVIEW_SCENE_PATH := "res://scenes/golden_master_preview_district.tscn"

var _failures: Array[String] = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_test_quality_policy()
	var manifest := _read_manifest()
	if manifest.is_empty():
		_finish()
		return
	_test_generated_resources(manifest)
	await _test_preview_scene()
	_finish()


func _test_quality_policy() -> void:
	_expect(GoldenMasterQuality.normalize_profile(" HIGH ") == "high", "profile normalization failed")
	_expect(GoldenMasterQuality.normalize_profile("unsupported") == "balanced", "invalid profile did not fall back")
	_expect(GoldenMasterQuality.select_lod(35.0, 0, 30.0, 70.0, 4.0) == 1, "LOD0 outward transition failed")
	_expect(GoldenMasterQuality.select_lod(32.0, 1, 30.0, 70.0, 4.0) == 1, "LOD0 hysteresis band failed")
	_expect(GoldenMasterQuality.select_lod(25.0, 1, 30.0, 70.0, 4.0) == 0, "LOD1 inward transition failed")
	_expect(GoldenMasterQuality.select_lod(75.0, 1, 30.0, 70.0, 4.0) == 2, "LOD1 outward transition failed")
	_expect(GoldenMasterQuality.select_lod(68.0, 2, 30.0, 70.0, 4.0) == 2, "LOD2 hysteresis band failed")
	_expect(GoldenMasterQuality.select_lod(65.0, 2, 30.0, 70.0, 4.0) == 1, "LOD2 inward transition failed")


func _read_manifest() -> Dictionary:
	var file := FileAccess.open(MANIFEST_PATH, FileAccess.READ)
	_expect(file != null, "manifest could not be opened")
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	_expect(parsed is Dictionary, "manifest is not a Dictionary")
	if parsed is Dictionary:
		var manifest: Dictionary = parsed
		_expect(manifest.get("schema_version", 0) == 1, "unexpected manifest schema")
		_expect((manifest.get("assets", []) as Array).size() == 5, "manifest does not contain five assets")
		return manifest
	return {}


func _test_generated_resources(manifest: Dictionary) -> void:
	var asset_count := 0
	var runtime_path_count := 0
	var unique_paths := {}
	for record_value in manifest.get("assets", []):
		if not record_value is Dictionary:
			_failures.append("manifest asset record is not a Dictionary")
			continue
		asset_count += 1
		var record: Dictionary = record_value
		var paths_by_profile: Dictionary = record.get("paths", {})
		for profile in manifest.get("profiles", []):
			var profile_name := str(profile)
			_expect(paths_by_profile.has(profile_name), "missing profile %s for %s" % [profile_name, record.get("asset_id", "unknown")])
			if not paths_by_profile.has(profile_name):
				continue
			var paths: Array = paths_by_profile[profile_name]
			_expect(paths.size() == 3, "profile %s does not have three LODs" % profile_name)
			for resource_value in paths:
				var resource_path := str(resource_value)
				runtime_path_count += 1
				unique_paths[resource_path] = true
				_expect(ResourceLoader.exists(resource_path), "missing generated GLB: %s" % resource_path)
				if not ResourceLoader.exists(resource_path):
					continue
				var packed := load(resource_path) as PackedScene
				_expect(packed != null, "generated GLB is not a PackedScene: %s" % resource_path)
				if packed != null:
					var instance := packed.instantiate() as Node3D
					_expect(instance != null, "generated GLB did not instantiate: %s" % resource_path)
					if instance != null:
						instance.free()
	_expect(asset_count == 5, "runtime asset count was not five")
	_expect(runtime_path_count == 45, "runtime path count was not 45")
	_expect(unique_paths.size() == 45, "runtime paths are not unique")


func _test_preview_scene() -> void:
	_expect(ResourceLoader.exists(PREVIEW_SCENE_PATH), "preview scene is missing")
	if not ResourceLoader.exists(PREVIEW_SCENE_PATH):
		return
	var packed := load(PREVIEW_SCENE_PATH) as PackedScene
	_expect(packed != null, "preview scene did not load as PackedScene")
	if packed == null:
		return
	var preview := packed.instantiate()
	root.add_child(preview)
	for _frame in range(6):
		await process_frame
	_expect(preview.has_method("get_loaded_asset_count"), "preview scene lacks runtime inspection method")
	if preview.has_method("get_loaded_asset_count"):
		_expect(int(preview.call("get_loaded_asset_count")) == 5, "preview did not load five golden masters")
	_expect(preview.has_method("get_quality_profile"), "preview scene lacks quality inspection method")
	if preview.has_method("get_quality_profile"):
		_expect(str(preview.call("get_quality_profile")) == "balanced", "preview did not default to balanced quality")
	preview.free()


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


func _finish() -> void:
	if _failures.is_empty():
		print("GOLDEN_MASTER_RUNTIME_TEST_PASS assets=5 resources=45 profile=balanced")
		quit(0)
		return
	for failure in _failures:
		push_error("GOLDEN_MASTER_RUNTIME_TEST_FAILURE %s" % failure)
	print("GOLDEN_MASTER_RUNTIME_TEST_FAIL count=%d" % _failures.size())
	quit(1)
