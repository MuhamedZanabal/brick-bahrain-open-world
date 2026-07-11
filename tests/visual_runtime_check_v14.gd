extends SceneTree

const Collector := preload("res://tools/collect_runtime_screenshots.gd")
const OUTPUT := "res://build/runtime_screenshots"
var collector: RuntimeScreenshotCollector
var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://build/ci_logs"))
    collector = Collector.new()
    root.add_child(collector)
    collector.configure(OUTPUT)
    await _scene_capture("res://scenes/main_menu.tscn", "01_main_menu.png")
    await _scene_capture("res://scenes/character_select.tscn", "02_character_select.png")
    if not await _load("res://scenes/world.tscn"):
        await _finish(); return
    var world := current_scene
    if not await _wait_world(world):
        _fail("world did not reach ready state"); await _finish(); return
    var player := _find_player(world)
    if player == null:
        _fail("player missing")
    elif player is Node3D and (player as Node3D).global_position.y <= -1.0:
        _fail("player spawned below ground")
    await _shot("03_hero_district.png")
    if player:
        var before := (player as Node3D).global_position if player is Node3D else Vector3.ZERO
        Input.action_press("move_forward")
        for _i in range(90): await physics_frame
        Input.action_release("move_forward")
        if player is Node3D and before.distance_to((player as Node3D).global_position) < 0.25: _fail("player did not move")
        await _shot("04_player_walking.png")
    var vehicle := _find_group_or_name(world, ["vehicles", "vehicle", "drivable_vehicles"], "vehicle")
    if player and vehicle and await _enter(player, vehicle):
        Input.action_press("move_forward")
        Input.action_press("move_right")
        for _i in range(90): await physics_frame
        Input.action_release("move_forward"); Input.action_release("move_right")
        await _shot("05_vehicle_driving.png")
        if not await _exit(player): _fail("vehicle exit failed")
    else:
        _fail("vehicle entry unavailable")
    var npc := _find_group_or_name(world, ["npcs", "pedestrians"], "pedestrian")
    if npc:
        _place_near(player, npc); await _shot("06_souq_npcs.png")
    else: _fail("NPC evidence unavailable")
    var traffic := _find_group_or_name(world, ["traffic_vehicles", "traffic"], "traffic")
    if traffic:
        _place_near(player, traffic); await _shot("07_boulevard_traffic.png")
    else: _fail("traffic evidence unavailable")
    if player is Node3D:
        (player as Node3D).global_position = Vector3(0.0, 2.0, -92.0)
        await _settle(45); await _shot("08_waterfront.png")
    if _night(world): await _settle(45); await _shot("09_night_scene.png")
    else: _fail("night controller unavailable")
    if _sandstorm(): await _settle(60); await _shot("10_sandstorm.png")
    else: _fail("sandstorm API unavailable")
    if _phone(world): await _shot("11_phone_ui.png")
    else: _fail("phone UI unavailable")
    if _mission(): await _settle(20); await _shot("12_mission_hud.png")
    else: _fail("mission activation unavailable")
    if _find_name(world, "minimap"): await _shot("13_minimap.png")
    else: _fail("minimap unavailable")
    await _finish()

func _scene_capture(path: String, filename: String) -> void:
    if await _load(path): await _shot(filename)

func _load(path: String) -> bool:
    if not ResourceLoader.exists(path): _fail("scene missing: %s" % path); return false
    var err := change_scene_to_file(path)
    if err != OK: _fail("scene change failed %s code %d" % [path, err]); return false
    for _i in range(45): await process_frame
    return current_scene != null

func _wait_world(world: Node) -> bool:
    for i in range(1800):
        await process_frame
        if not is_instance_valid(world): return false
        var ready = world.get("_world_ready")
        if ready is bool and ready: return true
        if i > 120 and _find_player(world): return true
    return false

func _find_player(world: Node) -> Node:
    for group in ["player", "players"]:
        var nodes := get_nodes_in_group(group)
        if not nodes.is_empty(): return nodes[0]
    return _find_name(world, "player")

func _find_group_or_name(world: Node, groups: Array, fragment: String) -> Node:
    for group in groups:
        var nodes := get_nodes_in_group(group)
        if not nodes.is_empty(): return nodes[0]
    return _find_name(world, fragment)

func _find_name(scope: Node, fragment: String) -> Node:
    if scope == null: return null
    var queue: Array[Node] = [scope]
    while not queue.is_empty():
        var node: Node = queue.pop_front() as Node
        if fragment.to_lower() in String(node.name).to_lower(): return node
        for child in node.get_children():
            if child is Node: queue.append(child)
    return null

func _enter(player: Node, vehicle: Node) -> bool:
    _place_near(player, vehicle); await _settle(12)
    for method in ["enter_vehicle", "try_enter_vehicle", "request_enter_vehicle"]:
        if player.has_method(method):
            player.call(method, vehicle); await _settle(20)
            return player.get("current_vehicle") == vehicle or player.get("is_in_vehicle") == true
    return false

func _exit(player: Node) -> bool:
    for method in ["exit_vehicle", "request_exit_vehicle"]:
        if player.has_method(method):
            player.call(method); await _settle(20)
            return player.get("current_vehicle") == null or player.get("is_in_vehicle") == false
    return false

func _place_near(player: Node, target: Node) -> void:
    if player is Node3D and target is Node3D: (player as Node3D).global_position = (target as Node3D).global_position + Vector3(1.5, 0.5, 4.0)

func _night(world: Node) -> bool:
    var node := _find_name(world, "daynight")
    if node == null: node = _find_name(world, "day_night")
    if node == null: return false
    for key in ["time_of_day", "current_hour", "hour"]:
        if _has_property(node, key): node.set(key, 21.0); return true
    for method in ["set_time_of_day", "set_time", "set_hour"]:
        if node.has_method(method): node.call(method, 21.0); return true
    return false

func _sandstorm() -> bool:
    var weather := root.get_node_or_null("WeatherSystem")
    if weather == null: return false
    for method in ["start_sandstorm", "trigger_sandstorm"]:
        if weather.has_method(method): weather.call(method); return true
    return false

func _phone(world: Node) -> bool:
    var phone := _find_name(world, "phone")
    if phone == null: return false
    for method in ["open_phone", "show_phone", "toggle_phone", "open"]:
        if phone.has_method(method): phone.call(method); return true
    if phone is CanvasItem: (phone as CanvasItem).show(); return true
    return false

func _mission() -> bool:
    var manager := root.get_node_or_null("MissionManager")
    if manager == null: return false
    for id in ["pearl_diving", "taxi_job", "property_acquisition"]:
        for method in ["start_mission", "activate_mission"]:
            if manager.has_method(method):
                var result = manager.call(method, id)
                if result == null or result == true: return true
    return false

func _has_property(object: Object, name: String) -> bool:
    for p in object.get_property_list():
        if String(p.get("name", "")) == name: return true
    return false

func _settle(frames: int) -> void:
    for _i in range(frames): await physics_frame

func _shot(filename: String) -> void:
    var result := await collector.capture(filename, 10)
    if result.get("status", "") != "captured": _fail("capture failed: %s" % filename)

func _fail(message: String) -> void:
    failures.append(message); push_error("VISUAL_GATE_FAILED: %s" % message)

func _finish() -> void:
    collector.write_report("res://build/ci_logs/visual_runtime_report.json")
    var f := FileAccess.open("res://build/ci_logs/visual_runtime_failures.txt", FileAccess.WRITE)
    if f: f.store_string("\n".join(failures))
    if failures.is_empty(): print("VISUAL_RUNTIME_CHECK_PASS screenshots=%d" % collector.records.size()); quit(0)
    else: print("VISUAL_RUNTIME_CHECK_FAIL failures=%d" % failures.size()); quit(1)
