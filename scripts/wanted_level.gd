extends Node

# Wanted level system (1-5 stars)
var current_level: int = 0
var max_level: int = 5
var decay_timer: float = 0.0
var decay_interval: float = 30.0  # Lose a star every 30s without crime
var police_spawned: int = 0
var max_police: int = 10
var police_npcs: Array[Node3D] = []
var last_crime_time: float = 0.0
var hud_stars: Array[Label] = []

# Crime tracking
var hit_pedestrian_penalty: int = 1  # Stars per hit
var sidewalk_driving_timer: float = 0.0
var sidewalk_driving_threshold: float = 3.0  # Seconds on sidewalk

signal wanted_level_changed(level: int)
signal police_count_changed(count: int)

func _ready() -> void:
	add_to_group("wanted_level")
	_build_wanted_hud()
	wanted_level_changed.emit(current_level)

func _build_wanted_hud() -> void:
	# Stars display (top-right)
	for i in range(max_level):
		var star: Label = Label.new()
		star.text = "★"
		star.position = Vector2(940 + i * 25, 10)
		star.size = Vector2(25, 30)
		star.add_theme_font_size_override("font_size", 24)
		star.add_theme_color_override("font_color", Color(0.3, 0.3, 0.3))
		star.visible = false
		add_child(star)
		hud_stars.append(star)

func _process(delta: float) -> void:
	if current_level > 0:
		decay_timer += delta
		if decay_timer >= decay_interval:
			decay_timer = 0.0
			decrease_level(1)

	# Check for crimes
	_check_crimes(delta)

	# Update police AI
	_update_police(delta)

func _check_crimes(delta: float) -> void:
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return

	# Check for hitting pedestrians
	var npcs: Array[Node] = get_tree().get_nodes_in_group("npc_pedestrians")
	for npc in npcs:
		if npc is NPCPedestrian:
			var dist: float = player.global_position.distance_to(npc.global_position)
			if dist < 1.5 and player.velocity.length() > 5.0:
				increase_level(hit_pedestrian_penalty)
				npc.state = NPCPedestrian.NPCState.FLEEING
				npc.flee_timer = 5.0
				npc.target_position = player.global_position
				last_crime_time = Time.get_ticks_msec() / 1000.0
				break  # One hit per frame

	# Check for driving on sidewalks (near buildings)
	var vehicle: Node3D = get_tree().get_first_node_in_group("player_vehicle")
	if vehicle and vehicle is RigidBody3D:
		if vehicle.linear_velocity.length() > 8.0:
			# Simplified: check if player is in souk area (pedestrian zone)
			var in_souk: bool = abs(vehicle.global_position.x) < 20 and vehicle.global_position.z < -30 and vehicle.global_position.z > -60
			if in_souk:
				sidewalk_driving_timer += delta
				if sidewalk_driving_timer >= sidewalk_driving_threshold:
					increase_level(1)
					sidewalk_driving_timer = 0.0
					last_crime_time = Time.get_ticks_msec() / 1000.0
			else:
				sidewalk_driving_timer = 0.0

func increase_level(amount: int) -> void:
	var new_level: int = clamp(current_level + amount, 0, max_level)
	if new_level != current_level:
		current_level = new_level
		_update_hud()
		wanted_level_changed.emit(current_level)
		_spawn_police()
		print("WantedLevel: Increased to %d stars" % current_level)

func decrease_level(amount: int) -> void:
	var new_level: int = clamp(current_level - amount, 0, max_level)
	if new_level != current_level:
		current_level = new_level
		_update_hud()
		wanted_level_changed.emit(current_level)
		_despawn_excess_police()
		print("WantedLevel: Decreased to %d stars" % current_level)

func _update_hud() -> void:
	for i in range(max_level):
		if i < current_level:
			hud_stars[i].visible = true
			hud_stars[i].add_theme_color_override("font_color", Color(1, 0.8, 0.0))
		else:
			hud_stars[i].visible = false

func _spawn_police() -> void:
	var target_count: int = current_level * 2
	while police_spawned < target_count and police_spawned < max_police:
		var player: Node3D = get_tree().get_first_node_in_group("player")
		if not player:
			return

		# Spawn police near but not too close
		var angle: float = randf() * TAU
		var dist: float = randf_range(30.0, 60.0)
		var spawn_pos: Vector3 = player.global_position + Vector3(cos(angle) * dist, 1.0, sin(angle) * dist)

		var police: PoliceNPC = PoliceNPC.new()
		get_tree().current_scene.add_child(police)  # must be added to the tree BEFORE setting global_position
		police.global_position = spawn_pos
		police_npcs.append(police)
		police_spawned += 1

	police_count_changed.emit(police_spawned)

func _despawn_excess_police() -> void:
	var target_count: int = current_level * 2
	while police_npcs.size() > target_count:
		var police: Node3D = police_npcs.pop_back()
		if police and is_instance_valid(police):
			police.queue_free()
		police_spawned -= 1

func _update_police(delta: float) -> void:
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return

	for police in police_npcs:
		if police and is_instance_valid(police) and police is PoliceNPC:
			police.set_target(player.global_position)

	# Check if player has escaped (all police are far away)
	var all_far: bool = true
	for police in police_npcs:
		if police and is_instance_valid(police):
			var dist: float = police.global_position.distance_to(player.global_position)
			if dist < 80.0:
				all_far = false
				break

	if all_far and current_level > 0:
		# Player is escaping — speed up decay
		decay_timer += delta * 3.0

func clear_level() -> void:
	current_level = 0
	_update_hud()
	wanted_level_changed.emit(current_level)
	for police in police_npcs:
		if police and is_instance_valid(police):
			police.queue_free()
	police_npcs.clear()
	police_spawned = 0

func get_level() -> int:
	return current_level
