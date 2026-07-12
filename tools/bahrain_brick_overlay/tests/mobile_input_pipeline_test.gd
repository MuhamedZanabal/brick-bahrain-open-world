extends Node
## Runtime validation for the Android touch path:
## screen touch -> VirtualJoystick -> TouchInput -> player velocity -> physics motion.

var _failed := 0
var _passed := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("_run")


func _check(condition: bool, description: String, evidence: Variant = null) -> void:
	if condition:
		_passed += 1
	else:
		_failed += 1
	print("[%s] %s%s" % [
		"PASS" if condition else "FAIL",
		description,
		" — %s" % str(evidence) if evidence != null else "",
	])


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


func _run_direction(
	player: CharacterBody3D,
	joystick: VirtualJoystick,
	center: Vector2,
	offset: Vector2,
	touch_index: int,
	label: String
) -> Dictionary:
	TouchInput.reset_all()
	player.global_position = Vector3(0.0, 2.4, 68.0)
	player.velocity = Vector3.ZERO
	player.set("camera_yaw", 0.0)
	await _wait_physics_frames(18)
	var start_position := player.global_position
	var touch_position := center + offset
	joystick._input(_screen_touch(touch_index, touch_position, true))
	await _wait_process_frames(2)
	var input_vector := TouchInput.movement
	var peak_velocity := Vector3.ZERO
	for _frame in range(54):
		await get_tree().physics_frame
		if Vector2(player.velocity.x, player.velocity.z).length() > Vector2(peak_velocity.x, peak_velocity.z).length():
			peak_velocity = player.velocity
	var end_position := player.global_position
	joystick._input(_screen_touch(touch_index, touch_position, false))
	await _wait_process_frames(2)
	var evidence := {
		"direction": label,
		"joystick_vector": input_vector,
		"start_position": start_position,
		"peak_velocity": peak_velocity,
		"end_position": end_position,
		"position_delta": end_position - start_position,
	}
	print("[TELEMETRY] %s" % JSON.stringify(evidence))
	return evidence


func _run() -> void:
	print("Bahrain Brick mobile input pipeline test starting")
	TouchInput.reset_all()
	GameManager.current_mode = GameManager.GameMode.SINGLE_PLAYER
	for owner in ["phone", "shop", "chat", "pause"]:
		GameManager.release_ui_lock(owner)

	var packed := load("res://scenes/world.tscn") as PackedScene
	_check(packed != null, "world scene loads")
	if packed == null:
		_finish()
		return

	var world := packed.instantiate() as Node3D
	get_tree().root.add_child(world)
	var ready_timeout := 1000
	while ready_timeout > 0 and not bool(world.get("_world_ready")):
		ready_timeout -= 1
		await get_tree().process_frame
	_check(bool(world.get("_world_ready")), "world completes staged loading", 1000 - ready_timeout)
	if not bool(world.get("_world_ready")):
		_finish()
		return

	await _wait_process_frames(12)
	var player := world.get("player") as CharacterBody3D
	var hud := world.get("hud") as CanvasLayer
	var joystick := hud.find_child("MovementJoystick", true, false) as VirtualJoystick if hud else null
	var safe_root := hud.find_child("SafeAreaHUD", true, false) as Control if hud else null
	var walking_controls := hud.get("_walking_controls") as Control if hud else null
	var vehicle_controls := hud.get("_vehicle_controls") as Control if hud else null

	_check(player != null, "local player exists")
	_check(hud != null, "mobile HUD exists")
	_check(joystick != null, "movement joystick exists")
	_check(
		safe_root != null and safe_root.mouse_filter == Control.MOUSE_FILTER_IGNORE,
		"full-screen HUD does not consume world camera touches"
	)
	_check(walking_controls != null and walking_controls.visible, "walking controls start visible")
	_check(vehicle_controls != null and not vehicle_controls.visible, "vehicle controls start hidden")

	if player == null or joystick == null:
		_finish()
		return

	await _wait_process_frames(4)
	var rect := joystick.get_global_rect()
	var center := rect.get_center()
	var radius_x := rect.size.x * 0.40
	var radius_y := rect.size.y * 0.40

	var forward: Dictionary = await _run_direction(player, joystick, center, Vector2(0.0, -radius_y), 41, "forward")
	var forward_input: Vector2 = forward["joystick_vector"]
	var forward_delta: Vector3 = forward["position_delta"]
	var forward_velocity: Vector3 = forward["peak_velocity"]
	_check(forward_input.y < -0.45, "forward joystick vector is non-zero", forward)
	_check(forward_delta.z > 1.0, "forward movement changes player position", forward)
	_check(Vector2(forward_velocity.x, forward_velocity.z).length() > 1.0, "forward movement produces player velocity", forward)

	var backward: Dictionary = await _run_direction(player, joystick, center, Vector2(0.0, radius_y), 42, "backward")
	var backward_input: Vector2 = backward["joystick_vector"]
	var backward_delta: Vector3 = backward["position_delta"]
	var backward_velocity: Vector3 = backward["peak_velocity"]
	_check(backward_input.y > 0.45, "backward joystick vector is non-zero", backward)
	_check(backward_delta.z < -1.0, "backward movement changes player position", backward)
	_check(Vector2(backward_velocity.x, backward_velocity.z).length() > 1.0, "backward movement produces player velocity", backward)

	var left: Dictionary = await _run_direction(player, joystick, center, Vector2(-radius_x, 0.0), 43, "left")
	var left_input: Vector2 = left["joystick_vector"]
	var left_delta: Vector3 = left["position_delta"]
	var left_velocity: Vector3 = left["peak_velocity"]
	_check(left_input.x < -0.45, "left joystick vector is non-zero", left)
	_check(left_delta.x < -1.0, "left movement changes player position", left)
	_check(Vector2(left_velocity.x, left_velocity.z).length() > 1.0, "left movement produces player velocity", left)

	var right: Dictionary = await _run_direction(player, joystick, center, Vector2(radius_x, 0.0), 44, "right")
	var right_input: Vector2 = right["joystick_vector"]
	var right_delta: Vector3 = right["position_delta"]
	var right_velocity: Vector3 = right["peak_velocity"]
	_check(right_input.x > 0.45, "right joystick vector is non-zero", right)
	_check(right_delta.x > 1.0, "right movement changes player position", right)
	_check(Vector2(right_velocity.x, right_velocity.z).length() > 1.0, "right movement produces player velocity", right)

	var diagonal: Dictionary = await _run_direction(player, joystick, center, Vector2(radius_x * 0.75, -radius_y * 0.75), 45, "forward_right_diagonal")
	var diagonal_input: Vector2 = diagonal["joystick_vector"]
	var diagonal_delta: Vector3 = diagonal["position_delta"]
	_check(absf(diagonal_input.x) > 0.25 and absf(diagonal_input.y) > 0.25, "diagonal joystick generates two-axis input", diagonal)
	_check(absf(diagonal_delta.x) > 0.5 and absf(diagonal_delta.z) > 0.5, "diagonal movement affects both horizontal axes", diagonal)

	_check(TouchInput.movement.length() < 0.001, "joystick resets to zero on release", TouchInput.movement)
	await _wait_physics_frames(35)
	var stopped_position := player.global_position
	await _wait_physics_frames(25)
	var drift_distance := stopped_position.distance_to(player.global_position)
	_check(drift_distance < 0.15, "player does not drift after joystick release", drift_distance)

	var yaw_before := float(player.get("camera_yaw"))
	var viewport_size := get_viewport().get_visible_rect().size
	var look_start := Vector2(viewport_size.x * 0.70, viewport_size.y * 0.42)
	TouchInput._input(_screen_touch(77, look_start, true))
	TouchInput._input(_screen_drag(77, look_start + Vector2(90.0, -25.0), Vector2(90.0, -25.0)))
	TouchInput._input(_screen_touch(77, look_start + Vector2(90.0, -25.0), false))
	await _wait_physics_frames(3)
	var yaw_after := float(player.get("camera_yaw"))
	_check(absf(yaw_after - yaw_before) > 0.01, "right-side touch drag rotates camera", {"before": yaw_before, "after": yaw_after})

	while not player.is_on_floor():
		await get_tree().physics_frame
	var y_before := player.global_position.y
	TouchInput.request_jump()
	await _wait_physics_frames(8)
	_check(
		player.global_position.y > y_before + 0.08 or player.velocity.y > 0.1,
		"jump remains functional after movement",
		{"y_before": y_before, "position": player.global_position, "velocity": player.velocity}
	)

	var snapshot: Dictionary = player.call("get_input_debug_snapshot")
	_check(bool(snapshot.get("is_local", false)), "active controller is local", snapshot)
	_check(not bool(snapshot.get("gameplay_input_blocked", true)), "gameplay input is not locked", snapshot)

	TouchInput.reset_all()
	world.queue_free()
	await _wait_process_frames(2)
	_finish()


func _finish() -> void:
	print("Bahrain Brick mobile input pipeline test complete: %d passed, %d failed" % [_passed, _failed])
	get_tree().quit(1 if _failed > 0 else 0)
