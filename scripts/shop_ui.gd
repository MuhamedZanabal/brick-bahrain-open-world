extends CanvasLayer
class_name ShopUI

var shop_container: Panel
var is_open: bool = false
var current_mode: int = 0  # 0=Properties, 1=Vehicles
var content_label: RichTextLabel
var buy_buttons: Array[Button] = []
var button_container: VBoxContainer
var prop_manager: PropertyManager
var close_hint: Label
var coins_label: Label

func _ready() -> void:
	_build_shop_ui()
	visible = false
	process_mode = Node.PROCESS_MODE_WHEN_PAUSED

func _build_shop_ui() -> void:
	shop_container = Panel.new()
	shop_container.set_anchors_preset(Control.PRESET_CENTER)
	shop_container.size = Vector2(500, 600)
	shop_container.position = Vector2(-250, -300)

	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.12, 0.12, 0.15)
	style.border_width_left = 6
	style.border_width_right = 6
	style.border_width_top = 6
	style.border_width_bottom = 6
	style.border_color = Color(0.2, 0.5, 0.2)
	style.corner_radius_top_left = 12
	style.corner_radius_top_right = 12
	style.corner_radius_bottom_left = 12
	style.corner_radius_bottom_right = 12
	shop_container.add_theme_stylebox_override("panel", style)
	add_child(shop_container)

	# Title
	var title: Label = Label.new()
	title.text = "BRICK REAL ESTATE & AUTO"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 15)
	title.size = Vector2(500, 35)
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", Color(0.3, 0.9, 0.3))
	shop_container.add_child(title)

	# Coins display
	coins_label = Label.new()
	coins_label.text = "Coins: 0"
	coins_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	coins_label.position = Vector2(350, 15)
	coins_label.size = Vector2(140, 30)
	coins_label.add_theme_font_size_override("font_size", 16)
	coins_label.add_theme_color_override("font_color", Color(1, 0.9, 0.2))
	shop_container.add_child(coins_label)

	# Mode tabs
	var prop_tab: Button = Button.new()
	prop_tab.text = "Properties"
	prop_tab.position = Vector2(20, 55)
	prop_tab.size = Vector2(220, 35)
	prop_tab.pressed.connect(func(): _switch_mode(0))
	shop_container.add_child(prop_tab)

	var veh_tab: Button = Button.new()
	veh_tab.text = "Vehicles"
	veh_tab.position = Vector2(260, 55)
	veh_tab.size = Vector2(220, 35)
	veh_tab.pressed.connect(func(): _switch_mode(1))
	shop_container.add_child(veh_tab)

	# Content area
	button_container = VBoxContainer.new()
	button_container.position = Vector2(20, 100)
	button_container.size = Vector2(460, 460)
	button_container.add_theme_constant_override("separation", 8)
	shop_container.add_child(button_container)

	# Close hint
	close_hint = Label.new()
	close_hint.text = "Press B to close"
	close_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	close_hint.position = Vector2(0, 570)
	close_hint.size = Vector2(500, 25)
	close_hint.add_theme_color_override("font_color", Color(0.5, 0.5, 0.5))
	shop_container.add_child(close_hint)

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_B:
			if is_open:
				close()
			else:
				# Only open if near a shop zone
				if _is_near_shop():
					open()
			get_viewport().set_input_as_handled()

func _is_near_shop() -> bool:
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return false
	# Near City Center (car shop) or Amwaj (property shop)
	var city_center: float = player.global_position.distance_to(Vector3(80, 0, 60))
	var amwaj: float = player.global_position.distance_to(Vector3(140, 0, -50))
	return city_center < 30 or amwaj < 30

func open() -> void:
	is_open = true
	visible = true
	get_tree().paused = true
	prop_manager = get_tree().get_first_node_in_group("property_manager") as PropertyManager
	_switch_mode(0)

func close() -> void:
	is_open = false
	visible = false
	get_tree().paused = false

func _switch_mode(mode: int) -> void:
	current_mode = mode
	_refresh()

func _refresh() -> void:
	# Clear existing buttons
	for btn in buy_buttons:
		btn.queue_free()
	buy_buttons.clear()

	# Update coins
	var coins: int = 0
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player and player.has_meta("coin_count"):
		coins = int(player.get_meta("coin_count"))
	coins_label.text = "Coins: %d" % coins

	if not prop_manager:
		return

	if current_mode == 0:
		# Properties
		var props: Array[Dictionary] = prop_manager.get_properties()
		for prop in props:
			var btn: Button = Button.new()
			var owned: bool = prop_manager.get_owned_properties().has(prop["id"])
			var can_afford: bool = coins >= int(prop["price"])
			if owned:
				btn.text = "[OWNED] %s" % prop["name"]
				btn.disabled = true
			elif not can_afford:
				btn.text = "%s — %d coins (need %d more)" % [prop["name"], int(prop["price"]), int(prop["price"]) - coins]
				btn.disabled = true
			else:
				btn.text = "%s — %d coins" % [prop["name"], int(prop["price"])]
				var prop_id: String = prop["id"]
				btn.pressed.connect(func(): _buy_property(prop_id))
			btn.custom_minimum_size = Vector2(460, 50)
			btn.add_theme_font_size_override("font_size", 14)
			button_container.add_child(btn)
			buy_buttons.append(btn)
	else:
		# Vehicles
		var vehs: Array[Dictionary] = prop_manager.get_vehicles_for_sale()
		for veh in vehs:
			var btn: Button = Button.new()
			var owned: bool = prop_manager.get_owned_vehicles().has(veh["id"])
			var can_afford: bool = coins >= int(veh["price"])
			if owned:
				btn.text = "[OWNED] %s" % veh["name"]
				btn.disabled = true
			elif not can_afford:
				btn.text = "%s — %d coins (need %d more)" % [veh["name"], int(veh["price"]), int(veh["price"]) - coins]
				btn.disabled = true
			else:
				btn.text = "%s — %d coins (Speed: %d)" % [veh["name"], int(veh["price"]), int(veh["max_speed"])]
				var veh_id: String = veh["id"]
				btn.pressed.connect(func(): _buy_vehicle(veh_id))
			btn.custom_minimum_size = Vector2(460, 50)
			btn.add_theme_font_size_override("font_size", 14)
			button_container.add_child(btn)
			buy_buttons.append(btn)

func _buy_property(prop_id: String) -> void:
	if prop_manager and prop_manager.buy_property(prop_id):
		_refresh()

func _buy_vehicle(veh_id: String) -> void:
	if prop_manager and prop_manager.buy_vehicle(veh_id):
		_refresh()
