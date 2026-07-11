extends Node3D
## World - Main game world scene
## Contains the terrain, landmarks, player, vehicles, missions, NPCs, weather, and multiplayer
## Uses deferred/coroutine loading to avoid freezing on mobile

var player: CharacterBody3D
var vehicles: Array[Node3D] = []
var mission_system: Node
var mission_manager: Node
var multiplayer_manager: Node
var hud: CanvasLayer
var world_environment: WorldEnvironment
var sun: DirectionalLight3D
var day_night: DayNightCycle
var weather: WeatherSystem
var npc_manager: NPCManager
var phone_ui: PhoneUI
var shop_ui: ShopUI
var property_mgr: PropertyManager
var server_world: ServerWorld

# Spawn points
var player_spawn: Vector3 = Vector3(0, 2, 0)
var vehicle_spawns: Array[Vector3] = [
	Vector3(5, 1, 5), Vector3(-5, 1, 5), Vector3(10, 1, 0),
	Vector3(45, 1, 0), Vector3(45, 1, -50), Vector3(40, 1, 100)
]

var _collected: Array[String] = []

# ── Loading screen ──
var _loading_overlay: Control
var _loading_bar_bg: ColorRect
var _loading_bar_fill: ColorRect
var _loading_label: Label
var _loading_step: int = 0
var _total_steps: int = 8
var _world_ready: bool = false

func _ready() -> void:
	_show_loading_screen()
	# Start deferred loading — one step per frame so the engine can render
	_load_step_environment()

## Shows a fullscreen loading overlay that updates as world pieces load
func _show_loading_screen() -> void:
	var vp := get_viewport().get_visible_rect().size
	
	_loading_overlay = Control.new()
	_loading_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_loading_overlay.mouse_filter = Control.MOUSE_FILTER_STOP  # block input during load
	add_child(_loading_overlay)
	
	var bg := ColorRect.new()
	bg.color = Color(0.05, 0.05, 0.08)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_loading_overlay.add_child(bg)
	
	# Title
	var title := Label.new()
	title.text = "BRICK BAHRAIN"
	title.add_theme_font_size_override("font_size", 42)
	title.add_theme_color_override("font_color", Color(1.0, 0.8, 0.0))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, vp.y * 0.35)
	title.size = Vector2(vp.x, 50)
	_loading_overlay.add_child(title)
	
	# Status label
	_loading_label = Label.new()
	_loading_label.text = "Loading..."
	_loading_label.add_theme_font_size_override("font_size", 20)
	_loading_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.8))
	_loading_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_loading_label.position = Vector2(0, vp.y * 0.55)
	_loading_label.size = Vector2(vp.x, 30)
	_loading_overlay.add_child(_loading_label)
	
	# Progress bar background
	var bar_w: float = min(vp.x * 0.6, 500.0)
	_loading_bar_bg = ColorRect.new()
	_loading_bar_bg.color = Color(0.15, 0.15, 0.15)
	_loading_bar_bg.position = Vector2(vp.x / 2 - bar_w / 2, vp.y * 0.62)
	_loading_bar_bg.size = Vector2(bar_w, 20)
	_loading_overlay.add_child(_loading_bar_bg)
	
	# Progress bar fill
	_loading_bar_fill = ColorRect.new()
	_loading_bar_fill.color = Color(0.2, 0.7, 0.3)
	_loading_bar_fill.position = _loading_bar_bg.position + Vector2(2, 2)
	_loading_bar_fill.size = Vector2(0, 16)
	_loading_overlay.add_child(_loading_bar_fill)

func _update_loading(text: String) -> void:
	_loading_step += 1
	var pct := float(_loading_step) / float(_total_steps)
	var bar_w := _loading_bar_bg.size.x - 4
	_loading_bar_fill.size.x = bar_w * pct
	_loading_label.text = "%s (%d%%)" % [text, int(pct * 100)]

# ── Deferred loading steps (each calls the next via call_deferred) ──

func _load_step_environment() -> void:
	_setup_environment()
	_update_loading("Building terrain...")
	call_deferred("_load_step_landmarks")

func _load_step_landmarks() -> void:
	LandmarkGenerator.generate_world(self)
	_update_loading("Placing Bahrain landmarks...")
	call_deferred("_load_step_day_night")

func _load_step_day_night() -> void:
	day_night = DayNightCycle.new()
	day_night.name = "DayNightCycle"
	add_child(day_night)
	
	# WeatherSystem is a global autoload singleton — reuse it instead of
	# instancing a second one (Node autoload identifiers can't be .new()'d).
	weather = WeatherSystem
	weather.set_references(day_night)
	
	_update_loading("Setting sky and weather...")
	call_deferred("_load_step_lamps_vehicles")

func _load_step_lamps_vehicles() -> void:
	_spawn_street_lamps()
	_spawn_vehicles()
	_scatter_vegetation()
	_update_loading("Fueling vehicles...")
	call_deferred("_load_step_player")

func _load_step_player() -> void:
	_spawn_player()
	_update_loading("Spawning your character...")
	call_deferred("_load_step_npcs")

func _load_step_npcs() -> void:
	npc_manager = NPCManager.new()
	npc_manager.name = "NPCManager"
	add_child(npc_manager)
	_update_loading("Populating streets of Bahrain...")
	call_deferred("_load_step_systems")

func _load_step_systems() -> void:
	# Mission system (legacy)
	mission_system = preload("res://scripts/mission_system.gd").new()
	mission_system.name = "MissionSystem"
	add_child(mission_system)
	mission_system.initialize(self)
	
	# Multiplayer
	multiplayer_manager = preload("res://scripts/multiplayer_manager.gd").new()
	multiplayer_manager.name = "MultiplayerManager"
	add_child(multiplayer_manager)
	multiplayer_manager.initialize(self)
	
	# PropertyManager is a global autoload singleton — reuse it instead of
	# instancing a second one (Node autoload identifiers can't be .new()'d).
	property_mgr = PropertyManager
	
	_update_loading("Loading missions and systems...")
	call_deferred("_load_step_ui")

func _load_step_ui() -> void:
	# HUD
	hud = preload("res://scenes/hud.tscn").instantiate()
	add_child(hud)
	
	# Phone UI overlay
	phone_ui = PhoneUI.new()
	phone_ui.name = "PhoneUI"
	phone_ui.layer = 10
	add_child(phone_ui)
	
	# Shop UI overlay
	shop_ui = ShopUI.new()
	shop_ui.name = "ShopUI"
	shop_ui.layer = 10
	add_child(shop_ui)
	
	# Server world for authoritative mode
	server_world = ServerWorld.new()
	server_world.name = "ServerWorld"
	add_child(server_world)
	
	# Load save data
	_apply_save_data()
	
	GameManager.current_state = GameManager.GameState.IN_WORLD
	_world_ready = true
	
	_update_loading("Welcome to Bahrain!")
	
	# Fade out loading screen after a brief moment
	await get_tree().create_timer(0.8).timeout
	_hide_loading_screen()

func _hide_loading_screen() -> void:
	if _loading_overlay:
		_loading_overlay.queue_free()
		_loading_overlay = null

func _setup_environment() -> void:
	# NOTE: the primary sun + WorldEnvironment (with sky/glow/SSAO/SSR/fog) are
	# owned by DayNightCycle (added in _load_step_day_night) so time-of-day can
	# drive them. We only add a static cool fill light here for bounce lighting.

	# === Fill light — cool sky bounce from opposite direction ===
	var fill := DirectionalLight3D.new()
	fill.light_color = Color(0.55, 0.65, 0.9)
	fill.light_energy = 0.35
	fill.shadow_enabled = false  # no shadows from fill for perf
	fill.rotation = Vector3(deg_to_rad(35), deg_to_rad(150), 0)
	add_child(fill)

func _spawn_street_lamps() -> void:
	# Spawn street lamps around key landmarks — reduced for mobile perf
	var lamp_positions: Array[Vector3] = [
		Vector3(10, 0, -40), Vector3(-10, 0, -40), Vector3(15, 0, -45),
		Vector3(-15, 0, -45), Vector3(20, 0, -50), Vector3(-20, 0, -50),
		Vector3(80, 0, 55), Vector3(-60, 0, 75),
		Vector3(30, 0, 15), Vector3(0, 0, 120),
	]

	for pos in lamp_positions:
		var lamp_post: MeshInstance3D = MeshInstance3D.new()
		var post_box: BoxMesh = BoxMesh.new()
		post_box.size = Vector3(0.2, 4, 0.2)
		lamp_post.mesh = post_box
		lamp_post.position = pos + Vector3(0, 2, 0)
		var mat: StandardMaterial3D = StandardMaterial3D.new()
		mat.albedo_color = Color(0.3, 0.3, 0.3)
		lamp_post.material_override = mat
		lamp_post.cast_shadow = 0
		add_child(lamp_post)

		# Lamp light — shadows off for mobile performance
		var lamp_light: OmniLight3D = OmniLight3D.new()
		lamp_light.position = pos + Vector3(0, 4, 0)
		lamp_light.light_color = Color(1, 0.9, 0.6)
		lamp_light.light_energy = 1.5
		lamp_light.omni_range = 12.0
		lamp_light.omni_attenuation = 1.5
		lamp_light.shadow_enabled = false
		lamp_light.visible = false
		lamp_light.add_to_group("street_lamps")
		add_child(lamp_light)

func _scatter_vegetation() -> void:
	# Scatter palm trees along roads and near landmarks
	var tree_positions: Array[Vector3] = [
		Vector3(35, 0, 5), Vector3(48, 0, -10), Vector3(25, 0, -25),
		Vector3(55, 0, -60), Vector3(70, 0, -30), Vector3(90, 0, 50),
		Vector3(-30, 0, 10), Vector3(-45, 0, -20), Vector3(-55, 0, 50),
		Vector3(100, 0, -55), Vector3(120, 0, -90), Vector3(130, 0, -40),
		Vector3(-70, 0, 90), Vector3(-40, 0, 110), Vector3(50, 0, 55),
		Vector3(15, 0, -70), Vector3(-15, 0, -55), Vector3(75, 0, -45),
	]
	for pos in tree_positions:
		var tree: Node3D = BrickFactory.create_palm_tree()
		tree.position = pos
		# Random rotation for variety
		tree.rotation.y = randf() * TAU
		# Random scale 0.8-1.2
		var s: float = randf_range(0.8, 1.2)
		tree.scale = Vector3(s, s, s)
		add_child(tree)
	
	# Scatter small bushes / rocks in desert areas
	for i in range(30):
		var angle: float = randf() * TAU
		var dist: float = randf_range(80, 200)
		var pos2: Vector3 = Vector3(cos(angle) * dist, 0, sin(angle) * dist)
		# Skip if too close to a landmark
		var too_close: bool = false
		for lm in LandmarkGenerator.landmarks:
			if pos2.distance_to(lm["pos"]) < 15:
				too_close = true
				break
		if too_close:
			continue
		
		if randf() < 0.5:
			# Small bush
			var bush := MeshInstance3D.new()
			var sphere := SphereMesh.new()
			sphere.radius = randf_range(0.4, 0.8)
			sphere.height = randf_range(0.5, 1.0)
			bush.mesh = sphere
			var mat := StandardMaterial3D.new()
			mat.albedo_color = Color(0.2, 0.45, 0.15)
			mat.roughness = 0.6
			mat.clearcoat_enabled = true
			mat.clearcoat = 0.3
			bush.material_override = mat
			bush.position = pos2 + Vector3(0, 0.4, 0)
			bush.cast_shadow = 1
			add_child(bush)
		else:
			# Small rock
			var rock := MeshInstance3D.new()
			var sphere2 := SphereMesh.new()
			sphere2.radius = randf_range(0.3, 0.6)
			sphere2.height = randf_range(0.3, 0.5)
			rock.mesh = sphere2
			var rmat := StandardMaterial3D.new()
			rmat.albedo_color = Color(0.6, 0.52, 0.38)
			rmat.roughness = 0.7
			rock.material_override = rmat
			rock.position = pos2 + Vector3(0, 0.2, 0)
			rock.cast_shadow = 1
			add_child(rock)

func _spawn_vehicles() -> void:
	# Use different Kenney car models for each spawn
	var car_indices: Array[int] = [0, 2, 4, 8]  # sedan, hatchback-sports, suv, race
	for i in range(min(vehicle_spawns.size(), 4)):
		var vehicle_script = preload("res://scripts/vehicle.gd")
		var vehicle: VehicleBody3D = VehicleBody3D.new()
		vehicle.set_script(vehicle_script)
		vehicle.position = vehicle_spawns[i]
		vehicle.set_meta("car_index", car_indices[i % car_indices.size()])
		add_child(vehicle)
		vehicles.append(vehicle)

func _spawn_player() -> void:
	var player_script = preload("res://scripts/player_controller.gd")
	player = CharacterBody3D.new()
	player.set_script(player_script)
	# Load saved position if available
	if SaveManager and SaveManager.has_save():
		var saved_pos: Vector3 = SaveManager.get_position()
		if saved_pos != Vector3.ZERO:
			player.position = saved_pos
		else:
			player.position = player_spawn
	else:
		player.position = player_spawn
	player.is_local = true
	player.multiplayer_id = multiplayer.get_unique_id()
	add_child(player)

	# Load saved coins
	if SaveManager:
		var coins: int = SaveManager.get_coins()
		player.set_meta("coin_count", coins)

func _apply_save_data() -> void:
	if not SaveManager:
		return
	# Apply unlocked characters, completed missions, etc.
	var completed: Array = SaveManager.get_completed_missions()
	GameManager.set_meta("completed_missions", completed)
	GameManager.set_meta("unlocked_characters", SaveManager.get_unlocked_characters())
	GameManager.set_meta("owned_properties", SaveManager.get_owned_properties())
	GameManager.set_meta("owned_vehicles", SaveManager.get_owned_vehicles())

func _process(delta: float) -> void:
	if not _world_ready:
		return
	
	# Handle collectible pickups
	_check_collectibles()

	# Update HUD
	if hud and hud.has_method("update_hud"):
		hud.update_hud(player, mission_system)

	# Handle vehicle radio
	_handle_radio_input()

func _handle_radio_input() -> void:
	# Radio is handled by RadioSystem autoload + input mapping
	# Check if player is in a vehicle
	if not player:
		return
	if player.has_meta("in_vehicle") and player.get_meta("in_vehicle"):
		if not RadioSystem.is_radio_playing():
			RadioSystem.start_radio()
	else:
		if RadioSystem.is_radio_playing():
			RadioSystem.stop_radio()

func _check_collectibles() -> void:
	if not player:
		return

	for child in get_children():
		if child is MeshInstance3D and child.has_meta("is_collectible"):
			if child.visible == false:
				continue
			var dist: float = player.global_position.distance_to(child.global_position)
			if dist < 2.0:
				var value: int = int(child.get_meta("collectible_value", 10))
				GameManager.add_coins(value)
				child.visible = false
				_collected.append(child.name)
				# Report to authoritative server
				if AuthoritativeServer:
					AuthoritativeServer.report_coin_pickup(child.name, value)
				# Update save manager
				if SaveManager:
					SaveManager.add_coins(value)
				# Update player meta
				var current_coins: int = int(player.get_meta("coin_count", 0))
				player.set_meta("coin_count", current_coins + value)
				_respawn_collectible(child, 10.0)

func _respawn_collectible(coin: MeshInstance3D, delay: float) -> void:
	await get_tree().create_timer(delay).timeout
	coin.visible = true

func _input(event: InputEvent) -> void:
	if not _world_ready:
		return
	if event is InputEventKey and event.pressed:
		# Radio toggle (R key)
		if event.keycode == KEY_R:
			if RadioSystem:
				RadioSystem.next_station()
		# Mission tracking (Q key — use mission manager)
		if event.keycode == KEY_Q:
			if MissionManager and player:
				var nearest: int = MissionManager.get_nearest_mission(player.global_position)
				if nearest >= 0:
					MissionManager.start_mission(nearest)
