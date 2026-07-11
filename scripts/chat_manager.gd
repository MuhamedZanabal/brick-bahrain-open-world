extends Node

# Text chat and voice chat system for multiplayer
var chat_log: Array[String] = []
var max_log_size: int = 50

# UI elements
var chat_container: Panel
var chat_input: LineEdit
var chat_display: RichTextLabel
var chat_bubbles: Dictionary = {}  # peer_id -> Label3D
var is_chat_open: bool = false
var is_voice_active: bool = false

# Voice indicator
var voice_indicator: ColorRect

# Network
var multiplayer_peer: ENetMultiplayerPeer

signal chat_message_sent(message: String)
signal voice_toggled(active: bool)

func _ready() -> void:
	_build_chat_ui()
	# Multiplayer signals will be connected when multiplayer manager is ready

func _build_chat_ui() -> void:
	# Chat display (bottom-left, semi-transparent)
	chat_container = Panel.new()
	chat_container.position = Vector2(10, 400)
	chat_container.size = Vector2(400, 200)

	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0, 0, 0, 0.5)
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_left = 8
	style.corner_radius_bottom_right = 8
	chat_container.add_theme_stylebox_override("panel", style)
	add_child(chat_container)

	# Chat log display
	chat_display = RichTextLabel.new()
	chat_display.position = Vector2(5, 5)
	chat_display.size = Vector2(390, 160)
	chat_display.bbcode_enabled = true
	chat_display.scroll_following = true
	chat_display.add_theme_font_size_override("normal_font_size", 13)
	chat_display.add_theme_color_override("default_color", Color(0.9, 0.9, 0.9))
	chat_container.add_child(chat_display)

	# Chat input
	chat_input = LineEdit.new()
	chat_input.position = Vector2(5, 170)
	chat_input.size = Vector2(390, 25)
	chat_input.placeholder_text = "Press Enter to chat..."
	chat_input.visible = false
	chat_input.text_submitted.connect(_on_chat_submitted)
	chat_container.add_child(chat_input)

	# Voice indicator (top-center)
	voice_indicator = ColorRect.new()
	voice_indicator.position = Vector2(540, 10)
	voice_indicator.size = Vector2(20, 20)
	voice_indicator.color = Color(0.2, 0.2, 0.2)
	voice_indicator.visible = false
	add_child(voice_indicator)

	# Initially hide chat container (show on first message or input)
	chat_container.visible = false

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ENTER:
			if is_chat_open:
				chat_input.visible = false
				is_chat_open = false
				if chat_input.text.strip_edges().length() > 0:
					_send_chat_message(chat_input.text)
				chat_input.text = ""
				get_tree().paused = false
			else:
				chat_container.visible = true
				chat_input.visible = true
				chat_input.grab_focus()
				is_chat_open = true
			get_viewport().set_input_as_handled()

		elif event.keycode == KEY_V:
			is_voice_active = !is_voice_active
			voice_indicator.visible = is_voice_active
			voice_indicator.color = Color(0.2, 0.8, 0.3) if is_voice_active else Color(0.2, 0.2, 0.2)
			voice_toggled.emit(is_voice_active)
			get_viewport().set_input_as_handled()

func _on_chat_submitted(text: String) -> void:
	if text.strip_edges().length() > 0:
		_send_chat_message(text)
	chat_input.text = ""
	chat_input.visible = false
	is_chat_open = false
	get_tree().paused = false

func _send_chat_message(text: String) -> void:
	var player_name: String = "Player"
	var msg: String = "[color=cyan]%s[/color]: %s" % [player_name, text]
	_add_to_log(msg)

	# Send over network if in multiplayer
	if multiplayer_peer and multiplayer_peer.get_connection_status() == MultiplayerPeer.CONNECTION_CONNECTED:
		rpc("_rpc_receive_chat", multiplayer.get_unique_id(), text)

	# Show bubble above player
	_show_chat_bubble(text)

	chat_message_sent.emit(text)

@rpc("any_peer", "call_local", "reliable")
func _rpc_receive_chat(sender_id: int, text: String) -> void:
	var player_name: String = "Player_%d" % sender_id
	var msg: String = "[color=orange]%s[/color]: %s" % [player_name, text]
	_add_to_log(msg)

func _add_to_log(msg: String) -> void:
	chat_log.append(msg)
	if chat_log.size() > max_log_size:
		chat_log.pop_front()
	_update_chat_display()
	chat_container.visible = true

func _update_chat_display() -> void:
	chat_display.text = "\n".join(chat_log)

func _show_chat_bubble(text: String) -> void:
	var player: Node3D = get_tree().get_first_node_in_group("player")
	if not player:
		return

	# Create or update bubble
	var bubble: Label3D = Label3D.new()
	bubble.text = text
	bubble.font_size = 20
	bubble.position = Vector3(0, 2.5, 0)
	bubble.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	bubble.no_depth_test = true
	bubble.modulate = Color(1, 1, 0.8)
	player.add_child(bubble)

	# Remove after 5 seconds
	get_tree().create_timer(5.0).timeout.connect(func():
		if bubble and is_instance_valid(bubble):
			bubble.queue_free()
	)

func _on_player_connected(peer_id: int) -> void:
	_add_to_log("[color=green]Player %d joined[/color]" % peer_id)

func _on_player_disconnected(peer_id: int) -> void:
	_add_to_log("[color=red]Player %d left[/color]" % peer_id)
	if chat_bubbles.has(peer_id):
		chat_bubbles[peer_id].queue_free()
		chat_bubbles.erase(peer_id)

func get_chat_log() -> Array[String]:
	return chat_log

func is_voice_push_to_talk_active() -> bool:
	return is_voice_active
