extends Node3D
class_name NPCManager

# NPC spawn zones around landmarks
var spawn_zones: Array[Dictionary] = []
var npc_scene: PackedScene
var npc_count: int = 0
# Reduced from 60 to 25 for mobile performance
var max_npcs: int = 25
var _spawn_queue: Array[Dictionary] = []
var _spawn_per_frame: int = 3

# NPC colors (brick-style palette)
const NPC_COLORS: Array[Color] = [
	Color(0.9, 0.1, 0.1),   # Red
	Color(0.1, 0.4, 0.9),   # Blue
	Color(0.9, 0.7, 0.0),   # Yellow
	Color(0.1, 0.7, 0.2),   # Green
	Color(0.8, 0.3, 0.8),   # Purple
	Color(0.9, 0.5, 0.1),   # Orange
	Color(0.2, 0.2, 0.2),   # Black
	Color(0.9, 0.9, 0.9),   # White
	Color(0.6, 0.8, 0.9),   # Light blue
	Color(0.8, 0.4, 0.3),   # Brown
]

# Real animated NPC models (assets/characters_kit/, CC0 Quaternius-style pack)
# — distinct from the 6 playable roster models so pedestrians look different
# from the player character.
const NPC_MODELS: Array[String] = [
	"res://assets/characters_kit/Casual_Male.gltf",
	"res://assets/characters_kit/Casual_Female.gltf",
	"res://assets/characters_kit/Casual2_Female.gltf",
	"res://assets/characters_kit/Casual3_Female.gltf",
	"res://assets/characters_kit/Doctor_Male_Young.gltf",
	"res://assets/characters_kit/Doctor_Female_Young.gltf",
	"res://assets/characters_kit/Chef_Male.gltf",
	"res://assets/characters_kit/Chef_Female.gltf",
	"res://assets/characters_kit/Worker_Female.gltf",
	"res://assets/characters_kit/OldClassy_Male.gltf",
	"res://assets/characters_kit/OldClassy_Female.gltf",
	"res://assets/characters_kit/Cowboy_Female.gltf",
	"res://assets/characters_kit/Kimono_Female.gltf",
	"res://assets/characters_kit/Pirate_Male.gltf",
	"res://assets/characters_kit/Pirate_Female.gltf",
]

# NPC names (Bahraini-style)
const NPC_NAMES: Array[String] = [
	"Ahmed", "Mohammed", "Ali", "Hassan", "Khalid", "Omar", "Yusuf", "Ibrahim",
	"Fatima", "Noora", "Aisha", "Mariam", "Zainab", "Sara", "Hala", "Nada",
	"Mohammed", "Abdullah", "Salman", "Hamad", "Isa", "Khalifa", "Rashid", "Tariq"
]

func _ready() -> void:
	# Build NPC scene from code since we can't load .tscn easily
	npc_scene = PackedScene.new()
	_setup_spawn_zones()
	# Build the spawn queue but don't spawn all at once — spawn a few per frame
	_build_spawn_queue()
	set_process(true)

func _setup_spawn_zones() -> void:
	# Manama Souk area — dense crowd
	spawn_zones.append({
		"center": Vector3(0, 0, -40),
		"radius": 25.0,
		"count": 10
	})
	# City Center Mall area — shoppers
	spawn_zones.append({
		"center": Vector3(80, 0, 60),
		"radius": 20.0,
		"count": 7
	})
	# Marina Beach area — tourists
	spawn_zones.append({
		"center": Vector3(-60, 0, 80),
		"radius": 30.0,
		"count": 5
	})
	# Financial Harbour — business people
	spawn_zones.append({
		"center": Vector3(30, 0, 20),
		"radius": 15.0,
		"count": 3
	})

func _build_spawn_queue() -> void:
	for zone in spawn_zones:
		var center: Vector3 = zone["center"]
		var radius: float = zone["radius"]
		var count: int = zone["count"]
		for i in range(count):
			if npc_count >= max_npcs:
				return
			var angle: float = (float(i) / float(count)) * TAU + randf_range(-0.5, 0.5)
			var dist: float = randf_range(0.0, radius)
			var pos: Vector3 = center + Vector3(cos(angle) * dist, 0.0, sin(angle) * dist)
			_spawn_queue.append({
				"pos": pos,
				"color": NPC_COLORS[randi() % NPC_COLORS.size()],
				"name": NPC_NAMES[randi() % NPC_NAMES.size()],
				"radius": radius,
				"model_path": NPC_MODELS[randi() % NPC_MODELS.size()],
			})
			npc_count += 1

func _process(_delta: float) -> void:
	# Spawn a few NPCs per frame to avoid stutters
	var to_spawn: int = min(_spawn_per_frame, _spawn_queue.size())
	for i in range(to_spawn):
		var data: Dictionary = _spawn_queue.pop_front()
		var npc: NPCPedestrian = NPCPedestrian.new()
		npc.home_position = data["pos"]
		npc.npc_color = data["color"]
		npc.npc_name = data["name"]
		npc.walk_radius = data["radius"]
		npc.model_path = data.get("model_path", "")
		add_child(npc)  # must be added to the tree BEFORE setting global_position
		npc.global_position = data["pos"]
	
	if _spawn_queue.is_empty():
		set_process(false)
		print("NPCManager: Spawned %d NPCs" % npc_count)

func get_npc_count() -> int:
	return npc_count

func spawn_npc_at(pos: Vector3) -> NPCPedestrian:
	if npc_count >= max_npcs:
		return null
	var npc: NPCPedestrian = NPCPedestrian.new()
	npc.home_position = pos
	npc.npc_color = NPC_COLORS[randi() % NPC_COLORS.size()]
	npc.npc_name = NPC_NAMES[randi() % NPC_NAMES.size()]
	npc.model_path = NPC_MODELS[randi() % NPC_MODELS.size()]
	add_child(npc)  # must be added to the tree BEFORE setting global_position
	npc.global_position = pos
	npc_count += 1
	return npc
