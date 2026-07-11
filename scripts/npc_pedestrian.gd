extends CharacterBody3D
class_name NPCPedestrian

# NPC states
enum NPCState { WALKING, FLEEING, IDLING, GREETING }

var state: NPCState = NPCState.WALKING
var walk_speed: float = 2.0
var flee_speed: float = 6.0
var target_position: Vector3 = Vector3.ZERO
var home_position: Vector3 = Vector3.ZERO
var walk_radius: float = 30.0
var change_direction_timer: float = 0.0
var flee_timer: float = 0.0
var greet_timer: float = 0.0
var has_greeted: bool = false
var npc_name: String = ""
var npc_color: Color = Color.WHITE
var model_path: String = ""  # gltf model from assets/characters_kit/, set by NPCManager

# Arabic/Bahraini greetings
const GREETINGS: Array[String] = [
	"Marhaba!",
	"Aloha!",
	"Salam Alaikum!",
	"Kayf halak?",
	"Shlonak?",
	"Yalla!",
	"Hala wallah!",
	"Tasharrafna!",
	"Naice!",
	"Shukran!"
]

# Legacy box-primitive body parts — only built if no model_path is set
var body: MeshInstance3D
var head: MeshInstance3D
var legs: MeshInstance3D
var arms: MeshInstance3D
var label_3d: Label3D

# Real animated character model (assets/characters_kit/*.gltf)
var _model: Node3D = null
var _anim_player: AnimationPlayer = null
var _current_anim: String = ""

func _ready() -> void:
	_build_npc()
	_pick_new_target()
	add_to_group("npc_pedestrians")

func _build_npc() -> void:
	if not model_path.is_empty() and ResourceLoader.exists(model_path):
		_model = BrickFactory.load_character_model(model_path)
	if _model != null:
		_model.name = "Model"
		add_child(_model)
		_anim_player = _model.get_meta("anim_player", null)
		if _anim_player:
			_play_anim("Idle")
	else:
		_build_box_npc()

	# Name/greeting label
	label_3d = Label3D.new()
	label_3d.text = ""
	label_3d.font_size = 24
	label_3d.position = Vector3(0, 2.0, 0)
	label_3d.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label_3d.no_depth_test = true
	label_3d.modulate = Color(1, 1, 0.4)
	add_child(label_3d)

	# Collision
	var col: CollisionShape3D = CollisionShape3D.new()
	var shape: CapsuleShape3D = CapsuleShape3D.new()
	shape.height = 1.6
	shape.radius = 0.3
	col.shape = shape
	col.position = Vector3(0, 0.8, 0) if _model else Vector3.ZERO
	add_child(col)

## Fallback box-primitive figure (used only if a real model fails to load)
func _build_box_npc() -> void:
	body = MeshInstance3D.new()
	var body_box: BoxMesh = BoxMesh.new()
	body_box.size = Vector3(0.4, 0.5, 0.25)
	body.mesh = body_box
	body.position = Vector3(0, 0.8, 0)
	var body_mat: StandardMaterial3D = StandardMaterial3D.new()
	body_mat.albedo_color = npc_color
	body.material_override = body_mat
	body.cast_shadow = 2
	add_child(body)

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

	legs = MeshInstance3D.new()
	var legs_box: BoxMesh = BoxMesh.new()
	legs_box.size = Vector3(0.35, 0.4, 0.25)
	legs.mesh = legs_box
	legs.position = Vector3(0, 0.35, 0)
	var legs_mat: StandardMaterial3D = StandardMaterial3D.new()
	legs_mat.albedo_color = Color(0.2, 0.2, 0.3)
	legs.material_override = legs_mat
	legs.cast_shadow = 2
	add_child(legs)

	arms = MeshInstance3D.new()
	var arms_box: BoxMesh = BoxMesh.new()
	arms_box.size = Vector3(0.15, 0.45, 0.2)
	arms.mesh = arms_box
	arms.position = Vector3(0, 0.8, 0)
	var arms_mat: StandardMaterial3D = StandardMaterial3D.new()
	arms_mat.albedo_color = npc_color
	arms.material_override = arms_mat
	arms.cast_shadow = 2
	add_child(arms)

func _play_anim(anim_key: String, blend: float = 0.2) -> void:
	if not _anim_player:
		return
	if _current_anim == anim_key:
		return
	if not _anim_player.has_animation(anim_key):
		return
	_anim_player.play(anim_key, blend)
	_current_anim = anim_key

func _physics_process(delta: float) -> void:
	match state:
		NPCState.WALKING:
			_process_walking(delta)
		NPCState.FLEEING:
			_process_fleeing(delta)
		NPCState.IDLING:
			_process_idling(delta)
		NPCState.GREETING:
			_process_greeting(delta)

	# Check for nearby fast vehicles
	_check_for_danger()

	# Check for nearby player for greeting
	_check_for_player_greeting()

	move_and_slide()

func _process_walking(delta: float) -> void:
	change_direction_timer -= delta
	if change_direction_timer <= 0 or global_position.distance_to(target_position) < 2.0:
		_pick_new_target()
		change_direction_timer = randf_range(3.0, 8.0)

	var dir: Vector3 = (target_position - global_position)
	dir.y = 0
	dir = dir.normalized()
	velocity = dir * walk_speed
	_play_anim("Walk")
	# Face direction
	if dir.length() > 0.01:
		var look_target: Vector3 = global_position + dir
		look_at(look_target, Vector3.UP)

func _process_fleeing(delta: float) -> void:
	flee_timer -= delta
	if flee_timer <= 0:
		state = NPCState.WALKING
		label_3d.text = ""
		return

	var dir: Vector3 = (global_position - target_position)
	dir.y = 0
	dir = dir.normalized()
	velocity = dir * flee_speed
	_play_anim("Run")
	if dir.length() > 0.01:
		var look_target: Vector3 = global_position + dir
		look_at(look_target, Vector3.UP)

func _process_idling(delta: float) -> void:
	velocity = Vector3.ZERO
	_play_anim("Idle")
	change_direction_timer -= delta
	if change_direction_timer <= 0:
		state = NPCState.WALKING
		_pick_new_target()

func _process_greeting(delta: float) -> void:
	velocity = Vector3.ZERO
	_play_anim("Victory")
	greet_timer -= delta
	if greet_timer <= 0:
		state = NPCState.WALKING
		label_3d.text = ""

func _pick_new_target() -> void:
	var angle: float = randf() * TAU
	var dist: float = randf_range(10.0, walk_radius)
	target_position = home_position + Vector3(cos(angle) * dist, 0, sin(angle) * dist)
	# Occasionally idle
	if randf() < 0.2:
		state = NPCState.IDLING
		change_direction_timer = randf_range(2.0, 5.0)

func _check_for_danger() -> void:
	var vehicles: Array[Node] = get_tree().get_nodes_in_group("vehicles")
	for v in vehicles:
		if v is RigidBody3D:
			var dist: float = global_position.distance_to(v.global_position)
			if dist < 8.0 and v.linear_velocity.length() > 10.0:
				state = NPCState.FLEEING
				target_position = v.global_position  # Flee FROM this position
				flee_timer = 3.0
				label_3d.text = "!"
				return

func _check_for_player_greeting() -> void:
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player == null:
		return
	var dist: float = global_position.distance_to(player.global_position)
	if dist < 4.0 and not has_greeted and state != NPCState.FLEEING:
		state = NPCState.GREETING
		greet_timer = 3.0
		has_greeted = true
		label_3d.text = GREETINGS[randi() % GREETINGS.size()]
		# Reset greeting after some time
		get_tree().create_timer(15.0).timeout.connect(func(): has_greeted = false)
	elif dist > 10.0 and has_greeted:
		has_greeted = false

func set_npc_color(color: Color) -> void:
	npc_color = color
	if body:
		var mat: StandardMaterial3D = StandardMaterial3D.new()
		mat.albedo_color = color
		body.material_override = mat
		arms.material_override = mat
