extends Node

## Example script showing how to use the AudioServiceOSC receiver
##
## This demonstrates common patterns for accessing audio service data in Godot

@onready var osc_receiver = $AudioServiceOSC  # Adjust path to your OSC receiver node

func _ready():
	if not osc_receiver:
		push_error("AudioServiceOSC node not found! Make sure the path is correct.")
		return
	
	# Connect to updates signal to react to changes
	osc_receiver.endpoint_updated.connect(_on_endpoint_updated)
	
	print("Example: Connected to Audio Service OSC receiver")

func _process(_delta):
	if not osc_receiver:
		return
	
	# Example 1: Get tempo information
	var bpm = osc_receiver.get_float("/clock/bpm")
	var confidence = osc_receiver.get_float("/clock/conf")
	
	# Example 2: Get basic audio levels
	var bass = osc_receiver.get_float("/audio/bass")
	var mid = osc_receiver.get_float("/audio/mid")
	var treble = osc_receiver.get_float("/audio/treble")
	
	# Example 3: Check for beat events
	var is_beat = osc_receiver.get_bool("/audio/beat")
	var is_pulse = osc_receiver.get_bool("/audio/pulse")
	
	# Example 4: Use values to drive visuals (example: modulate color)
	if bass > 0.0 or mid > 0.0 or treble > 0.0:
		# Example: Create a color based on frequency distribution
		var color = Color(bass, mid, treble)
		# modulate = color  # Uncomment if you want to modulate this node's color
	
	# Example 5: Get detailed band information
	var band_bass_1 = osc_receiver.get_float("/audio/band_bass_1")
	var normalized_mid = osc_receiver.get_float("/audio/band_normalized_mid_1")
	
	# Example 6: Scale object based on energy
	var total_energy = osc_receiver.get_float("/audio/total_energy")
	# scale = Vector3(1.0, 1.0 + total_energy, 1.0)  # Uncomment to scale based on energy

func _on_endpoint_updated(endpoint_name: String, value):
	# React to specific endpoint updates
	match endpoint_name:
		"/clock/beat":
			print("Beat detected! Beat ID: ", value)
			# Trigger beat-synchronized effects here
			_trigger_beat_effect()
		
		"/audio/pulse":
			if value != 0:
				print("Pulse detected!")
				_trigger_pulse_effect()
		
		"/clock/bpm":
			# Only print BPM changes occasionally to avoid spam
			if randf() < 0.01:  # 1% chance per update
				print("BPM: ", value)

func _trigger_beat_effect():
	# Example: Create a visual effect on beat
	# You could spawn particles, flash lights, animate objects, etc.
	pass

func _trigger_pulse_effect():
	# Example: Create a visual effect on pulse
	# You could trigger different effects for pulses vs beats
	pass

## Example: Get the full standardized payload
func get_full_audio_data() -> Dictionary:
	if not osc_receiver:
		return {}
	
	var payload = osc_receiver.get_dict("/audio/standardized")
	return payload

## Example: Check if a specific band is present
func is_band_present(band_name: String) -> bool:
	var endpoint = "/audio/band_presence_%s" % band_name
	return osc_receiver.get_bool(endpoint)

## Example: Get all current values at once
func get_all_audio_data() -> Dictionary:
	if not osc_receiver:
		return {}
	return osc_receiver.get_all_values()
