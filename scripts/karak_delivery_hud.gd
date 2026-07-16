extends CanvasLayer
class_name KarakDeliveryHUD

signal replay_requested()

@onready var mission_title: Label = $MissionPanel/Margin/Rows/MissionTitle
@onready var objective_text: Label = $MissionPanel/Margin/Rows/ObjectiveText
@onready var distance_text: Label = $MissionPanel/Margin/Rows/DistanceText
@onready var order_indicator: Label = $MissionPanel/Margin/Rows/OrderIndicator
@onready var reward_text: Label = $MissionPanel/Margin/Rows/RewardText
@onready var interaction_prompt: Label = $MissionPanel/Margin/Rows/InteractionPrompt
@onready var replay_button: Button = $MissionPanel/Margin/Rows/ReplayButton

var _mission: KarakDeliveryMission
var _player: Node3D
var _status_deadline_msec := 0
var _status_restore_text := ""


func _ready() -> void:
	replay_button.pressed.connect(_on_replay_pressed)
	set_process(true)


func bind_mission(mission: KarakDeliveryMission, player: Node3D) -> void:
	_disconnect_mission()
	_mission = mission
	_player = player
	if _mission == null:
		return
	_mission.objective_changed.connect(_on_objective_changed)
	_mission.state_changed.connect(_on_state_changed)
	_mission.mission_completed.connect(_on_mission_completed)
	_mission.mission_failed.connect(_on_mission_failed)
	mission_title.text = "KARAK DELIVERY"
	objective_text.text = _mission.get_current_objective()
	order_indicator.text = "Order: Collected" if _mission.has_order() else "Order: Not collected"
	reward_text.visible = false
	replay_button.visible = false
	_update_distance()


func set_interaction_prompt(text: String, visible: bool) -> void:
	interaction_prompt.text = text
	interaction_prompt.visible = visible and not text.is_empty()


func set_status_message(text: String, duration_seconds: float = 2.0) -> void:
	if text.is_empty():
		return
	_status_restore_text = objective_text.text
	objective_text.text = text
	_status_deadline_msec = Time.get_ticks_msec() + int(maxf(duration_seconds, 0.1) * 1000.0)


func _process(_delta: float) -> void:
	_update_distance()
	if _status_deadline_msec > 0 and Time.get_ticks_msec() >= _status_deadline_msec:
		_status_deadline_msec = 0
		objective_text.text = _mission.get_current_objective() if _mission != null else _status_restore_text


func _update_distance() -> void:
	if _mission == null or not is_instance_valid(_player):
		distance_text.text = "Distance: --"
		return
	if _mission.current_state in [KarakDeliveryMission.MissionState.COMPLETED, KarakDeliveryMission.MissionState.FAILED]:
		distance_text.text = "Distance: --"
		return
	var distance := _player.global_position.distance_to(_mission.get_current_target())
	distance_text.text = "Distance: %dm" % int(round(distance))
	order_indicator.text = "Order: Collected" if _mission.has_order() else "Order: Not collected"


func _on_objective_changed(text: String, _target: Vector3) -> void:
	if _status_deadline_msec == 0:
		objective_text.text = text
	_update_distance()


func _on_state_changed(_previous_state: int, current_state: int) -> void:
	match current_state:
		KarakDeliveryMission.MissionState.COLLECT_ORDER:
			set_interaction_prompt("INTERACT: COLLECT ORDER", true)
		KarakDeliveryMission.MissionState.ENTER_VEHICLE:
			set_interaction_prompt("INTERACT: ENTER VEHICLE", true)
		KarakDeliveryMission.MissionState.EXIT_VEHICLE:
			set_interaction_prompt("INTERACT: EXIT VEHICLE", true)
		KarakDeliveryMission.MissionState.DELIVER_ORDER:
			set_interaction_prompt("INTERACT: DELIVER ORDER", true)
		_:
			set_interaction_prompt("", false)


func _on_mission_completed(reward_coins: int, _elapsed_seconds: float) -> void:
	objective_text.text = "Delivery complete"
	distance_text.text = "Distance: --"
	order_indicator.text = "Order: Collected"
	reward_text.text = "Reward: %d coins" % reward_coins
	reward_text.visible = true
	replay_button.visible = true
	set_interaction_prompt("", false)


func _on_mission_failed(reason: String) -> void:
	objective_text.text = reason
	distance_text.text = "Distance: --"
	reward_text.visible = false
	replay_button.visible = true
	set_interaction_prompt("", false)


func _on_replay_pressed() -> void:
	replay_requested.emit()


func _disconnect_mission() -> void:
	if _mission == null:
		return
	if _mission.objective_changed.is_connected(_on_objective_changed):
		_mission.objective_changed.disconnect(_on_objective_changed)
	if _mission.state_changed.is_connected(_on_state_changed):
		_mission.state_changed.disconnect(_on_state_changed)
	if _mission.mission_completed.is_connected(_on_mission_completed):
		_mission.mission_completed.disconnect(_on_mission_completed)
	if _mission.mission_failed.is_connected(_on_mission_failed):
		_mission.mission_failed.disconnect(_on_mission_failed)
