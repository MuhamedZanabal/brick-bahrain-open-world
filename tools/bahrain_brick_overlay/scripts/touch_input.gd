extends Node
## Unified mobile input state. Movement uses explicit viewport-level touch capture;
## camera look uses a separate safe region so UI buttons and the joystick do not conflict.

signal movement_changed(value: Vector2)
signal look_delta_added(value: Vector2)

var movement := Vector2.ZERO
var look_delta := Vector2.ZERO
var sprint_held := false
var throttle := 0.0
var brake := 0.0
var steering := 0.0
var handbrake_held := false
var look_back_held := false
var horn_held := false
var _jump_requested := false
var _interact_requested := false
var _attack_requested := false
var _radio_requested := false
var _phone_requested := false
var _look_touch_index := -1


func _ready() -> void:
	set_process_input(true)


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed:
			if _look_touch_index == -1 and _look_region().has_point(touch.position):
				_look_touch_index = touch.index
		elif touch.index == _look_touch_index:
			_look_touch_index = -1
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		if drag.index == _look_touch_index and not GameManager.is_gameplay_input_blocked():
			add_look_delta(drag.relative)


func request_jump() -> void:
	_jump_requested = true


func consume_jump() -> bool:
	if _jump_requested:
		_jump_requested = false
		return true
	return false


func request_interact() -> void:
	_interact_requested = true


func consume_interact() -> bool:
	if _interact_requested:
		_interact_requested = false
		return true
	return false


func request_attack() -> void:
	_attack_requested = true


func consume_attack() -> bool:
	if _attack_requested:
		_attack_requested = false
		return true
	return false


func request_radio() -> void:
	_radio_requested = true


func consume_radio() -> bool:
	if _radio_requested:
		_radio_requested = false
		return true
	return false


func request_phone() -> void:
	_phone_requested = true


func consume_phone() -> bool:
	if _phone_requested:
		_phone_requested = false
		return true
	return false


func set_movement(value: Vector2) -> void:
	var normalized := value.limit_length(1.0)
	if movement.distance_squared_to(normalized) < 0.000001:
		return
	movement = normalized
	movement_changed.emit(movement)


func add_look_delta(value: Vector2) -> void:
	look_delta += value
	look_delta_added.emit(value)


func consume_look_delta() -> Vector2:
	var result := look_delta
	look_delta = Vector2.ZERO
	return result


func set_sprint(held: bool) -> void:
	sprint_held = held


func set_vehicle_throttle(value: float) -> void:
	throttle = clampf(value, 0.0, 1.0)


func set_vehicle_brake(value: float) -> void:
	brake = clampf(value, 0.0, 1.0)


func set_vehicle_steering(value: float) -> void:
	steering = clampf(value, -1.0, 1.0)


func set_handbrake(held: bool) -> void:
	handbrake_held = held


func set_look_back(held: bool) -> void:
	look_back_held = held


func set_horn(held: bool) -> void:
	horn_held = held


func reset_walking_controls() -> void:
	set_movement(Vector2.ZERO)
	sprint_held = false
	_jump_requested = false
	_interact_requested = false
	_attack_requested = false
	_look_touch_index = -1
	look_delta = Vector2.ZERO


func reset_vehicle_controls() -> void:
	throttle = 0.0
	brake = 0.0
	steering = 0.0
	handbrake_held = false
	look_back_held = false
	horn_held = false


func reset_all() -> void:
	reset_walking_controls()
	reset_vehicle_controls()
	_radio_requested = false
	_phone_requested = false


func _look_region() -> Rect2:
	var viewport_size := get_viewport().get_visible_rect().size
	return Rect2(
		Vector2(viewport_size.x * 0.36, viewport_size.y * 0.16),
		Vector2(viewport_size.x * 0.62, viewport_size.y * 0.56)
	)


func get_debug_snapshot() -> Dictionary:
	return {
		"movement": movement,
		"look_delta": look_delta,
		"look_touch_index": _look_touch_index,
		"sprint": sprint_held,
		"throttle": throttle,
		"brake": brake,
		"steering": steering,
		"input_blocked": GameManager.is_gameplay_input_blocked(),
	}
