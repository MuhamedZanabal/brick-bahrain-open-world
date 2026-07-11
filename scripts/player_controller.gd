extends CharacterBody3D
## PlayerController - Third-person character controller for the minifigure
## Handles movement, jumping, sprinting, vehicle entry/exit, and multiplayer sync

const WALK_SPEED := 4.5
const SPRINT_SPEED := 8.0
const JUMP_VELOCITY := 4.5
const GRAVITY := 9.8
const ROTATION_SPEED := 10.0
const ANIM_SPEED := 8.0
const MAX_ENERGY := 100.0
const MAX_HEALTH := 100.0
const ENERGY_DRAIN_RATE := 18.0   # per second while sprinting
const ENERGY_REGEN_RATE := 12.0   # per second while not sprinting

var character_data: Dictionary = {}
var speed_mult: float = 1.0
var jump_mult: float = 1.0
var is_sprinting: bool = false
var walk_anim_phase: float = 0.0
var current_vehicle: Node3D = null
var camera_pivot: Node3D = null
var camera_yaw: float = 0.0
var camera_pitch: float = -0.18
var camera_distance: float = 4.2  # closer, over-the-shoulder framing

var health: float = MAX_HEALTH
var energy: float = MAX_ENERGY

# Real FBX model animation (if character has a model_path); falls back to
# procedural bone-rotation animation on BrickFactory minifigures otherwise.
var _anim_player: AnimationPlayer = null
var _anim_prefix: String = ""
var _current_anim: String = ""

var multiplayer_id: int = 1
var is_local: bool = true

@onready var model: Node3D = get_node_or_null("Model")

func _ready() -> void:
	add_to_group("player")
	if character_data.is_empty():
		character_data = GameManager.get_selected_character()
	speed_mult = character_data.get("speed_mult", 1.0)
	jump_mult = character_data.get("jump_mult", 1.0)
	
	# Build the character model — prefer a real animated FBX model
	# (Quaternius Ultimate Animated Character Pack, CC0) and fall back to a
	# procedural brick minifigure if no model_path is set.
	if model == null:
		var model_path: String = character_data.get("model_path", "")
		model = BrickFactory.load_character_model(model_path)
		if model == null:
			model = BrickFactory.create_minifigure(character_data)
		else:
			_anim_player = model.get_meta("anim_player", null)
			_anim_prefix = model.get_meta("anim_prefix", "")
		model.name = "Model"
		add_child(model)
	
	# Set up collision
	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.3
	shape.height = 1.6
	collision.shape = shape
	collision.name = "Collision"
	add_child(collision)
	
	# Camera pivot — over-the-shoulder third person
	if is_local:
		camera_pivot = Node3D.new()
		camera_pivot.name = "CameraPivot"
		camera_pivot.position = Vector3(0, 1.3, 0)  # pivot near shoulder height
		add_child(camera_pivot)
		var camera := Camera3D.new()
		camera.name = "Camera"
		camera.fov = 65.0
		camera_pivot.add_child(camera)
		camera.position = Vector3(0.5, 1.0, camera_distance)  # slight side offset like reference
		camera.look_at_from_position(camera.position, Vector3(0.5, 0.6, 0), Vector3.UP)
		camera_pivot.rotation = Vector3(camera_pitch, camera_yaw, 0)

func _physics_process(delta: float) -> void:
	if not is_local:
		return
	
	if current_vehicle != null:
		# While in vehicle, hide character and don't process movement
		if model:
			model.visible = false
		_handle_vehicle_camera(delta)
		return
	else:
		if model:
			model.visible = true
	
	# Gravity
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	
	# Jump — keyboard or touch button
	var jump_pressed: bool = Input.is_action_just_pressed("jump") or TouchInput.consume_jump()
	if jump_pressed and is_on_floor():
		velocity.y = JUMP_VELOCITY * jump_mult
		_play_anim("Jump", 0.05)
	
	# Camera rotation (keyboard rebind keys, touch drag could be added later)
	if Input.is_action_pressed("camera_left"):
		camera_yaw += delta * 2.0
	if Input.is_action_pressed("camera_right"):
		camera_yaw -= delta * 2.0
	
	# Movement — combine keyboard vector with virtual joystick vector
	var kb_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var touch_dir: Vector2 = TouchInput.movement
	var input_dir: Vector2 = kb_dir
	if touch_dir.length() > 0.05:
		input_dir = touch_dir
	
	var direction := Vector3.ZERO
	var cam_basis := Basis(Vector3.UP, camera_yaw)
	direction = (cam_basis * Vector3(input_dir.x, 0, -input_dir.y)).normalized()
	
	# Sprint — keyboard hold or touch "run" button, gated by energy
	var sprint_request: bool = Input.is_action_pressed("sprint") or TouchInput.sprint_held
	is_sprinting = sprint_request and energy > 0.0 and input_dir.length() > 0.05
	
	if is_sprinting:
		energy = max(0.0, energy - ENERGY_DRAIN_RATE * delta)
	else:
		energy = min(MAX_ENERGY, energy + ENERGY_REGEN_RATE * delta)
	
	var speed := SPRINT_SPEED * speed_mult if is_sprinting else WALK_SPEED * speed_mult
	
	if direction:
		velocity.x = direction.x * speed
		velocity.z = direction.z * speed
		# Rotate model to face movement direction
		var target_angle := atan2(direction.x, direction.z)
		model.rotation.y = lerp_angle(model.rotation.y, target_angle, delta * ROTATION_SPEED)
		# Walk animation
		walk_anim_phase += delta * ANIM_SPEED * (speed / WALK_SPEED)
		_animate_walking()
	else:
		velocity.x = move_toward(velocity.x, 0, speed * delta * 5)
		velocity.z = move_toward(velocity.z, 0, speed * delta * 5)
		_animate_idle()
	
	move_and_slide()
	_update_camera(delta)
	
	# Vehicle enter/exit — keyboard or touch interact button
	if Input.is_action_just_pressed("enter_vehicle") or TouchInput.consume_interact():
		if current_vehicle:
			exit_vehicle()
		else:
			_try_enter_vehicle()

func _play_anim(anim_key: String, blend: float = 0.2) -> void:
	if not _anim_player:
		return
	var full_name := _anim_prefix + anim_key
	if _current_anim == full_name:
		return
	if not _anim_player.has_animation(full_name):
		return
	_anim_player.play(full_name, blend)
	_current_anim = full_name

func _animate_walking() -> void:
	if not model:
		return
	if _anim_player:
		# Real FBX model — pick Run vs Walk clip based on sprint state
		_play_anim("Run" if is_sprinting else "Walk")
		return
	# Procedural brick minifigure fallback
	var leg_l = model.get_meta("leg_l")
	var leg_r = model.get_meta("leg_r")
	var arm_l = model.get_meta("arm_l")
	var arm_r = model.get_meta("arm_r")
	
	if leg_l:
		leg_l.rotation.x = sin(walk_anim_phase) * 0.4
	if leg_r:
		leg_r.rotation.x = -sin(walk_anim_phase) * 0.4
	if arm_l:
		arm_l.rotation.x = -sin(walk_anim_phase) * 0.3
	if arm_r:
		arm_r.rotation.x = sin(walk_anim_phase) * 0.3

func _animate_idle() -> void:
	if not model:
		return
	if _anim_player:
		_play_anim("Idle")
		return
	# Procedural brick minifigure fallback
	var leg_l = model.get_meta("leg_l")
	var leg_r = model.get_meta("leg_r")
	var arm_l = model.get_meta("arm_l")
	var arm_r = model.get_meta("arm_r")
	
	if leg_l: leg_l.rotation.x = lerp(leg_l.rotation.x, 0.0, 0.1)
	if leg_r: leg_r.rotation.x = lerp(leg_r.rotation.x, 0.0, 0.1)
	if arm_l: arm_l.rotation.x = lerp(arm_l.rotation.x, 0.0, 0.1)
	if arm_r: arm_r.rotation.x = lerp(arm_r.rotation.x, 0.0, 0.1)

func _update_camera(delta: float) -> void:
	if not camera_pivot:
		return
	camera_pivot.rotation = Vector3(camera_pitch, camera_yaw, 0)
	var cam = camera_pivot.get_node_or_null("Camera")
	if cam:
		cam.position = Vector3(0.5, 1.0, camera_distance)

func _handle_vehicle_camera(delta: float) -> void:
	if not camera_pivot or not current_vehicle:
		return
	# Position camera behind vehicle
	var target_pos = current_vehicle.global_position
	camera_pivot.global_position = target_pos + Vector3(0, 1, 0)
	camera_yaw = lerp_angle(camera_yaw, current_vehicle.rotation.y + PI, delta * 3.0)
	camera_pivot.rotation = Vector3(camera_pitch - 0.1, camera_yaw, 0)
	var cam = camera_pivot.get_node_or_null("Camera")
	if cam:
		cam.position = Vector3(0, 3, camera_distance + 3)

func _try_enter_vehicle() -> void:
	# Find nearest vehicle within range
	var vehicles = get_tree().get_nodes_in_group("vehicles")
	var nearest: Node3D = null
	var nearest_dist := 5.0
	
	for v in vehicles:
		var d = global_position.distance_to(v.global_position)
		if d < nearest_dist:
			nearest = v
			nearest_dist = d
	
	if nearest:
		current_vehicle = nearest
		nearest.set_meta("driver", self)
		if nearest.has_method("set_driver"):
			nearest.set_driver(self)

func exit_vehicle() -> void:
	if current_vehicle:
		# Position player beside the vehicle
		global_position = current_vehicle.global_position + Vector3(2, 0, 0)
		if current_vehicle.has_method("remove_driver"):
			current_vehicle.remove_driver()
		current_vehicle = null
		if model:
			model.visible = true

