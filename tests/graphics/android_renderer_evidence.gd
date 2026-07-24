extends Node

const SliceScene := preload("res://scenes/manama_souq_vertical_slice.tscn")
const VIEWPORT_SIZE := Vector2i(2400, 1080)
const WARMUP_FRAMES := 180
const CAPTURE_FRAME := 300
const TOTAL_MEASURED_FRAMES := 360
const CAMERA_POSITION := Vector3(-104.0, 48.0, 104.0)
const CAMERA_TARGET := Vector3(-4.0, 4.0, -4.0)
const READY_MARKER := "BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6"
const MISSION_START_MARKER := "BAHRAIN_BRICK_KARAK_MISSION_STARTED"

var _slice: ManamaSouqVerticalSlice
var _mission: KarakDeliveryMission
var _frame_times_ms: Array[float] = []


func _ready() -> void:
	ProjectSettings.set_setting("bahrain_brick/qa_auto_mission", false)
	get_window().size = VIEWPORT_SIZE
	call_deferred("_run")


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED:
		print("G0_ANDROID_LIFECYCLE_PAUSED")
	elif what == NOTIFICATION_APPLICATION_RESUMED:
		print("G0_ANDROID_LIFECYCLE_RESUMED")


func _run() -> void:
	_slice = SliceScene.instantiate() as ManamaSouqVerticalSlice
	if _slice == null:
		_fail("Manama Souq scene root type mismatch")
		return
	add_child(_slice)
	for _frame in range(1800):
		if _slice.is_slice_ready():
			break
		await get_tree().process_frame
	if not _slice.is_slice_ready():
		_fail("Manama Souq scene did not reach readiness")
		return
	_mission = _slice.get_mission()
	if _mission == null or _mission.current_state != KarakDeliveryMission.MissionState.WALK_TO_CAFE:
		_fail("Karak Delivery mission did not start")
		return

	var camera := Camera3D.new()
	camera.name = "G0AndroidEvidenceCamera"
	camera.fov = 62.0
	camera.near = 0.1
	camera.far = 500.0
	add_child(camera)
	camera.global_position = CAMERA_POSITION
	camera.look_at(CAMERA_TARGET, Vector3.UP)
	camera.current = true

	print("G0_ANDROID_RENDERER_READY renderer=%s driver=%s gpu=%s" % [
		_renderer_name(),
		_driver_name(),
		RenderingServer.get_video_adapter_name(),
	])
	for _frame in range(WARMUP_FRAMES):
		await get_tree().process_frame
	print("G0_ANDROID_WARMUP_COMPLETE frame=%d" % WARMUP_FRAMES)

	for measured_frame in range(1, TOTAL_MEASURED_FRAMES + 1):
		var start_usec := Time.get_ticks_usec()
		await get_tree().process_frame
		_frame_times_ms.append(float(Time.get_ticks_usec() - start_usec) / 1000.0)
		if measured_frame == CAPTURE_FRAME:
			await RenderingServer.frame_post_draw
			print("G0_ANDROID_CAPTURE_FRAME frame=%d" % CAPTURE_FRAME)

	print("G0_ANDROID_EVIDENCE_LIVE renderer=%s frames=%d memory=%d draw_calls=%d visible_objects=%d visible_primitives=%d" % [
		_renderer_name(),
		TOTAL_MEASURED_FRAMES,
		OS.get_static_memory_usage(),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
	])


func _renderer_name() -> String:
	return str(ProjectSettings.get_setting("rendering/renderer/rendering_method", "unknown"))


func _driver_name() -> String:
	if _renderer_name() == "gl_compatibility":
		return "opengl3"
	return "vulkan"


func _fail(message: String) -> void:
	push_error(message)
	print("G0_ANDROID_EVIDENCE_FAILURE message=%s" % message)
