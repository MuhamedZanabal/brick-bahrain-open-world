extends Node
## TouchInput - Autoload singleton bridging virtual joystick / touch buttons to gameplay
## PlayerController reads these values every physics frame alongside keyboard input

var movement: Vector2 = Vector2.ZERO  # from virtual joystick, range -1..1 each axis
var sprint_held: bool = false          # from "run" action button
var _jump_requested: bool = false      # one-shot, from jump action button
var _interact_requested: bool = false  # one-shot, from interact/fist action button

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

func set_movement(v: Vector2) -> void:
	movement = v

func set_sprint(held: bool) -> void:
	sprint_held = held
