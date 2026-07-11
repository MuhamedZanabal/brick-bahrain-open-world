extends Node
## BrickFactory - Autoload singleton

# Preloaded shaders for toy plastic + outline look
var _toy_plastic_shader: Shader
var _outline_shader: Shader
## Creates brick-style 3D meshes procedurally. Every building, vehicle, character
## is built from these brick primitives — giving the game its signature look.

# Standard brick dimensions (in meters)
const BRICK_UNIT := 0.08
const STUD_RADIUS := 0.024
const STUD_HEIGHT := 0.016
const PLATE_HEIGHT := BRICK_UNIT * 0.4
const BRICK_HEIGHT := BRICK_UNIT * 1.2

var _brick_mesh: BoxMesh
var _stud_mesh: CylinderMesh
var _mesh_cache: Dictionary = {}

func _ready() -> void:
	_toy_plastic_shader = load("res://addons/flexible_toon_shader/flexible_toon.gdshader")
	_outline_shader = load("res://shaders/outline.gdshader")
	_brick_mesh = BoxMesh.new()
	_brick_mesh.size = Vector3(1, 1, 1)
	_stud_mesh = CylinderMesh.new()
	_stud_mesh.top_radius = STUD_RADIUS
	_stud_mesh.bottom_radius = STUD_RADIUS
	_stud_mesh.height = STUD_HEIGHT

## Create a single brick instance with optional studs
func create_brick(size: Vector3, color: Color, with_studs: bool = true, stud_grid: Vector2i = Vector2i(2, 2)) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = _brick_mesh
	mi.scale = size
	# Scale is baked into the mesh via the instance transform
	mi.scale = Vector3.ONE
	# Create a properly sized box mesh
	var box := BoxMesh.new()
	box.size = size
	mi.mesh = box
	
	# Use Flexible Toon Shader (MIT) for LEGO-style cel-shaded look
	var mat := ShaderMaterial.new()
	mat.shader = _toy_plastic_shader
	mat.set_shader_parameter("albedo", Color(color.r, color.g, color.b, 1.0))
	mat.set_shader_parameter("cuts", 3)
	mat.set_shader_parameter("wrap", 0.05)
	mat.set_shader_parameter("steepness", 2.0)
	mat.set_shader_parameter("use_attenuation", true)
	mat.set_shader_parameter("use_specular", true)
	mat.set_shader_parameter("specular_strength", 0.8)
	mat.set_shader_parameter("specular_shininess", 20.0)
	mat.set_shader_parameter("use_rim", true)
	mat.set_shader_parameter("rim_width", 6.0)
	mat.set_shader_parameter("rim_color", Color(1.0, 0.95, 0.8, 0.3))
	mat.set_shader_parameter("use_borders", false)
	mi.material_override = mat
	
	# Add outline as second pass for that toy/LEGO outline look
	var outline_mat := ShaderMaterial.new()
	outline_mat.shader = _outline_shader
	outline_mat.set_shader_parameter("outline_color", Color(0.05, 0.04, 0.03, 1.0))
	outline_mat.set_shader_parameter("outline_size", 1.012)
	mat.next_pass = outline_mat
	
	mi.cast_shadow = 2
	mi.gi_mode = GeometryInstance3D.GI_MODE_STATIC
	
	if with_studs:
		_add_studs_to_brick(mi, size, color, stud_grid)
	
	return mi

func _add_studs_to_brick(parent: MeshInstance3D, brick_size: Vector3, color: Color, grid: Vector2i) -> void:
	var stud_spacing_x := brick_size.x / float(grid.x)
	var stud_spacing_z := brick_size.z / float(grid.y)
	var start_x := -brick_size.x / 2.0 + stud_spacing_x / 2.0
	var start_z := -brick_size.z / 2.0 + stud_spacing_z / 2.0
	var top_y := brick_size.y / 2.0 + STUD_HEIGHT / 2.0
	
	# Use Flexible Toon Shader for studs — tighter bands, more specular
	var mat := ShaderMaterial.new()
	mat.shader = _toy_plastic_shader
	mat.set_shader_parameter("albedo", Color(color.r, color.g, color.b, 1.0))
	mat.set_shader_parameter("cuts", 4)
	mat.set_shader_parameter("wrap", 0.02)
	mat.set_shader_parameter("steepness", 3.0)
	mat.set_shader_parameter("use_attenuation", true)
	mat.set_shader_parameter("use_specular", true)
	mat.set_shader_parameter("specular_strength", 1.0)
	mat.set_shader_parameter("specular_shininess", 28.0)
	mat.set_shader_parameter("use_rim", true)
	mat.set_shader_parameter("rim_width", 4.0)
	mat.set_shader_parameter("rim_color", Color(1.0, 1.0, 0.9, 0.4))
	mat.set_shader_parameter("use_borders", false)
	
	for ix in range(grid.x):
		for iz in range(grid.y):
			var stud := MeshInstance3D.new()
			stud.mesh = _stud_mesh
			stud.material_override = mat
			stud.position = Vector3(start_x + ix * stud_spacing_x, top_y, start_z + iz * stud_spacing_z)
			stud.cast_shadow = 2
			parent.add_child(stud)

## Create a building from stacked bricks
func create_building(width: float, depth: float, height: float, base_color: Color, accent_color: Color = Color(0.3, 0.3, 0.3), window_color: Color = Color(0.5, 0.7, 1.0, 0.8)) -> Node3D:
	var building := Node3D.new()
	var brick_h := BRICK_HEIGHT * 3  # tall brick
	var current_y := brick_h / 2.0
	var layer := 0
	
	while current_y < height:
		var is_accent := layer % 4 == 3
		var brick_color := base_color if not is_accent else accent_color
		var row_h := brick_h if layer % 3 != 2 else BRICK_HEIGHT
		
		# Main walls
		var wall_brick := create_brick(Vector3(width, row_h, depth), brick_color, true, Vector2i(int(width / 0.5), int(depth / 0.5)))
		wall_brick.position = Vector3(0, current_y, 0)
		building.add_child(wall_brick)
		
		# Window row every 3rd layer
		if layer % 3 == 1 and layer > 0:
			_add_windows(building, width, depth, current_y, window_color)
		
		current_y += row_h
		layer += 1
	
	# Roof
	var roof := create_brick(Vector3(width + 0.1, BRICK_HEIGHT, depth + 0.1), accent_color.darkened(0.2), true, Vector2i(int(width / 0.5), int(depth / 0.5)))
	roof.position = Vector3(0, height, 0)
	building.add_child(roof)
	
	return building

func _add_windows(building: Node3D, width: float, depth: float, y: float, window_color: Color) -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = window_color
	mat.emission = window_color * 0.6
	mat.emission_energy_multiplier = 1.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.metalness = 0.5
	mat.metallic_specular = 0.8
	mat.roughness = 0.15
	mat.clearcoat_enabled = true
	mat.clearcoat = 0.7
	
	var win_size := 0.3
	var num_windows_x := int(width / 0.8)
	var num_windows_z := int(depth / 0.8)
	
	for i in range(num_windows_x):
		var x := -width/2 + 0.4 + i * 0.8
		for side_z in [depth/2 + 0.01, -depth/2 - 0.01]:
			var win := MeshInstance3D.new()
			var box := BoxMesh.new()
			box.size = Vector3(win_size, win_size, 0.05)
			win.mesh = box
			win.material_override = mat
			win.position = Vector3(x, y, side_z)
			win.cast_shadow = 0
			building.add_child(win)
	
	for i in range(num_windows_z):
		var z := -depth/2 + 0.4 + i * 0.8
		for side_x in [width/2 + 0.01, -width/2 - 0.01]:
			var win := MeshInstance3D.new()
			var box := BoxMesh.new()
			box.size = Vector3(0.05, win_size, win_size)
			win.mesh = box
			win.material_override = mat
			win.position = Vector3(side_x, y, z)
			win.cast_shadow = 0
			building.add_child(win)

## Create a tower (for Manama skyline)
func create_tower(width: float, depth: float, height: float, color: Color, has_crown: bool = false) -> Node3D:
	var tower := Node3D.new()
	var sections := int(height / 5.0)
	var current_w := width
	var current_d := depth
	var current_y := 0.0
	
	for s in range(sections):
		var section_h := 5.0
		var is_glass := s % 2 == 1
		var section_color := color if not is_glass else color.lightened(0.15)
		var section := create_brick(Vector3(current_w, section_h, current_d), section_color, true, Vector2i(4, 4))
		section.position = Vector3(0, current_y + section_h/2, 0)
		tower.add_child(section)
		
		# Glass facade
		if is_glass:
			var glass_mat := StandardMaterial3D.new()
			glass_mat.albedo_color = Color(0.25, 0.45, 0.75, 0.45)
			glass_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			glass_mat.metalness = 0.9
			glass_mat.metallic_specular = 1.0
			glass_mat.roughness = 0.02
			glass_mat.clearcoat_enabled = true
			glass_mat.clearcoat = 1.0
			glass_mat.clearcoat_roughness = 0.01
			glass_mat.emission = Color(0.15, 0.25, 0.4)
			glass_mat.emission_energy_multiplier = 0.4
			section.material_override = glass_mat
		
		current_y += section_h
		# Slight taper
		if s > sections / 3:
			current_w = max(width * 0.6, current_w - 0.1)
			current_d = max(depth * 0.6, current_d - 0.1)
	
	if has_crown:
		var crown := create_brick(Vector3(current_w * 0.8, 3.0, current_d * 0.8), color.lightened(0.3), true, Vector2i(3, 3))
		crown.position = Vector3(0, current_y + 1.5, 0)
		tower.add_child(crown)
		# Antenna spire
		var spire := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.05
		cyl.bottom_radius = 0.15
		cyl.height = 8.0
		spire.mesh = cyl
		var spire_mat := StandardMaterial3D.new()
		spire_mat.albedo_color = Color(0.8, 0.8, 0.85)
		spire_mat.metalness = 0.8
		spire.material_override = spire_mat
		spire.position = Vector3(0, current_y + 7.0, 0)
		tower.add_child(spire)
	
	return tower

## Create a road segment
func create_road(width: float, length: float) -> Node3D:
	var group := Node3D.new()
	
	# Road surface
	var road := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(width, 0.05, length)
	road.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.14, 0.14, 0.16)
	mat.roughness = 0.85
	mat.clearcoat_enabled = true
	mat.clearcoat = 0.2
	mat.clearcoat_roughness = 0.4
	road.material_override = mat
	road.cast_shadow = 2
	road.gi_mode = GeometryInstance3D.GI_MODE_STATIC
	group.add_child(road)
	
	# Center yellow dashed line
	var dash_count := int(length / 4.0)
	for i in range(dash_count):
		var dash := MeshInstance3D.new()
		var dash_box := BoxMesh.new()
		dash_box.size = Vector3(0.2, 0.06, 2.0)
		dash.mesh = dash_box
		var dash_mat := StandardMaterial3D.new()
		dash_mat.albedo_color = Color(0.9, 0.75, 0.1)
		dash_mat.emission = Color(0.5, 0.4, 0.05)
		dash_mat.emission_energy_multiplier = 0.3
		dash_mat.roughness = 0.5
		dash.material_override = dash_mat
		dash.position = Vector3(0, 0.03, -length/2 + i * 4.0 + 2.0)
		dash.cast_shadow = 0
		group.add_child(dash)
	
	# White edge lines
	for side in [width/2 - 0.15, -width/2 + 0.15]:
		var edge := MeshInstance3D.new()
		var edge_box := BoxMesh.new()
		edge_box.size = Vector3(0.1, 0.06, length)
		edge.mesh = edge_box
		var edge_mat := StandardMaterial3D.new()
		edge_mat.albedo_color = Color(0.85, 0.85, 0.85)
		edge_mat.roughness = 0.5
		edge.material_override = edge_mat
		edge.position = Vector3(side, 0.03, 0)
		edge.cast_shadow = 0
		group.add_child(edge)
	
	return group

## Create a tree (palm tree style for Bahrain)
func create_palm_tree() -> Node3D:
	var tree := Node3D.new()
	
	# Trunk - stacked brown bricks with slight lean
	var trunk_color := Color(0.5, 0.32, 0.15)
	for i in range(8):
		var seg := create_brick(Vector3(0.3, 0.5, 0.3), trunk_color, true, Vector2i(1, 1))
		seg.position = Vector3(0, 0.25 + i * 0.5, 0)
		# Slight curve
		seg.position.x = sin(float(i) * 0.15) * 0.1
		tree.add_child(seg)
	
	# Palm fronds - vibrant green bricks radiating outward
	var leaf_color := Color(0.18, 0.55, 0.18)
	for i in range(8):
		var angle := i * (PI / 4.0)
		var leaf := create_brick(Vector3(2.5, 0.15, 0.5), leaf_color, false)
		leaf.position = Vector3(cos(angle) * 1.2, 4.3, sin(angle) * 1.2)
		leaf.rotation = Vector3(deg_to_rad(-25), angle, deg_to_rad(5))
		tree.add_child(leaf)
		# Second frond layer slightly lower
		var leaf2 := create_brick(Vector3(2.0, 0.12, 0.4), leaf_color.lightened(0.1), false)
		leaf2.position = Vector3(cos(angle + 0.2) * 1.0, 4.0, sin(angle + 0.2) * 1.0)
		leaf2.rotation = Vector3(deg_to_rad(-15), angle + 0.2, 0)
		tree.add_child(leaf2)
	
	# Top dome
	var top := create_brick(Vector3(0.5, 0.3, 0.5), leaf_color, true, Vector2i(2, 2))
	top.position = Vector3(0, 4.3, 0)
	tree.add_child(top)
	
	return tree

## Create ground terrain
func create_ground(size: float, color: Color) -> MeshInstance3D:
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(size, size)
	ground.mesh = plane
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	mat.metallic_specular = 0.3
	mat.clearcoat_enabled = true
	mat.clearcoat = 0.1
	mat.clearcoat_roughness = 0.6
	ground.material_override = mat
	ground.cast_shadow = 2
	ground.gi_mode = GeometryInstance3D.GI_MODE_STATIC
	return ground

## Create water surface
func create_water(size: float) -> MeshInstance3D:
	var water := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(size, size)
	water.mesh = plane
	water.position.y = 0.0
	# Cartoon 3D Water shader (CC0) — toon water with waves + outlines
	var water_shader := load("res://shaders/cartoon_water.gdshader")
	var mat := ShaderMaterial.new()
	mat.shader = water_shader
	mat.set_shader_parameter("wave_amplitude", 0.04)
	mat.set_shader_parameter("wave_frequency", 8.0)
	mat.set_shader_parameter("wave_speed", 1.2)
	mat.set_shader_parameter("seamless", true)
	mat.set_shader_parameter("_speed", 0.8)
	mat.set_shader_parameter("_scale", 2.5)
	mat.set_shader_parameter("color_deep", Color(0.04, 0.2, 0.5, 0.85))
	mat.set_shader_parameter("color_shallow", Color(0.3, 0.7, 0.9, 0.5))
	mat.set_shader_parameter("color_threshold", 0.45)
	mat.set_shader_parameter("outline_enabled", true)
	mat.set_shader_parameter("outline_color", Color(0.0, 0.0, 0.0, 0.8))
	mat.set_shader_parameter("outline_thickness", 0.03)
	water.material_override = mat
	water.cast_shadow = 0
	return water

## Create a minifigure character model
func create_minifigure(char_data: Dictionary) -> Node3D:
	var fig := Node3D.new()
	var body_color: Color = char_data.get("body_color", Color(0.5, 0.5, 0.5))
	var head_color: Color = char_data.get("head_color", Color(1.0, 0.8, 0.6))
	var hair_color: Color = char_data.get("hair_color", Color(0.1, 0.1, 0.1))
	
	# Legs
	var leg_l := create_brick(Vector3(0.18, 0.35, 0.22), Color(0.15, 0.15, 0.2), true, Vector2i(1, 1))
	leg_l.position = Vector3(-0.1, 0.175, 0)
	fig.add_child(leg_l)
	
	var leg_r := create_brick(Vector3(0.18, 0.35, 0.22), Color(0.15, 0.15, 0.2), true, Vector2i(1, 1))
	leg_r.position = Vector3(0.1, 0.175, 0)
	fig.add_child(leg_r)
	
	# Hip
	var hip := create_brick(Vector3(0.4, 0.12, 0.24), body_color.darkened(0.2), true, Vector2i(2, 1))
	hip.position = Vector3(0, 0.41, 0)
	fig.add_child(hip)
	
	# Torso
	var torso := create_brick(Vector3(0.4, 0.5, 0.24), body_color, true, Vector2i(2, 1))
	torso.position = Vector3(0, 0.72, 0)
	fig.add_child(torso)
	
	# Arms
	var arm_l := create_brick(Vector3(0.12, 0.45, 0.16), body_color, true, Vector2i(1, 1))
	arm_l.position = Vector3(-0.27, 0.72, 0)
	fig.add_child(arm_l)
	
	var arm_r := create_brick(Vector3(0.12, 0.45, 0.16), body_color, true, Vector2i(1, 1))
	arm_r.position = Vector3(0.27, 0.72, 0)
	fig.add_child(arm_r)
	
	# Hands
	var hand_l := create_brick(Vector3(0.12, 0.1, 0.14), Color(1.0, 0.8, 0.6), false)
	hand_l.position = Vector3(-0.27, 0.5, 0)
	fig.add_child(hand_l)
	
	var hand_r := create_brick(Vector3(0.12, 0.1, 0.14), Color(1.0, 0.8, 0.6), false)
	hand_r.position = Vector3(0.27, 0.5, 0)
	fig.add_child(hand_r)
	
	# Neck
	var neck := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.06
	cyl.bottom_radius = 0.06
	cyl.height = 0.08
	neck.mesh = cyl
	var neck_mat := StandardMaterial3D.new()
	neck_mat.albedo_color = head_color
	neck.material_override = neck_mat
	neck.position = Vector3(0, 1.02, 0)
	fig.add_child(neck)
	
	# Head
	var head := create_brick(Vector3(0.35, 0.35, 0.35), head_color, true, Vector2i(2, 2))
	head.position = Vector3(0, 1.23, 0)
	fig.add_child(head)
	
	# Face - eyes
	var eye_mat := StandardMaterial3D.new()
	eye_mat.albedo_color = Color.WHITE
	for eye_x in [-0.08, 0.08]:
		var eye := MeshInstance3D.new()
		var eye_box := BoxMesh.new()
		eye_box.size = Vector3(0.05, 0.06, 0.02)
		eye.mesh = eye_box
		eye.material_override = eye_mat
		eye.position = Vector3(eye_x, 1.25, 0.18)
		fig.add_child(eye)
		
		# Pupil
		var pupil := MeshInstance3D.new()
		var p_box := BoxMesh.new()
		p_box.size = Vector3(0.02, 0.03, 0.01)
		pupil.mesh = p_box
		var p_mat := StandardMaterial3D.new()
		p_mat.albedo_color = Color(0.05, 0.05, 0.1)
		pupil.material_override = p_mat
		pupil.position = Vector3(eye_x, 1.25, 0.19)
		fig.add_child(pupil)
	
	# Smile
	var smile := MeshInstance3D.new()
	var s_box := BoxMesh.new()
	s_box.size = Vector3(0.12, 0.02, 0.02)
	smile.mesh = s_box
	var s_mat := StandardMaterial3D.new()
	s_mat.albedo_color = Color(0.05, 0.05, 0.05)
	smile.material_override = s_mat
	smile.position = Vector3(0, 1.16, 0.18)
	fig.add_child(smile)
	
	# Hair
	var hair := create_brick(Vector3(0.38, 0.12, 0.38), hair_color, true, Vector2i(2, 2))
	hair.position = Vector3(0, 1.46, 0)
	fig.add_child(hair)
	
	# Store references for animation
	fig.set_meta("leg_l", leg_l)
	fig.set_meta("leg_r", leg_r)
	fig.set_meta("arm_l", arm_l)
	fig.set_meta("arm_r", arm_r)
	fig.set_meta("torso", torso)
	
	return fig

## Cache of loaded FBX character scenes so we don't re-parse from disk per spawn
var _character_scene_cache: Dictionary = {}

## Load a real animated character model (Quaternius Ultimate Animated Character
## Pack, CC0) instead of a procedural brick minifigure. Returns null if the
## path doesn't exist or fails to load, so callers can fall back gracefully.
## The returned node has:
##   - meta "anim_player": the AnimationPlayer driving the model
##   - meta "anim_prefix": the string prefix used before each animation name
##     (e.g. "CharacterArmature|" so callers can do anim_prefix + "Walk")
##   - meta "using_fbx_model": true
func load_character_model(model_path: String) -> Node3D:
	if model_path.is_empty():
		return null
	if not ResourceLoader.exists(model_path):
		push_warning("BrickFactory: character model not found: " + model_path)
		return null
	
	var scene: PackedScene = _character_scene_cache.get(model_path)
	if scene == null:
		scene = load(model_path)
		if scene == null:
			return null
		_character_scene_cache[model_path] = scene
	
	var inst: Node3D = scene.instantiate()
	if inst == null:
		return null
	
	# Some FBX exports include empty organizational MeshInstance3D nodes
	# (sockets/anchors) with no mesh resource assigned — Godot's renderer
	# throws "Parameter m is null" trying to compute their AABB the moment
	# they enter the tree. queue_free() is deferred (still present when this
	# instance gets add_child'd moments later), so remove them immediately
	# instead while inst is still an orphaned, not-yet-in-tree subtree.
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null:
			mi.get_parent().remove_child(mi)
			mi.free()
	
	var anim_player: AnimationPlayer = inst.find_child("AnimationPlayer", true, false)
	inst.set_meta("using_fbx_model", true)
	if anim_player:
		inst.set_meta("anim_player", anim_player)
		# Figure out the animation name prefix, e.g. "CharacterArmature|Idle"
		var lib_list := anim_player.get_animation_library_list()
		var prefix := ""
		for lib_name in lib_list:
			var lib: AnimationLibrary = anim_player.get_animation_library(lib_name)
			var anims := lib.get_animation_list()
			if anims.size() > 0:
				var first: String = anims[0]
				var pipe_idx := first.find("|")
				if pipe_idx != -1:
					prefix = first.substr(0, pipe_idx + 1)
				break
		inst.set_meta("anim_prefix", prefix)
	
	# Calibrate scale: the glTF character kit (assets/characters_kit/) is
	# authored at ~2.0m rest height; scale down to a natural ~1.7m so it
	# matches the player capsule collision (height 1.6) and vehicle seats.
	# Legacy FBX models (assets/characters/fbx/) have broken/degenerate
	# skeleton rest poses on import (bones collapse near origin) — kept
	# on disk for reference but no longer used by the character roster.
	if model_path.begins_with("res://assets/characters_kit/"):
		inst.scale = Vector3.ONE * 0.85
	
	return inst

## Create a brick car
func create_brick_car(body_color: Color = Color(0.8, 0.1, 0.1), roof_color: Color = Color(0.15, 0.15, 0.2)) -> Node3D:
	var car := Node3D.new()
	
	# Chassis
	var chassis := create_brick(Vector3(1.8, 0.3, 0.9), Color(0.1, 0.1, 0.12), true, Vector2i(4, 2))
	chassis.position = Vector3(0, 0.35, 0)
	car.add_child(chassis)
	
	# Body
	var body := create_brick(Vector3(1.6, 0.4, 0.85), body_color, true, Vector2i(4, 2))
	body.position = Vector3(0, 0.7, 0)
	car.add_child(body)
	
	# Cabin/roof
	var roof := create_brick(Vector3(1.0, 0.35, 0.8), roof_color, true, Vector2i(2, 2))
	roof.position = Vector3(-0.1, 1.07, 0)
	car.add_child(roof)
	
	# Windshield
	var wind_mat := StandardMaterial3D.new()
	wind_mat.albedo_color = Color(0.2, 0.4, 0.7, 0.4)
	wind_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	wind_mat.metalness = 0.9
	wind_mat.metallic_specular = 1.0
	wind_mat.roughness = 0.02
	wind_mat.clearcoat_enabled = true
	wind_mat.clearcoat = 1.0
	wind_mat.clearcoat_roughness = 0.01
	
	var windshield := MeshInstance3D.new()
	var w_box := BoxMesh.new()
	w_box.size = Vector3(0.05, 0.35, 0.75)
	windshield.mesh = w_box
	windshield.material_override = wind_mat
	windshield.position = Vector3(0.5, 1.07, 0)
	windshield.rotation = Vector3(0, 0, deg_to_rad(-25))
	car.add_child(windshield)
	
	# Wheels
	var wheel_mat := StandardMaterial3D.new()
	wheel_mat.albedo_color = Color(0.08, 0.08, 0.08)
	wheel_mat.roughness = 0.8
	
	for pos in [Vector3(-0.6, 0.2, 0.5), Vector3(-0.6, 0.2, -0.5), Vector3(0.6, 0.2, 0.5), Vector3(0.6, 0.2, -0.5)]:
		var wheel := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.2
		cyl.bottom_radius = 0.2
		cyl.height = 0.15
		wheel.mesh = cyl
		wheel.material_override = wheel_mat
		wheel.position = pos
		wheel.rotation = Vector3(deg_to_rad(90), 0, 0)
		wheel.set_meta("is_wheel", true)
		car.add_child(wheel)
	
	# Headlights
	var light_mat := StandardMaterial3D.new()
	light_mat.albedo_color = Color(1, 1, 0.8)
	light_mat.emission = Color(1, 1, 0.8)
	light_mat.emission_energy_multiplier = 1.5
	
	for z in [0.3, -0.3]:
		var light := MeshInstance3D.new()
		var l_box := BoxMesh.new()
		l_box.size = Vector3(0.08, 0.1, 0.12)
		light.mesh = l_box
		light.material_override = light_mat
		light.position = Vector3(0.85, 0.65, z)
		car.add_child(light)
	
	# Taillights
	var tail_mat := StandardMaterial3D.new()
	tail_mat.albedo_color = Color(1, 0.1, 0.05)
	tail_mat.emission = Color(1, 0.1, 0.05)
	tail_mat.emission_energy_multiplier = 1.0
	
	for z in [0.3, -0.3]:
		var light := MeshInstance3D.new()
		var l_box := BoxMesh.new()
		l_box.size = Vector3(0.06, 0.08, 0.1)
		light.mesh = l_box
		light.material_override = tail_mat
		light.position = Vector3(-0.85, 0.65, z)
		car.add_child(light)
	
	return car
