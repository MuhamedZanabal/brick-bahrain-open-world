extends Node

const SliceScene := preload("res://scenes/manama_souq_vertical_slice.tscn")
const VIEWPORT_SIZE := Vector2i(1920, 1080)
const WARMUP_FRAMES := 180
const CAPTURE_FRAME := 300
const TOTAL_MEASURED_FRAMES := 360
const CAMERA_POSITION := Vector3(-104.0, 48.0, 104.0)
const CAMERA_TARGET := Vector3(-4.0, 4.0, -4.0)
const READY_MARKER := "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6"
const MISSION_START_MARKER := "BAHRAIN_BRICK_KARAK_MISSION_STARTED"

var _evidence_dir: String
var _frame_rows: Array[Dictionary] = []
var _frame_times_ms: Array[float] = []
var _screenshot_report: Dictionary = {
	"captured": false,
	"valid_non_black": false,
	"average_luminance": 0.0,
	"maximum_luminance": 0.0,
}


func _ready() -> void:
	_evidence_dir = OS.get_environment("G0_EVIDENCE_DIR")
	if _evidence_dir.is_empty():
		push_error("G0_EVIDENCE_DIR is required")
		get_tree().quit(2)
		return
	DirAccess.make_dir_recursive_absolute(_evidence_dir)
	call_deferred("_run")


func _run() -> void:
	ProjectSettings.set_setting("bahrain_brick/qa_auto_mission", false)
	get_window().size = VIEWPORT_SIZE
	var slice := SliceScene.instantiate() as ManamaSouqVerticalSlice
	if slice == null:
		_fail("Manama Souq scene root type mismatch", 3)
		return
	add_child(slice)
	for _frame in range(1800):
		if slice.is_slice_ready():
			break
		await get_tree().process_frame
	if not slice.is_slice_ready():
		_fail("Manama Souq scene did not reach readiness", 4)
		return

	var mission: KarakDeliveryMission = slice.get_mission()
	if mission == null or mission.current_state != KarakDeliveryMission.MissionState.WALK_TO_CAFE:
		_fail("Karak Delivery mission did not start", 5)
		return

	var camera := Camera3D.new()
	camera.name = "G0EvidenceCamera"
	camera.fov = 62.0
	camera.near = 0.1
	camera.far = 500.0
	add_child(camera)
	camera.global_position = CAMERA_POSITION
	camera.look_at(CAMERA_TARGET, Vector3.UP)
	camera.current = true

	for _frame in range(WARMUP_FRAMES):
		await get_tree().process_frame

	for measured_frame in range(1, TOTAL_MEASURED_FRAMES + 1):
		var frame_start_usec := Time.get_ticks_usec()
		await get_tree().process_frame
		var frame_end_usec := Time.get_ticks_usec()
		var frame_time_ms := float(frame_end_usec - frame_start_usec) / 1000.0
		_frame_times_ms.append(frame_time_ms)
		_frame_rows.append(_sample_frame(measured_frame, frame_time_ms))
		if measured_frame == CAPTURE_FRAME:
			await RenderingServer.frame_post_draw
			_capture_screenshot()

	_write_frame_metrics()
	_write_runtime_report(slice, mission)
	print("G0_RENDERER_EVIDENCE_COMPLETE renderer=%s frames=%d" % [RenderingServer.get_current_rendering_method(), TOTAL_MEASURED_FRAMES])
	get_tree().quit(0)


func _sample_frame(frame_number: int, frame_time_ms: float) -> Dictionary:
	return {
		"frame": frame_number,
		"frame_time_ms": frame_time_ms,
		"reported_fps": float(Performance.get_monitor(Performance.TIME_FPS)),
		"process_ms": float(Performance.get_monitor(Performance.TIME_PROCESS)) * 1000.0,
		"physics_process_ms": float(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)) * 1000.0,
		"process_memory_bytes": int(OS.get_static_memory_usage()),
		"graphics_memory_bytes": int(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)),
		"draw_calls": int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		"visible_objects": int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)),
		"visible_primitives": int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
	}


func _capture_screenshot() -> void:
	var image: Image = get_viewport().get_texture().get_image()
	if image == null or image.is_empty():
		_screenshot_report = {
			"captured": false,
			"valid_non_black": false,
			"average_luminance": 0.0,
			"maximum_luminance": 0.0,
		}
		return
	var save_error := image.save_png(_path("screenshot.png"))
	var total_luminance := 0.0
	var maximum_luminance := 0.0
	var samples := 0
	var x_step: int = maxi(1, image.get_width() / 32)
	var y_step: int = maxi(1, image.get_height() / 18)
	for y in range(0, image.get_height(), y_step):
		for x in range(0, image.get_width(), x_step):
			var luminance := image.get_pixel(x, y).get_luminance()
			total_luminance += luminance
			maximum_luminance = maxf(maximum_luminance, luminance)
			samples += 1
	var average_luminance := total_luminance / maxf(float(samples), 1.0)
	_screenshot_report = {
		"captured": save_error == OK,
		"save_error": save_error,
		"width": image.get_width(),
		"height": image.get_height(),
		"average_luminance": average_luminance,
		"maximum_luminance": maximum_luminance,
		"valid_non_black": save_error == OK and average_luminance > 0.005 and maximum_luminance > 0.02,
	}


func _write_frame_metrics() -> void:
	var file := FileAccess.open(_path("frame_metrics.csv"), FileAccess.WRITE)
	if file == null:
		push_error("Unable to write frame_metrics.csv")
		return
	file.store_line("frame,frame_time_ms,reported_fps,process_ms,physics_process_ms,process_memory_bytes,graphics_memory_bytes,draw_calls,visible_objects,visible_primitives")
	for row: Dictionary in _frame_rows:
		file.store_line("%d,%.6f,%.3f,%.6f,%.6f,%d,%d,%d,%d,%d" % [
			int(row["frame"]),
			float(row["frame_time_ms"]),
			float(row["reported_fps"]),
			float(row["process_ms"]),
			float(row["physics_process_ms"]),
			int(row["process_memory_bytes"]),
			int(row["graphics_memory_bytes"]),
			int(row["draw_calls"]),
			int(row["visible_objects"]),
			int(row["visible_primitives"]),
		])


func _write_runtime_report(slice: ManamaSouqVerticalSlice, mission: KarakDeliveryMission) -> void:
	var sorted_times: Array[float] = _frame_times_ms.duplicate()
	sorted_times.sort()
	var average_ms := _average(_frame_times_ms)
	var report := {
		"schema_version": 1,
		"evidence_tier": "A",
		"evidence_class": "HOST_CI_FUNCTIONAL",
		"engine": Engine.get_version_info(),
		"renderer": RenderingServer.get_current_rendering_method(),
		"rendering_driver": RenderingServer.get_current_rendering_driver_name(),
		"operating_system": OS.get_name(),
		"operating_system_version": OS.get_version(),
		"gpu_name": RenderingServer.get_video_adapter_name(),
		"gpu_vendor": RenderingServer.get_video_adapter_vendor(),
		"gpu_driver_info": OS.get_video_adapter_driver_info(),
		"viewport": {"width": VIEWPORT_SIZE.x, "height": VIEWPORT_SIZE.y},
		"render_scale": 1.0,
		"quality_settings": "frozen_baseline",
		"scene": "res://scenes/manama_souq_vertical_slice.tscn",
		"camera": {
			"position": [CAMERA_POSITION.x, CAMERA_POSITION.y, CAMERA_POSITION.z],
			"target": [CAMERA_TARGET.x, CAMERA_TARGET.y, CAMERA_TARGET.z],
			"fov": 62.0,
		},
		"scene_ready": slice.is_slice_ready(),
		"scene_ready_marker": true,
		"mission_start_marker": true,
		"mission_state": mission.current_state,
		"mission_objective": mission.get_current_objective(),
		"warmup_frames": WARMUP_FRAMES,
		"captured_frame_number": CAPTURE_FRAME,
		"measured_frame_count": _frame_times_ms.size(),
		"frame_time_ms": {
			"average": average_ms,
			"median": _percentile(sorted_times, 0.50),
			"p95": _percentile(sorted_times, 0.95),
			"p99": _percentile(sorted_times, 0.99),
		},
		"average_fps": 1000.0 / maxf(average_ms, 0.001),
		"one_percent_low_fps": 1000.0 / maxf(_percentile(sorted_times, 0.99), 0.001),
		"process_memory_bytes": int(OS.get_static_memory_usage()),
		"process_memory_peak_bytes": int(OS.get_static_memory_peak_usage()),
		"graphics_memory_bytes": int(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)),
		"draw_calls": int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		"visible_objects": int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)),
		"visible_primitives": int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
		"visible_triangles": null,
		"protocol_markers": {"ready": READY_MARKER, "mission_start": MISSION_START_MARKER},
		"screenshot": _screenshot_report,
		"exit_code": 0,
		"evidence_complete": false,
	}
	var file := FileAccess.open(_path("runtime.json"), FileAccess.WRITE)
	if file == null:
		push_error("Unable to write runtime.json")
		return
	file.store_string(JSON.stringify(report, "\t") + "\n")


func _average(values: Array[float]) -> float:
	if values.is_empty():
		return 0.0
	var total := 0.0
	for value in values:
		total += value
	return total / float(values.size())


func _percentile(sorted_values: Array[float], percentile: float) -> float:
	if sorted_values.is_empty():
		return 0.0
	var index := int(ceil(percentile * float(sorted_values.size()))) - 1
	return sorted_values[clampi(index, 0, sorted_values.size() - 1)]


func _path(filename: String) -> String:
	return _evidence_dir.path_join(filename)


func _fail(message: String, code: int) -> void:
	push_error(message)
	var report := {
		"schema_version": 1,
		"evidence_tier": "A",
		"renderer": RenderingServer.get_current_rendering_method(),
		"rendering_driver": RenderingServer.get_current_rendering_driver_name(),
		"failure": message,
		"exit_code": code,
		"evidence_complete": false,
	}
	var file := FileAccess.open(_path("runtime.json"), FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
	get_tree().quit(code)
