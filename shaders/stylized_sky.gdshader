// Stylized Sky Shader for Godot 4
// Creates a vibrant gradient sky with soft cloud puffs
// Adapted from GDQuest stylized sky techniques (MIT)
shader_type sky;

group_uniforms SkyColors;
uniform vec3 zenith_color : source_color = vec3(0.15, 0.45, 0.9);
uniform vec3 horizon_color : source_color = vec3(0.75, 0.82, 0.95);
uniform vec3 ground_color : source_color = vec3(0.82, 0.72, 0.48);
uniform vec3 sun_glow_color : source_color = vec3(1.0, 0.9, 0.7);
group_uniforms;

group_uniforms Clouds;
uniform float cloud_density : hint_range(0.0, 1.0) = 0.35;
uniform float cloud_scale : hint_range(0.5, 10.0) = 3.0;
uniform float cloud_speed : hint_range(0.0, 1.0) = 0.02;
uniform float cloud_threshold : hint_range(0.0, 1.0) = 0.5;
uniform vec3 cloud_color : source_color = vec3(1.0, 0.98, 0.95);
uniform vec3 cloud_shadow_color : source_color = vec3(0.7, 0.75, 0.85);
group_uniforms;

group_uniforms Sun;
uniform float sun_size : hint_range(0.001, 0.2) = 0.04;
uniform float sun_glow_size : hint_range(0.01, 1.0) = 0.25;
uniform float sun_energy : hint_range(0.0, 5.0) = 2.0;
group_uniforms;

// Simple hash-based noise for clouds
float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise2d(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash(i);
	float b = hash(i + vec2(1.0, 0.0));
	float c = hash(i + vec2(0.0, 1.0));
	float d = hash(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += a * noise2d(p);
		p *= 2.0;
		a *= 0.5;
	}
	return v;
}

void sky() {
	// Get direction
	vec3 dir = EYEDIR;
	
	// Gradient from zenith to horizon
	float gradient = clamp(dir.y * 1.2, 0.0, 1.0);
	gradient = pow(gradient, 0.6);
	
	vec3 sky_color = mix(horizon_color, zenith_color, gradient);
	
	// Ground hemisphere
	if (dir.y < 0.0) {
		float ground_grad = clamp(-dir.y * 2.0, 0.0, 1.0);
		sky_color = mix(horizon_color, ground_color, ground_grad);
	}
	
	// Sun glow
	float sun_dot = max(dot(dir, vec3(0.0, 0.5, 0.3)), 0.0);
	float glow = pow(sun_dot, 8.0) * sun_glow_size;
	sky_color = mix(sky_color, sun_glow_color, glow * 0.3);
	
	// Sun disc
	float sun_disc = smoothstep(sun_size, sun_size * 0.5, acos(sun_dot));
	sky_color += sun_glow_color * sun_disc * sun_energy * 0.5;
	
	// Procedural clouds — only above horizon
	if (dir.y > 0.02) {
		vec2 cloud_uv = dir.xz / (dir.y + 0.1) * cloud_scale;
		cloud_uv += TIME * cloud_speed;
		
		float cloud_val = fbm(cloud_uv);
		cloud_val = smoothstep(cloud_threshold, cloud_threshold + 0.3, cloud_val);
		
		// Fade clouds near horizon
		float horizon_fade = smoothstep(0.02, 0.25, dir.y);
		cloud_val *= horizon_fade * cloud_density;
		
		// Cloud shading — bottom is darker
		float cloud_shade = mix(0.6, 1.0, smoothstep(0.0, 0.3, dir.y));
		vec3 final_cloud = mix(cloud_shadow_color, cloud_color, cloud_shade);
		
		sky_color = mix(sky_color, final_cloud, cloud_val);
	}
	
	COLOR = sky_color;
}
