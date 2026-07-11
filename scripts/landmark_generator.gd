extends Node
## LandmarkGenerator - Autoload singleton
## Generates all Bahrain landmarks using Kenney CC0 3D models where possible,
## falling back to procedural bricks for unique structures.
## The world map approximates Bahrain's geography.

var world_size := 500.0
var landmarks: Array[Dictionary] = []

func _ready() -> void:
	_define_landmarks()

func _define_landmarks() -> void:
	landmarks = [
		{"name": "Manama Skyline", "pos": Vector3(120, 0, -100), "type": "skyline", "desc": "The capital's iconic skyline"},
		{"name": "Bahrain World Trade Center", "pos": Vector3(115, 0, -90), "type": "wtc", "desc": "Sail-shaped twin towers"},
		{"name": "Bahrain Financial Harbour", "pos": Vector3(135, 0, -105), "type": "financial", "desc": "Financial district towers"},
		{"name": "Al Fateh Grand Mosque", "pos": Vector3(105, 0, -80), "type": "mosque", "desc": "Bahrain's largest mosque"},
		{"name": "Bab Al Bahrain", "pos": Vector3(110, 0, -70), "type": "gate", "desc": "Historic gateway to the souk"},
		{"name": "Manama Souk", "pos": Vector3(100, 0, -60), "type": "souk", "desc": "Traditional market district"},
		{"name": "Bahrain National Museum", "pos": Vector3(125, 0, -70), "type": "museum", "desc": "National museum and cultural center"},
		{"name": "Bahrain Fort", "pos": Vector3(-60, 0, -110), "type": "fort", "desc": "UNESCO World Heritage Site"},
		{"name": "Tree of Life", "pos": Vector3(-80, 0, 100), "type": "tree", "desc": "Lone tree in the desert"},
		{"name": "Bahrain International Circuit", "pos": Vector3(-50, 0, 130), "type": "circuit", "desc": "Home of the F1 Grand Prix"},
		{"name": "King Fahd Causeway", "pos": Vector3(-120, 0, -60), "type": "causeway", "desc": "Bridge to Saudi Arabia"},
		{"name": "Riffa Fort", "pos": Vector3(60, 0, 60), "type": "fort2", "desc": "Historic fort in Riffa"},
		{"name": "Amwaj Islands", "pos": Vector3(160, 0, -130), "type": "islands", "desc": "Waterfront residential islands"},
		{"name": "City Center Mall", "pos": Vector3(80, 0, -40), "type": "mall", "desc": "Largest mall in Bahrain"},
		{"name": "Marina Beach", "pos": Vector3(140, 0, -50), "type": "marina", "desc": "Waterfront promenade"},
	]

func get_landmark_by_name(name: String) -> Dictionary:
	for l in landmarks:
		if l["name"] == name:
			return l
	return {}

## Build the entire world with all landmarks
func generate_world(parent: Node3D) -> void:
	# Ground / terrain — sandy desert
	var ground := BrickFactory.create_ground(world_size, Color(0.76, 0.68, 0.5))
	ground.position = Vector3(0, 0, 0)
	parent.add_child(ground)
	
	# Water surrounding (sea)
	var sea := BrickFactory.create_water(world_size * 1.5)
	sea.position = Vector3(0, -0.1, 0)
	parent.add_child(sea)
	
	# Main road network — use Kenney road models + fallback
	_build_roads(parent)
	
	# Generate each landmark
	for landmark in landmarks:
		_build_landmark(parent, landmark)
	
	# Decorative elements — palm trees, cactus, flowers
	_add_decorations(parent)
	
	# Spawn points for collectibles
	_add_collectibles(parent)

func _build_roads(parent: Node3D) -> void:
	# Main highway running north-south — use Kenney road segments
	_lay_road_strip(parent, Vector3(40, 0.03, 0), world_size * 0.7, 0.0)
	# East-west highway
	_lay_road_strip(parent, Vector3(0, 0.03, -40), world_size * 0.6, deg_to_rad(90))
	# Connecting roads
	_lay_road_strip(parent, Vector3(40, 0.03, -100), 200, deg_to_rad(45))
	_lay_road_strip(parent, Vector3(-20, 0.03, 60), 150, deg_to_rad(30))
	# F1 circuit access road
	_lay_road_strip(parent, Vector3(-20, 0.03, 120), 120, 0.0)

func _lay_road_strip(parent: Node3D, center: Vector3, total_length: float, rot_y: float) -> void:
	# Use Kenney road-straight segments laid end to end
	# Each Kenney road segment is roughly 10m long
	var seg_length := 10.0
	var num_segs := int(total_length / seg_length)
	var start_offset := -(total_length / 2.0) + seg_length / 2.0
	
	for i in range(num_segs):
		var local_z := start_offset + i * seg_length
		# Position in world space accounting for rotation
		var cos_r := cos(rot_y)
		var sin_r := sin(rot_y)
		var world_x := center.x + local_z * sin_r
		var world_z := center.z + local_z * cos_r
		
		var road := AssetLoader.spawn_road("straight", Vector3(world_x, center.y, world_z), rot_y, 1.0)
		if road:
			parent.add_child(road)
		else:
			# Fallback to procedural road
			var fb := BrickFactory.create_road(8, seg_length)
			fb.position = Vector3(world_x, center.y, world_z)
			fb.rotation = Vector3(0, rot_y, 0)
			parent.add_child(fb)

func _build_landmark(parent: Node3D, landmark: Dictionary) -> void:
	var pos: Vector3 = landmark["pos"]
	var type: String = landmark["type"]
	var group := Node3D.new()
	group.position = pos
	group.name = landmark["name"].replace(" ", "_")
	
	group.set_meta("landmark_name", landmark["name"])
	group.set_meta("landmark_type", type)
	group.set_meta("landmark_desc", landmark["desc"])
	
	match type:
		"skyline": _build_skyline(group)
		"wtc": _build_wtc(group)
		"financial": _build_financial_harbour(group)
		"mosque": _build_mosque(group)
		"gate": _build_bab_al_bahrain(group)
		"souk": _build_souk(group)
		"museum": _build_museum(group)
		"fort": _build_bahrain_fort(group)
		"tree": _build_tree_of_life(group)
		"circuit": _build_f1_circuit(group)
		"causeway": _build_causeway(group)
		"fort2": _build_riffa_fort(group)
		"islands": _build_amwaj(group)
		"mall": _build_mall(group)
		"marina": _build_marina(group)
	
	parent.add_child(group)

## Helper: spawn a Kenney building with position/rotation/scale
func _kb(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0, color_override: Color = Color.TRANSPARENT) -> Node3D:
	var b := AssetLoader.spawn_building(pos, scale, rot_y, color_override)
	if b == null:
		# Fallback to procedural
		b = BrickFactory.create_building(6, 6, 8 + randi() % 6, Color(0.7, 0.7, 0.75))
		b.position = pos
		b.rotation = Vector3(0, rot_y, 0)
		b.scale = Vector3(scale, scale, scale)
	return b

## Helper: spawn a Kenney skyscraper
func _ks(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0, color_override: Color = Color.TRANSPARENT) -> Node3D:
	var b := AssetLoader.spawn_skyscraper(pos, scale, rot_y, color_override)
	if b == null:
		b = BrickFactory.create_tower(6, 6, 25 + randi() % 20, Color(0.6, 0.6, 0.65), false)
		b.position = pos
	return b

## Helper: spawn a Kenney palm tree
func _kp(pos: Vector3, scale: float = 1.0, rot_y: float = 0.0) -> Node3D:
	var t := AssetLoader.spawn_palm(pos, scale, rot_y)
	if t == null:
		t = BrickFactory.create_palm_tree()
		t.position = pos
		t.scale = Vector3(scale, scale, scale)
	return t

func _build_skyline(group: Node3D) -> void:
	# Cluster of skyscrapers — use Kenney skyscraper models
	for i in range(8):
		var x := (i % 4) * 12 - 18
		var z := (i / 4) * 12 - 6
		var s := 1.0 + (i % 3) * 0.15
		var tower := _ks(Vector3(x, 0, z), s, deg_to_rad(randf_range(0, 360)))
		group.add_child(tower)
	# Add some regular buildings around the base — mix real-textured modular
	# brick buildings (AssetLoader city kit) with the toon Kenney models for variety
	for i in range(6):
		var x := randf_range(-25, 25)
		var z := randf_range(-15, 15)
		if abs(x) < 10 and abs(z) < 10:
			continue
		var b: Node3D
		if i % 2 == 0:
			b = AssetLoader.spawn_modular_building(Vector3(x, 0, z), deg_to_rad(randf_range(0, 360)), 2, 5)
		else:
			b = _kb(Vector3(x, 0, z), 0.8, deg_to_rad(randf_range(0, 360)))
		group.add_child(b)

func _build_wtc(group: Node3D) -> void:
	# Bahrain World Trade Center — twin towers using skyscraper models
	for side in [1, -1]:
		var tower := _ks(Vector3(side * 6, 0, 0), 1.3, 0.0)
		group.add_child(tower)
	# Connecting bridge (procedural — unique structure)
	var bridge := BrickFactory.create_brick(Vector3(14, 2, 4), Color(0.65, 0.67, 0.7), true, Vector2i(8, 2))
	bridge.position = Vector3(0, 20, 0)
	group.add_child(bridge)

func _build_financial_harbour(group: Node3D) -> void:
	# Financial district — mix of skyscrapers and regular buildings
	for i in range(5):
		var s := 1.0 + i * 0.1
		var tower := _ks(Vector3((i - 2) * 10, 0, (i % 2) * 8 - 4), s, deg_to_rad(randf_range(0, 360)))
		group.add_child(tower)
	# Add ground-level buildings — modular brick for real texture detail
	for i in range(4):
		var pos := Vector3(randf_range(-18, 18), 0, randf_range(-12, 12))
		var b: Node3D = AssetLoader.spawn_modular_building(pos, deg_to_rad(randf_range(0, 360)), 2, 4)
		group.add_child(b)

func _build_mosque(group: Node3D) -> void:
	# Al Fateh Grand Mosque — use a large building model as the prayer hall
	var hall := _kb(Vector3.ZERO, 1.5, 0.0, Color(0.85, 0.82, 0.75))
	group.add_child(hall)
	
	# Dome (procedural — unique to mosque architecture)
	var dome := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 6
	sphere.height = 10
	dome.mesh = sphere
	var dome_mat := StandardMaterial3D.new()
	dome_mat.albedo_color = Color(0.7, 0.65, 0.5)
	dome_mat.metalness = 0.3
	dome_mat.roughness = 0.4
	dome_mat.clearcoat_enabled = true
	dome_mat.clearcoat = 0.5
	dome.material_override = dome_mat
	dome.position = Vector3(0, 11, 0)
	group.add_child(dome)
	
	# Minarets — use thin skyscraper models as minaret towers
	for corner in [Vector2(12, 9), Vector2(-12, 9), Vector2(12, -9), Vector2(-12, -9)]:
		var minaret := _ks(Vector3(corner.x, 0, corner.y), 0.4, 0.0, Color(0.85, 0.82, 0.75))
		group.add_child(minaret)

func _build_bab_al_bahrain(group: Node3D) -> void:
	# Iconic gateway — procedural (unique structure, no GLB equivalent)
	var pillar_l := BrickFactory.create_building(3, 3, 12, Color(0.8, 0.7, 0.4))
	pillar_l.position = Vector3(-5, 0, 0)
	group.add_child(pillar_l)
	var pillar_r := BrickFactory.create_building(3, 3, 12, Color(0.8, 0.7, 0.4))
	pillar_r.position = Vector3(5, 0, 0)
	group.add_child(pillar_r)
	var arch := BrickFactory.create_brick(Vector3(14, 3, 3), Color(0.85, 0.75, 0.45), true, Vector2i(6, 2))
	arch.position = Vector3(0, 12, 0)
	group.add_child(arch)
	# Flank with Kenney buildings
	var b1 := _kb(Vector3(-12, 0, 0), 0.8, 0.0)
	group.add_child(b1)
	var b2 := _kb(Vector3(12, 0, 0), 0.8, 0.0)
	group.add_child(b2)

func _build_souk(group: Node3D) -> void:
	# Traditional market — rows of small buildings, mixing real-brick modular
	# stalls with Kenney models for variety
	for row in range(3):
		for col in range(6):
			var pos := Vector3((col - 2.5) * 6, 0, (row - 1) * 7)
			var b: Node3D
			if (row + col) % 2 == 0:
				b = AssetLoader.spawn_modular_building(pos, deg_to_rad(randf_range(0, 360)), 1, 2)
			else:
				b = _kb(pos, 0.6, deg_to_rad(randf_range(0, 360)))
			group.add_child(b)
	# Covered walkway arches (procedural — unique)
	for i in range(5):
		var arch := BrickFactory.create_brick(Vector3(0.8, 3, 0.8), Color(0.7, 0.55, 0.3), true, Vector2i(1, 1))
		arch.position = Vector3((i - 2) * 3, 1.5, 3.5)
		group.add_child(arch)

func _build_museum(group: Node3D) -> void:
	# Bahrain National Museum — modern flat building
	var main := _kb(Vector3.ZERO, 1.8, 0.0, Color(0.75, 0.73, 0.7))
	group.add_child(main)
	# Distinctive pink dome (procedural)
	var dome := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 4
	sphere.height = 6
	dome.mesh = sphere
	var dome_mat := StandardMaterial3D.new()
	dome_mat.albedo_color = Color(0.85, 0.6, 0.55)
	dome_mat.clearcoat_enabled = true
	dome_mat.clearcoat = 0.4
	dome.material_override = dome_mat
	dome.position = Vector3(0, 9, 0)
	group.add_child(dome)

func _build_bahrain_fort(group: Node3D) -> void:
	# UNESCO World Heritage fort — walls and towers
	var wall_color := Color(0.65, 0.55, 0.35)
	# Outer walls (procedural — fort walls are unique)
	for angle_idx in range(4):
		var angle := angle_idx * PI / 2.0
		var wall := BrickFactory.create_brick(Vector3(30, 4, 2), wall_color, true, Vector2i(12, 1))
		wall.position = Vector3(cos(angle) * 15, 2, sin(angle) * 15)
		wall.rotation = Vector3(0, angle + PI/2, 0)
		group.add_child(wall)
	# Corner towers — use small buildings
	for corner in [Vector2(15, 15), Vector2(-15, 15), Vector2(15, -15), Vector2(-15, -15)]:
		var tower := _kb(Vector3(corner.x, 0, corner.y), 0.5, 0.0, wall_color)
		group.add_child(tower)
	# Central keep
	var keep := _kb(Vector3.ZERO, 1.0, 0.0, wall_color.darkened(0.1))
	group.add_child(keep)

func _build_tree_of_life(group: Node3D) -> void:
	# Single tree in the desert — use detailed palm model
	var tree := _kp(Vector3.ZERO, 2.0, deg_to_rad(randf_range(0, 360)))
	group.add_child(tree)
	# Sandy mound around it
	var mound := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 5
	sphere.height = 1
	mound.mesh = sphere
	var m_mat := StandardMaterial3D.new()
	m_mat.albedo_color = Color(0.76, 0.65, 0.4)
	m_mat.roughness = 0.9
	mound.material_override = m_mat
	mound.position = Vector3(0, 0.1, 0)
	group.add_child(mound)

func _build_f1_circuit(group: Node3D) -> void:
	# Bahrain International Circuit — race track using road segments
	var circuit_points := [
		Vector3(-40, 0.05, -30), Vector3(-40, 0.05, 30), Vector3(-20, 0.05, 50),
		Vector3(20, 0.05, 50), Vector3(40, 0.05, 30), Vector3(40, 0.05, -30),
		Vector3(20, 0.05, -50), Vector3(-20, 0.05, -50)
	]
	for i in range(circuit_points.size()):
		var start: Vector3 = circuit_points[i]
		var end: Vector3 = circuit_points[(i + 1) % circuit_points.size()]
		var mid: Vector3 = (start + end) / 2.0
		var dir: Vector3 = end - start
		var length: float = dir.length()
		var angle := atan2(dir.x, dir.z)
		# Use Kenney road segments for the track
		var num_segs := int(length / 10.0)
		for j in range(num_segs):
			var t := (float(j) + 0.5) / float(num_segs)
			var pt := start.lerp(end, t)
			var road := AssetLoader.spawn_road("straight", pt, angle, 1.0)
			if road:
				group.add_child(road)
			else:
				var seg := BrickFactory.create_road(6, 10.0)
				seg.position = pt
				seg.rotation = Vector3(0, angle, 0)
				group.add_child(seg)
	# Grandstand
	var stand := _kb(Vector3(0, 0, -55), 2.0, 0.0, Color(0.8, 0.75, 0.7))
	group.add_child(stand)
	# Control tower
	var tower := _ks(Vector3(0, 0, 60), 0.8, 0.0, Color(0.9, 0.85, 0.8))
	group.add_child(tower)
	# Starting line marker
	var start_line := BrickFactory.create_brick(Vector3(6, 0.06, 1), Color.WHITE, false)
	start_line.position = Vector3(0, 0.06, -30)
	group.add_child(start_line)

func _build_causeway(group: Node3D) -> void:
	# King Fahd Causeway — long bridge over water using road-bridge segments
	var total_len := 100.0
	var seg_len := 10.0
	var num_segs := int(total_len / seg_len)
	var rot := deg_to_rad(20)
	for i in range(num_segs):
		var t := (float(i) + 0.5) / float(num_segs)
		var local_pos := (t - 0.5) * total_len
		var x := cos(rot) * local_pos
		var z := sin(rot) * local_pos
		var road_type := "bridge" if i % 3 == 1 else "straight"
		var road := AssetLoader.spawn_road(road_type, Vector3(x, 2, z), rot, 1.0)
		if road:
			group.add_child(road)
		else:
			var seg := BrickFactory.create_road(8, seg_len)
			seg.position = Vector3(x, 2, z)
			seg.rotation = Vector3(0, rot, 0)
			group.add_child(seg)
	# Bridge supports (procedural)
	for i in range(8):
		var t := i / 7.0
		var pillar := BrickFactory.create_building(2, 2, 5, Color(0.6, 0.6, 0.6))
		pillar.position = Vector3(cos(rot) * (t * 100 - 50), 0, sin(rot) * (t * 100 - 50))
		group.add_child(pillar)
	# Border checkpoint
	var checkpoint := _kb(Vector3(40, 0, 15), 1.2, 0.0, Color(0.7, 0.7, 0.72))
	group.add_child(checkpoint)

func _build_riffa_fort(group: Node3D) -> void:
	var wall_color := Color(0.6, 0.5, 0.35)
	# Walls (procedural — fort walls are unique)
	for angle_idx in range(4):
		var angle := angle_idx * PI / 2.0
		var wall := BrickFactory.create_brick(Vector3(20, 4, 2), wall_color, true, Vector2i(8, 1))
		wall.position = Vector3(cos(angle) * 10, 2, sin(angle) * 10)
		wall.rotation = Vector3(0, angle + PI/2, 0)
		group.add_child(wall)
	# Main keep
	var keep := _kb(Vector3.ZERO, 1.0, 0.0, wall_color)
	group.add_child(keep)
	# Tower
	var tower := _ks(Vector3(8, 0, 8), 0.5, 0.0, wall_color)
	group.add_child(tower)

func _build_amwaj(group: Node3D) -> void:
	# Waterfront residential — modern villas using Kenney buildings
	for i in range(6):
		var s := 0.8 + (i % 3) * 0.15
		var b := _kb(Vector3((i % 3) * 12 - 12, 0, (i / 3) * 10 - 5), s, deg_to_rad(randf_range(0, 360)),
			Color(0.8, 0.78, 0.75).lightened(i * 0.03))
		group.add_child(b)
	# Marina walkway
	var marina := AssetLoader.spawn_road("straight", Vector3(0, 0.05, 15), 0.0, 3.0)
	if marina:
		group.add_child(marina)
	else:
		var fb := BrickFactory.create_road(4, 30)
		fb.position = Vector3(0, 0.05, 15)
		group.add_child(fb)

func _build_mall(group: Node3D) -> void:
	# City Center Mall — large building
	var main := _kb(Vector3.ZERO, 2.5, 0.0, Color(0.75, 0.72, 0.7))
	group.add_child(main)
	# Entrance
	var entrance := _kb(Vector3(0, 0, 11), 0.8, 0.0, Color(0.6, 0.7, 0.8))
	group.add_child(entrance)
	# Parking lot
	var parking := AssetLoader.spawn_road("straight", Vector3(0, 0.03, 18), 0.0, 2.0)
	if parking:
		group.add_child(parking)
	else:
		var fb := BrickFactory.create_road(15, 20)
		fb.position = Vector3(0, 0.03, 18)
		group.add_child(fb)

func _build_marina(group: Node3D) -> void:
	# Waterfront promenade
	var prom := AssetLoader.spawn_road("straight", Vector3(0, 0.05, 0), deg_to_rad(90), 4.0)
	if prom:
		group.add_child(prom)
	else:
		var fb := BrickFactory.create_road(6, 40)
		fb.position = Vector3(0, 0.05, 0)
		fb.rotation = Vector3(0, deg_to_rad(90), 0)
		group.add_child(fb)
	# Restaurants and cafes
	for i in range(4):
		var cafe := _kb(Vector3((i - 1.5) * 8, 0, -5), 0.6, deg_to_rad(180),
			Color(0.85, 0.75, 0.55).lightened(i * 0.05))
		group.add_child(cafe)
	# Docked boats (procedural — unique)
	for i in range(3):
		var boat := BrickFactory.create_brick(Vector3(3, 0.5, 1.2), Color(1, 1, 1), true, Vector2i(2, 1))
		boat.position = Vector3((i - 1) * 5, 0.3, 8)
		group.add_child(boat)

func _add_decorations(parent: Node3D) -> void:
	# Palm trees along roads and scattered — use Kenney palm models
	for i in range(40):
		var x := randf_range(-200, 200)
		var z := randf_range(-200, 200)
		if abs(x) > 10 and abs(z) > 10:
			var s := randf_range(0.8, 1.4)
			var tree := _kp(Vector3(x, 0, z), s, deg_to_rad(randf_range(0, 360)))
			parent.add_child(tree)
	
	# Cactus and flowers in desert areas
	for i in range(20):
		var x := randf_range(-200, 200)
		var z := randf_range(-200, 200)
		if abs(x) > 30 and abs(z) > 30:
			var prop := AssetLoader.spawn_nature_prop(Vector3(x, 0, z), randf_range(0.5, 1.2), deg_to_rad(randf_range(0, 360)))
			if prop:
				parent.add_child(prop)
	
	# Regular trees in parks/green areas
	for i in range(15):
		var x := randf_range(-150, 150)
		var z := randf_range(-150, 150)
		var tree := AssetLoader.spawn_tree(Vector3(x, 0, z), randf_range(0.7, 1.3), deg_to_rad(randf_range(0, 360)))
		if tree:
			parent.add_child(tree)
	
	# Street lights (procedural — with toon material)
	for i in range(20):
		var pole := BrickFactory.create_brick(Vector3(0.2, 4, 0.2), Color(0.3, 0.3, 0.3), false)
		pole.position = Vector3(44 + randf_range(-1, 1), 0, randf_range(-150, 150))
		parent.add_child(pole)
		var light_mesh := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.3
		sphere.height = 0.5
		light_mesh.mesh = sphere
		var light_mat := StandardMaterial3D.new()
		light_mat.albedo_color = Color(1, 0.9, 0.5)
		light_mat.emission = Color(1, 0.9, 0.5)
		light_mat.emission_energy_multiplier = 2.0
		light_mesh.material_override = light_mat
		light_mesh.position = pole.position + Vector3(0, 4, 0)
		parent.add_child(light_mesh)

func _add_collectibles(parent: Node3D) -> void:
	# Golden coins scattered around the map
	var coin_mat := StandardMaterial3D.new()
	coin_mat.albedo_color = Color(1.0, 0.82, 0.05)
	coin_mat.metalness = 0.9
	coin_mat.metallic_specular = 1.0
	coin_mat.roughness = 0.1
	coin_mat.clearcoat_enabled = true
	coin_mat.clearcoat = 1.0
	coin_mat.clearcoat_roughness = 0.02
	coin_mat.emission = Color(1.0, 0.7, 0.0)
	coin_mat.emission_energy_multiplier = 0.8
	for i in range(80):
		var coin := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.25
		cyl.bottom_radius = 0.25
		cyl.height = 0.06
		coin.mesh = cyl
		coin.material_override = coin_mat
		coin.rotation = Vector3(deg_to_rad(90), 0, 0)
		coin.position = Vector3(randf_range(-200, 200), 1.0, randf_range(-200, 200))
		coin.set_meta("is_collectible", true)
		coin.set_meta("collectible_type", "coin")
		coin.set_meta("collectible_value", 10)
		coin.name = "Coin_%d" % i
		parent.add_child(coin)
