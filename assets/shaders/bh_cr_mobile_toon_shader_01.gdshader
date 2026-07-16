shader_type spatial;
render_mode diffuse_burley, specular_disabled;

uniform vec4 base_color : source_color = vec4(0.82, 0.68, 0.48, 1.0);
uniform float shadow_band : hint_range(0.0, 1.0) = 0.42;
uniform float lit_level : hint_range(0.0, 1.0) = 0.92;
uniform float shade_level : hint_range(0.0, 1.0) = 0.58;
uniform float rim_strength : hint_range(0.0, 1.0) = 0.12;

void fragment() {
    ALBEDO = base_color.rgb;
    ROUGHNESS = 0.86;
}

void light() {
    float ndotl = dot(NORMAL, LIGHT);
    float band = step(shadow_band, ndotl) * lit_level + (1.0 - step(shadow_band, ndotl)) * shade_level;
    float rim = pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 3.0) * rim_strength;
    DIFFUSE_LIGHT += base_color.rgb * LIGHT_COLOR * ATTENUATION * (band + rim);
}
