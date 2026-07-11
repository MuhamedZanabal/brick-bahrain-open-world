// Simple Outline Shader — CC0 (from godotshaders.com / RPaciorek)
// Creates a black outline by rendering a scaled-up mesh with inverted backface culling
// Add as a second material pass on any mesh that needs an outline
shader_type spatial;
render_mode blend_mix, cull_front, unshaded;

uniform vec4 outline_color : source_color = vec4(0.08, 0.06, 0.05, 1.0);
uniform float outline_size : hint_range(1.0, 1.3, 0.005) = 1.04;

void vertex() {
	VERTEX *= outline_size;
}

void fragment() {
	ALBEDO = outline_color.rgb;
	ALPHA = outline_color.a;
}
