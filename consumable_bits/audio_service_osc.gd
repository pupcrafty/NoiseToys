extends Node

## Audio Service OSC Receiver
## 
## Listens to OSC messages from the NoiseToys audio service and makes them
## easily accessible in Godot.
##
## Usage:
##   1. Add this script to a Node in your scene
##   2. Set the `endpoint_names` array in the inspector with the endpoints you want
##   3. Call `get_value(endpoint_name)` to get the latest value for any endpoint
##
## Example endpoints:
##   - "/clock/bpm"
##   - "/clock/beat"
##   - "/audio/bass"
##   - "/audio/mid"
##   - "/audio/treble"
##   - "/audio/band_bass_1"
##   - "/audio/band_normalized_mid_1"
##   - etc.

signal endpoint_updated(endpoint_name: String, value)

# Configuration
@export var osc_host: String = "127.0.0.1"
@export var osc_port: int = 9000
@export var endpoint_names: Array[String] = [
	"/clock/bpm",
	"/clock/beat",
	"/clock/conf",
	"/audio/bass",
	"/audio/mid",
	"/audio/treble",
	"/audio/total_energy",
	"/audio/beat",
	"/audio/pulse"
]

# Internal state
var _udp: PacketPeerUDP
var _endpoint_values: Dictionary = {}
var _is_connected: bool = false

func _ready():
	_connect_to_osc()

func _connect_to_osc():
	_udp = PacketPeerUDP.new()
	# Bind to the port (use "*" to listen on all interfaces, or specific host)
	# For receiving OSC, we bind to the port the audio service sends to
	var bind_host = "*"  # Listen on all interfaces
	var err = _udp.bind(osc_port, bind_host)
	if err != OK:
		push_error("Failed to bind UDP socket on port %d. Error: %d" % [osc_port, err])
		push_error("Make sure the audio service is configured to send to this port and no other application is using it.")
		return
	
	_is_connected = true
	print("Audio Service OSC: Listening on port %d (expecting messages from %s)" % [osc_port, osc_host])
	print("Audio Service OSC: Subscribed to %d endpoints" % endpoint_names.size())

func _exit_tree():
	if _udp:
		_udp.close()

func _process(_delta):
	if not _is_connected or not _udp:
		return
	
	# Check for incoming packets
	_udp.wait = 0  # Non-blocking
	while _udp.get_available_packet_count() > 0:
		var packet = _udp.get_packet()
		_parse_osc_message(packet)

func _parse_osc_message(packet: PackedByteArray):
	# Basic OSC message parser
	# OSC format: address string (null-padded to 4 bytes), type tag string (null-padded to 4 bytes), arguments
	
	if packet.size() < 8:
		return
	
	var offset = 0
	
	# Parse address string
	var address = _read_osc_string(packet, offset)
	if address == "":
		return
	offset = _align_to_4_bytes(offset + address.length() + 1)
	
	if offset >= packet.size():
		return
	
	# Parse type tag string
	var type_tag = _read_osc_string(packet, offset)
	offset = _align_to_4_bytes(offset + type_tag.length() + 1)
	
	if type_tag.length() == 0 or type_tag[0] != ',':
		return
	
	# Check if this endpoint is in our subscription list
	if not endpoint_names.has(address):
		return
	
	# Parse arguments based on type tag
	var value = null
	if type_tag.length() > 1:
		var arg_type = type_tag[1]
		match arg_type:
			'f':  # float32
				if offset + 4 <= packet.size():
					var bytes = packet.slice(offset, offset + 4)
					value = _bytes_to_float32(bytes)
			'i':  # int32
				if offset + 4 <= packet.size():
					var bytes = packet.slice(offset, offset + 4)
					value = _bytes_to_int32(bytes)
			's':  # string
				if offset < packet.size():
					var str_value = _read_osc_string(packet, offset)
					value = str_value
					# Try to parse as JSON if it looks like JSON
					if str_value.begins_with("{") or str_value.begins_with("["):
						var json = JSON.new()
						var parse_result = json.parse(str_value)
						if parse_result == OK:
							value = json.data
	
	# Store the value
	if value != null:
		_endpoint_values[address] = value
		endpoint_updated.emit(address, value)

func _read_osc_string(packet: PackedByteArray, offset: int) -> String:
	var result = PackedByteArray()
	var i = offset
	while i < packet.size() and packet[i] != 0:
		result.append(packet[i])
		i += 1
	return result.get_string_from_utf8()

func _align_to_4_bytes(offset: int) -> int:
	# OSC strings are padded to 4-byte boundaries
	return (offset + 3) & ~3

func _bytes_to_float32(bytes: PackedByteArray) -> float:
	if bytes.size() < 4:
		return 0.0
	# Convert big-endian bytes to float
	var uint_value = (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3]
	# Interpret as IEEE 754 float32
	return _uint32_to_float(uint_value)

func _uint32_to_float(uint_val: int) -> float:
	# Convert uint32 to float (IEEE 754 single precision)
	# Handle special cases
	if uint_val == 0:
		return 0.0
	if uint_val == 0x80000000:
		return -0.0
	if uint_val == 0x7F800000:
		return INF
	if uint_val == 0xFF800000:
		return -INF
	if (uint_val & 0x7F800000) == 0x7F800000 and (uint_val & 0x007FFFFF) != 0:
		return NAN
	
	# Extract components
	var sign_bit = (uint_val >> 31) & 1
	var exponent_bits = (uint_val >> 23) & 0xFF
	var mantissa_bits = uint_val & 0x7FFFFF
	
	var sign = 1.0 if sign_bit == 0 else -1.0
	
	# Handle denormalized numbers
	if exponent_bits == 0:
		var mantissa = mantissa_bits / 8388608.0  # 2^23
		return sign * mantissa * pow(2.0, -126)
	
	# Normalized numbers
	var exponent = exponent_bits - 127
	var mantissa = 1.0 + (mantissa_bits / 8388608.0)
	return sign * mantissa * pow(2.0, exponent)

func _bytes_to_int32(bytes: PackedByteArray) -> int:
	if bytes.size() < 4:
		return 0
	# Convert big-endian bytes to int32
	var uint_value = (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3]
	# Handle sign extension for int32
	if uint_value & 0x80000000:
		return uint_value - 0x100000000
	return uint_value

## Public API

## Get the latest value for an endpoint
## Returns null if the endpoint hasn't received any data yet
func get_value(endpoint_name: String):
	return _endpoint_values.get(endpoint_name, null)

## Get the latest value as a float (returns 0.0 if not available)
func get_float(endpoint_name: String) -> float:
	var value = get_value(endpoint_name)
	if value == null:
		return 0.0
	if value is float:
		return value
	if value is int:
		return float(value)
	return 0.0

## Get the latest value as an int (returns 0 if not available)
func get_int(endpoint_name: String) -> int:
	var value = get_value(endpoint_name)
	if value == null:
		return 0
	if value is int:
		return value
	if value is float:
		return int(value)
	return 0

## Get the latest value as a bool (returns false if not available)
func get_bool(endpoint_name: String) -> bool:
	var value = get_value(endpoint_name)
	if value == null:
		return false
	if value is bool:
		return value
	if value is int:
		return value != 0
	if value is float:
		return value != 0.0
	return false

## Get the latest value as a Dictionary (for JSON payloads like /audio/standardized)
func get_dict(endpoint_name: String) -> Dictionary:
	var value = get_value(endpoint_name)
	if value is Dictionary:
		return value
	return {}

## Check if an endpoint has received data
func has_value(endpoint_name: String) -> bool:
	return _endpoint_values.has(endpoint_name)

## Get all current endpoint values as a dictionary
func get_all_values() -> Dictionary:
	return _endpoint_values.duplicate()

## Add an endpoint to the subscription list at runtime
func subscribe_to_endpoint(endpoint_name: String):
	if not endpoint_names.has(endpoint_name):
		endpoint_names.append(endpoint_name)
		print("Audio Service OSC: Subscribed to new endpoint: %s" % endpoint_name)

## Remove an endpoint from the subscription list
func unsubscribe_from_endpoint(endpoint_name: String):
	var index = endpoint_names.find(endpoint_name)
	if index >= 0:
		endpoint_names.remove_at(index)
		_endpoint_values.erase(endpoint_name)
		print("Audio Service OSC: Unsubscribed from endpoint: %s" % endpoint_name)
