extends Node3D
class_name ServerWorld

# Server-side world simulation for authoritative server mode
# Handles physics simulation, NPC management, and state broadcasting on the server

var simulated_players: Dictionary = {}  # peer_id -> {position, velocity, health, coins}
var simulated_npcs: Array[Dictionary] = []
var world_bounds: AABB = AABB(Vector3(-500, -10, -500), Vector3(1000, 100, 1000))
var physics_world: Node3D
var server_tick: float = 0.0
var tick_rate: float = 20.0  # Server ticks at 20Hz
var tick_accumulator: float = 0.0
var is_active: bool = false

# Server-side physics constants
const GRAVITY: float = 9.8
const MAX_PLAYER_SPEED: float = 12.0
const MAX_VEHICLE_SPEED: float = 50.0
const PLAYER_JUMP_FORCE: float = 6.0

func _ready() -> void:
	var mp: Node = get_tree().get_first_node_in_group("multiplayer_manager")
	if mp and mp.has_method("is_host") and mp.is_host():
		is_active = true
		_init_server_world()
		print("ServerWorld: Initialized for authoritative server")

func _init_server_world() -> void:
	# Set up server-side simulation space
	physics_world = Node3D.new()
	physics_world.name = "ServerPhysics"
	add_child(physics_world)

	# Initialize NPC simulation data
	var npc_mgr: Node = get_tree().get_first_node_in_group("npc_manager")
	if npc_mgr:
		for child in npc_mgr.get_children():
			if child is NPCPedestrian:
				simulated_npcs.append({
					"node": child,
					"position": child.global_position,
					"velocity": Vector3.ZERO,
					"state": child.state
				})

func _process(delta: float) -> void:
	if not is_active:
		return

	tick_accumulator += delta
	var tick_interval: float = 1.0 / tick_rate

	while tick_accumulator >= tick_interval:
		tick_accumulator -= tick_interval
		server_tick += 1
		_run_simulation_tick(tick_interval)

func _run_simulation_tick(dt: float) -> void:
	# Simulate player physics
	for peer_id in simulated_players:
		var state: Dictionary = simulated_players[peer_id]
		_simulate_player(peer_id, state, dt)

	# Simulate NPC movement
	_simulate_npcs(dt)

	# Broadcast world state
	if int(server_tick) % 5 == 0:  # Broadcast every 5 ticks (4Hz)
		_broadcast_world_state()

func _simulate_player(peer_id: int, state: Dictionary, dt: float) -> void:
	var pos: Vector3 = state.get("position", Vector3.ZERO)
	var vel: Vector3 = state.get("velocity", Vector3.ZERO)

	# Apply gravity
	vel.y -= GRAVITY * dt

	# Apply movement from inputs
	var move_dir: Vector3 = state.get("move_dir", Vector3.ZERO)
	vel.x = move_dir.x * MAX_PLAYER_SPEED
	vel.z = move_dir.z * MAX_PLAYER_SPEED

	# Update position
	pos += vel * dt

	# Ground collision (simplified)
	if pos.y < 1.0:
		pos.y = 1.0
		vel.y = 0

	# World bounds
	pos.x = clamp(pos.x, world_bounds.position.x, world_bounds.position.x + world_bounds.size.x)
	pos.z = clamp(pos.z, world_bounds.position.z, world_bounds.position.z + world_bounds.size.z)

	# Validate speed
	if vel.length() > MAX_PLAYER_SPEED * 2:
		# Speed hack — clamp
		vel = vel.normalized() * MAX_PLAYER_SPEED

	state["position"] = pos
	state["velocity"] = vel

func _simulate_npcs(dt: float) -> void:
	for npc_data in simulated_npcs:
		var npc: NPCPedestrian = npc_data["node"]
		if not npc or not is_instance_valid(npc):
			continue

		# Server runs simplified NPC AI
		var pos: Vector3 = npc_data["position"]
		var vel: Vector3 = npc_data["velocity"]

		# Random walk
		if randf() < 0.02:
			var angle: float = randf() * TAU
			vel = Vector3(cos(angle), 0, sin(angle)) * 2.0

		pos += vel * dt
		npc_data["position"] = pos
		npc_data["velocity"] = vel

func _broadcast_world_state() -> void:
	if not multiplayer or not multiplayer.has_multiplayer_peer():
		return

	var state: Dictionary = {}
	for peer_id in simulated_players:
		var p_state: Dictionary = simulated_players[peer_id]
		state[str(peer_id)] = {
			"pos": {
				"x": float(p_state.get("position", Vector3.ZERO).x),
				"y": float(p_state.get("position", Vector3.ZERO).y),
				"z": float(p_state.get("position", Vector3.ZERO).z)
			},
			"coins": int(p_state.get("coins", 0)),
			"health": int(p_state.get("health", 100))
		}

	# Broadcast to all clients
	rpc("_rpc_update_world_state", state)

@rpc("authority", "call_remote", "unreliable")
func _rpc_update_world_state(state: Dictionary) -> void:
	# Clients receive and apply world state
	for peer_id_str in state:
		var peer_id: int = int(peer_id_str)
		var data: Dictionary = state[peer_id_str]

		if peer_id == multiplayer.get_unique_id():
			# Reconcile local player with server state
			_reconcile_player(data)
		else:
			# Update remote player avatar
			_update_remote_avatar(peer_id, data)

func _reconcile_player(data: Dictionary) -> void:
	# Smooth correction — only snap if large discrepancy
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return

	var pos_data: Dictionary = data.get("pos", {"x": 0, "y": 0, "z": 0})
	var server_pos: Vector3 = Vector3(float(pos_data["x"]), float(pos_data["y"]), float(pos_data["z"]))
	var dist: float = player.global_position.distance_to(server_pos)

	if dist > 5.0:
		# Large discrepancy — snap to server position
		player.global_position = server_pos
	elif dist > 0.5:
		# Small discrepancy — smooth interpolation
		player.global_position = player.global_position.lerp(server_pos, 0.3)

func _update_remote_avatar(peer_id: int, data: Dictionary) -> void:
	# Update remote player position (handled by multiplayer_manager)
	pass

# Server API: Register a new player
func register_player(peer_id: int) -> void:
	simulated_players[peer_id] = {
		"position": Vector3.ZERO,
		"velocity": Vector3.ZERO,
		"health": 100,
		"coins": 0,
		"move_dir": Vector3.ZERO
	}
	print("ServerWorld: Registered player %d" % peer_id)

# Server API: Remove a player
func unregister_player(peer_id: int) -> void:
	simulated_players.erase(peer_id)
	print("ServerWorld: Unregistered player %d" % peer_id)

# Server API: Update player input
func update_player_input(peer_id: int, move_dir: Vector3, jump: bool) -> void:
	if not simulated_players.has(peer_id):
		return
	var state: Dictionary = simulated_players[peer_id]
	state["move_dir"] = move_dir
	if jump:
		var vel: Vector3 = state.get("velocity", Vector3.ZERO)
		vel.y = PLAYER_JUMP_FORCE
		state["velocity"] = vel

# Server API: Award coins to player
func award_coins(peer_id: int, amount: int) -> void:
	if not simulated_players.has(peer_id):
		return
	var state: Dictionary = simulated_players[peer_id]
	state["coins"] = int(state.get("coins", 0)) + amount

# Server API: Get player state
func get_player_state(peer_id: int) -> Dictionary:
	return simulated_players.get(peer_id, {})
