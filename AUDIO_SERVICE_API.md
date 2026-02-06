# Audio Service API Documentation

This document describes how to consume the NoiseToys audio service and all its OSC endpoints.

## Overview

The audio service is a real-time audio analysis engine that:
- Captures audio from your system's input device
- Extracts frequency bands, beat detection, and other audio features
- Broadcasts all data via OSC (Open Sound Control) protocol
- Runs continuously and sends updates at audio frame rate

## Protocol

**Protocol**: OSC (Open Sound Control) over UDP  
**Default Host**: `127.0.0.1`  
**Default Port**: `9000` (configurable via `config.json`)

All endpoints send data as OSC messages. Most values are floats, some are integers, and booleans are sent as `0` or `1`.

## Endpoint Categories

The service exposes three main categories of endpoints:
1. **Clock/Tempo** - Beat detection and BPM tracking
2. **Audio Features** - Real-time frequency analysis and energy metrics
3. **Band Statistics** - Aggregated statistics about frequency band behavior

---

## 1. Clock/Tempo Endpoints

These endpoints provide beat detection and tempo information.

### `/clock/beat`
**Type**: Integer  
**Frequency**: On each detected beat  
**Description**: Beat event notification. The value is a monotonically increasing beat ID.

**Example**: `1`, `2`, `3`, ...

### `/clock/beat_id`
**Type**: Integer  
**Frequency**: On each beat + periodic updates (default 10 Hz)  
**Description**: Current beat counter (same as `/clock/beat` but sent more frequently).

### `/clock/bpm`
**Type**: Float  
**Frequency**: On each beat + periodic updates (default 10 Hz)  
**Description**: Estimated BPM (beats per minute). Uses exponential moving average to smooth tempo estimates. Only updates when confidence is sufficient.

**Range**: Typically 70-180 BPM (configurable)

### `/clock/conf`
**Type**: Float  
**Frequency**: On each beat + periodic updates (default 10 Hz)  
**Description**: Confidence level of the tempo detection (0.0 to 1.0). Higher values indicate more reliable tempo estimates.

### `/clock/time`
**Type**: Float  
**Frequency**: On each beat + periodic updates (default 10 Hz)  
**Description**: Unix timestamp (seconds since epoch) when the clock state was computed.

---

## 2. Audio Feature Endpoints

These endpoints provide real-time audio analysis data. Most are sent every audio frame (typically 512 samples at 44.1kHz ≈ 11.6ms intervals).

### Standardized Payload

#### `/audio/standardized`
**Type**: JSON String  
**Frequency**: Every audio frame  
**Description**: Complete feature payload as a JSON object. Contains all audio features in a single message.

**Example JSON**:
```json
{
  "bass": 0.45,
  "mid": 0.32,
  "treble": 0.18,
  "total_energy": 0.95,
  "energy_delta": 0.02,
  "movement": 0.15,
  "energy_variance": 0.001,
  "bass_ratio": 0.47,
  "mid_ratio": 0.34,
  "treble_ratio": 0.19,
  "band_balance": 0.85,
  "beat": false,
  "pulse": true,
  "band_sub_1": 0.12,
  "band_sub_2": 0.23,
  ...
}
```

### Individual Feature Endpoints

All values below are also available as individual OSC endpoints for easier consumption.

#### Basic Frequency Bands

##### `/audio/bass`
**Type**: Float  
**Description**: Bass frequency band energy (40-160 Hz, configurable). Smoothed with exponential moving average.

##### `/audio/mid`
**Type**: Float  
**Description**: Mid frequency band energy (160-1200 Hz, configurable). Smoothed with exponential moving average.

##### `/audio/treble`
**Type**: Float  
**Description**: Treble frequency band energy (1200-8000 Hz, configurable). Smoothed with exponential moving average.

#### Energy Metrics

##### `/audio/total_energy`
**Type**: Float  
**Description**: Sum of bass + mid + treble energy.

##### `/audio/energy_delta`
**Type**: Float  
**Description**: Change in total energy from previous frame. Positive values indicate increasing energy.

##### `/audio/energy_variance`
**Type**: Float  
**Description**: Variance of energy around its smoothed mean. Higher values indicate more dynamic/changing audio.

##### `/audio/movement`
**Type**: Float  
**Description**: Smoothed rate of change in total energy. Higher values indicate more "movement" in the audio.

#### Frequency Ratios

##### `/audio/bass_ratio`
**Type**: Float  
**Description**: Proportion of bass energy relative to total energy (0.0 to 1.0).

##### `/audio/mid_ratio`
**Type**: Float  
**Description**: Proportion of mid energy relative to total energy (0.0 to 1.0).

##### `/audio/treble_ratio`
**Type**: Float  
**Description**: Proportion of treble energy relative to total energy (0.0 to 1.0).

##### `/audio/band_balance`
**Type**: Float  
**Description**: Measure of how balanced the frequency distribution is (0.0 to 1.0). Higher values indicate more balanced distribution across bands.

#### Event Detection

##### `/audio/beat`
**Type**: Integer (0 or 1)  
**Description**: Beat detection event. `1` when a beat is detected in the bass frequencies, `0` otherwise. Uses flux-based detection with refractory period.

##### `/audio/pulse`
**Type**: Integer (0 or 1)  
**Description**: Pulse detection event. `1` when a pulse is detected in the treble frequencies, `0` otherwise. Uses flux-based detection with refractory period.

### Detailed Frequency Bands

The service analyzes 11 detailed frequency bands for more granular analysis. Each band has multiple representations:

#### Raw Band Energy
**Endpoints**: `/audio/band_{band_name}`  
**Type**: Float  
**Description**: Fast-smoothed energy for each detailed band.

**Available Bands**:
- `/audio/band_sub_1` - 20-40 Hz (true sub / rumble)
- `/audio/band_sub_2` - 40-70 Hz (kick fundamental territory + sub notes)
- `/audio/band_bass_1` - 70-120 Hz (bass fundamentals)
- `/audio/band_bass_2` - 120-200 Hz (bass body / warmth)
- `/audio/band_low_mid_1` - 200-350 Hz (mud / lower synth body)
- `/audio/band_low_mid_2` - 350-600 Hz (snare body, synth thickness)
- `/audio/band_mid_1` - 600-1200 Hz (vocal core, lead presence)
- `/audio/band_mid_2` - 1200-2400 Hz (bite, intelligibility)
- `/audio/band_high_1` - 2400-4000 Hz (snare crack / bite)
- `/audio/band_high_2` - 4000-6500 Hz (hi-hat "tick")
- `/audio/band_air_1` - 6500-10000 Hz (sparkle)

#### EMA Band Energy (Analyzer View)
**Endpoints**: `/audio/band_ema_{band_name}`  
**Type**: Float  
**Description**: Slower exponential moving average of band energy, suitable for analyzer-style visualization. More stable than raw band values.

**Example**: `/audio/band_ema_bass_1`, `/audio/band_ema_mid_2`, etc.

#### Band Baseline
**Endpoints**: `/audio/band_baseline_{band_name}`  
**Type**: Float  
**Description**: Very slow-moving baseline that tracks the "normal" or "context" level for each band. Used for context-aware normalization.

**Example**: `/audio/band_baseline_sub_1`, `/audio/band_baseline_high_2`, etc.

#### Normalized Band Energy
**Endpoints**: `/audio/band_normalized_{band_name}`  
**Type**: Float  
**Description**: EMA energy divided by baseline. Values around 1.0 indicate normal levels. Values > 1.0 indicate energy above baseline. Useful for detecting relative changes.

**Example**: `/audio/band_normalized_bass_1` = 1.5 means bass_1 is 50% above its baseline.

#### Band Presence
**Endpoints**: `/audio/band_presence_{band_name}`  
**Type**: Integer (0 or 1)  
**Description**: Hysteresis-based presence detection. `1` when the band's energy is significantly above baseline (threshold: 1.6x), `0` when it drops below (threshold: 1.3x). Prevents flickering.

**Example**: `/audio/band_presence_mid_1` indicates whether mid-range vocals/leads are currently present.

---

## 3. Band Statistics Endpoints

These endpoints provide aggregated statistics computed over multiple beats.

### Band Winner Statistics

These endpoints indicate which frequency band "won" (had the highest energy) most often in recent beat windows.

#### `/audio/beat_raw_band_win_{window}`
**Type**: Integer  
**Frequency**: On each detected beat  
**Description**: Index of the band that won most often in the last `{window}` beats, based on raw EMA energy. Windows: 30, 60, 90 beats.

**Band Index Mapping**:
- `0` = sub_1
- `1` = sub_2
- `2` = bass_1
- `3` = bass_2
- `4` = low_mid_1
- `5` = low_mid_2
- `6` = mid_1
- `7` = mid_2
- `8` = high_1
- `9` = high_2
- `10` = air_1

**Endpoints**:
- `/audio/beat_raw_band_win_30`
- `/audio/beat_raw_band_win_60`
- `/audio/beat_raw_band_win_90`

#### `/audio/beat_norm_band_win_{window}`
**Type**: Integer  
**Frequency**: On each detected beat  
**Description**: Index of the band that won most often in the last `{window}` beats, based on normalized energy (EMA × normalized). Windows: 30, 60, 90 beats.

**Endpoints**:
- `/audio/beat_norm_band_win_30`
- `/audio/beat_norm_band_win_60`
- `/audio/beat_norm_band_win_90`

### Band Pulse Frequency

These endpoints count how many times each band's normalized energy exceeded a threshold in recent beat windows.

#### `/audio/band_pulse{window_size}_{band_name}`
**Type**: Integer  
**Frequency**: On each detected beat  
**Description**: Count of how many times the band's normalized energy exceeded the threshold in the last `{window_size}` beats. Range: 0 to `{window_size}`.

**Window Sizes**: 4, 8, 16, 32 beats

**Examples**:
- `/audio/band_pulse4_bass_1` - Count in last 4 beats
- `/audio/band_pulse8_mid_2` - Count in last 8 beats
- `/audio/band_pulse16_high_1` - Count in last 16 beats
- `/audio/band_pulse32_sub_2` - Count in last 32 beats

**Note**: These counts include both on-beat and off-beat pulses, providing a measure of how "active" each band has been recently.

---

## Configuration

The service behavior is controlled via `config.json` in the repository root.

### OSC Configuration
```json
{
  "osc": {
    "host": "127.0.0.1",
    "port": 9000
  }
}
```

### Audio Configuration
```json
{
  "audio": {
    "samplerate": 44100,
    "hop_size": 512,
    "win_size": 1024,
    "channels": 1,
    "device": null
  }
}
```

### Tempo Detection Configuration
```json
{
  "tempo": {
    "conf_min": 0.25,
    "bpm_min": 70.0,
    "bpm_max": 180.0,
    "bpm_ema_alpha": 0.08,
    "bpm_resend_hz": 10.0
  }
}
```

### Feature Extraction Configuration
```json
{
  "features": {
    "bass_lo": 40.0,
    "bass_hi": 160.0,
    "mid_lo": 160.0,
    "mid_hi": 1200.0,
    "treble_lo": 1200.0,
    "treble_hi": 8000.0,
    "gain": 1.5,
    "smooth": 0.25,
    "auto_normalize": true,
    "normalized_pulse_threshold": 1.2,
    ...
  }
}
```

---

## Usage Examples

### Python (using python-osc)

```python
from pythonosc import udp_client

# Create OSC client
client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

# Note: The audio service sends messages, it doesn't receive them.
# To consume, you need an OSC server. See example below.
```

### Python (receiving OSC messages)

```python
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

def handle_audio_bass(address, *args):
    print(f"Bass level: {args[0]}")

def handle_clock_beat(address, *args):
    print(f"Beat detected! Beat ID: {args[0]}")

def handle_standardized(address, *args):
    import json
    payload = json.loads(args[0])
    print(f"Total energy: {payload['total_energy']}")

# Create dispatcher
dispatcher = Dispatcher()
dispatcher.map("/audio/bass", handle_audio_bass)
dispatcher.map("/clock/beat", handle_clock_beat)
dispatcher.map("/audio/standardized", handle_standardized)

# Create server
server = BlockingOSCUDPServer(("127.0.0.1", 9000), dispatcher)
print("Listening for OSC messages on 127.0.0.1:9000")
server.serve_forever()
```

### Max/MSP

1. Create a `udpreceive` object: `udpreceive 9000`
2. Route messages using `route` objects: `route /audio/bass /clock/beat`
3. Connect to your processing logic

### Pure Data

1. Create a `[udpreceive 9000]` object
2. Use `[route /audio/bass /clock/beat]` to separate messages
3. Connect to your patches

### Node.js (using osc)

```javascript
const osc = require('osc');

const udpPort = new osc.UDPPort({
    localAddress: "127.0.0.1",
    localPort: 9000
});

udpPort.on("message", function (oscMsg) {
    console.log("OSC Message:", oscMsg.address, oscMsg.args);
    
    if (oscMsg.address === "/audio/bass") {
        console.log("Bass:", oscMsg.args[0]);
    } else if (oscMsg.address === "/clock/beat") {
        console.log("Beat:", oscMsg.args[0]);
    }
});

udpPort.open();
```

### TouchDesigner

1. Add a `UDP In DAT`
2. Set the port to `9000`
3. Use `parse` DATs to extract OSC address and arguments
4. Route to your logic using `select` DATs

---

## Data Flow Summary

1. **Audio Input** → Captured from system audio device (configurable)
2. **Feature Extraction** → FFT analysis, band energy, beat detection
3. **OSC Broadcasting** → All features sent as OSC messages
4. **Periodic Updates**:
   - Audio features: Every audio frame (~11.6ms at 44.1kHz with 512 hop)
   - Clock state: On beats + 10 Hz periodic updates
   - Band statistics: On each detected beat

---

## Tips for Consumers

1. **Use `/audio/standardized`** for complete snapshots if you need all features at once
2. **Use individual endpoints** for selective processing to reduce message parsing overhead
3. **Band indices** in winner stats are 0-10, map to band names using the list in section 2
4. **Normalized values** (`band_normalized_*`) are useful for detecting relative changes regardless of absolute volume
5. **Presence indicators** (`band_presence_*`) provide stable on/off states without flickering
6. **Pulse frequencies** give you activity levels over time windows, useful for detecting patterns

---

## Troubleshooting

- **No messages received**: Check that the audio service is running and that OSC host/port match
- **Missing endpoints**: Some endpoints only send on beats (e.g., band statistics). Ensure audio is playing with detectable beats
- **High CPU usage**: Consider filtering to only the endpoints you need rather than subscribing to all
- **Audio device issues**: Check `config.json` audio device setting. Use `None` for default device

---

## See Also

- `README.md` - General project documentation
- `PHRASE_LOGIC.md` - Design notes about musical logic
- `config.json` - Configuration reference
