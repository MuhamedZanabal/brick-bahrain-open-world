extends Control
class_name VirtualJoystick
## Viewport-level mobile joystick with explicit touch capture.
## It keeps the active finger after leaving the visual circle and never depends on
## full-screen GUI propagation, which is essential on Android multi-touch devices.

signal movement_changed(value: Vector2)

@export var radius := 70.0
@export var knob_radius := 32.0
@export var deadzone := 0.08
@export var activation_padding := 24.0

var _active_touch := -1
var _mouse_active := false
var _center := Vector2.ZERO
var _knob_position := Vector2.ZERO


func _ready() -> void:
	name = "MovementJoystick"
	custom_minimum_size = Vector2(radius * 2.0, radius * 2.0)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	focus_mode = Control.FOCUS_NONE
	set_process_input(true)
	resized.connect(_sync_geometry)
	_sync_geometry()
	call_deferred("_sync_geometry")


func _exit_tree() -> void:
	_release_input()


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree():
		_release_input()


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree() or GameManager.is_gameplay_input_blocked():
		if _active_touch != -1 or _mouse_active:
			_release_input()
		return

	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed:
			if _active_touch == -1 and _activation_rect().has_point(touch.position):
				_active_touch = touch.index
				_update_from_viewport(touch.position)
				get_viewport().set_input_as_handled()
		elif touch.index == _active_touch:
			_release_input()
			get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		if drag.index == _active_touch:
			_update_from_viewport(drag.position)
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.button_index != MOUSE_BUTTON_LEFT:
			return
		if button.pressed and _activation_rect().has_point(button.position):
			_mouse_active = true
			_update_from_viewport(button.position)
			get_viewport().set_input_as_handled()
		elif not button.pressed and _mouse_active:
			_release_input()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _mouse_active:
		_update_from_viewport((event as InputEventMouseMotion).position)
		get_viewport().set_input_as_handled()


func _draw() -> void:
	draw_circle(_center, radius, Color(0.015, 0.03, 0.055, 0.56))
	draw_arc(_center, radius, 0.0, TAU, 64, Color(0.55, 0.88, 1.0, 0.72), 3.0, true)
	draw_circle(_knob_position, knob_radius, Color(0.2, 0.68, 0.95, 0.72))
	draw_arc(
		_knob_position,
		knob_radius,
		0.0,
		TAU,
		48,
		Color(0.9, 0.98, 1.0, 0.94),
		2.0,
		true
	)


func _sync_geometry() -> void:
	_center = size * 0.5
	if _active_touch == -1 and not _mouse_active:
		_knob_position = _center
	queue_redraw()


func _activation_rect() -> Rect2:
	return get_global_rect().grow(activation_padding)


func _viewport_to_local(viewport_position: Vector2) -> Vector2:
	return get_global_transform_with_canvas().affine_inverse() * viewport_position


func _update_from_viewport(viewport_position: Vector2) -> void:
	var local_position := _viewport_to_local(viewport_position)
	var offset := local_position - _center
	if offset.length() > radius:
		offset = offset.normalized() * radius
	_knob_position = _center + offset
	var value := offset / maxf(radius, 1.0)
	if value.length() < deadzone:
		value = Vector2.ZERO
	else:
		value = value.limit_length(1.0)
	TouchInput.set_movement(value)
	movement_changed.emit(value)
	queue_redraw()


func _release_input() -> void:
	_active_touch = -1
	_mouse_active = false
	_knob_position = _center
	TouchInput.set_movement(Vector2.ZERO)
	movement_changed.emit(Vector2.ZERO)
	queue_redraw()


func get_debug_state() -> Dictionary:
	return {
		"active_touch": _active_touch,
		"mouse_active": _mouse_active,
		"center": _center,
		"knob_position": _knob_position,
		"movement": TouchInput.movement,
		"global_rect": get_global_rect(),
	}
