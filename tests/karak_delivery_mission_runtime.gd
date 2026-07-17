extends SceneTree

const MissionScript := preload("res://scripts/karak_delivery_mission.gd")

var _states: Array[int] = []
var _completion_count := 0
var _failure_count := 0


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var player := Node3D.new()
	player.name = "RuntimePlayer"
	root.add_child(player)
	var vehicle := Node3D.new()
	vehicle.name = "RuntimeVehicle"
	root.add_child(vehicle)
	var other_vehicle := Node3D.new()
	other_vehicle.name = "WrongVehicle"
	root.add_child(other_vehicle)

	var mission: KarakDeliveryMission = MissionScript.new()
	mission.name = "KarakDeliveryMissionRuntime"
	root.add_child(mission)
	mission.state_changed.connect(_on_state_changed)
	mission.mission_completed.connect(_on_completed)
	mission.mission_failed.connect(_on_failed)

	var points := {
		"player_spawn": Vector3(-82.0, 1.0, 65.0),
		"cafe_collection": Vector3(-72.0, 0.0, 62.0),
		"vehicle_spawn": Vector3(-58.0, 0.6, 48.0),
		"waterfront_dropoff": Vector3(72.0, 0.0, -62.0),
		"replay_anchor": Vector3(-82.0, 0.0, 65.0),
	}
	_require(mission.configure(points, 250, 300.0), "configure failed")
	_require(mission.start(player, vehicle), "start failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.WALK_TO_CAFE, "WALK_TO_CAFE missing")
	_require(not mission.start(player, vehicle), "duplicate transition emitted by start")

	_require(mission.advance_from_player_position(points["cafe_collection"]), "cafe arrival failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.COLLECT_ORDER, "COLLECT_ORDER missing")
	_require(not mission.advance_from_player_position(points["cafe_collection"]), "duplicate transition emitted at cafe")

	_require(mission.notify_order_collected(), "order collection failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.ENTER_VEHICLE, "ENTER_VEHICLE missing")
	_require(not mission.notify_order_collected(), "duplicate transition emitted for order")
	_require(not mission.notify_vehicle_entered(other_vehicle), "wrong vehicle accepted")

	_require(mission.notify_vehicle_entered(vehicle), "vehicle entry failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.DRIVE_TO_WATERFRONT, "DRIVE_TO_WATERFRONT missing")
	_require(not mission.notify_vehicle_entered(vehicle), "duplicate transition emitted for vehicle entry")

	_require(mission.advance_from_player_position(points["waterfront_dropoff"]), "waterfront arrival failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.EXIT_VEHICLE, "EXIT_VEHICLE missing")
	_require(not mission.advance_from_player_position(points["waterfront_dropoff"]), "duplicate transition emitted at waterfront")

	_require(mission.notify_vehicle_exited(), "vehicle exit failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.DELIVER_ORDER, "DELIVER_ORDER missing")
	_require(not mission.notify_vehicle_exited(), "duplicate transition emitted for vehicle exit")

	_require(mission.advance_from_player_position(points["waterfront_dropoff"]), "delivery completion failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.COMPLETED, "COMPLETED missing")
	_require(not mission.advance_from_player_position(points["waterfront_dropoff"]), "duplicate transition emitted after completion")

	var expected := [
		KarakDeliveryMission.MissionState.WALK_TO_CAFE,
		KarakDeliveryMission.MissionState.COLLECT_ORDER,
		KarakDeliveryMission.MissionState.ENTER_VEHICLE,
		KarakDeliveryMission.MissionState.DRIVE_TO_WATERFRONT,
		KarakDeliveryMission.MissionState.EXIT_VEHICLE,
		KarakDeliveryMission.MissionState.DELIVER_ORDER,
		KarakDeliveryMission.MissionState.COMPLETED,
	]
	_require(_states == expected, "state sequence mismatch: %s" % [_states])
	_require(_completion_count == 1, "completion emitted %d times" % _completion_count)
	_require(_failure_count == 0, "mission failed unexpectedly")
	_require(mission.restart(), "restart failed")
	_require(mission.current_state == KarakDeliveryMission.MissionState.WALK_TO_CAFE, "restart did not return to WALK_TO_CAFE")

	print("KARAK_DELIVERY_RUNTIME_PASS")
	quit(0)


func _on_state_changed(_previous: int, current: int) -> void:
	_states.append(current)


func _on_completed(_reward: int, _elapsed: float) -> void:
	_completion_count += 1


func _on_failed(_reason: String) -> void:
	_failure_count += 1


func _require(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
