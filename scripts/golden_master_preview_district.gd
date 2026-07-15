class_name GoldenMasterPreviewDistrict
extends Node3D

const MANIFEST_PATH := "res://asset_lab/runtime/golden_master_manifest.json"

var _manifest: Dictionary = {}
var _quality_profile: String = "balanced"
var _camera: Camera3D
var _status_label: Label
var _loaded_assets: int = 0
var _lod_instances: Array[GoldenMasterLODInstance] = []


func _ready() -> void:
	_quality_profile = GoldenMasterQuality.normalize_profile(_requested_quality_profile())
	_setup_environment()
	_setup_district_geometry()
	_camera = _create_camera()
	_setup_overlay()
	call_deferred("_load_manifest_assets")


func _requested_quality_profile() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--quality="):
			return argument.trim_prefix("--quality=")
	var environment_profile := OS.get_environment("BAHRAIN_BRICK_QUALITY")
	if not environment_profile.is_empty():
		return environment_profile
	return "balanced"


func _load_manifest_assets() -> void:
	var manifest_file := FileAccess.open(MANIFEST_PATH, FileAccess.READ)
	if manifest_file == null:
		_fail_preview("manifest could not be opened: %s" % MANIFEST_PATH)
		return
	var parsed = JSON.parse_string(manifest_file.get_as_text())
	if not parsed is Dictionary:
		_fail_preview("manifest is not a JSON object")
		return
	_manifest = parsed

	var assets: Array = _manifest.get("assets", [])
	var hysteresis_m := float(_manifest.get("hysteresis_m", 4.0))
	_loaded_assets = 0
	_lod_instances.clear()

	for record_value in assets:
		if not record_value is Dictionary:
			continue
		var record: Dictionary = record_value
		var controller := GoldenMasterLODInstance.new()
		controller.position = _vector3(record.get("position", []), Vector3.ZERO)
		controller.rotation_degrees.y = float(record.get("rotation_degrees", 0.0))
		controller.scale = _vector3(record.get("scale", []), Vector3.ONE)
		add_child(controller)
		if controller.configure(record, _quality_profile, _camera, hysteresis_m):
			_loaded_assets += 1
			_lod_instances.append(controller)
		else:
			controller.queue_free()

	_update_status()
	if _loaded_assets == assets.size() and _loaded_assets == 5:
		print("GOLDEN_MASTER_PREVIEW_READY profile=%s assets=%d" % [_quality_profile, _loaded_assets])
	else:
		_fail_preview("expected 5 assets, loaded %d of %d" % [_loaded_assets, assets.size()])


func _setup_environment() -> void:
	var world_environment := WorldEnvironment.new()
	world_environment.name = "PreviewWorldEnvironment"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.36, 0.62, 0.80)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.62, 0.72, 0.86)
	environment.ambient_light_energy = 0.78
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world_environment.environment = environment
	add_child(world_environment)

	var sun := DirectionalLight3D.new()
	sun.name = "PreviewSun"
	sun.light_color = Color(1.0, 0.89, 0.70)
	sun.light_energy = 1.25
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 180.0
	sun.rotation_degrees = Vector3(-42.0, -28.0, 0.0)
	add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.name = "PreviewFill"
	fill.light_color = Color(0.48, 0.62, 0.90)
	fill.light_energy = 0.34
	fill.shadow_enabled = false
	fill.rotation_degrees = Vector3(-25.0, 145.0, 0.0)
	add_child(fill)


func _setup_district_geometry() -> void:
	var ground := MeshInstance3D.new()
	ground.name = "DistrictGround"
	var ground_mesh := PlaneMesh.new()
	ground_mesh.size = Vector2(130.0, 130.0)
	ground.mesh = ground_mesh
	ground.material_override = _material(Color(0.74, 0.64, 0.46), 0.82, 0.0)
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ground)

	_add_box("MainBoulevard", Vector3(0.0, 0.06, 7.5), Vector3(74.0, 0.12, 13.0), Color(0.13, 0.15, 0.18), 0.92)
	_add_box("CrossStreet", Vector3(0.0, 0.07, 20.0), Vector3(13.0, 0.14, 62.0), Color(0.15, 0.17, 0.20), 0.92)
	_add_box("WaterfrontPromenade", Vector3(-16.0, 0.09, 36.0), Vector3(29.0, 0.18, 13.0), Color(0.72, 0.69, 0.59), 0.82)
	_add_box("HeroPlaza", Vector3(19.0, 0.10, 39.0), Vector3(31.0, 0.20, 18.0), Color(0.76, 0.73, 0.64), 0.78)

	var water := MeshInstance3D.new()
	water.name = "PreviewWater"
	var water_mesh := PlaneMesh.new()
	water_mesh.size = Vector2(80.0, 36.0)
	water.mesh = water_mesh
	water.position = Vector3(-31.0, -0.12, 55.0)
	var water_material := _material(Color(0.05, 0.39, 0.57), 0.24, 0.04)
	water_material.metallic_specular = 0.75
	water.material_override = water_material
	add_child(water)

	for x in [-31.0, -23.0, -15.0, -7.0, 1.0, 9.0, 17.0, 25.0, 33.0]:
		_add_box("RoadMarker_%s" % str(x), Vector3(x, 0.14, 7.5), Vector3(3.5, 0.03, 0.18), Color(0.95, 0.81, 0.28), 0.65)


func _create_camera() -> Camera3D:
	var camera := Camera3D.new()
	camera.name = "PreviewCamera"
	camera.fov = 52.0
	camera.near = 0.15
	camera.far = 300.0
	camera.position = Vector3(0.0, 35.0, 102.0)
	add_child(camera)
	camera.look_at(Vector3(0.0, 16.0, 19.0), Vector3.UP)
	camera.current = true
	return camera


func _setup_overlay() -> void:
	var overlay := CanvasLayer.new()
	overlay.name = "PreviewOverlay"
	add_child(overlay)

	var panel := ColorRect.new()
	panel.color = Color(0.025, 0.035, 0.055, 0.88)
	panel.position = Vector2(28.0, 24.0)
	panel.size = Vector2(700.0, 98.0)
	overlay.add_child(panel)

	var title := Label.new()
	title.text = "BAHRAIN BRICK • GOLDEN MASTER PREVIEW"
	title.position = Vector2(24.0, 14.0)
	title.size = Vector2(650.0, 38.0)
	title.add_theme_font_size_override("font_size", 25)
	title.add_theme_color_override("font_color", Color(1.0, 0.82, 0.30))
	panel.add_child(title)

	_status_label = Label.new()
	_status_label.text = "PROFILE: %s • LOADING ASSETS" % _quality_profile.to_upper()
	_status_label.position = Vector2(25.0, 54.0)
	_status_label.size = Vector2(650.0, 30.0)
	_status_label.add_theme_font_size_override("font_size", 17)
	_status_label.add_theme_color_override("font_color", Color(0.86, 0.91, 0.96))
	panel.add_child(_status_label)


func _update_status() -> void:
	if is_instance_valid(_status_label):
		_status_label.text = "PROFILE: %s • ASSETS: %d/5 • DYNAMIC LOD + 4 m HYSTERESIS" % [
			_quality_profile.to_upper(),
			_loaded_assets,
		]


func _fail_preview(reason: String) -> void:
	push_error("GOLDEN_MASTER_PREVIEW_FAILED %s" % reason)
	if is_instance_valid(_status_label):
		_status_label.text = "PREVIEW FAILED • %s" % reason


func _add_box(node_name: String, box_position: Vector3, box_size: Vector3, color: Color, roughness: float) -> void:
	var instance := MeshInstance3D.new()
	instance.name = node_name
	var mesh := BoxMesh.new()
	mesh.size = box_size
	instance.mesh = mesh
	instance.position = box_position
	instance.material_override = _material(color, roughness, 0.0)
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(instance)


func _material(color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material


func _vector3(value: Variant, fallback: Vector3) -> Vector3:
	if not value is Array:
		return fallback
	var components: Array = value
	if components.size() != 3:
		return fallback
	return Vector3(float(components[0]), float(components[1]), float(components[2]))


func get_loaded_asset_count() -> int:
	return _loaded_assets


func get_quality_profile() -> String:
	return _quality_profile


func get_lod_instances() -> Array[GoldenMasterLODInstance]:
	return _lod_instances
