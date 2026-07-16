extends "res://scripts/full_asset_matrix_runtime.gd"

var _qa_camera: Camera3D
var _qa_elapsed: float = 0.0


func _ready() -> void:
	_build_qa_stage()
	super()
	_compact_runtime_districts()
	print("BAHRAIN_BRICK_FULL_MATRIX_QA_FRAME_READY")


func _process(delta: float) -> void:
	_qa_elapsed += delta
	if not is_instance_valid(_qa_camera):
		return
	var angle := sin(_qa_elapsed * 0.08) * 0.16
	_qa_camera.position = Vector3(sin(angle) * 118.0, 72.0, cos(angle) * 118.0)
	_qa_camera.look_at(Vector3(0.0, 8.0, 0.0), Vector3.UP)


func _build_qa_stage() -> void:
	var environment_node := WorldEnvironment.new()
	environment_node.name = "QAWorldEnvironment"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.20, 0.43, 0.64, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.93, 0.91, 0.84, 1.0)
	environment.ambient_light_energy = 1.15
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment_node.environment = environment
	add_child(environment_node)

	var sun := DirectionalLight3D.new()
	sun.name = "QASun"
	sun.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
	sun.light_energy = 1.65
	sun.shadow_enabled = true
	add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.name = "QAFill"
	fill.rotation_degrees = Vector3(-28.0, 145.0, 0.0)
	fill.light_color = Color(0.56, 0.68, 0.88, 1.0)
	fill.light_energy = 0.55
	add_child(fill)

	var ground := MeshInstance3D.new()
	ground.name = "QAGround"
	var plane := PlaneMesh.new()
	plane.size = Vector2(270.0, 270.0)
	ground.mesh = plane
	var ground_material := StandardMaterial3D.new()
	ground_material.albedo_color = Color(0.46, 0.40, 0.31, 1.0)
	ground_material.roughness = 0.92
	ground.material_override = ground_material
	ground.position.y = -0.06
	add_child(ground)

	_qa_camera = Camera3D.new()
	_qa_camera.name = "QACamera"
	_qa_camera.current = true
	_qa_camera.fov = 56.0
	_qa_camera.near = 0.2
	_qa_camera.far = 500.0
	_qa_camera.position = Vector3(0.0, 72.0, 118.0)
	_qa_camera.look_at(Vector3(0.0, 8.0, 0.0), Vector3.UP)
	add_child(_qa_camera)


func _compact_runtime_districts() -> void:
	var shifts := {
		"VillaDistrict": Vector3(47.0, 0.0, -39.0),
		"TraditionalDistrict": Vector3(33.0, 0.0, -72.0),
		"SouqDistrict": Vector3(-1.0, 0.0, 22.0),
		"WaterfrontDistrict": Vector3(-51.0, 0.0, 13.0),
		"CommercialDistrict": Vector3(-17.0, 0.0, -37.0),
		"RoadNetwork": Vector3(0.0, 0.0, -24.0),
		"StreetPropSpawner": Vector3(-13.0, 0.0, -7.0),
	}
	for district_name: String in shifts:
		var district := get_node_or_null(district_name) as Node3D
		if district != null:
			district.position = shifts[district_name]
