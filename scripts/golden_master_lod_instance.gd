class_name GoldenMasterLODInstance
extends Node3D

signal lod_changed(asset_id: String, previous_lod: int, active_lod: int)

var asset_id: String = ""
var family: String = ""
var quality_profile: String = "balanced"
var lod0_max_m: float = 30.0
var lod1_max_m: float = 70.0
var hysteresis_m: float = 4.0

var _camera: Camera3D
var _lod_scenes: Array[PackedScene] = []
var _active_instance: Node3D
var _active_lod: int = -1


func configure(record: Dictionary, requested_profile: String, camera: Camera3D, default_hysteresis_m: float) -> bool:
	asset_id = str(record.get("asset_id", ""))
	family = str(record.get("family", ""))
	quality_profile = GoldenMasterQuality.normalize_profile(requested_profile)
	_camera = camera
	lod0_max_m = float(record.get("lod0_max_m", 30.0))
	lod1_max_m = float(record.get("lod1_max_m", 70.0))
	hysteresis_m = maxf(default_hysteresis_m, 0.0)

	if asset_id.is_empty() or family.is_empty():
		push_error("GoldenMasterLODInstance: manifest record is missing asset_id or family")
		return false

	var paths_by_profile: Dictionary = record.get("paths", {})
	if not paths_by_profile.has(quality_profile):
		push_error("GoldenMasterLODInstance: profile '%s' missing for %s" % [quality_profile, asset_id])
		return false

	var runtime_paths: Array = paths_by_profile[quality_profile]
	if runtime_paths.size() != 3:
		push_error("GoldenMasterLODInstance: expected three LOD paths for %s/%s" % [asset_id, quality_profile])
		return false

	_lod_scenes.clear()
	for lod in range(3):
		var resource_path := str(runtime_paths[lod])
		if not ResourceLoader.exists(resource_path):
			push_error("GoldenMasterLODInstance: missing runtime resource %s" % resource_path)
			_lod_scenes.clear()
			return false
		var scene := load(resource_path) as PackedScene
		if scene == null:
			push_error("GoldenMasterLODInstance: resource is not a PackedScene: %s" % resource_path)
			_lod_scenes.clear()
			return false
		_lod_scenes.append(scene)

	name = asset_id
	set_process(true)
	_switch_lod(0)
	return true


func _process(_delta: float) -> void:
	if _lod_scenes.size() != 3:
		return
	if not is_instance_valid(_camera):
		_camera = get_viewport().get_camera_3d()
	if not is_instance_valid(_camera):
		return

	var distance_m := global_position.distance_to(_camera.global_position)
	var target_lod := GoldenMasterQuality.select_lod(
		distance_m,
		maxi(_active_lod, 0),
		lod0_max_m,
		lod1_max_m,
		hysteresis_m
	)
	if target_lod != _active_lod:
		_switch_lod(target_lod)


func _switch_lod(target_lod: int) -> void:
	if _lod_scenes.size() != 3:
		return
	var normalized_lod := clampi(target_lod, 0, 2)
	if normalized_lod == _active_lod and is_instance_valid(_active_instance):
		return

	var previous_lod := _active_lod
	if is_instance_valid(_active_instance):
		_active_instance.free()
		_active_instance = null

	var instance := _lod_scenes[normalized_lod].instantiate() as Node3D
	if instance == null:
		push_error("GoldenMasterLODInstance: failed to instantiate %s LOD%d" % [asset_id, normalized_lod])
		return
	instance.name = "%s_LOD%d" % [asset_id, normalized_lod]
	instance.transform = Transform3D.IDENTITY
	add_child(instance)
	_active_instance = instance
	_active_lod = normalized_lod
	lod_changed.emit(asset_id, previous_lod, _active_lod)


func get_active_lod() -> int:
	return _active_lod


func get_loaded_lod_count() -> int:
	return _lod_scenes.size()


func force_lod_for_test(target_lod: int) -> void:
	_switch_lod(target_lod)
