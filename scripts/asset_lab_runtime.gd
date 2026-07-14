extends Node3D
## Verified Asset Lab runtime bridge.
## Loads checksum-evidenced Balanced/LOD0 assets into real world districts.
## This node is deliberately isolated from all protected input and authority code.

const VILLA_ASSETS = [
    "res://assets/environment/architecture/villas/bh_villa_wall_solid_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_wall_window_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_wall_door_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_corner_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_balcony_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_roof_edge_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_parapet_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_gate_pedestrian_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_gate_vehicle_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_boundary_wall_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_column_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_canopy_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_stair_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_garage_opening_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_ac_unit_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_water_tank_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_satellite_dish_01_lod0.glb",
    "res://assets/environment/architecture/villas/bh_villa_driveway_01_lod0.glb",
]

const CLEAN_ROOM_ASSETS = [
    {
        "path": "res://assets/environment/architecture/commercial/bh_cr_building_block_01_lod0.glb",
        "district": "CommercialDistrict",
    },
    {
        "path": "res://assets/environment/architecture/waterfront/bh_cr_skyscraper_tower_01_lod0.glb",
        "district": "WaterfrontDistrict",
    },
    {
        "path": "res://assets/vehicles/clean_room/bh_cr_vehicle_sedan_01_lod0.glb",
        "district": "CommercialDistrict",
    },
    {
        "path": "res://assets/environment/vegetation/bh_cr_date_palm_01_lod0.glb",
        "district": "WaterfrontDistrict",
    },
    {
        "path": "res://assets/environment/vegetation/bh_cr_shade_tree_01_lod0.glb",
        "district": "TraditionalDistrict",
    },
    {
        "path": "res://assets/props/street/bh_cr_desert_planter_01_lod0.glb",
        "district": "SouqDistrict",
    },
    {
        "path": "res://assets/environment/roads/bh_cr_road_straight_01_lod0.glb",
        "district": "RoadNetwork",
    },
]

const CLEAN_ROOM_SHADER := "res://assets/shaders/bh_cr_mobile_toon_shader_01.gdshader"
const DISTRICTS = [
    "VillaDistrict",
    "TraditionalDistrict",
    "SouqDistrict",
    "WaterfrontDistrict",
    "CommercialDistrict",
    "RoadNetwork",
]


func _ready() -> void:
    for district_name in DISTRICTS:
        var district := Node3D.new()
        district.name = district_name
        add_child(district)

    _instantiate_family(
        get_node("VillaDistrict") as Node3D,
        VILLA_ASSETS,
        Vector3(-92.0, 0.0, 74.0)
    )
    _instantiate_clean_room_assets()
    _load_mobile_shader()
    print("BAHRAIN BRICK GAME ASSET LAB READY")


func _instantiate_family(parent: Node3D, paths: Array, origin: Vector3) -> void:
    for index in paths.size():
        _instantiate_verified_scene(parent, paths[index], origin, index)


func _instantiate_clean_room_assets() -> void:
    for index in CLEAN_ROOM_ASSETS.size():
        var record: Dictionary = CLEAN_ROOM_ASSETS[index]
        var district := get_node(str(record["district"])) as Node3D
        var district_origin := _district_origin(str(record["district"]))
        _instantiate_verified_scene(district, str(record["path"]), district_origin, index)


func _instantiate_verified_scene(parent: Node3D, path: String, origin: Vector3, index: int) -> void:
    if not ResourceLoader.exists(path, "PackedScene"):
        push_warning("Asset Lab resource pending: %s" % path)
        return
    var packed := ResourceLoader.load(path, "PackedScene") as PackedScene
    if packed == null:
        push_warning("Asset Lab resource failed to load: %s" % path)
        return
    var instance := packed.instantiate() as Node3D
    if instance == null:
        push_warning("Asset Lab resource is not Node3D: %s" % path)
        return
    var column := index % 6
    var row := index / 6
    instance.position = origin + Vector3(column * 7.0, 0.0, row * 8.0)
    instance.set_meta("asset_lab_source", path)
    instance.set_meta("quality_profile", "balanced")
    instance.set_meta("lod_level", 0)
    parent.add_child(instance)


func _load_mobile_shader() -> void:
    if not ResourceLoader.exists(CLEAN_ROOM_SHADER, "Shader"):
        push_warning("Asset Lab shader pending: %s" % CLEAN_ROOM_SHADER)
        return
    var shader := ResourceLoader.load(CLEAN_ROOM_SHADER, "Shader") as Shader
    if shader != null:
        set_meta("clean_room_mobile_shader", shader)


func _district_origin(district_name: String) -> Vector3:
    match district_name:
        "TraditionalDistrict":
            return Vector3(-58.0, 0.0, 92.0)
        "SouqDistrict":
            return Vector3(-24.0, 0.0, -42.0)
        "WaterfrontDistrict":
            return Vector3(76.0, 0.0, -28.0)
        "CommercialDistrict":
            return Vector3(42.0, 0.0, 62.0)
        "RoadNetwork":
            return Vector3(0.0, 0.0, 24.0)
        _:
            return Vector3.ZERO
