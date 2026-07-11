extends Node

# Weather states
enum WeatherType { CLEAR, SANDSTORM, DUST, CLOUDY }
var current_weather: WeatherType = WeatherType.CLEAR
var weather_timer: float = 0.0
var weather_change_interval: float = 180.0  # Change weather every ~3 minutes
var weather_intensity: float = 0.0  # 0-1, smooth transition
var target_intensity: float = 0.0

# Fog params
var base_fog_color: Color = Color(0.7, 0.7, 0.8)
var storm_fog_color: Color = Color(0.7, 0.55, 0.3)  # Brownish dust
var base_fog_density: float = 0.0
var storm_fog_density: float = 0.08

# Particle system for sandstorm
var sand_particles: GPUParticles3D
var world_env: WorldEnvironment
var day_night: DayNightCycle

# Wind effect
var wind_strength: float = 0.0
var wind_timer: float = 0.0

signal weather_changed(weather_type: WeatherType)

func _ready() -> void:
	# Create sandstorm particles (hidden initially)
	sand_particles = GPUParticles3D.new()
	sand_particles.amount = 500
	sand_particles.lifetime = 2.0
	sand_particles.explosiveness = 0.0
	sand_particles.visibility_aabb = AABB(Vector3(-50, -10, -50), Vector3(100, 30, 100))

	var mat: ParticleProcessMaterial = ParticleProcessMaterial.new()
	mat.direction = Vector3(1, 0, 0)
	mat.spread = 15.0
	mat.initial_velocity_min = 5.0
	mat.initial_velocity_max = 15.0
	mat.scale_min = 0.1
	mat.scale_max = 0.3
	mat.color = Color(0.8, 0.65, 0.35, 0.6)
	mat.gravity = Vector3(0, -0.5, 0)
	sand_particles.process_material = mat

	# Follow the player
	sand_particles.visible = false
	add_child(sand_particles)

	# Pick initial weather
	_pick_new_weather()

func set_references(dnc: DayNightCycle) -> void:
	day_night = dnc
	if day_night and day_night.world_env:
		world_env = day_night.world_env

func _process(delta: float) -> void:
	weather_timer += delta

	# Smooth intensity transition
	weather_intensity = lerp(weather_intensity, target_intensity, delta * 0.5)

	# Change weather periodically
	if weather_timer >= weather_change_interval:
		weather_timer = 0.0
		_pick_new_weather()

	# Apply weather effects
	_apply_weather_effects(delta)

	# Update particle position to follow player
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player:
		sand_particles.global_position = player.global_position + Vector3(0, 5, 0)

func _pick_new_weather() -> void:
	var rand: float = randf()
	if rand < 0.5:
		current_weather = WeatherType.CLEAR
		target_intensity = 0.0
	elif rand < 0.75:
		current_weather = WeatherType.CLOUDY
		target_intensity = 0.3
	elif rand < 0.9:
		current_weather = WeatherType.DUST
		target_intensity = 0.5
	else:
		current_weather = WeatherType.SANDSTORM
		target_intensity = 1.0

	weather_changed.emit(current_weather)
	var weather_name: String = WeatherType.keys()[current_weather]
	print("WeatherSystem: Changed to %s" % weather_name)

func _apply_weather_effects(delta: float) -> void:
	# Update fog
	if world_env and world_env.environment:
		var env: Environment = world_env.environment

		if current_weather == WeatherType.CLEAR:
			env.fog_enabled = false
			sand_particles.visible = false
			wind_strength = 0.0
		elif current_weather == WeatherType.CLOUDY:
			env.fog_enabled = weather_intensity > 0.1
			env.fog_light_color = base_fog_color
			env.fog_density = base_fog_density + 0.01 * weather_intensity
			sand_particles.visible = false
			wind_strength = 2.0 * weather_intensity
		elif current_weather == WeatherType.DUST:
			env.fog_enabled = true
			env.fog_light_color = base_fog_color.lerp(storm_fog_color, weather_intensity)
			env.fog_density = base_fog_density + 0.04 * weather_intensity
			sand_particles.visible = weather_intensity > 0.3
			sand_particles.amount = int(200 * weather_intensity)
			wind_strength = 5.0 * weather_intensity
		elif current_weather == WeatherType.SANDSTORM:
			env.fog_enabled = true
			env.fog_light_color = storm_fog_color
			env.fog_density = base_fog_density + storm_fog_density * weather_intensity
			sand_particles.visible = weather_intensity > 0.2
			sand_particles.amount = int(500 * weather_intensity)
			wind_strength = 15.0 * weather_intensity

	# Animate wind direction variation
	wind_timer += delta

func get_weather_name() -> String:
	return WeatherType.keys()[current_weather]

func get_visibility() -> float:
	# Returns 0-1, 1=perfect visibility
	return 1.0 - weather_intensity * (0.6 if current_weather == WeatherType.SANDSTORM else 0.3)

func is_storm() -> bool:
	return current_weather == WeatherType.SANDSTORM and weather_intensity > 0.5
