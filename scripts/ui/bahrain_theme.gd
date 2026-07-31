extends RefCounted
class_name BahrainTheme

const GOLD := Color("f4b91f")
const GOLD_LIGHT := Color("ffd968")
const PANEL := Color(0.025, 0.035, 0.05, 0.94)
const PANEL_SOFT := Color(0.04, 0.055, 0.075, 0.86)
const TEXT := Color("f7f7f2")
const TEXT_MUTED := Color("c7cbd1")
const GREEN := Color("55b53a")
const BLUE := Color("2877c7")
const PURPLE := Color("7d42c7")
const ORANGE := Color("ee941e")
const RED := Color("dc3e35")
const CYAN := Color("35a8bb")

static func panel_style(color: Color = PANEL, border: Color = GOLD, radius: int = 18) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = border
	style.set_border_width_all(2)
	style.set_corner_radius_all(radius)
	style.shadow_color = Color(0, 0, 0, 0.55)
	style.shadow_size = 10
	style.content_margin_left = 22
	style.content_margin_right = 22
	style.content_margin_top = 16
	style.content_margin_bottom = 16
	return style

static func button_style(color: Color, pressed: bool = false) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color.darkened(0.18) if pressed else color
	style.border_color = color.lightened(0.22)
	style.set_border_width_all(2)
	style.set_corner_radius_all(14)
	style.shadow_color = Color(0, 0, 0, 0.48)
	style.shadow_size = 3 if pressed else 7
	style.content_margin_left = 24
	style.content_margin_right = 24
	style.content_margin_top = 13
	style.content_margin_bottom = 13
	return style

static func title_size(viewport_size: Vector2) -> int:
	return int(clamp(min(viewport_size.x / 1920.0, viewport_size.y / 1080.0) * 86.0, 42.0, 92.0))
