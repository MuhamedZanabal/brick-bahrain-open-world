extends VehicleBody3D
## BrickVehicle - Drivable car using Kenney CC0 car models
## Handles driving physics, entering/exiting, and multiplayer sync

const MAX_STEER := 0.6
const STEER_SPEED := 3.0
const ENGINE_POWER := 250.0
const BRAKE_POWER := 100.0
const MAX_SPEED := 35.0
const NITRO_BOOST := 1.5

var driver: Node3D = null
var steer_input: float = 0.0
var throttle_input: float = 0.0
var brake_input: float = 0.0
var nitro_active: bool = false
var nitro_timer: float = 0.0
var has_nitro: bool = false
var is_local: bool = true
var car_index: int = 0

var wheel_front_l: VehicleWheel3D
var wheel_front_r: VehicleWheel3D
var wheel_rear_l: VehicleWheel3D
var wheel_rear_r: VehicleWheel3D

func _ready() -> void:
	add_to_group("vehicles")
	
	# Set up vehicle wheels
	_wheel_setup()
	
	# Build car model — use Kenney GLB if available, fallback to procedural
	var model: Node3D = null
	car_index = get_meta("car_index", randi())
	var car_color: Color = get_meta("car_color", Color(0.8, 0.1, 0.1))
	
	if AssetLoader and AssetLoader.get_car_count() > 0:
		model = AssetLoader.spawn_car(car_index, Vector3.ZERO, 0.0)
		if model:
			# Scale the Kenney car model to fit the vehicle body
			model.scale = Vector3(1.0, 1.0, 1.0)
			# Kenney cars might need Y offset to sit on wheels
			model.position = Vector3(0, 0.15, 0)
	
	if model == null:
		# Fallback to procedural brick car
		model = BrickFactory.create_brick_car(car_color, Color(0.15, 0.15, 0.2))
		model.position = Vector3(0, 0.15, 0)
	
	model.name = "Model"
	add_child(model)
	
	# Mass and physics
	mass = 800.0
	gravity_scale = 1.0
	
	# Check driver ability for nitro
	if driver and driver.has_meta("character_data"):
		pass  # Will be set by set_driver

func _wheel_setup() -> void:
	var wheel_data := [
		{"name": "WheelFL", "pos": Vector3(-0.6, 0.2, 0.5), "steer": true, "drive": false},
		{"name": "WheelFR", "pos": Vector3(0.6, 0.2, 0.5), "steer": true, "drive": false},
		{"name": "WheelRL", "pos": Vector3(-0.6, 0.2, -0.5), "steer": false, "drive": true},
		{"name": "WheelRR", "pos": Vector3(0.6, 0.2, -0.5), "steer": false, "drive": true},
	]
	
	for wd in wheel_data:
		var wheel := VehicleWheel3D.new()
		wheel.name = wd.name
		wheel.position = wd.pos
		wheel.use_as_steering = wd.steer
		wheel.use_as_traction = wd.drive
		wheel.suspension_travel = 0.2
		wheel.suspension_stiffness = 40.0
		wheel.damping_compression = 3.0
		wheel.damping_relaxation = 3.0
		wheel.wheel_roll_influence = 0.1
		wheel.wheel_friction_slip = 1.5
		
		# Wheel mesh
		var wheel_mesh := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.2
		cyl.bottom_radius = 0.2
		cyl.height = 0.15
		wheel_mesh.mesh = cyl
		wheel_mesh.rotation = Vector3(deg_to_rad(90), 0, 0)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.08, 0.08, 0.08)
		mat.roughness = 0.8
		wheel_mesh.material_override = mat
		wheel.add_child(wheel_mesh)
		
		add_child(wheel)
	
	wheel_front_l = get_node("WheelFL")
	wheel_front_r = get_node("WheelFR")
	wheel_rear_l = get_node("WheelRL")
	wheel_rear_r = get_node("WheelRR")

func _physics_process(delta: float) -> void:
	if not is_local or not driver:
		# Apply some drag when no driver
		engine_force = 0
		steering = move_toward(steering, 0, delta * STEER_SPEED)
		return
	
	# Input — keyboard + touch
	steer_input = 0.0
	throttle_input = 0.0
	brake_input = 0.0
	
	if Input.is_action_pressed("move_left"):
		steer_input = -1.0
	elif Input.is_action_pressed("move_right"):
		steer_input = 1.0
	
	if Input.is_action_pressed("move_forward"):
		throttle_input = 1.0
	elif Input.is_action_pressed("move_back"):
		throttle_input = -0.5
	
	if Input.is_action_pressed("brake"):
		brake_input = 1.0
	
	# Touch input for vehicle
	if TouchInput:
		steer_input += TouchInput.movement.x * 0.8
		throttle_input += TouchInput.movement.y * -1.0  # forward is negative y on joystick
	
	# Nitro
	if has_nitro and (Input.is_action_just_pressed("sprint") or TouchInput.consume_sprint()):
		nitro_active = true
		nitro_timer = 2.0
	
	if nitro_active:
		nitro_timer -= delta
		if nitro_timer <= 0:
			nitro_active = false
	
	# Apply controls
	var power := ENGINE_POWER
	if nitro_active:
		power *= NITRO_BOOST
	
	# Steering with speed-sensitive reduction
	var speed_factor: float = 1.0 - clamp(linear_velocity.length() / MAX_SPEED, 0, 0.5)
	steering = steer_input * MAX_STEER * speed_factor
	
	# Engine force
	if throttle_input > 0:
		engine_force = throttle_input * power
	elif throttle_input < 0:
		engine_force = throttle_input * power * 0.6
	else:
		engine_force = 0
	
	# Braking
	if brake_input > 0:
		brake = BRAKE_POWER * brake_input
	else:
		brake = 0
	
	# Cap speed
	if linear_velocity.length() > MAX_SPEED * (NITRO_BOOST if nitro_active else 1.0):
		linear_velocity = linear_velocity.normalized() * MAX_SPEED * (NITRO_BOOST if nitro_active else 1.0)

func set_driver(player: Node3D) -> void:
	driver = player
	# Check for nitro ability
	if player and player.has_method("get") and player.character_data:
		if player.character_data.get("ability") == "nitro":
			has_nitro = true

func remove_driver() -> void:
	driver = null
	engine_force = 0
	brake = 50
	has_nitro = false
	nitro_active = false
