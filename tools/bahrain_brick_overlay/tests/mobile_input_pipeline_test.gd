extends Node
## Runtime validation for the real Android touch path:
## viewport touch -> VirtualJoystick -> TouchInput -> player velocity -> physics motion.

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
	var forward_touch := center + Vector2(0.0, -rect.size.y * 0.40)
	joystick._input(_screen_touch(41, forward_touch, true))
	await _wait_process_frames(2)
	_check(TouchInput.movement.y < -0.45, "joystick creates continuous forward vector", TouchInput.movement)

	var start := player.global_position
	await _wait_physics_frames(90)
	var forward_delta := player.global_position - start
	_check(
		Vector2(forward_delta.x, forward_delta.z).length() > 1.0,
		"joystick vector reaches player physics movement",
		{"delta": forward_delta, "velocity": player.velocity}
	)
	joystick._input(_screen_touch(41, forward_touch, false))
	await _wait_process_frames(2)
	_check(TouchInput.movement.length() < 0.001, "joystick resets to zero on release", TouchInput.movement)

	await _wait_physics_frames(40)
	var stopped_position := player.global_position
	await _wait_physics_frames(30)
	var drift_distance := stopped_position.distance_to(player.global_position)
	_check(drift_distance < 0.15, "player does not drift after joystick release", drift_distance)

	var diagonal_touch := center + Vector2(rect.size.x * 0.30, -rect.size.y * 0.30)
	var diagonal_start := player.global_position
	joystick._input(_screen_touch(42, diagonal_touch, true))
	await _wait_physics_frames(70)
	joystick._input(_screen_touch(42, diagonal_touch, false))
	var diagonal_delta := player.global_position - diagonal_start
	_check(
		absf(diagonal_delta.x) > 0.25 and absf(diagonal_delta.z) > 0.25,
		"diagonal joystick movement affects both horizontal axes",
		diagonal_delta
	)

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
	_check(player.global_position.y > y_before + 0.08 or player.velocity.y > 0.1, "jump remains functional after movement")

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
