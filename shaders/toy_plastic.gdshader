// Toy Plastic Shader for Godot 4.3
// Combines cel-shaded (banded) lighting with sharp specular highlights
// and rim/fresnel lighting for a glossy LEGO-style toy plastic look.
// License: MIT (based on techniques from godotshaders.com)
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_toon, specular_schlick_ggx;

group_uniforms BaseColors;
uniform vec4 albedo : source_color = vec4(0.8, 0.1, 0.1, 1.0);
uniform float albedo_brightness : hint_range(0.5, 1.5) = 1.0;
group_uniforms;

group_uniforms ToonBands;
uniform float band_smoothness : hint_range(0.0, 0.5) = 0.05;
uniform float shadow_threshold : hint_range(0.0, 1.0) = 0.35;
uniform float mid_threshold : hint_range(0.0, 1.0) = 0.6;
uniform vec3 shadow_tint : source_color = vec3(0.55, 0.5, 0.5);
uniform vec3 mid_tint : source_color = vec3(0.85, 0.82, 0.8);
uniform vec3 highlight_tint : source_color = vec3(1.0, 1.0, 1.0);
group_uniforms;

group_uniforms Specular;
uniform float specular_amount : hint_range(0.0, 2.0) = 0.8;
uniform float specular_sharpness : hint_range(1.0, 128.0) = 32.0;
uniform vec3 specular_color : source_color = vec3(1.0, 1.0, 1.0);
group_uniforms;

group_uniforms RimLight;
uniform float rim_strength : hint_range(0.0, 2.0) = 0.6;
uniform float rim_smoothness : hint_range(0.1, 10.0) = 3.0;
uniform vec3 rim_color : source_color = vec3(1.0, 0.95, 0.8);
uniform float rim_energy : hint_range(0.0, 3.0) = 0.4;
group_uniforms;

group_uniforms Clearcoat;
uniform float clearcoat_amount : hint_range(0.0, 1.0) = 0.7;
uniform float clearcoat_roughness : hint_range(0.0, 1.0) = 0.08;
group_uniforms;

void fragment() {
	// Base albedo with brightness boost
	vec3 base_color = albedo.rgb * albedo_brightness;
	ALBEDO = base_color;
	
	// Clearcoat for glossy plastic look
	CLEARCOAT = clearcoat_amount;
	CLEARCOAT_ROUGHNESS = clearcoat_roughness;
	
	// Metallic = 0 for plastic, but high specular
	METALLIC = 0.0;
	ROUGHNESS = 0.22;
	SPECULAR = specular_amount;
}

void light() {
	// Calculate diffuse with toon banding
	float NdotL = dot(NORMAL, LIGHT);
	
	// Toon banding — quantize the light into 3 bands
	float toon_diffuse;
	if (NdotL > mid_threshold + band_smoothness) {
		toon_diffuse = 1.0;
	} else if (NdotL > shadow_threshold + band_smoothness) {
		// Smooth transition in mid band
		float t = smoothstep(shadow_threshold - band_smoothness, mid_threshold + band_smoothness, NdotL);
		toon_diffuse = mix(0.5, 0.85, t);
	} else if (NdotL > 0.0) {
		float t = smoothstep(0.0, shadow_threshold + band_smoothness, NdotL);
		toon_diffuse = mix(0.15, 0.5, t);
	} else {
		toon_diffuse = 0.0;
	}
	
	// Apply band tints
	vec3 banded_color;
	if (toon_diffuse > 0.8) {
		banded_color = highlight_tint;
	} else if (toon_diffuse > 0.4) {
		banded_color = mid_tint;
	} else {
		banded_color = shadow_tint;
	}
	
	DIFFUSE_LIGHT += banded_color * ALBEDO * LIGHT_COLOR * toon_diffuse * ATTENUATION;
	
	// Sharp specular highlight — toy plastic has tight specular blobs
	vec3 half_vec = normalize(LIGHT + VIEW);
	float spec_angle = dot(NORMAL, half_vec);
	float spec_intensity = pow(max(spec_angle, 0.0), specular_sharpness);
	// Quantize specular for toon look
	if (spec_intensity > 0.5) {
		spec_intensity = 1.0;
	} else if (spec_intensity > 0.1) {
		spec_intensity = 0.5;
	} else {
		spec_intensity = 0.0;
	}
	SPECULAR_LIGHT += specular_color * spec_intensity * specular_amount * LIGHT_COLOR * ATTENUATION;
	
	// Rim/Fresnel lighting — edge glow for that toy look
	float rim_dot = 1.0 - max(dot(NORMAL, VIEW), 0.0);
	float rim_term = pow(rim_dot, rim_smoothness);
	// Toonify the rim — hard cutoff
	if (rim_term > 0.5) {
		rim_term = 1.0;
	} else {
		rim_term = rim_term * 2.0;
	}
	DIFFUSE_LIGHT += rim_color * rim_term * rim_energy * LIGHT_COLOR * ATTENUATION;
}
