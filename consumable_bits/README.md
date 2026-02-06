# Audio Service OSC Receiver for Godot

This directory contains a Godot script that connects to the NoiseToys audio service and makes OSC endpoint data easily accessible in your Godot project.

## Files

- `audio_service_osc.gd` - Main script that receives OSC messages and provides easy access to endpoint values

## Setup

1. **Add the script to your scene:**
   - Create a new Node (or use an existing one like an AutoLoad singleton)
   - Attach the `audio_service_osc.gd` script to the node
   - If you want it available globally, add it as an AutoLoad singleton in Project Settings

2. **Configure endpoints:**
   - In the Inspector, set the `endpoint_names` array with the OSC endpoints you want to listen to
   - Default endpoints are already configured for common use cases
   - Set `osc_host` and `osc_port` to match your `config.json` settings (default: 127.0.0.1:9000)

3. **Start the audio service:**
   - Make sure the NoiseToys audio service is running and sending OSC messages
   - The script will automatically connect when the scene starts

## Usage Examples

### Basic Value Access

```gdscript
# Get a reference to the OSC receiver node
var osc_receiver = $AudioServiceOSC  # or get_node("/root/AudioServiceOSC") if AutoLoad

# Get values as different types
var bpm = osc_receiver.get_float("/clock/bpm")
var beat_id = osc_receiver.get_int("/clock/beat")
var is_beat = osc_receiver.get_bool("/audio/beat")

# Get raw value (returns null if not available)
var bass_level = osc_receiver.get_value("/audio/bass")
```

### Reacting to Updates

```gdscript
# Connect to the signal to react when values update
func _ready():
    var osc_receiver = $AudioServiceOSC
    osc_receiver.endpoint_updated.connect(_on_endpoint_updated)

func _on_endpoint_updated(endpoint_name: String, value):
    if endpoint_name == "/clock/beat":
        print("Beat detected! ID: ", value)
        # Trigger visual effects, animations, etc.
    elif endpoint_name == "/audio/bass":
        # Update visualizations based on bass level
        update_bass_visualization(value)
```

### Using in _process()

```gdscript
func _process(delta):
    var osc_receiver = $AudioServiceOSC
    
    # Get current values
    var bass = osc_receiver.get_float("/audio/bass")
    var mid = osc_receiver.get_float("/audio/mid")
    var treble = osc_receiver.get_float("/audio/treble")
    
    # Use values to drive visuals, audio, etc.
    modulate_color = Color(bass, mid, treble)
    scale = Vector3(1.0, 1.0 + bass * 2.0, 1.0)
```

### Getting the Full Standardized Payload

```gdscript
# The /audio/standardized endpoint sends a JSON payload with all features
var payload = osc_receiver.get_dict("/audio/standardized")
if not payload.is_empty():
    var total_energy = payload.get("total_energy", 0.0)
    var movement = payload.get("movement", 0.0)
    var bass_ratio = payload.get("bass_ratio", 0.0)
```

### Dynamic Subscription

```gdscript
# Subscribe to additional endpoints at runtime
osc_receiver.subscribe_to_endpoint("/audio/band_bass_1")
osc_receiver.subscribe_to_endpoint("/audio/band_normalized_mid_2")

# Unsubscribe when no longer needed
osc_receiver.unsubscribe_from_endpoint("/audio/band_bass_1")
```

## Available Endpoints

See `AUDIO_SERVICE_API.md` in the project root for a complete list of available endpoints. Common ones include:

### Clock/Tempo
- `/clock/bpm` - Beats per minute (float)
- `/clock/beat` - Beat event (int, beat ID)
- `/clock/conf` - Tempo confidence (float, 0.0-1.0)
- `/clock/beat_id` - Current beat counter (int)
- `/clock/time` - Timestamp (float)

### Basic Audio Features
- `/audio/bass` - Bass energy (float)
- `/audio/mid` - Mid energy (float)
- `/audio/treble` - Treble energy (float)
- `/audio/total_energy` - Total energy (float)
- `/audio/beat` - Beat detection (int, 0 or 1)
- `/audio/pulse` - Pulse detection (int, 0 or 1)
- `/audio/movement` - Energy movement (float)
- `/audio/bass_ratio` - Bass proportion (float, 0.0-1.0)
- `/audio/mid_ratio` - Mid proportion (float, 0.0-1.0)
- `/audio/treble_ratio` - Treble proportion (float, 0.0-1.0)

### Detailed Frequency Bands
- `/audio/band_sub_1`, `/audio/band_sub_2` - Sub frequencies
- `/audio/band_bass_1`, `/audio/band_bass_2` - Bass frequencies
- `/audio/band_low_mid_1`, `/audio/band_low_mid_2` - Low mid frequencies
- `/audio/band_mid_1`, `/audio/band_mid_2` - Mid frequencies
- `/audio/band_high_1`, `/audio/band_high_2` - High frequencies
- `/audio/band_air_1` - Air frequencies

### Normalized and EMA Bands
- `/audio/band_ema_{band_name}` - EMA smoothed band energy
- `/audio/band_normalized_{band_name}` - Normalized band energy (relative to baseline)
- `/audio/band_presence_{band_name}` - Presence detection (int, 0 or 1)
- `/audio/band_baseline_{band_name}` - Baseline energy level

### Complete Payload
- `/audio/standardized` - JSON string with all features (use `get_dict()` to parse)

## Tips

1. **Use AutoLoad**: Consider adding this script as an AutoLoad singleton so it's available throughout your project without needing node paths.

2. **Filter Endpoints**: Only subscribe to endpoints you actually use to reduce processing overhead.

3. **Check for Values**: Use `has_value()` before accessing values to avoid null errors:
   ```gdscript
   if osc_receiver.has_value("/clock/bpm"):
       var bpm = osc_receiver.get_float("/clock/bpm")
   ```

4. **Type Safety**: Use the typed getters (`get_float()`, `get_int()`, `get_bool()`) for safer access with default values.

5. **Performance**: The script processes OSC messages in `_process()`, so it updates every frame. For high-frequency endpoints, this is fine, but be aware of the update rate.

## Troubleshooting

- **No values received**: 
  - Check that the audio service is running
  - Verify `osc_host` and `osc_port` match your `config.json`
  - Check the Godot console for connection errors
  - Make sure the endpoints you're subscribing to are actually being sent by the audio service

- **Wrong values**: 
  - Some endpoints only send on beats (like band statistics)
  - Make sure audio is playing with detectable beats for tempo-related endpoints

- **Port already in use**: 
  - Only one application can bind to a UDP port at a time
  - If the viewer is running, it might be using port 9000
  - Consider using a different port or stopping other OSC receivers

## Example Scene Setup

1. Create a new scene with a Node named "AudioServiceOSC"
2. Attach the `audio_service_osc.gd` script
3. In the Inspector, configure your desired endpoints
4. Save the scene
5. In other scripts, reference it: `var osc = get_node("/root/AudioServiceOSC")` (if AutoLoad) or `var osc = $AudioServiceOSC` (if in same scene)
