extends Control
class_name VirtualJoystick
## VirtualJoystick - Draggable on-screen joystick for mobile movement
## Bottom-left thumbstick matching the reference UI (translucent ring + knob)

var _radius: float = 70.0
var _knob_radius: float = 32.0
var _touch_index: int = -1
var _center: Vector2 = Vector2.ZERO
var _knob_pos: Vector2 = Vector2.ZERO

var _bg: Control
var _knob: Control

func _ready() -> void:
	custom_minimum_size = Vector2(_radius * 2, _radius * 2)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_center = size / 2.0
	_knob_pos = _center
	
	_bg = Control.new()
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bg.draw.connect(_draw_bg)
	add_child(_bg)
	
	_knob = Control.new()
	_knob.set_anchors_preset(Control.PRESET_FULL_RECT)
	_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_knob.draw.connect(_draw_knob)
	add_child(_knob)
	
	queue_redraw_all()

func queue_redraw_all() -> void:
	if _bg: _bg.queue_redraw()
	if _knob: _knob.queue_redraw()

func _draw_bg() -> void:
	_bg.draw_circle(_center, _radius, Color(1, 1, 1, 0.12))
	_bg.draw_arc(_center, _radius, 0, TAU, 48, Color(1, 1, 1, 0.4), 3.0)

func _draw_knob() -> void:
	_knob.draw_circle(_knob_pos, _knob_radius, Color(1, 1, 1, 0.55))
	_knob.draw_arc(_knob_pos, _knob_radius, 0, TAU, 32, Color(1, 1, 1, 0.8), 2.0)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _touch_index == -1:
			_touch_index = event.index
			_update_knob(event.position)
		elif not event.pressed and event.index == _touch_index:
			_touch_index = -1
			_reset_knob()
	elif event is InputEventScreenDrag:
		if event.index == _touch_index:
			_update_knob(event.position)
	elif event is InputEventMouseButton:
		# Mouse support for desktop testing
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_touch_index = 1000
				_update_knob(event.position)
			else:
				_touch_index = -1
				_reset_knob()
	elif event is InputEventMouseMotion:
		if _touch_index == 1000:
			_update_knob(event.position)

func _update_knob(pos: Vector2) -> void:
	var offset: Vector2 = pos - _center
	var dist: float = offset.length()
	if dist > _radius:
		offset = offset.normalized() * _radius
	_knob_pos = _center + offset
	queue_redraw_all()
	
	var normalized: Vector2 = offset / _radius
	# Y is inverted: screen-down is positive, but move_forward should be "up" drag
	TouchInput.set_movement(Vector2(normalized.x, normalized.y))

func _reset_knob() -> void:
	_knob_pos = _center
	queue_redraw_all()
	TouchInput.set_movement(Vector2.ZERO)
