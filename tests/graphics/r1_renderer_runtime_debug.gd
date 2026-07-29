extends Node

const SliceScene := preload("res://scenes/manama_souq_vertical_slice.tscn")
const MODE_PATH := "user://r1_mode.txt"
const MATERIAL_REPORT_PATH := "user://r1_material_inventory.json"
const MOBILE_PROGRESS_PATH := "user://r1_mobile_progress.json"
const SCENE_TREE_PATH := "user://r1_scene_tree.json"
const WAIT_INVENTORY_PATH := "user://r1_wait_inventory.json"
const GL_MODES := [
	"gl_unshaded",
	"gl_empty",
	"gl_sun",
	"gl_sun_shadow",
	"gl_two_directional",
	"gl_two_directional_shadow",
	"gl_production",
]
const MOBILE_MODES := ["mobile_baseline", "mobile_render_disabled_control"]
const CAMERA_POSITION := Vector3(-104.0, 48.0, 104.0)
const CAMERA_TARGET := Vector3(-4.0, 4.0, -4.0)

var _mode := ""
var _slice: ManamaSouqVerticalSlice
var _started_usec := 0


func _ready() -> void:
	_started_usec = Time.get_ticks_usec()
	_mode = _read_mode()
	print("R1_MODE_SELECTED mode=%s" % _mode)
	call_deferred("_run")


func _read_mode() -> String:
	if not FileAccess.file_exists(MODE_PATH):
		return "mobile_baseline"
	var file := FileAccess.open(MODE_PATH, FileAccess.READ)
	if file == null:
		return "mobile_baseline"
	return file.get_as_text().strip_edges()


func _run() -> void:
	if _mode in GL_MODES:
		await _run_gl_mode()
	elif _mode in MOBILE_MODES:
		await _run_mobile_mode()
	else:
		_fail("unknown mode: %s" % _mode)


func _run_gl_mode() -> void:
	print("R1_GL_SCENARIO_BEGIN mode=%s" % _mode)
	if _mode == "gl_production":
		await _instantiate_production_slice()
		if _slice == null:
			return
		_write_material_inventory(_slice)
	else:
		_build_minimal_gl_scene(_mode)
	for frame in range(1, 121):
		await get_tree().process_frame
		if frame % 30 == 0:
			print("R1_GL_HEARTBEAT mode=%s frame=%d process=%d physics=%d drawn=%d wall_ms=%d" % [
				_mode,
				frame,
				Engine.get_process_frames(),
				Engine.get_physics_frames(),
				Engine.get_frames_drawn(),
				_elapsed_ms(),
			])
	await RenderingServer.frame_post_draw
	print("R1_GL_SCENARIO_COMPLETE mode=%s frames=120" % _mode)


func _build_minimal_gl_scene(mode: String) -> void:
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.18, 0.26, 0.38, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.8, 0.8, 0.8, 1.0)
	environment.ambient_light_energy = 0.5
	environment_node.environment = environment
	add_child(environment_node)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 2.5, 6.0)
	camera.look_at(Vector3.ZERO, Vector3.UP)
	camera.current = true
	add_child(camera)

	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(2.0, 2.0, 2.0)
	mesh_instance.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.72, 0.28, 0.14, 1.0)
	material.roughness = 0.55
	if mode == "gl_unshaded":
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mesh_instance.material_override = material
	add_child(mesh_instance)

	if mode in ["gl_sun", "gl_sun_shadow", "gl_two_directional", "gl_two_directional_shadow"]:
		_add_directional_light("Sun", Vector3(-48.0, -32.0, 0.0), 1.28, mode in ["gl_sun_shadow", "gl_two_directional_shadow"])
	if mode in ["gl_two_directional", "gl_two_directional_shadow"]:
		_add_directional_light("Fill", Vector3(-25.0, 145.0, 0.0), 0.30, false)


func _add_directional_light(name_value: String, rotation_value: Vector3, energy: float, shadows: bool) -> void:
	var light := DirectionalLight3D.new()
	light.name = name_value
	light.rotation_degrees = rotation_value
	light.light_energy = energy
	light.shadow_enabled = shadows
	add_child(light)


func _instantiate_production_slice() -> void:
	_slice = SliceScene.instantiate() as ManamaSouqVerticalSlice
	if _slice == null:
		_fail("production slice root type mismatch")
		return
	add_child(_slice)
	for _frame in range(1800):
		if _slice.is_slice_ready():
			break
		await get_tree().process_frame
	if not _slice.is_slice_ready():
		_fail("production slice did not reach readiness")
		return
	var camera := Camera3D.new()
	camera.name = "R1EvidenceCamera"
	camera.fov = 62.0
	camera.near = 0.1
	camera.far = 500.0
	add_child(camera)
	camera.global_position = CAMERA_POSITION
	camera.look_at(CAMERA_TARGET, Vector3.UP)
	camera.current = true
	print("R1_PRODUCTION_SCENE_READY nodes=%d" % _count_nodes(_slice))


func _write_material_inventory(root: Node) -> void:
	var records: Array[Dictionary] = []
	_collect_materials(root, records)
	var signatures: Dictionary = {}
	var user_shader_count := 0
	for record: Dictionary in records:
		var signature := str(record.get("signature", "unknown"))
		signatures[signature] = int(signatures.get(signature, 0)) + 1
		if bool(record.get("shader_material", false)):
			user_shader_count += 1
	var payload := {
		"schema_version": 1,
		"mode": _mode,
		"material_records": records,
		"signature_counts": signatures,
		"material_count": records.size(),
		"user_authored_shader_count": user_shader_count,
	}
	_write_json(MATERIAL_REPORT_PATH, payload)
	print("R1_GL_MATERIAL_INVENTORY_WRITTEN count=%d path=%s" % [records.size(), MATERIAL_REPORT_PATH])


func _collect_materials(node: Node, records: Array[Dictionary]) -> void:
	if node is MeshInstance3D:
		var mesh_instance := node as MeshInstance3D
		var mesh := mesh_instance.mesh
		if mesh != null:
			for surface in range(mesh.get_surface_count()):
				var material := mesh_instance.get_active_material(surface)
				if material != null:
					records.append(_material_record(mesh_instance, surface, material))
	for child: Node in node.get_children():
		_collect_materials(child, records)


func _material_record(mesh_instance: MeshInstance3D, surface: int, material: Material) -> Dictionary:
	var properties := {}
	var names := [
		"transparency", "shading_mode", "vertex_color_use_as_albedo", "albedo_texture",
		"normal_enabled", "orm_texture", "emission_enabled", "emission_texture",
		"heightmap_enabled", "subsurf_scatter_enabled", "clearcoat_enabled", "rim_enabled",
		"anisotropy_enabled", "detail_enabled", "billboard_mode", "cull_mode",
	]
	var available := {}
	for info: Dictionary in material.get_property_list():
		available[str(info.get("name", ""))] = true
	for name_value: String in names:
		if available.has(name_value):
			var value = material.get(name_value)
			properties[name_value] = str(value) if value is Resource else value
	var shader_material := material is ShaderMaterial
	var shader_code := ""
	if shader_material:
		var shader := (material as ShaderMaterial).shader
		if shader != null:
			shader_code = shader.code
	var signature := "%s:%s" % [material.get_class(), JSON.stringify(properties)]
	return {
		"node_path": str(mesh_instance.get_path()),
		"surface": surface,
		"material_class": material.get_class(),
		"resource_path": material.resource_path,
		"resource_name": material.resource_name,
		"shader_material": shader_material,
		"shader_code": shader_code,
		"properties": properties,
		"signature": signature,
	}


func _run_mobile_mode() -> void:
	await _instantiate_production_slice()
	if _slice == null:
		return
	_write_scene_tree_inventory(_slice)
	_write_wait_inventory()
	var render_disabled := _mode == "mobile_render_disabled_control"
	if render_disabled:
		RenderingServer.render_loop_enabled = false
	print("R1_MOBILE_BEGIN mode=%s render_loop=%s" % [_mode, str(RenderingServer.render_loop_enabled)])
	var progress: Array[Dictionary] = []
	var initial := _progress_record(0, 0.0)
	progress.append(initial)
	_write_json(MOBILE_PROGRESS_PATH, {"schema_version": 1, "mode": _mode, "records": progress, "complete": false})
	var previous_usec := Time.get_ticks_usec()
	for local_frame in range(1, 301):
		await get_tree().process_frame
		var now_usec := Time.get_ticks_usec()
		var record := _progress_record(local_frame, float(now_usec - previous_usec) / 1000.0)
		previous_usec = now_usec
		progress.append(record)
		if local_frame % 10 == 0:
			print("R1_MOBILE_HEARTBEAT mode=%s local_frame=%d process=%d physics=%d drawn=%d wall_ms=%d frame_wait_ms=%.3f render_loop=%s" % [
				_mode,
				local_frame,
				int(record.get("process_frames", 0)),
				int(record.get("physics_frames", 0)),
				int(record.get("frames_drawn", 0)),
				int(record.get("wall_ms", 0)),
				float(record.get("frame_wait_ms", 0.0)),
				str(record.get("render_loop_enabled", true)),
			])
			_write_json(MOBILE_PROGRESS_PATH, {"schema_version": 1, "mode": _mode, "records": progress, "complete": false})
	if render_disabled:
		RenderingServer.render_loop_enabled = true
		for _frame in range(5):
			await get_tree().process_frame
		print("R1_MOBILE_CONTROL_COMPLETE frames=300 wall_ms=%d" % _elapsed_ms())
	else:
		await RenderingServer.frame_post_draw
		print("R1_MOBILE_CAPTURE_FRAME frame=300 wall_ms=%d" % _elapsed_ms())
	_write_json(MOBILE_PROGRESS_PATH, {"schema_version": 1, "mode": _mode, "records": progress, "complete": true})


func _progress_record(local_frame: int, frame_wait_ms: float) -> Dictionary:
	return {
		"mode": _mode,
		"local_frame": local_frame,
		"process_frames": Engine.get_process_frames(),
		"physics_frames": Engine.get_physics_frames(),
		"frames_drawn": Engine.get_frames_drawn(),
		"wall_ms": _elapsed_ms(),
		"frame_wait_ms": frame_wait_ms,
		"render_loop_enabled": RenderingServer.render_loop_enabled,
		"scene_nodes": _count_nodes(_slice),
		"await_site": "SceneTree.process_frame",
		"objects": int(Performance.get_monitor(Performance.OBJECT_COUNT)),
		"nodes": int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
		"resources": int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT)),
		"draw_calls": int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		"primitives": int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
	}


func _write_scene_tree_inventory(root: Node) -> void:
	var records: Array[Dictionary] = []
	_collect_scene_tree(root, records)
	_write_json(SCENE_TREE_PATH, {"schema_version": 1, "nodes": records, "node_count": records.size()})
	print("R1_MOBILE_SCENE_TREE_WRITTEN count=%d" % records.size())


func _collect_scene_tree(node: Node, records: Array[Dictionary]) -> void:
	var script_path := ""
	var script = node.get_script()
	if script is Script:
		script_path = (script as Script).resource_path
	var signal_connections := 0
	for signal_info: Dictionary in node.get_signal_list():
		var signal_name := StringName(str(signal_info.get("name", "")))
		signal_connections += node.get_signal_connection_list(signal_name).size()
	records.append({
		"path": str(node.get_path()),
		"class": node.get_class(),
		"script": script_path,
		"process_mode": node.process_mode,
		"process_priority": node.process_priority,
		"can_process": node.can_process(),
		"signal_connection_count": signal_connections,
	})
	for child: Node in node.get_children():
		_collect_scene_tree(child, records)


func _write_wait_inventory() -> void:
	_write_json(WAIT_INVENTORY_PATH, {
		"schema_version": 1,
		"harness_coroutine_wait": "SceneTree.process_frame",
		"harness_async_resource_requests": [],
		"production_scene_ready_before_measurement": true,
		"resource_loader_thread_status_api": "no global pending-request enumeration available",
		"watchdog_owner": "external R1 runner",
	})
	print("R1_MOBILE_WAIT_INVENTORY_WRITTEN")


func _write_json(path: String, payload: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(payload, "\t"))


func _count_nodes(root: Node) -> int:
	var total := 1
	for child: Node in root.get_children():
		total += _count_nodes(child)
	return total


func _elapsed_ms() -> int:
	return int((Time.get_ticks_usec() - _started_usec) / 1000)


func _fail(message: String) -> void:
	push_error(message)
	print("R1_RUNTIME_DEBUG_FAILURE message=%s" % message)
