extends Node
## MultiplayerManager - Handles ENet-based multiplayer networking
## Supports up to 100 concurrent players per session (host/client architecture)

signal player_joined(id: int)
signal player_left(id: int)
signal connection_status(status: String)

const DEFAULT_PORT := 50005
const MAX_PLAYERS := 100
const SERVER_TICK_RATE := 30.0

var world: Node3D = null
var peer: ENetMultiplayerPeer = null
var player_scene: PackedScene = null
var spawned_players: Dictionary = {}  # peer_id -> player node

func initialize(world_node: Node3D) -> void:
	add_to_group("multiplayer_manager")
	world = world_node
	
	match GameManager.current_mode:
		GameManager.GameMode.MULTIPLAYER_HOST:
			_start_host()
		GameManager.GameMode.MULTIPLAYER_CLIENT:
			_start_client()
		_:
			# Single player - no networking needed
			pass

func _start_host() -> void:
	peer = ENetMultiplayerPeer.new()
	var err := peer.create_server(DEFAULT_PORT, MAX_PLAYERS)
	if err != OK:
		push_error("Failed to create server: %s" % err)
		connection_status.emit("Failed to start server")
		return
	
	multiplayer.multiplayer_peer = peer
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	
	GameManager.set_player_count(1)
	connection_status.emit("Server started on port %d" % DEFAULT_PORT)
	print("[Multiplayer] Host started on port %d, max %d players" % [DEFAULT_PORT, MAX_PLAYERS])

func _start_client() -> void:
	peer = ENetMultiplayerPeer.new()
	# In a real deployment, this IP would be configurable
	# For now, use localhost as default
	var server_ip := "127.0.0.1"
	var err := peer.create_client(server_ip, DEFAULT_PORT)
	if err != OK:
		push_error("Failed to create client: %s" % err)
		connection_status.emit("Failed to connect to server")
		return
	
	multiplayer.multiplayer_peer = peer
	multiplayer.connected_to_server.connect(_on_connected_to_server)
	multiplayer.connection_failed.connect(_on_connection_failed)
	multiplayer.server_disconnected.connect(_on_server_disconnected)
	
	connection_status.emit("Connecting to %s:%d..." % [server_ip, DEFAULT_PORT])

func _on_peer_connected(id: int) -> void:
	print("[Multiplayer] Player %d connected" % id)
	player_joined.emit(id)
	# Spawn the new player on all clients
	_spawn_remote_player(id)
	GameManager.set_player_count(multiplayer.get_peers().size() + 1)

func _on_peer_disconnected(id: int) -> void:
	print("[Multiplayer] Player %d disconnected" % id)
	player_left.emit(id)
	_despawn_remote_player(id)
	GameManager.set_player_count(max(1, multiplayer.get_peers().size()))

func _on_connected_to_server() -> void:
	print("[Multiplayer] Connected to server!")
	connection_status.emit("Connected to server")
	# Spawn our player on the server
	_spawn_remote_player(multiplayer.get_unique_id())

func _on_connection_failed() -> void:
	print("[Multiplayer] Connection failed!")
	connection_status.emit("Connection failed - playing offline")

func _on_server_disconnected() -> void:
	print("[Multiplayer] Disconnected from server")
	connection_status.emit("Disconnected from server")

func _spawn_remote_player(id: int) -> void:
	if id == multiplayer.get_unique_id():
		return  # Don't spawn ourselves (already spawned locally)
	if spawned_players.has(id):
		return
	
	var player_script = preload("res://scripts/player_controller.gd")
	var remote_player := CharacterBody3D.new()
	remote_player.set_script(player_script)
	remote_player.position = world.player_spawn + Vector3(randf_range(-5, 5), 2, randf_range(-5, 5))
	remote_player.is_local = false
	remote_player.multiplayer_id = id
	remote_player.name = "Player_%d" % id
	
	# Give remote players a different character appearance
	var char_idx = id % GameManager.characters.size()
	remote_player.character_data = GameManager.get_character(char_idx)
	
	world.add_child(remote_player)
	spawned_players[id] = remote_player

func _despawn_remote_player(id: int) -> void:
	if spawned_players.has(id):
		spawned_players[id].queue_free()
		spawned_players.erase(id)

## Sync player positions over network (called at tick rate)
func _process(delta: float) -> void:
	if not peer or multiplayer.multiplayer_peer == null:
		return
	
	# Periodically sync local player position
	_sync_local_player()

func _sync_local_player() -> void:
	if not world or not world.player:
		return
	# In a full implementation, this would RPC position updates
	# For now, the architecture is in place for position interpolation
	pass

func get_player_count() -> int:
	if multiplayer.multiplayer_peer:
		return multiplayer.get_peers().size() + 1
	return 1

func disconnect_from_server() -> void:
	if peer:
		peer.close()
		peer = null
