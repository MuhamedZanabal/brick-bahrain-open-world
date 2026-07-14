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

const TRADITIONAL_ASSETS = [
    "res://assets/environment/architecture/traditional/bh_traditional_party_wall_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_timber_door_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_projecting_window_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_alley_arch_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_parapet_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_courtyard_hint_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_shop_bay_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_shade_canopy_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_roof_tank_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_ac_screen_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_vent_panel_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_traditional_lamp_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_bench_01_lod0.glb",
    "res://assets/environment/architecture/traditional/bh_traditional_utility_cable_01_lod0.glb",
]

const SOUQ_ASSETS = [
    "res://assets/environment/architecture/souq/bh_souq_shop_gold_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_spice_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_tailor_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_perfume_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_electronics_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_fabric_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_toy_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_grocery_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_cafe_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_bakery_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shop_souvenir_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_awning_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_display_table_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_crate_set_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_covered_passage_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_delivery_door_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_shutter_01_lod0.glb",
    "res://assets/environment/architecture/souq/bh_souq_sign_panel_01_lod0.glb",
]

const WATERFRONT_ASSETS = [
    "res://assets/environment/architecture/waterfront/bh_waterfront_promenade_10m_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_promenade_20m_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_curve_15deg_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_curve_30deg_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_curve_45deg_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_marina_edge_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_railing_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_bench_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_palm_planter_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_cafe_terrace_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_water_stair_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_hotel_dropoff_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_tower_a_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_tower_b_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_tower_c_01_lod0.glb",
    "res://assets/environment/architecture/waterfront/bh_waterfront_skyline_silhouette_01_lod0.glb",
]

const ROAD_ASSETS = [
    "res://assets/environment/roads/bh_road_two_lane_straight_20m_01.glb",
    "res://assets/environment/roads/bh_kerb_standard_straight_4m_01.glb",
    "res://assets/environment/roads/bh_road_intersection_four_way_20m_01.glb",
    "res://assets/environment/roads/bh_road_intersection_t_20m_01.glb",
    "res://assets/environment/roads/bh_road_roundabout_compact_24m_01.glb",
    "res://assets/environment/roads/bh_road_crossing_zebra_8m_01.glb",
    "res://assets/environment/roads/bh_road_highway_six_lane_straight_40m_01.glb",
    "res://assets/environment/roads/bh_road_highway_curve_40m_01.glb",
    "res://assets/environment/roads/bh_road_highway_slip_road_30m_01.glb",
    "res://assets/environment/roads/bh_road_highway_exit_40m_01.glb",
    "res://assets/environment/roads/bh_sidewalk_commercial_straight_4m_01.glb",
    "res://assets/environment/roads/bh_sidewalk_driveway_cut_4m_01.glb",
    "res://assets/environment/roads/bh_drainage_channel_straight_4m_01.glb",
]

const STREET_PROP_ASSETS = [
    "res://assets/props/street/bh_prop_street_bollard_a_01.glb",
    "res://assets/props/street/bh_prop_streetlamp_prom_a_01.glb",
    "res://assets/props/street/bh_prop_traffic_signal_a_01.glb",
    "res://assets/props/street/bh_prop_crash_barrier_4m_01.glb",
    "res://assets/props/street/bh_prop_bus_shelter_a_01.glb",
    "res://assets/props/street/bh_prop_direction_sign_frame_a_01.glb",
]

const COMMERCIAL_ASSETS = [
    "res://assets/environment/architecture/commercial/bh_supermarket_storefront_a_01.glb",
    "res://assets/environment/architecture/commercial/bh_supermarket_shelf_1m_01.glb",
    "res://assets/environment/architecture/commercial/bh_cafe_storefront_karak_a_01.glb",
    "res://assets/environment/architecture/commercial/bh_cafe_table_chair_set_a_01.glb",
    "res://assets/environment/architecture/commercial/bh_prop_supermarket_checkout_a_01.glb",
]

const CLEAN_ROOM_ASSETS = [
    {"path": "res://assets/environment/architecture/commercial/bh_cr_building_block_01_lod0.glb", "district": "CommercialDistrict"},
    {"path": "res://assets/environment/architecture/waterfront/bh_cr_skyscraper_tower_01_lod0.glb", "district": "WaterfrontDistrict"},
    {"path": "res://assets/vehicles/clean_room/bh_cr_vehicle_sedan_01_lod0.glb", "district": "CommercialDistrict"},
    {"path": "res://assets/environment/vegetation/bh_cr_date_palm_01_lod0.glb", "district": "WaterfrontDistrict"},
    {"path": "res://assets/environment/vegetation/bh_cr_shade_tree_01_lod0.glb", "district": "TraditionalDistrict"},
    {"path": "res://assets/props/street/bh_cr_desert_planter_01_lod0.glb", "district": "SouqDistrict"},
    {"path": "res://assets/environment/roads/bh_cr_road_straight_01_lod0.glb", "district": "RoadNetwork"},
]

const CLEAN_ROOM_SHADER := "res://assets/shaders/bh_cr_mobile_toon_shader_01.gdshader"
const DISTRICTS = ["VillaDistrict", "TraditionalDistrict", "SouqDistrict", "WaterfrontDistrict", "CommercialDistrict", "RoadNetwork", "StreetPropSpawner"]


func _ready() -> void:
    for district_name in DISTRICTS:
        var district := Node3D.new()
        district.name = district_name
        add_child(district)
    _instantiate_family(get_node("VillaDistrict") as Node3D, VILLA_ASSETS, Vector3(-92.0, 0.0, 74.0))
    _instantiate_family(get_node("TraditionalDistrict") as Node3D, TRADITIONAL_ASSETS, _district_origin("TraditionalDistrict"))
    _instantiate_family(get_node("SouqDistrict") as Node3D, SOUQ_ASSETS, _district_origin("SouqDistrict"))
    _instantiate_family(get_node("WaterfrontDistrict") as Node3D, WATERFRONT_ASSETS, _district_origin("WaterfrontDistrict"))
    _instantiate_family(get_node("RoadNetwork") as Node3D, ROAD_ASSETS, _district_origin("RoadNetwork"))
    _instantiate_family(get_node("StreetPropSpawner") as Node3D, STREET_PROP_ASSETS, _district_origin("StreetPropSpawner"))
    _instantiate_family(get_node("CommercialDistrict") as Node3D, COMMERCIAL_ASSETS, _district_origin("CommercialDistrict"))
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
        _instantiate_verified_scene(district, str(record["path"]), _district_origin(str(record["district"])), index)


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
        "StreetPropSpawner":
            return Vector3(18.0, 0.0, 12.0)
        _:
            return Vector3.ZERO
