extends Node
class_name KarakDeliveryMission

signal objective_changed(text: String, target: Vector3)
signal state_changed(previous_state: int, current_state: int)
signal mission_completed(reward_coins: int, elapsed_seconds: float)
signal mission_failed(reason: String)

enum MissionState {
	NOT_STARTED,
	WALK_TO_CAFE,
	COLLECT_ORDER,
	ENTER_VEHICLE,
	DRIVE_TO_WATERFRONT,
	EXIT_VEHICLE,
	DELIVER_ORDER,
	COMPLETED,
	FAILED,
}

const DEFAULT_REWARD_COINS := 250
const DEFAULT_TIME_LIMIT_SECONDS := 300.0
const CAFE_RADIUS_METRES := 3.0
const WATERFRONT_VEHICLE_RADIUS_METRES := 8.0
const DELIVERY_RADIUS_METRES := 3.0

const LEGAL_TRANSITIONS := {
	MissionState.NOT_STARTED: [MissionState.WALK_TO_CAFE],
	MissionState.WALK_TO_CAFE: [MissionState.COLLECT_ORDER, MissionState.FAILED],
	MissionState.COLLECT_ORDER: [MissionState.ENTER_VEHICLE, MissionState.FAILED],
	MissionState.ENTER_VEHICLE: [MissionState.DRIVE_TO_WATERFRONT, MissionState.FAILED],
	MissionState.DRIVE_TO_WATERFRONT: [MissionState.EXIT_VEHICLE, MissionState.FAILED],
	MissionState.EXIT_VEHICLE: [MissionState.DELIVER_ORDER, MissionState.FAILED],
	MissionState.DELIVER_ORDER: [MissionState.COMPLETED, MissionState.FAILED],
	MissionState.COMPLETED: [],
	MissionState.FAILED: [],
}

var current_state: int = MissionState.NOT_STARTED
var _points: Dictionary = {}
var _reward_coins: int = DEFAULT_REWARD_COINS
var _time_limit_seconds: float = DEFAULT_TIME_LIMIT_SECONDS
var _elapsed_seconds: float = 0.0
var _configured: bool = false
var _started: bool = false
var _order_collected: bool = false
var _completed_once: bool = false
var _player: Node3D
var _mission_vehicle: Node3D
var _active_vehicle: Node3D


func configure(points: Dictionary, reward_coins: int = 250, time_limit_seconds: float = 300.0) -> bool:
	var required := [
		"player_spawn",
		"cafe_collection",
		"vehicle_spawn",
		"waterfront_dropoff",
		"replay_anchor",
	]
	for key: String in required:
		if not points.has(key) or not points[key] is Vector3:
			return false
	if reward_coins <= 0 or time_limit_seconds <= 0.0:
		return false
	_points = points.duplicate(true)
	_reward_coins = reward_coins
	_time_limit_seconds = time_limit_seconds
	_configured = true
	return true


func start(player: Node3D, vehicle: Node3D) -> bool:
	if not _configured or player == null or vehicle == null:
		return false
	if _started and current_state != MissionState.COMPLETED and current_state != MissionState.FAILED:
		return false
	_reset_runtime_state()
	_player = player
	_mission_vehicle = vehicle
	_started = true
	if not _transition(MissionState.WALK_TO_CAFE):
		return false
	print("BAHRAIN_BRICK_KARAK_MISSION_STARTED")
	return true


func advance_from_player_position(position: Vector3) -> bool:
	if not _started:
		return false
	match current_state:
		MissionState.WALK_TO_CAFE:
			if position.distance_to(_point("cafe_collection")) <= CAFE_RADIUS_METRES:
				return _transition(MissionState.COLLECT_ORDER)
		MissionState.DRIVE_TO_WATERFRONT:
			if _active_vehicle == _mission_vehicle and position.distance_to(_point("waterfront_dropoff")) <= WATERFRONT_VEHICLE_RADIUS_METRES:
				return _transition(MissionState.EXIT_VEHICLE)
		MissionState.DELIVER_ORDER:
			if _order_collected and position.distance_to(_point("waterfront_dropoff")) <= DELIVERY_RADIUS_METRES:
				return _complete()
	return false


func notify_order_collected() -> bool:
	if current_state != MissionState.COLLECT_ORDER or _order_collected:
		return false
	_order_collected = true
	return _transition(MissionState.ENTER_VEHICLE)


func notify_vehicle_entered(vehicle: Node3D) -> bool:
	if current_state != MissionState.ENTER_VEHICLE or vehicle == null or vehicle != _mission_vehicle:
		return false
	if _active_vehicle != null:
		return false
	_active_vehicle = vehicle
	return _transition(MissionState.DRIVE_TO_WATERFRONT)


func notify_vehicle_exited() -> bool:
	if current_state != MissionState.EXIT_VEHICLE or _active_vehicle == null:
		return false
	_active_vehicle = null
	return _transition(MissionState.DELIVER_ORDER)


func restart() -> bool:
	if not _configured or _player == null or _mission_vehicle == null:
		return false
	var player := _player
	var vehicle := _mission_vehicle
	_started = false
	current_state = MissionState.NOT_STARTED
	return start(player, vehicle)


func fail(reason: String) -> bool:
	if not _started or current_state in [MissionState.COMPLETED, MissionState.FAILED]:
		return false
	if not _transition(MissionState.FAILED):
		return false
	_started = false
	mission_failed.emit(reason)
	return true


func get_current_objective() -> String:
	return _objective_for_state(current_state)


func get_current_target() -> Vector3:
	match current_state:
		MissionState.WALK_TO_CAFE, MissionState.COLLECT_ORDER:
			return _point("cafe_collection")
		MissionState.ENTER_VEHICLE:
			return _point("vehicle_spawn")
		MissionState.DRIVE_TO_WATERFRONT, MissionState.EXIT_VEHICLE, MissionState.DELIVER_ORDER:
			return _point("waterfront_dropoff")
		MissionState.COMPLETED:
			return _point("replay_anchor")
	return Vector3.ZERO


func get_elapsed_seconds() -> float:
	return _elapsed_seconds


func get_reward_coins() -> int:
	return _reward_coins


func has_order() -> bool:
	return _order_collected


func _process(delta: float) -> void:
	if not _started or current_state in [MissionState.NOT_STARTED, MissionState.COMPLETED, MissionState.FAILED]:
		return
	_elapsed_seconds += maxf(delta, 0.0)
	if _elapsed_seconds >= _time_limit_seconds:
		fail("Karak delivery time limit exceeded")


func _transition(next_state: int) -> bool:
	if current_state == next_state:
		return false
	var allowed: Array = LEGAL_TRANSITIONS.get(current_state, [])
	if not next_state in allowed:
		return false
	var previous := current_state
	current_state = next_state
	state_changed.emit(previous, current_state)
	objective_changed.emit(_objective_for_state(current_state), get_current_target())
	return true


func _complete() -> bool:
	if _completed_once:
		return false
	if not _transition(MissionState.COMPLETED):
		return false
	_completed_once = true
	_started = false
	mission_completed.emit(_reward_coins, _elapsed_seconds)
	print("BAHRAIN_BRICK_KARAK_MISSION_COMPLETED reward=%d" % _reward_coins)
	return true


func _reset_runtime_state() -> void:
	current_state = MissionState.NOT_STARTED
	_elapsed_seconds = 0.0
	_order_collected = false
	_completed_once = false
	_active_vehicle = null


func _point(key: String) -> Vector3:
	return _points.get(key, Vector3.ZERO) as Vector3


func _objective_for_state(state: int) -> String:
	match state:
		MissionState.WALK_TO_CAFE:
			return "Walk to the karak café"
		MissionState.COLLECT_ORDER:
			return "Collect the sealed karak order"
		MissionState.ENTER_VEHICLE:
			return "Enter the delivery vehicle"
		MissionState.DRIVE_TO_WATERFRONT:
			return "Drive to the waterfront customer"
		MissionState.EXIT_VEHICLE:
			return "Exit the vehicle at the delivery court"
		MissionState.DELIVER_ORDER:
			return "Deliver the karak order"
		MissionState.COMPLETED:
			return "Delivery complete"
		MissionState.FAILED:
			return "Delivery failed"
	return "Karak Delivery"
