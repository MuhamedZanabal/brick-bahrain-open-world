extends Node

# 3 radio stations with procedural music
enum Station { MANAMA_FM, DESERT_ROCK, PEARL_RADIO }
var current_station: Station = Station.MANAMA_FM
var is_playing: bool = false
var current_player: AudioStreamPlayer

# Station info
const STATION_NAMES: Array[String] = ["Manama FM", "Desert Rock", "Pearl Radio"]
const STATION_DESC: Array[String] = ["Chill vibes", "Fast beats", "Traditional sounds"]

# Procedural audio generators
var manama_fm_generator: AudioStreamGenerator
var desert_rock_generator: AudioStreamGenerator
var pearl_radio_generator: AudioStreamGenerator

# Active note data
var note_timer: float = 0.0
var current_note_idx: int = 0
var beat_timer: float = 0.0
var beat_idx: int = 0

# Note frequencies (Arabic-inspired scales)
const MANAMA_SCALE: Array[float] = [261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 493.88, 523.25]
const DESERT_SCALE: Array[float] = [196.0, 220.0, 246.94, 277.18, 329.63, 369.99, 415.30, 440.0]
const PEARL_SCALE: Array[float] = [174.61, 196.0, 220.0, 233.08, 261.63, 293.66, 311.13, 349.23]

# Beat patterns
const MANAMA_BEATS: Array[int] = [0, 2, 4, 3, 5, 7, 5, 3]
const DESERT_BEATS: Array[int] = [0, 4, 2, 6, 4, 0, 7, 5]
const PEARL_BEATS: Array[int] = [0, 3, 5, 2, 4, 7, 5, 2]

func _ready() -> void:
	add_to_group("radio_system")
	# Create audio player
	current_player = AudioStreamPlayer.new()
	current_player.volume_db = -6.0
	add_child(current_player)

	# Create generators
	manama_fm_generator = AudioStreamGenerator.new()
	manama_fm_generator.mix_rate = 44100
	manama_fm_generator.buffer_length = 0.5

	desert_rock_generator = AudioStreamGenerator.new()
	desert_rock_generator.mix_rate = 44100
	desert_rock_generator.buffer_length = 0.5

	pearl_radio_generator = AudioStreamGenerator.new()
	pearl_radio_generator.mix_rate = 44100
	pearl_radio_generator.buffer_length = 0.5

func _process(delta: float) -> void:
	if not is_playing:
		return

	beat_timer += delta

	# Change notes based on station tempo
	var beat_interval: float = 0.3
	match current_station:
		Station.MANAMA_FM:
			beat_interval = 0.4
		Station.DESERT_ROCK:
			beat_interval = 0.15
		Station.PEARL_RADIO:
			beat_interval = 0.5

	if beat_timer >= beat_interval:
		beat_timer = 0.0
		beat_idx = (beat_idx + 1) % 8
		_play_next_note()

func _play_next_note() -> void:
	var scale: Array[float]
	var beats: Array[int]

	match current_station:
		Station.MANAMA_FM:
			scale = MANAMA_SCALE
			beats = MANAMA_BEATS
		Station.DESERT_ROCK:
			scale = DESERT_SCALE
			beats = DESERT_BEATS
		Station.PEARL_RADIO:
			scale = PEARL_SCALE
			beats = PEARL_BEATS

	var note_idx: int = beats[beat_idx % beats.size()]
	var freq: float = scale[note_idx % scale.size()]

	# Create a brief tone using AudioStreamGenerator
	# Since we can't easily generate real-time audio in GDScript without 
	# filling buffers, we'll use a simpler approach with AudioStreamPlayer
	# and procedural note playback
	_emit_tone(freq, current_station)

func _emit_tone(freq: float, station: Station) -> void:
	# Create a simple sine wave tone
	var sample_rate: int = 44100
	var duration: float = 0.3
	var samples: int = int(sample_rate * duration)

	var stream: AudioStreamWAV = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false

	var data: PackedByteArray = PackedByteArray()
	data.resize(samples * 2)

	for i in range(samples):
		var t: float = float(i) / float(sample_rate)
		var envelope: float = 1.0 - (t / duration)  # Decay
		var wave: float = 0.0

		match station:
			Station.MANAMA_FM:
				# Soft sine + harmonic
				wave = sin(t * freq * TAU) * 0.5 + sin(t * freq * 2.0 * TAU) * 0.2
				wave *= envelope * 0.3
			Station.DESERT_ROCK:
				# Sawtooth-ish for aggressive sound
				wave = (t * freq - floor(t * freq)) * 2.0 - 1.0
				wave *= envelope * 0.25
			Station.PEARL_RADIO:
				# Pentatonic flute-like
				wave = sin(t * freq * TAU) * 0.4 + sin(t * freq * 1.5 * TAU) * 0.15
				wave *= envelope * 0.35

		var sample_val: int = int(wave * 32767)
		# Clamp
		sample_val = clamp(sample_val, -32768, 32767)
		data.set(i * 2, sample_val & 0xFF)
		data.set(i * 2 + 1, (sample_val >> 8) & 0xFF)

	stream.data = data
	current_player.stream = stream
	current_player.play()

func start_radio() -> void:
	is_playing = true
	_play_next_note()

func stop_radio() -> void:
	is_playing = false
	current_player.stop()

func toggle_radio() -> void:
	if is_playing:
		stop_radio()
	else:
		start_radio()

func next_station() -> void:
	current_station = (current_station + 1) as Station
	if current_station >= Station.size():
		current_station = Station.MANAMA_FM
	beat_idx = 0
	if is_playing:
		_play_next_note()

func get_station_name() -> String:
	return STATION_NAMES[current_station]

func get_station_desc() -> String:
	return STATION_DESC[current_station]

func is_radio_playing() -> bool:
	return is_playing
