extends SceneTree

const MissionScript := preload("res://scripts/karak_delivery_mission.gd")
const HUDScene := preload("res://scenes/karak_delivery_hud.tscn")

var _replay_count := 0


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var player := Node3D.new()
	player.name = "HUDRuntimePlayer"
	root.add_child(player)
	var vehicle := Node3D.new()
	vehicle.name = "HUDRuntimeVehicle"
	root.add_child(vehicle)
	var mission: KarakDeliveryMission = MissionScript.new()
	root.add_child(mission)
	var hud := HUDScene.instantiate() as KarakDeliveryHUD
	_require(hud != null, "HUD scene root is not KarakDeliveryHUD")
	root.add_child(hud)
	await process_frame

	var points := {
		"player_spawn": Vector3(-82.0, 1.0, 65.0),
		"cafe_collection": Vector3(-72.0, 0.0, 62.0),
		"vehicle_spawn": Vector3(-58.0, 0.6, 48.0),
		"waterfront_dropoff": Vector3(72.0, 0.0, -62.0),
		"replay_anchor": Vector3(-82.0, 0.0, 65.0),
	}
	_require(mission.configure(points), "mission configure failed")
	_require(mission.start(player, vehicle), "mission start failed")
	hud.replay_requested.connect(_on_replay_requested)
	hud.bind_mission(mission, player)
	await process_frame

	var title := hud.get_node("MissionPanel/Margin/Rows/MissionTitle") as Label
	var objective := hud.get_node("MissionPanel/Margin/Rows/ObjectiveText") as Label
	var replay := hud.get_node("MissionPanel/Margin/Rows/ReplayButton") as Button
	_require(title != null and title.name == "MissionTitle", "MissionTitle missing")
	_require(objective != null and objective.name == "ObjectiveText", "ObjectiveText missing")
	_require(replay != null and replay.name == "ReplayButton", "ReplayButton missing")
	_require(objective.text == "Walk to the karak café", "initial objective mismatch")

	player.global_position = points["cafe_collection"]
	_require(mission.advance_from_player_position(player.global_position), "cafe transition failed")
	_require(mission.notify_order_collected(), "order transition failed")
	_require((hud.get_node("MissionPanel/Margin/Rows/OrderIndicator") as Label).text == "Order: Collected", "order indicator mismatch")
	_require(mission.notify_vehicle_entered(vehicle), "vehicle enter transition failed")
	player.global_position = points["waterfront_dropoff"]
	_require(mission.advance_from_player_position(player.global_position), "waterfront transition failed")
	_require(mission.notify_vehicle_exited(), "vehicle exit transition failed")
	_require(mission.advance_from_player_position(player.global_position), "completion transition failed")
	await process_frame
	_require(replay.visible, "ReplayButton not visible after completion")
	_require((hud.get_node("MissionPanel/Margin/Rows/RewardText") as Label).text == "Reward: 250 coins", "reward text mismatch")
	replay.emit_signal("pressed")
	_require(_replay_count == 1, "replay_requested signal mismatch")

	print("KARAK_DELIVERY_HUD_RUNTIME_PASS")
	quit(0)


func _on_replay_requested() -> void:
	_replay_count += 1


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
