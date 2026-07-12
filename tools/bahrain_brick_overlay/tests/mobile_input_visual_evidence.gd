extends Node
## Rendered control evidence only. This scene does not change production art or menus.

var _frame_index := 0
var _output_dir := ""
var _telemetry_label: Label
var _results: Array[Dictionary] = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("_run")


func _wait_process_frames(count: int) -> void:
	for _index in range(count):
		await get_tree().process_frame


func _wait_physics_frames(count: int) -> void:
	for _index in range(count):
		await get_tree().physics_frame


func _screen_touch(index: int, position: Vector2, pressed: bool) -> InputEventScreenTouch:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = position
	event.pressed = pressed
	return event


func _screen_drag(index: int, position: Vector2, relative: Vector2) -> InputEventScreenDrag:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = position
	event.relative = relative
	return event


func _build_telemetry_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 100
	add_child(layer)
	var panel := ColorRect.new()
	panel.position = Vector2(18, 300)
	panel.size = Vector2(610, 150)
	panel.color = Color(0.01, 0.02, 0.035, 0.88)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(panel)
	_telemetry_label = Label.new()
	_telemetry_label.position = Vector2(18, 12)
	_telemetry_label.size = Vector2(574, 126)
	_telemetry_label.add_theme_font_size_override("font_size", 20)
	_telemetry_label.add_theme_color_override("font_color", Color(0.88, 0.97, 1.0))
	_telemetry_label.add_theme_color_override("font_shadow_color", Color.BLACK)
	_telemetry_label.add_theme_constant_override("shadow_offset_x", 2)
	_telemetry_label.add_theme_constant_override("shadow_offset_y", 2)
	panel.add_child(_telemetry_label)


func _telemetry_text(stage: String, player: CharacterBody3D) -> String:
	return (
		"CONTROL EVIDENCE — %s\nJoystick: %s\nVelocity: %s\nPosition: %s\nCamera yaw: %.3f"
		% [stage, str(TouchInput.movement), str(player.velocity), str(player.global_position), float(player.get("camera_yaw"))]
	)


func _capture(stage: String, player: CharacterBody3D, named_file: String = "") -> void:
	_telemetry_label.text = _telemetry_text(stage, player)
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var frame_path := "%s/frames/frame_%04d.png" % [_output_dir, _frame_index]
	var frame_error := image.save_png(frame_path)
	if frame_error != OK:
		push_error("failed to save frame %s: %s" % [frame_path, frame_error])
	_frame_index += 1
	if not named_file.is_empty():
		var named_path := "%s/screenshots/%s" % [_output_dir, named_file]
		var named_error := image.save_png(named_path)
		if named_error != OK:
			push_error("failed to save screenshot %s: %s" % [named_path, named_error])


func _run_direction(
	player: CharacterBody3D,
	joystick: VirtualJoystick,
	center: Vector2,
	offset: Vector2,
	touch_index: int,
	label: String
) -> void:
	TouchInput.reset_all()
	player.global_position = Vector3(0.0, 2.4, 68.0)
	player.velocity = Vector3.ZERO
	player.set("camera_yaw", 0.0)
	await _wait_physics_frames(18)
	var start_position := player.global_position
	await _capture(label.to_upper() + " — BEFORE", player, "%s_before.png" % label)
	var touch_position := center + offset
	joystick._input(_screen_touch(touch_index, touch_position, true))
	await _wait_process_frames(2)
	var input_vector := TouchInput.movement
	var peak_velocity := Vector3.ZERO
	for frame in range(48):
		await get_tree().physics_frame
		if Vector2(player.velocity.x, player.velocity.z).length() > Vector2(peak_velocity.x, peak_velocity.z).length():
			peak_velocity = player.velocity
		if frame % 4 == 0:
			await _capture(label.to_upper() + " — MOVING", player, "%s_moving.png" % label if frame == 24 else "")
	var end_position := player.global_position
	joystick._input(_screen_touch(touch_index, touch_position, false))
	await _wait_process_frames(2)
	await _capture(label.to_upper() + " — RELEASED", player, "%s_after.png" % label)
	var result := {
		"stage": label,
		"joystick_vector": input_vector,
		"start_position": start_position,
		"peak_velocity": peak_velocity,
		"end_position": end_position,
		"position_delta": end_position - start_position,
	}
	_results.append(result)
	print("[VISUAL_TELEMETRY] %s" % JSON.stringify(result))


func _run() -> void:
	get_window().size = Vector2i(1280, 720)
	_output_dir = ProjectSettings.globalize_path("res://build/visual_evidence")
	DirAccess.make_dir_recursive_absolute(_output_dir + "/frames")
	DirAccess.make_dir_recursive_absolute(_output_dir + "/screenshots")
	TouchInput.reset_all()
	GameManager.current_mode = GameManager.GameMode.SINGLE_PLAYER
	for owner in ["phone", "shop", "chat", "pause"]:
		GameManager.release_ui_lock(owner)

	var packed := load("res://scenes/world.tscn") as PackedScene
	if packed == null:
		push_error("world scene failed to load")
		get_tree().quit(1)
		return
	var world := packed.instantiate() as Node3D
	get_tree().root.add_child(world)
	var timeout := 1000
	while timeout > 0 and not bool(world.get("_world_ready")):
		timeout -= 1
		await get_tree().process_frame
	if not bool(world.get("_world_ready")):
		push_error("world failed to reach ready state")
		get_tree().quit(1)
		return
	await _wait_process_frames(18)
	var player := world.get("player") as CharacterBody3D
	var hud := world.get("hud") as CanvasLayer
	var joystick := hud.find_child("MovementJoystick", true, false) as VirtualJoystick if hud else null
	if player == null or joystick == null:
		push_error("player or joystick missing")
		get_tree().quit(1)
		return
	_build_telemetry_overlay()
	await _wait_process_frames(4)
	var rect := joystick.get_global_rect()
	var center := rect.get_center()
	var radius_x := rect.size.x * 0.40
	var radius_y := rect.size.y * 0.40

	await _run_direction(player, joystick, center, Vector2(0.0, -radius_y), 101, "forward")
	await _run_direction(player, joystick, center, Vector2(0.0, radius_y), 102, "backward")
	await _run_direction(player, joystick, center, Vector2(-radius_x, 0.0), 103, "left")
	await _run_direction(player, joystick, center, Vector2(radius_x, 0.0), 104, "right")
	await _run_direction(player, joystick, center, Vector2(radius_x * 0.75, -radius_y * 0.75), 105, "diagonal")

	TouchInput.reset_all()
	player.global_position = Vector3(0.0, 2.4, 68.0)
	player.velocity = Vector3.ZERO
	player.set("camera_yaw", 0.0)
	await _wait_physics_frames(18)
	var yaw_before := float(player.get("camera_yaw"))
	await _capture("CAMERA ROTATION — BEFORE", player, "camera_before.png")
	var viewport_size := get_viewport().get_visible_rect().size
	var look_start := Vector2(viewport_size.x * 0.72, viewport_size.y * 0.42)
	TouchInput._input(_screen_touch(201, look_start, true))
	for frame in range(8):
		var relative := Vector2(18.0, -3.0)
		var drag_position := look_start + relative * float(frame + 1)
		TouchInput._input(_screen_drag(201, drag_position, relative))
		await _wait_physics_frames(2)
		await _capture("CAMERA ROTATION — DRAG", player, "camera_rotated.png" if frame == 7 else "")
	TouchInput._input(_screen_touch(201, look_start + Vector2(144.0, -24.0), false))
	var yaw_after := float(player.get("camera_yaw"))
	_results.append({"stage": "camera", "yaw_before": yaw_before, "yaw_after": yaw_after, "yaw_delta": yaw_after - yaw_before})
	print("[VISUAL_TELEMETRY] camera yaw before=%s after=%s delta=%s" % [yaw_before, yaw_after, yaw_after - yaw_before])

	while not player.is_on_floor():
		await get_tree().physics_frame
	var jump_start := player.global_position
	await _capture("JUMP — BEFORE", player, "jump_before.png")
	TouchInput.request_jump()
	var jump_peak_velocity := 0.0
	for frame in range(24):
		await get_tree().physics_frame
		jump_peak_velocity = maxf(jump_peak_velocity, player.velocity.y)
		if frame % 2 == 0:
			await _capture("JUMP — AIRBORNE", player, "jump_airborne.png" if frame == 8 else "")
	var jump_end := player.global_position
	_results.append({"stage": "jump", "start_position": jump_start, "peak_vertical_velocity": jump_peak_velocity, "captured_position": jump_end, "height_delta": jump_end.y - jump_start.y})
	print("[VISUAL_TELEMETRY] jump start=%s peak_velocity=%s captured=%s" % [jump_start, jump_peak_velocity, jump_end])

	var manifest := {
		"classification": "rendered software-runtime control evidence; not physical Android capture",
		"frame_count": _frame_index,
		"results": _results,
	}
	var manifest_path := _output_dir + "/visual_evidence_manifest.json"
	var manifest_file := FileAccess.open(manifest_path, FileAccess.WRITE)
	if manifest_file == null:
		push_error("failed to open visual evidence manifest")
		get_tree().quit(1)
		return
	manifest_file.store_string(JSON.stringify(manifest, "  ") + "\n")
	print("Bahrain Brick rendered control evidence complete: %d frames" % _frame_index)
	TouchInput.reset_all()
	await _wait_process_frames(2)
	get_tree().quit(0)
