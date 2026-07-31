extends MarginContainer
class_name SafeAreaRoot

signal safe_rect_changed(rect: Rect2)

func _ready() -> void:
	get_viewport().size_changed.connect(_apply_safe_area)
	_apply_safe_area()

func get_safe_rect() -> Rect2:
	var viewport_rect := get_viewport().get_visible_rect()
	var safe := DisplayServer.get_display_safe_area()
	if safe.size == Vector2i.ZERO:
		return viewport_rect
	return Rect2(Vector2(safe.position), Vector2(safe.size))

func _apply_safe_area() -> void:
	var viewport_rect := get_viewport().get_visible_rect()
	var safe := get_safe_rect()
	add_theme_constant_override("margin_left", int(max(0.0, safe.position.x)))
	add_theme_constant_override("margin_top", int(max(0.0, safe.position.y)))
	add_theme_constant_override("margin_right", int(max(0.0, viewport_rect.size.x - safe.end.x)))
	add_theme_constant_override("margin_bottom", int(max(0.0, viewport_rect.size.y - safe.end.y)))
	safe_rect_changed.emit(safe)
