extends DirectionalLight3D
class_name DayNightCycle

# 20 real-time minutes = full day cycle
const CYCLE_DURATION: float = 1200.0  # 20 minutes in seconds
var time_of_day: float = 0.3  # 0-1, 0=midnight, 0.25=sunrise, 0.5=noon, 0.75=sunset
var cycle_speed: float = 1.0 / CYCLE_DURATION

# Sky colors
var sky_material  # kept for compatibility, unused with shader sky
var world_env: WorldEnvironment
var street_lamps: Array[Node3D] = []
var lamp_check_timer: float = 0.0

# Sun colors
const DAY_COLOR: Color = Color(1.0, 0.93, 0.78)
const DUSK_COLOR: Color = Color(1.0, 0.5, 0.2)
const NIGHT_COLOR: Color = Color(0.25, 0.25, 0.45)
const DAWN_COLOR: Color = Color(0.8, 0.5, 0.4)

func _ready() -> void:
	add_to_group("day_night_cycle")
	# Set up as the main sun
	light_energy = 2.0
	shadow_enabled = true
	shadow_bias = 0.08
	shadow_normal_bias = 0.3
	shadow_blur = 1.5
	directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	directional_shadow_blend_splits = true

	# Create stylized sky with procedural clouds
	sky_material = null  # We use a sky shader instead
	
	var sky: Sky = Sky.new()
	var sky_shader := load("res://shaders/stylized_sky.gdshader")
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = sky_shader
	sky_mat.set_shader_parameter("zenith_color", Color(0.15, 0.45, 0.9))
	sky_mat.set_shader_parameter("horizon_color", Color(0.75, 0.82, 0.95))
	sky_mat.set_shader_parameter("ground_color", Color(0.82, 0.72, 0.48))
	sky_mat.set_shader_parameter("sun_glow_color", Color(1.0, 0.9, 0.7))
	sky_mat.set_shader_parameter("cloud_density", 0.35)
	sky_mat.set_shader_parameter("cloud_scale", 3.0)
	sky_mat.set_shader_parameter("cloud_speed", 0.02)
	sky_mat.set_shader_parameter("cloud_threshold", 0.5)
	sky_mat.set_shader_parameter("sun_size", 0.04)
	sky_mat.set_shader_parameter("sun_glow_size", 0.25)
	sky_mat.set_shader_parameter("sun_energy", 2.0)
	sky.sky_material = sky_mat

	world_env = WorldEnvironment.new()
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	
	# Ambient — warm sky bounced light
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_color = Color(0.65, 0.7, 0.85)
	env.ambient_light_energy = 0.45
	
	# Tonemapping
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_white = 1.2
	
	# Glow / Bloom
	env.glow_enabled = true
	env.glow_intensity = 0.8
	env.glow_strength = 1.0
	env.glow_mix = 0.15
	env.glow_bloom = 0.6
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.glow_hdr_threshold = 0.8
	env.glow_map_strength = 0.4
	
	# NOTE: SSAO/SSR require the Forward+ rendering method. This project uses
	# "mobile" (renderer/rendering_method in project.godot) for Android
	# performance, where SSAO/SSR are silently no-ops (and print warnings on
	# every load) — so we don't enable them here. Glow/fog/tonemap/color
	# adjustment below all work fine on mobile and carry the visual load.
	
	# Fog — subtle warm haze
	env.fog_enabled = true
	env.fog_light_color = Color(0.88, 0.82, 0.68)
	env.fog_density = 0.0015
	env.fog_aerial_perspective = 0.3
	env.fog_sun_scatter = 0.15
	
	# Color correction — vibrant, warm
	env.adjustment_enabled = true
	env.adjustment_brightness = 1.05
	env.adjustment_contrast = 1.12
	env.adjustment_saturation = 1.25
	
	world_env.environment = env
	get_parent().add_child(world_env)

	# Collect street lamps
	_collect_street_lamps()

func _collect_street_lamps() -> void:
	street_lamps.clear()
	var lamps: Array[Node] = get_tree().get_nodes_in_group("street_lamps")
	for lamp in lamps:
		street_lamps.append(lamp)

func _process(delta: float) -> void:
	# Advance time
	time_of_day += cycle_speed * delta
	if time_of_day >= 1.0:
		time_of_day -= 1.0

	# Update sun position (rotate around the world)
	var sun_angle: float = time_of_day * TAU - PI / 2.0
	var sun_dir: Vector3 = Vector3(
		cos(sun_angle),
		sin(sun_angle),
		0.3
	).normalized()
	# Set light rotation to match sun direction
	look_at(global_position + sun_dir, Vector3.UP)

	# Calculate sun height (0 = horizon, 1 = zenith)
	var sun_height: float = max(0.0, sin(sun_angle))

	# Update light color and intensity based on time
	_update_lighting(sun_height, time_of_day)

	# Check street lamps periodically
	lamp_check_timer -= delta
	if lamp_check_timer <= 0:
		lamp_check_timer = 2.0
		_update_street_lamps(sun_height)

	# Re-collect lamps if none found yet
	if street_lamps.size() == 0:
		_collect_street_lamps()

func _update_lighting(sun_height: float, tod: float) -> void:
	var is_dawn: bool = tod > 0.20 and tod < 0.30
	var is_dusk: bool = tod > 0.70 and tod < 0.80

	if sun_height > 0.3:
		# Day — vibrant bright sky
		light_color = DAY_COLOR
		light_energy = 1.8 + sun_height * 0.6
		# sky shader params updated via the sky material
		world_env.environment.ambient_light_color = Color(0.65, 0.7, 0.85)
		world_env.environment.ambient_light_energy = 0.4 + sun_height * 0.15
		world_env.environment.adjustment_saturation = 1.25
		world_env.environment.glow_intensity = 0.8
	elif sun_height > 0.0:
		# Near horizon (dawn/dusk) — warm orange glow
		var t: float = sun_height / 0.3
		if is_dusk:
			light_color = DUSK_COLOR.lerp(DAY_COLOR, t)
		elif is_dawn:
			light_color = DAWN_COLOR.lerp(DAY_COLOR, t)
		else:
			light_color = NIGHT_COLOR.lerp(DAY_COLOR, t)
		light_energy = 0.5 + t * 1.5
		# sky shader handles gradient internally
		world_env.environment.ambient_light_color = Color(0.7, 0.5, 0.4).lerp(Color(0.65, 0.7, 0.85), t)
		world_env.environment.ambient_light_energy = 0.2 + t * 0.2
		world_env.environment.adjustment_saturation = 1.15 + (1.0 - t) * 0.15
		world_env.environment.glow_intensity = 1.0 + (1.0 - t) * 0.5
	else:
		# Night — deep blue with reduced SSAO
		light_color = NIGHT_COLOR
		light_energy = 0.2
		# sky shader handles night colors via sun position
		world_env.environment.ambient_light_color = Color(0.2, 0.2, 0.35)
		world_env.environment.ambient_light_energy = 0.1
		world_env.environment.adjustment_saturation = 0.9
		world_env.environment.glow_intensity = 0.5

func _update_street_lamps(sun_height: float) -> void:
	var lamps_on: bool = sun_height < 0.15
	for lamp in street_lamps:
		if lamp is OmniLight3D:
			lamp.visible = lamps_on
		elif lamp is SpotLight3D:
			lamp.visible = lamps_on
		elif lamp is Node3D:
			for child in lamp.get_children():
				if child is Light3D:
					child.visible = lamps_on

func get_time_string() -> String:
	var hours: int = int(time_of_day * 24.0)
	var minutes: int = int((time_of_day * 24.0 - hours) * 60.0)
	var ampm: String = "AM" if hours < 12 else "PM"
	var display_hour: int = hours % 12
	if display_hour == 0:
		display_hour = 12
	return "%d:%02d %s" % [display_hour, minutes, ampm]

func is_night() -> bool:
	return time_of_day < 0.22 or time_of_day > 0.78

func set_time(t: float) -> void:
	time_of_day = clamp(t, 0.0, 1.0)
