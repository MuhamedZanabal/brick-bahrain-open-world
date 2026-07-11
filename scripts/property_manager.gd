extends Node

# Property definitions
var properties: Array[Dictionary] = []
var vehicles_for_sale: Array[Dictionary] = []
var owned_properties: Dictionary = {}  # prop_id -> {name, position, vehicle_spawn}
var owned_vehicles: Dictionary = {}    # veh_id -> {name, type, color}
var nameplates: Dictionary = {}        # prop_id -> Label3D

func _ready() -> void:
	add_to_group("property_manager")
	_setup_properties()
	_setup_vehicles()
	_load_owned_from_save()

func _setup_properties() -> void:
	# Amwaj Islands properties
	properties.append({
		"id": "amwaj_villa_1",
		"name": "Amwaj Beach Villa",
		"position": Vector3(140, 0, -50),
		"price": 500,
		"vehicle_spawn": Vector3(145, 1, -50),
		"color": Color(0.9, 0.8, 0.6),
		"size": Vector3(8, 6, 8)
	})
	properties.append({
		"id": "amwaj_villa_2",
		"name": "Amwaj Luxury Penthouse",
		"position": Vector3(155, 0, -40),
		"price": 800,
		"vehicle_spawn": Vector3(160, 1, -40),
		"color": Color(0.8, 0.7, 0.9),
		"size": Vector3(10, 8, 10)
	})
	properties.append({
		"id": "marina_apartment",
		"name": "Marina Apartment",
		"position": Vector3(-65, 0, 75),
		"price": 300,
		"vehicle_spawn": Vector3(-70, 1, 75),
		"color": Color(0.7, 0.8, 0.9),
		"size": Vector3(6, 5, 6)
	})
	properties.append({
		"id": "souk_shop",
		"name": "Souk Shop",
		"position": Vector3(5, 0, -45),
		"price": 200,
		"vehicle_spawn": Vector3(10, 1, -45),
		"color": Color(0.9, 0.6, 0.3),
		"size": Vector3(5, 4, 5)
	})

func _setup_vehicles() -> void:
	vehicles_for_sale.append({
		"id": "brick_sedan",
		"name": "Brick Sedan",
		"price": 150,
		"color": Color(0.8, 0.1, 0.1),
		"max_speed": 30
	})
	vehicles_for_sale.append({
		"id": "brick_sports",
		"name": "Brick Sports Car",
		"price": 400,
		"color": Color(0.1, 0.3, 0.9),
		"max_speed": 45
	})
	vehicles_for_sale.append({
		"id": "brick_suv",
		"name": "Brick SUV",
		"price": 250,
		"color": Color(0.1, 0.5, 0.2),
		"max_speed": 25
	})
	vehicles_for_sale.append({
		"id": "brick_truck",
		"name": "Brick Truck",
		"price": 350,
		"color": Color(0.6, 0.6, 0.6),
		"max_speed": 20
	})

func _load_owned_from_save() -> void:
	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	if save_mgr and save_mgr.has_method("get_owned_properties"):
		var saved_props: Array = save_mgr.get_owned_properties()
		for prop_id in saved_props:
			for prop in properties:
				if prop["id"] == prop_id:
					owned_properties[prop_id] = prop
					_spawn_property_building(prop)
					break

		if save_mgr.has_method("get_owned_vehicles"):
			var saved_vehs: Array = save_mgr.get_owned_vehicles()
			for veh_id in saved_vehs:
				for veh in vehicles_for_sale:
					if veh["id"] == veh_id:
						owned_vehicles[veh_id] = veh
						break

func buy_property(prop_id: String) -> bool:
	# Check if already owned
	if owned_properties.has(prop_id):
		return false

	# Find property
	var prop: Dictionary = {}
	for p in properties:
		if p["id"] == prop_id:
			prop = p
			break
	if prop.is_empty():
		return false

	# Check coins
	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	if save_mgr and save_mgr.has_method("spend_coins"):
		if not save_mgr.spend_coins(int(prop["price"])):
			return false  # Not enough coins

	# Register ownership
	owned_properties[prop_id] = prop
	save_mgr.add_property(prop_id)

	# Spawn building
	_spawn_property_building(prop)

	return true

func buy_vehicle(veh_id: String) -> bool:
	if owned_vehicles.has(veh_id):
		return false

	var veh: Dictionary = {}
	for v in vehicles_for_sale:
		if v["id"] == veh_id:
			veh = v
			break
	if veh.is_empty():
		return false

	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	if save_mgr and save_mgr.has_method("spend_coins"):
		if not save_mgr.spend_coins(int(veh["price"])):
			return false

	owned_vehicles[veh_id] = veh
	save_mgr.add_vehicle(veh_id)

	# Spawn vehicle at nearest owned property
	_spawn_owned_vehicle(veh)

	return true

func _spawn_property_building(prop: Dictionary) -> void:
	var building: MeshInstance3D = MeshInstance3D.new()
	var box: BoxMesh = BoxMesh.new()
	box.size = prop["size"]
	building.mesh = box
	building.position = prop["position"] + Vector3(0, prop["size"].y / 2, 0)
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = prop["color"]
	building.material_override = mat
	building.cast_shadow = 2
	get_tree().current_scene.add_child(building)

	# Nameplate
	var nameplate: Label3D = Label3D.new()
	nameplate.text = prop["name"] + "\n[OWNED]"
	nameplate.font_size = 24
	nameplate.position = prop["position"] + Vector3(0, prop["size"].y + 1, 0)
	nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	nameplate.no_depth_test = true
	nameplate.modulate = Color(0.5, 1, 0.5)
	get_tree().current_scene.add_child(nameplate)
	nameplates[prop["id"]] = nameplate

func _spawn_owned_vehicle(veh: Dictionary) -> void:
	# Find nearest owned property to spawn vehicle at
	var spawn_pos: Vector3 = Vector3(0, 1, 0)
	if owned_properties.size() > 0:
		var first_prop: Dictionary = owned_properties.values()[0]
		spawn_pos = first_prop["vehicle_spawn"]

	# Create a simple brick vehicle
	var car_body: RigidBody3D = RigidBody3D.new()
	var car_mesh: MeshInstance3D = MeshInstance3D.new()
	var car_box: BoxMesh = BoxMesh.new()
	car_box.size = Vector3(2, 1, 4)
	car_mesh.mesh = car_box
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = veh["color"]
	car_mesh.material_override = mat
	car_mesh.cast_shadow = 2
	car_body.add_child(car_mesh)
	car_body.add_to_group("vehicles")
	car_body.add_to_group("owned_vehicles")
	get_tree().current_scene.add_child(car_body)  # must be added to the tree BEFORE setting global_position
	car_body.global_position = spawn_pos

func get_properties() -> Array[Dictionary]:
	return properties

func get_vehicles_for_sale() -> Array[Dictionary]:
	return vehicles_for_sale

func get_owned_properties() -> Dictionary:
	return owned_properties

func get_owned_vehicles() -> Dictionary:
	return owned_vehicles
