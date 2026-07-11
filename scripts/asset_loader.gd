extends Node
## AssetLoader - Autoload singleton
## Loads Kenney CC0 GLB models and applies toon/brick shading to match the game aesthetic.
## All external models go through here so materials are consistent.

# Preloaded scene references
const BUILDING_PATHS: Array[String] = [
	"res://assets/external/buildings/building-a.glb",
	"res://assets/external/buildings/building-b.glb",
	"res://assets/external/buildings/building-c.glb",
	"res://assets/external/buildings/building-d.glb",
	"res://assets/external/buildings/building-e.glb",
	"res://assets/external/buildings/building-f.glb",
	"res://assets/external/buildings/building-g.glb",
	"res://assets/external/buildings/building-h.glb",
	"res://assets/external/buildings/building-i.glb",
	"res://assets/external/buildings/building-j.glb",
	"res://assets/external/buildings/building-k.glb",
	"res://assets/external/buildings/building-l.glb",
	"res://assets/external/buildings/building-m.glb",
	"res://assets/external/buildings/building-n.glb",
]

const SKYSCRAPER_PATHS: Array[String] = [
	"res://assets/external/buildings/building-skyscraper-a.glb",
	"res://assets/external/buildings/building-skyscraper-b.glb",
	"res://assets/external/buildings/building-skyscraper-c.glb",
	"res://assets/external/buildings/building-skyscraper-d.glb",
]

const CAR_PATHS: Array[String] = [
	"res://assets/external/cars/sedan.glb",
	"res://assets/external/cars/sedan-sports.glb",
	"res://assets/external/cars/hatchback-sports.glb",
	"res://assets/external/cars/suv.glb",
	"res://assets/external/cars/suv-luxury.glb",
	"res://assets/external/cars/van.glb",
	"res://assets/external/cars/truck.glb",
	"res://assets/external/cars/taxi.glb",
	"res://assets/external/cars/race.glb",
	"res://assets/external/cars/police.glb",
]

const PALM_PATHS: Array[String] = [
	"res://assets/external/nature/tree_palm.glb",
	"res://assets/external/nature/tree_palmBend.glb",
	"res://assets/external/nature/tree_palmTall.glb",
	"res://assets/external/nature/tree_palmShort.glb",
	"res://assets/external/nature/tree_palmDetailedTall.glb",
	"res://assets/external/nature/tree_palmDetailedShort.glb",
]

const TREE_PATHS: Array[String] = [
	"res://assets/external/nature/tree_default.glb",
	"res://assets/external/nature/tree_oak.glb",
	"res://assets/external/nature/tree_small.glb",
	"res://assets/external/nature/tree_tall.glb",
]

const NATURE_PATHS: Array[String] = [
	"res://assets/external/nature/cactus_short.glb",
	"res://assets/external/nature/cactus_tall.glb",
	"res://assets/external/nature/flower_redA.glb",
	"res://assets/external/nature/flower_yellowA.glb",
]

const ROAD_PATHS: Dictionary = {
	"straight": "res://assets/external/roads/road-straight.glb",
	"bend": "res://assets/external/roads/road-bend.glb",
	"bridge": "res://assets/external/roads/road-bridge.glb",
}

# Cached loaded scenes
var _building_scenes: Array[PackedScene] = []
var _skyscraper_scenes: Array[PackedScene] = []
var _car_scenes: Array[PackedScene] = []
var _palm_scenes: Array[PackedScene] = []
var _tree_scenes: Array[PackedScene] = []
var _nature_scenes: Array[PackedScene] = []
var _road_scenes: Dictionary = {}

# Toon shader (loaded lazily)
var _toon_shader: Shader = null
var _outline_shader: Shader = null

func _ready() -> void:
	_load_all()

func _load_all() -> void:
	# Load toon shader
	_toon_shader = load("res://shaders/flexible_toon.gdshader")
	_outline_shader = load("res://shaders/outline.gdshader")
	
	# Load building scenes
	for path in BUILDING_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_building_scenes.append(scene)
	
	# Load skyscraper scenes
	for path in SKYSCRAPER_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_skyscraper_scenes.append(scene)
	
	# Load car scenes
	for path in CAR_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_car_scenes.append(scene)
	
	# Load palm scenes
	for path in PALM_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_palm_scenes.append(scene)
	
	# Load tree scenes
	for path in TREE_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_tree_scenes.append(scene)
	
	# Load nature scenes
	for path in NATURE_PATHS:
		var scene: PackedScene = load(path) as PackedScene
		if scene:
			_nature_scenes.append(scene)
	
	# Load road scenes
	for key in ROAD_PATHS:
		var scene: PackedScene = load(ROAD_PATHS[key]) as PackedScene
		if scene:
			_road_scenes[key] = scene
	
	print("[AssetLoader] Loaded %d buildings, %d skyscrapers, %d cars, %d palms, %d trees, %d nature, %d roads" % [
		_building_scenes.size(), _skyscraper_scenes.size(), _car_scenes.size(),
		_palm_scenes.size(), _tree_scenes.size(), _nature_scenes.size(), _road_scenes.size()
	])

## Apply toon shader to all meshes in a node (recursive)
func apply_toon_materials(node: Node, override_color: Color = Color.TRANSPARENT) -> void:
	_apply_toon_recursive(node, override_color)

func _apply_toon_recursive(node: Node, override_color: Color) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		var mesh := mi.mesh
		if mesh == null:
			return
		
		# Try to get the original material to sample its color
		var orig_color := override_color
		if orig_color == Color.TRANSPARENT:
			var surf_count := mesh.get_surface_count()
			if surf_count > 0:
				var mat := mi.get_surface_override_material(0)
				if mat == null:
					mat = mesh.surface_get_material(0)
				if mat and mat is StandardMaterial3D:
					orig_color = (mat as StandardMaterial3D).albedo_color
				elif mat and mat is ORMMaterial3D:
					orig_color = (mat as ORMMaterial3D).albedo_color
			if orig_color == Color.TRANSPARENT:
				orig_color = Color(0.7, 0.7, 0.7)
		
		# Create toon material
		var toon_mat: Material = _create_toon_material(orig_color)
		mi.material_override = toon_mat
		mi.cast_shadow = 1
		
		# Add outline as second pass
		if _outline_shader:
			var outline_mat := ShaderMaterial.new()
			outline_mat.shader = _outline_shader
			outline_mat.render_priority = 100
			if mi.material_override:
				mi.material_override.next_pass = outline_mat
			else:
				mi.material_override = outline_mat
	
	for child in node.get_children():
		_apply_toon_recursive(child, override_color)

func _create_toon_material(color: Color) -> Material:
	if _toon_shader:
		var mat := ShaderMaterial.new()
		mat.shader = _toon_shader
		mat.set_shader_parameter("albedo", color)
		mat.set_shader_parameter("cuts", 3)
		mat.set_shader_parameter("wrap", 0.05)
		mat.set_shader_parameter("steepness", 2.0)
		mat.set_shader_parameter("specular_strength", 0.8)
		mat.set_shader_parameter("specular_shininess", 20.0)
		mat.set_shader_parameter("rim_width", 8.0)
		return mat
	else:
		# Fallback to StandardMaterial3D if shader not available
		var sm := StandardMaterial3D.new()
		sm.albedo_color = color
		sm.roughness = 0.28
		sm.metallic_specular = 0.65
		sm.clearcoat_enabled = true
		sm.clearcoat = 0.5
		sm.clearcoat_roughness = 0.15
		return sm

## Spawn a random building at the given position with optional scale and rotation
func spawn_building(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0, color_override: Color = Color.TRANSPARENT) -> Node3D:
	if _building_scenes.is_empty():
		return null
	var scene: PackedScene = _building_scenes[randi() % _building_scenes.size()] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, scale, scale)
	apply_toon_materials(instance, color_override)
	return instance

## Spawn a skyscraper
func spawn_skyscraper(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0, color_override: Color = Color.TRANSPARENT) -> Node3D:
	if _skyscraper_scenes.is_empty():
		return null
	var scene: PackedScene = _skyscraper_scenes[randi() % _skyscraper_scenes.size()] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, scale, scale)
	apply_toon_materials(instance, color_override)
	return instance

## Spawn a specific car by index
func spawn_car(index: int, pos: Vector3, rot_y: float = 0.0) -> Node3D:
	if _car_scenes.is_empty():
		return null
	var idx := index % _car_scenes.size()
	var scene: PackedScene = _car_scenes[idx] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	apply_toon_materials(instance)
	return instance

## Spawn a random car
func spawn_random_car(pos: Vector3, rot_y: float = 0.0) -> Node3D:
	return spawn_car(randi(), pos, rot_y)

## Spawn a palm tree
func spawn_palm(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0) -> Node3D:
	if _palm_scenes.is_empty():
		return null
	var scene: PackedScene = _palm_scenes[randi() % _palm_scenes.size()] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, scale, scale)
	apply_toon_materials(instance)
	return instance

## Spawn a regular tree
func spawn_tree(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0) -> Node3D:
	if _tree_scenes.is_empty():
		return null
	var scene: PackedScene = _tree_scenes[randi() % _tree_scenes.size()] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, scale, scale)
	apply_toon_materials(instance)
	return instance

## Spawn nature prop (cactus, flower)
func spawn_nature_prop(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0) -> Node3D:
	if _nature_scenes.is_empty():
		return null
	var scene: PackedScene = _nature_scenes[randi() % _nature_scenes.size()] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, scale, scale)
	apply_toon_materials(instance)
	return instance

## Spawn road segment
func spawn_road(type: String, pos: Vector3, rot_y: float = 0.0, scale: float = 1.0) -> Node3D:
	if not _road_scenes.has(type):
		return null
	var scene: PackedScene = _road_scenes[type] as PackedScene
	var instance: Node3D = scene.instantiate() as Node3D
	instance.position = pos
	instance.rotation = Vector3(0, rot_y, 0)
	instance.scale = Vector3(scale, 1.0, scale)
	apply_toon_materials(instance)
	return instance

## Get number of available building models
func get_building_count() -> int:
	return _building_scenes.size()

func get_skyscraper_count() -> int:
	return _skyscraper_scenes.size()

func get_car_count() -> int:
	return _car_scenes.size()

func get_palm_count() -> int:
	return _palm_scenes.size()

# =====================================================================
# Modular City Kit (real PBR brick/concrete building pieces, 2m grid)
# Pieces keep their original textured PBR materials — NOT toon-shaded —
# to push building fidelity closer to photoreal while characters/props
# stay toy-plastic toon. This deliberate visual split reads as "real
# buildings, toy citizens" which matches the brief better than forcing
# a flat color onto detailed brick/concrete textures.
# =====================================================================

const CITYKIT_DIR := "res://assets/citykit/models/"

const CITYKIT_WALL_SOLID: Array[String] = ["Brick_Plain_3", "Brick_Plain_3_noWear", "Brick_Plain_4"]
const CITYKIT_WALL_WINDOW: Array[String] = ["Brick_Window_Square_Single", "Brick_Window_Trim_Single"]
const CITYKIT_CORNER := "Brick_Corner_Plain"
const CITYKIT_ROOF := "Roof_2x2"
const CITYKIT_BOTTOM_TRIM := "Brick_BottomTrim"

var _citykit_cache: Dictionary = {}

func _load_citykit_scene(piece_name: String) -> PackedScene:
	if _citykit_cache.has(piece_name):
		return _citykit_cache[piece_name]
	var path := CITYKIT_DIR + piece_name + ".gltf"
	if not ResourceLoader.exists(path):
		push_warning("AssetLoader: citykit piece not found: " + path)
		return null
	var scene: PackedScene = load(path) as PackedScene
	_citykit_cache[piece_name] = scene
	return scene

func _spawn_citykit_piece(piece_name: String, local_pos: Vector3, rot_y: float, parent: Node3D) -> void:
	var scene := _load_citykit_scene(piece_name)
	if scene == null:
		return
	var inst: Node3D = scene.instantiate()
	inst.position = local_pos
	inst.rotation.y = rot_y
	parent.add_child(inst)
	for mi in _find_mesh_instances(inst):
		mi.cast_shadow = 1

func _find_mesh_instances(node: Node) -> Array:
	var result: Array = []
	if node is MeshInstance3D:
		result.append(node)
	for c in node.get_children():
		result += _find_mesh_instances(c)
	return result

## Build a modular brick building on a 2m grid using the city kit pieces.
## width/depth in meters (multiples of 2, minimum 6), floors = number of storeys (3m each).
## window_chance = probability a given wall segment gets a window instead of solid brick.
## Returns a Node3D ready to be added to the scene and positioned/rotated by the caller.
func build_modular_building(width: float, depth: float, floors: int, window_chance: float = 0.45, rng_seed: int = -1) -> Node3D:
	var w: int = max(6, int(round(width / 2.0)) * 2)
	var d: int = max(6, int(round(depth / 2.0)) * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = rng_seed if rng_seed >= 0 else randi()
	
	var building := Node3D.new()
	var floor_h := 3.0
	var half_w := w / 2.0
	var half_d := d / 2.0
	var w_segs: int = int((w - 4) / 2.0)  # straight wall segments along each X-facing side
	var d_segs: int = int((d - 4) / 2.0)  # straight wall segments along each Z-facing side
	
	for f in range(floors):
		var y := float(f) * floor_h
		
		# --- 4 corners ---
		# Corner piece is an L spanning 2m on each adjoining face. Place at each
		# of the 4 building corners, rotated so the L wraps the correct way.
		_spawn_citykit_piece(CITYKIT_CORNER, Vector3(-half_w + 1, y, -half_d + 1), deg_to_rad(0), building)
		_spawn_citykit_piece(CITYKIT_CORNER, Vector3(half_w - 1, y, -half_d + 1), deg_to_rad(-90), building)
		_spawn_citykit_piece(CITYKIT_CORNER, Vector3(half_w - 1, y, half_d - 1), deg_to_rad(180), building)
		_spawn_citykit_piece(CITYKIT_CORNER, Vector3(-half_w + 1, y, half_d - 1), deg_to_rad(90), building)
		
		# --- front (z = -half_d) and back (z = +half_d) walls, running along X ---
		for i in range(w_segs):
			var x := -half_w + 2.0 + i * 2.0 + 1.0
			var solid_pool: Array[String] = CITYKIT_WALL_SOLID
			var window_pool: Array[String] = CITYKIT_WALL_WINDOW
			var use_window := rng.randf() < window_chance and f > 0  # ground floor stays solid/entrance-friendly
			var piece: String = window_pool[rng.randi() % window_pool.size()] if use_window else solid_pool[rng.randi() % solid_pool.size()]
			_spawn_citykit_piece(piece, Vector3(x, y, -half_d), deg_to_rad(0), building)
			piece = window_pool[rng.randi() % window_pool.size()] if (rng.randf() < window_chance and f > 0) else solid_pool[rng.randi() % solid_pool.size()]
			_spawn_citykit_piece(piece, Vector3(x, y, half_d), deg_to_rad(180), building)
		
		# --- left (x = -half_w) and right (x = +half_w) walls, running along Z ---
		for i in range(d_segs):
			var z := -half_d + 2.0 + i * 2.0 + 1.0
			var solid_pool2: Array[String] = CITYKIT_WALL_SOLID
			var window_pool2: Array[String] = CITYKIT_WALL_WINDOW
			var use_window2 := rng.randf() < window_chance and f > 0
			var piece2: String = window_pool2[rng.randi() % window_pool2.size()] if use_window2 else solid_pool2[rng.randi() % solid_pool2.size()]
			_spawn_citykit_piece(piece2, Vector3(-half_w, y, z), deg_to_rad(90), building)
			piece2 = window_pool2[rng.randi() % window_pool2.size()] if (rng.randf() < window_chance and f > 0) else solid_pool2[rng.randi() % solid_pool2.size()]
			_spawn_citykit_piece(piece2, Vector3(half_w, y, z), deg_to_rad(-90), building)
	
	# --- flat roof cap, tiled with Roof_2x2 pieces across the footprint ---
	var roof_y := float(floors) * floor_h
	var rw := w / 2
	var rd := d / 2
	for rx in range(rw):
		for rz in range(rd):
			var rpos := Vector3(-half_w + 1 + rx * 2.0, roof_y, -half_d + 1 + rz * 2.0)
			_spawn_citykit_piece(CITYKIT_ROOF, rpos, 0.0, building)
	
	return building

## Convenience wrapper matching the _kb/_ks pattern used by landmark_generator:
## spawns a modular building at world pos with randomized size/floors.
func spawn_modular_building(pos: Vector3, rot_y: float = 0.0, min_floors: int = 2, max_floors: int = 6) -> Node3D:
	var rng := RandomNumberGenerator.new()
	rng.seed = randi()
	var w: float = [6.0, 8.0, 10.0][rng.randi() % 3]
	var d: float = [6.0, 8.0, 10.0][rng.randi() % 3]
	var floors: int = rng.randi_range(min_floors, max_floors)
	var building := build_modular_building(w, d, floors, 0.45, rng.seed)
	building.position = pos
	building.rotation.y = rot_y
	return building
