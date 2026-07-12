extends RefCounted
class_name BahrainUI

static func background(parent: Control, path: String, tint: Color = Color(1, 1, 1, 1)) -> TextureRect:
	var node := TextureRect.new()
	node.texture = load(path)
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	node.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	node.modulate = tint
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(node)
	return node

static func panel(color: Color = Color(0.025, 0.045, 0.075, 0.93), accent: Color = Color(0.92, 0.66, 0.16)) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = accent
	style.set_border_width_all(2)
	style.corner_radius_top_left = 18
	style.corner_radius_top_right = 18
	style.corner_radius_bottom_left = 18
	style.corner_radius_bottom_right = 18
	style.content_margin_left = 24
	style.content_margin_right = 24
	style.content_margin_top = 20
	style.content_margin_bottom = 20
	style.shadow_color = Color(0, 0, 0, 0.5)
	style.shadow_size = 10
	return style

static func button_style(color: Color, pressed: bool = false) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color.darkened(0.14 if pressed else 0.0)
	style.border_color = color.lightened(0.22)
	style.set_border_width_all(2)
	style.corner_radius_top_left = 13
	style.corner_radius_top_right = 13
	style.corner_radius_bottom_left = 13
	style.corner_radius_bottom_right = 13
	style.content_margin_left = 22
	style.content_margin_right = 22
	style.content_margin_top = 13
	style.content_margin_bottom = 13
	return style

static func make_button(text: String, color: Color, minimum: Vector2 = Vector2(330, 60)) -> Button:
	var button := Button.new()
	button.text = text
	button.name = text.replace(" ", "") + "Button"
	button.custom_minimum_size = minimum
	button.add_theme_font_size_override("font_size", 24)
	button.add_theme_stylebox_override("normal", button_style(color))
	button.add_theme_stylebox_override("hover", button_style(color.lightened(0.10)))
	button.add_theme_stylebox_override("pressed", button_style(color, true))
	button.add_theme_stylebox_override("focus", button_style(color.lightened(0.15)))
	return button

static func title(text: String, size: int = 64, color: Color = Color(1, 0.82, 0.18)) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	label.add_theme_constant_override("outline_size", 7)
	return label
