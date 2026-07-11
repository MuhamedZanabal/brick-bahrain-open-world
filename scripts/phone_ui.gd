extends CanvasLayer
class_name PhoneUI

var phone_container: Panel
var is_open: bool = false
var current_tab: int = 0

var tab_buttons: Array[Button] = []
var tab_labels: Array[String] = ["Map", "Contacts", "Missions", "Bank", "Settings"]
var content_label: RichTextLabel
var minimap_rect: ColorRect

func _ready() -> void:
	_build_phone_ui()
	visible = false
	process_mode = Node.PROCESS_MODE_WHEN_PAUSED

func _build_phone_ui() -> void:
	phone_container = Panel.new()
	phone_container.set_anchors_preset(Control.PRESET_CENTER)
	phone_container.size = Vector2(360, 640)
	phone_container.position = Vector2(-180, -320)

	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.15, 0.15, 0.18)
	style.border_width_left = 8
	style.border_width_right = 8
	style.border_width_top = 8
	style.border_width_bottom = 8
	style.border_color = Color(0.3, 0.3, 0.35)
	style.corner_radius_top_left = 20
	style.corner_radius_top_right = 20
	style.corner_radius_bottom_left = 20
	style.corner_radius_bottom_right = 20
	phone_container.add_theme_stylebox_override("panel", style)
	add_child(phone_container)

	var title: Label = Label.new()
	title.text = "BrickPhone"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 15)
	title.size = Vector2(360, 40)
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color(0.9, 0.8, 0.2))
	phone_container.add_child(title)

	var tab_container: HBoxContainer = HBoxContainer.new()
	tab_container.position = Vector2(10, 60)
	tab_container.size = Vector2(340, 50)
	phone_container.add_child(tab_container)

	for i in range(tab_labels.size()):
		var btn: Button = Button.new()
		btn.text = tab_labels[i]
		btn.custom_minimum_size = Vector2(64, 40)
		btn.add_theme_font_size_override("font_size", 11)
		var idx: int = i
		btn.pressed.connect(func(): _switch_tab(idx))
		tab_container.add_child(btn)
		tab_buttons.append(btn)

	content_label = RichTextLabel.new()
	content_label.position = Vector2(15, 120)
	content_label.size = Vector2(330, 480)
	content_label.bbcode_enabled = true
	content_label.add_theme_font_size_override("normal_font_size", 16)
	content_label.add_theme_color_override("default_color", Color(0.9, 0.9, 0.9))
	phone_container.add_child(content_label)

	minimap_rect = ColorRect.new()
	minimap_rect.position = Vector2(30, 120)
	minimap_rect.size = Vector2(300, 300)
	minimap_rect.color = Color(0.1, 0.1, 0.2)
	minimap_rect.visible = false
	phone_container.add_child(minimap_rect)

	var hint: Label = Label.new()
	hint.text = "Press P to close"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.position = Vector2(0, 610)
	hint.size = Vector2(360, 25)
	hint.add_theme_color_override("font_color", Color(0.5, 0.5, 0.5))
	hint.add_theme_font_size_override("font_size", 12)
	phone_container.add_child(hint)

	_switch_tab(0)

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_P:
			if is_open:
				close()
			else:
				open()
			get_viewport().set_input_as_handled()

func open() -> void:
	is_open = true
	visible = true
	get_tree().paused = true
	_refresh_content()

func close() -> void:
	is_open = false
	visible = false
	get_tree().paused = false

func _switch_tab(tab: int) -> void:
	current_tab = tab
	for i in range(tab_buttons.size()):
		tab_buttons[i].disabled = (i == tab)
	_refresh_content()

func _refresh_content() -> void:
	content_label.visible = (current_tab != 0)
	minimap_rect.visible = (current_tab == 0)
	match current_tab:
		0: _show_map()
		1: _show_contacts()
		2: _show_missions()
		3: _show_bank()
		4: _show_settings()

func _show_map() -> void:
	content_label.visible = true
	content_label.text = "[b]BRICK BAHRAIN MAP[/b]\n\n"
	content_label.text += "• Manama Souk — Central\n"
	content_label.text += "• City Center Mall — East\n"
	content_label.text += "• Marina Beach — West\n"
	content_label.text += "• Bahrain Fort — North\n"
	content_label.text += "• F1 Circuit — South\n"
	content_label.text += "• King Fahd Causeway — NW\n"
	content_label.text += "• Amwaj Islands — NE\n"

func _show_contacts() -> void:
	content_label.text = "[b]CONTACTS[/b]\n\n"
	content_label.text += "[i]Single player mode[/i]\n"
	content_label.text += "Connect to multiplayer to see other players.\n\n"
	content_label.text += "[b]NPC Friends:[/b]\n"
	content_label.text += "• Ahmed (Souk merchant)\n"
	content_label.text += "• Noora (Marina local)\n"
	content_label.text += "• Khalid (Taxi driver)\n"

func _show_missions() -> void:
	content_label.text = "[b]MISSIONS[/b]\n\n"
	var missions: Array[Node] = get_tree().get_nodes_in_group("mission_system")
	if missions.size() > 0:
		content_label.text += "Check mission markers in the world.\n"
	else:
		content_label.text += "Mission system not active.\n"
	content_label.text += "\n[i]Press Q to track nearest mission[/i]\n"

func _show_bank() -> void:
	content_label.text = "[b]BRICK BANK[/b]\n\n"
	var coins: int = 0
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if player and player.has_meta("coin_count"):
		coins = int(player.get_meta("coin_count"))
	content_label.text += "Balance: [color=yellow]%d coins[/color]\n\n" % coins

	var save_mgr: Node = get_tree().get_first_node_in_group("save_manager")
	content_label.text += "[b]Properties Owned:[/b]\n"
	if save_mgr and save_mgr.has_method("get_owned_properties"):
		var props: Array = save_mgr.get_owned_properties()
		if props.size() == 0:
			content_label.text += "[i]No properties yet[/i]\n"
		else:
			for p in props:
				content_label.text += "• %s\n" % str(p)
	else:
		content_label.text += "[i]No properties yet[/i]\n"

	content_label.text += "\n[b]Vehicles Owned:[/b]\n"
	if save_mgr and save_mgr.has_method("get_owned_vehicles"):
		var vehs: Array = save_mgr.get_owned_vehicles()
		if vehs.size() == 0:
			content_label.text += "[i]No vehicles yet[/i]\n"
		else:
			for v in vehs:
				content_label.text += "• %s\n" % str(v)
	else:
		content_label.text += "[i]No vehicles yet[/i]\n"

func _show_settings() -> void:
	content_label.text = "[b]SETTINGS[/b]\n\n"
	content_label.text += "• Graphics: Medium\n"
	content_label.text += "• Music: On (press R in vehicle)\n"
	content_label.text += "• Controls:\n"
	content_label.text += "  WASD — Move\n"
	content_label.text += "  Space — Jump\n"
	content_label.text += "  F — Enter/Exit Vehicle\n"
	content_label.text += "  P — Phone\n"
	content_label.text += "  Q — Missions\n"
	content_label.text += "  M — Map\n"
	content_label.text += "  R — Radio\n"
	content_label.text += "  V — Voice Chat\n"
	content_label.text += "  Enter — Text Chat\n"
	content_label.text += "\n[i]Save game: Auto every 60s[/i]\n"
