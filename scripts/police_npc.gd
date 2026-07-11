extends CharacterBody3D
class_name PoliceNPC

var target_position: Vector3 = Vector3.ZERO
var chase_speed: float = 7.0
var catch_distance: float = 2.0
var body: MeshInstance3D
var head: MeshInstance3D
var light_bar_red: OmniLight3D
var light_bar_blue: OmniLight3D
var light_timer: float = 0.0
var light_state: bool = false
var caught_player: bool = false
var catch_timer: float = 0.0

func _ready() -> void:
	_build_police()
	add_to_group("police_npcs")

func _build_police() -> void:
	# Body (dark blue police uniform)
	body = MeshInstance3D.new()
	var body_box: BoxMesh = BoxMesh.new()
	body_box.size = Vector3(0.4, 0.5, 0.25)
	body.mesh = body_box
	body.position = Vector3(0, 0.8, 0)
	var body_mat: StandardMaterial3D = StandardMaterial3D.new()
	body_mat.albedo_color = Color(0.1, 0.15, 0.3)  # Police navy
	body.material_override = body_mat
	body.cast_shadow = 2
	add_child(body)

	# Head
	head = MeshInstance3D.new()
	var head_box: BoxMesh = BoxMesh.new()
	head_box.size = Vector3(0.3, 0.3, 0.3)
	head.mesh = head_box
	head.position = Vector3(0, 1.25, 0)
	var head_mat: StandardMaterial3D = StandardMaterial3D.new()
	head_mat.albedo_color = Color(1.0, 0.85, 0.7)
	head.material_override = head_mat
	head.cast_shadow = 2
	add_child(head)

	# Police cap
	var cap: MeshInstance3D = MeshInstance3D.new()
	var cap_box: BoxMesh = BoxMesh.new()
	cap_box.size = Vector3(0.35, 0.12, 0.35)
	cap.mesh = cap_box
	cap.position = Vector3(0, 1.45, 0)
	var cap_mat: StandardMaterial3D = StandardMaterial3D.new()
	cap_mat.albedo_color = Color(0.05, 0.08, 0.2)
	cap.material_override = cap_mat
	add_child(cap)

	# Light bar (red + blue flashing lights on shoulder)
	light_bar_red = OmniLight3D.new()
	light_bar_red.position = Vector3(0.2, 1.5, 0)
	light_bar_red.light_color = Color(1, 0, 0)
	light_bar_red.light_energy = 2.0
	light_bar_red.omni_range = 5.0
	light_bar_red.visible = false
	add_child(light_bar_red)

	light_bar_blue = OmniLight3D.new()
	light_bar_blue.position = Vector3(-0.2, 1.5, 0)
	light_bar_blue.light_color = Color(0, 0, 1)
	light_bar_blue.light_energy = 2.0
	light_bar_blue.omni_range = 5.0
	light_bar_blue.visible = false
	add_child(light_bar_blue)

	# Collision
	var col: CollisionShape3D = CollisionShape3D.new()
	var shape: CapsuleShape3D = CapsuleShape3D.new()
	shape.height = 1.6
	shape.radius = 0.3
	col.shape = shape
	add_child(col)

	# Label
	var label: Label3D = Label3D.new()
	label.text = "POLICE"
	label.font_size = 20
	label.position = Vector3(0, 1.8, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	label.modulate = Color(0.8, 0.8, 0.9)
	add_child(label)

func _physics_process(delta: float) -> void:
	# Flash lights
	light_timer += delta
	if light_timer >= 0.3:
		light_timer = 0.0
		light_state = !light_state
		light_bar_red.visible = light_state
		light_bar_blue.visible = !light_state

	# Chase target
	var dir: Vector3 = (target_position - global_position)
	dir.y = 0
	var dist: float = dir.length()

	if dist > 0.1:
		dir = dir.normalized()
		velocity = dir * chase_speed
		var look_target: Vector3 = global_position + dir
		look_at(look_target, Vector3.UP)
	else:
		velocity = Vector3.ZERO

	# Check if caught player
	if dist < catch_distance:
		catch_timer += delta
		if catch_timer > 1.0 and not caught_player:
			caught_player = true
			_arrest_player()
	else:
		catch_timer = 0.0

	move_and_slide()

func _arrest_player() -> void:
	print("PoliceNPC: Player arrested!")
	# Reset wanted level and teleport player to "jail" (spawn point)
	var wanted: Node = get_tree().get_first_node_in_group("wanted_level")
	if wanted and wanted.has_method("clear_level"):
		wanted.clear_level()

	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player:
		player.global_position = Vector3(0, 1, 0)  # Back to spawn

	# Clear coins as penalty
	if player:
		player.set_meta("coin_count", 0)

	caught_player = false

func set_target(pos: Vector3) -> void:
	target_position = pos
