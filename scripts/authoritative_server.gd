extends Node

# Authoritative server — validates all game actions
# Runs on the host/server. Clients send inputs, server simulates and broadcasts.

var is_server: bool = false
var validated_players: Dictionary = {}  # peer_id -> player_state
var validated_pickups: Dictionary = {}  # pickup_id -> claimed_by
var validated_missions: Dictionary = {}  # mission_id -> completed_by
var max_speed: float = 50.0
var max_coins_per_second: int = 100
var player_coin_rates: Dictionary = {}  # peer_id -> {coins, timestamp}
var physics_tick: float = 0.0
var tick_rate: float = 30.0  # 30 ticks per second
var tick_accumulator: float = 0.0

# Anti-cheat thresholds
const SPEED_HACK_THRESHOLD: float = 60.0  # Max legitimate speed
const TELEPORT_THRESHOLD: float = 100.0   # Max distance per tick
const COIN_HACK_THRESHOLD: int = 1000     # Max coins per pickup

signal cheat_detected(peer_id: int, reason: String)
signal state_broadcast(player_states: Dictionary)

func _ready() -> void:
	var mp: Node = get_tree().get_first_node_in_group("multiplayer_manager")
	if mp:
		is_server = mp.is_host if mp.has_method("is_host") else false
		if is_server:
			add_to_group("authoritative_server")
			print("AuthoritativeServer: Running as server")
			set_process(true)
		else:
			add_to_group("authoritative_server")
			print("AuthoritativeServer: Running as client")
			set_process(false)

func _process(delta: float) -> void:
	if not is_server:
		return

	tick_accumulator += delta
	var tick_interval: float = 1.0 / tick_rate

	while tick_accumulator >= tick_interval:
		tick_accumulator -= tick_interval
		physics_tick += 1
		_run_server_tick()

func _run_server_tick() -> void:
	# Validate all player positions
	for peer_id in validated_players:
		var state: Dictionary = validated_players[peer_id]
		_validate_player_state(peer_id, state)

	# Broadcast state to all clients (every 2 ticks)
	if int(physics_tick) % 2 == 0:
		state_broadcast.emit(validated_players)
		if multiplayer and multiplayer.has_multiplayer_peer():
			rpc("_rpc_receive_state", _serialize_state())

func _serialize_state() -> Dictionary:
	var result: Dictionary = {}
	for peer_id in validated_players:
		var state: Dictionary = validated_players[peer_id]
		result[str(peer_id)] = {
			"pos": {
				"x": float(state.get("position", Vector3.ZERO).x),
				"y": float(state.get("position", Vector3.ZERO).y),
				"z": float(state.get("position", Vector3.ZERO).z)
			},
			"coins": int(state.get("coins", 0)),
			"health": int(state.get("health", 100))
		}
	return result

@rpc("authority", "call_local", "unreliable")
func _rpc_receive_state(state: Dictionary) -> void:
	# Client receives authoritative state
	for peer_id_str in state:
		var peer_id: int = int(peer_id_str)
		var data: Dictionary = state[peer_id_str]
		# Apply state to local player representation
		if peer_id == multiplayer.get_unique_id():
			# Don't override local player directly — smooth correct
			pass
		else:
			# Update remote player avatars
			_update_remote_player(peer_id, data)

func _update_remote_player(peer_id: int, data: Dictionary) -> void:
	# Update remote player position from server state
	var pos_data: Dictionary = data.get("pos", {"x": 0, "y": 0, "z": 0})
	var pos: Vector3 = Vector3(float(pos_data["x"]), float(pos_data["y"]), float(pos_data["z"]))
	# Find or create remote player avatar
	# (handled by multiplayer_manager)
	pass

# Client -> Server: Report input
@rpc("any_peer", "call_local", "reliable")
func _rpc_report_input(move_dir: Vector3, jump: bool, action: int) -> void:
	var sender: int = multiplayer.get_rpc_sender_id()
	if not is_server:
		return
	# Server processes input and updates authoritative state
	if not validated_players.has(sender):
		validated_players[sender] = {"position": Vector3.ZERO, "coins": 0, "health": 100}

	# Apply movement (server-side simulation)
	var state: Dictionary = validated_players[sender]
	var current_pos: Vector3 = state["position"]
	var new_pos: Vector3 = current_pos + move_dir * 5.0  # 5 m/s base speed

	# Validate: no teleporting
	if current_pos.distance_to(new_pos) > TELEPORT_THRESHOLD:
		cheat_detected.emit(sender, "Teleport hack detected")
		# Revert position
		new_pos = current_pos
		# Kick after 3 offenses
		var offenses: int = int(state.get("offenses", 0)) + 1
		state["offenses"] = offenses
		if offenses >= 3:
			_kick_player(sender, "Repeated teleport hack")

	state["position"] = new_pos
	validated_players[sender] = state

# Client -> Server: Report coin pickup
@rpc("any_peer", "call_local", "reliable")
func _rpc_report_coin_pickup(pickup_id: String, amount: int) -> void:
	var sender: int = multiplayer.get_rpc_sender_id()
	if not is_server:
		return

	# Validate coin amount
	if amount > COIN_HACK_THRESHOLD:
		cheat_detected.emit(sender, "Coin amount hack: %d" % amount)
		return

	# Check if already claimed
	if validated_pickups.has(pickup_id):
		cheat_detected.emit(sender, "Duplicate coin pickup: %s" % pickup_id)
		return

	# Validate
	validated_pickups[pickup_id] = sender

	if not validated_players.has(sender):
		validated_players[sender] = {"position": Vector3.ZERO, "coins": 0, "health": 100}

	var state: Dictionary = validated_players[sender]
	state["coins"] = int(state.get("coins", 0)) + amount
	validated_players[sender] = state

	# Broadcast coin update
	rpc("_rpc_coin_update", sender, int(state["coins"]))

@rpc("authority", "call_local", "reliable")
func _rpc_coin_update(peer_id: int, new_total: int) -> void:
	if peer_id == multiplayer.get_unique_id():
		var player: Node3D = get_tree().get_first_node_in_group("player")
		if player:
			player.set_meta("coin_count", new_total)

# Client -> Server: Report mission completion
@rpc("any_peer", "call_local", "reliable")
func _rpc_report_mission_complete(mission_id: String) -> void:
	var sender: int = multiplayer.get_rpc_sender_id()
	if not is_server:
		return

	# Check for duplicate completion
	if validated_missions.has(mission_id):
		var completed_by: int = validated_missions[mission_id]
		if completed_by != sender:
			cheat_detected.emit(sender, "Duplicate mission completion: %s" % mission_id)
			return

	validated_missions[mission_id] = sender

	# Award coins
	if validated_players.has(sender):
		var state: Dictionary = validated_players[sender]
		state["coins"] = int(state.get("coins", 0)) + 50  # Mission reward
		validated_players[sender] = state

	# Notify all clients
	rpc("_rpc_mission_completed", sender, mission_id)

@rpc("authority", "call_local", "reliable")
func _rpc_mission_completed(peer_id: int, mission_id: String) -> void:
	print("AuthoritativeServer: Mission %s completed by player %d" % [mission_id, peer_id])

func _validate_player_state(peer_id: int, state: Dictionary) -> void:
	var pos: Vector3 = state.get("position", Vector3.ZERO)
	var vel: Vector3 = state.get("velocity", Vector3.ZERO)

	# Speed check
	if vel.length() > SPEED_HACK_THRESHOLD:
		cheat_detected.emit(peer_id, "Speed hack: %.1f m/s" % vel.length())
		# Clamp velocity
		state["velocity"] = vel.normalized() * max_speed

	# Out of bounds check
	if abs(pos.x) > 5000 or abs(pos.z) > 5000 or pos.y < -100 or pos.y > 2000:
		cheat_detected.emit(peer_id, "Out of bounds: %s" % str(pos))
		state["position"] = Vector3.ZERO  # Reset to origin

func _kick_player(peer_id: int, reason: String) -> void:
	print("AuthoritativeServer: Kicking player %d — %s" % [peer_id, reason])
	if multiplayer and multiplayer.has_multiplayer_peer():
		multiplayer.get_multiplayer_peer().disconnect_peer(peer_id)

# Client API: Send input to server
func send_input(move_dir: Vector3, jump: bool, action: int) -> void:
	if is_server:
		return  # Server doesn't need to RPC itself
	if multiplayer and multiplayer.has_multiplayer_peer():
		rpc_id(1, "_rpc_report_input", move_dir, jump, action)

# Client API: Report coin pickup
func report_coin_pickup(pickup_id: String, amount: int) -> void:
	if is_server:
		# Handle locally
		_rpc_report_coin_pickup(pickup_id, amount)
	else:
		if multiplayer and multiplayer.has_multiplayer_peer():
			rpc_id(1, "_rpc_report_coin_pickup", pickup_id, amount)

# Client API: Report mission complete
func report_mission_complete(mission_id: String) -> void:
	if is_server:
		_rpc_report_mission_complete(mission_id)
	else:
		if multiplayer and multiplayer.has_multiplayer_peer():
			rpc_id(1, "_rpc_report_mission_complete", mission_id)
