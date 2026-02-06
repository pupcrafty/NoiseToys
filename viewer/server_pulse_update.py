# Helper script to add pulse frequency handlers
# This will be used to generate the handlers for 8, 16, 32 beats

band_names = ["sub_1", "sub_2", "bass_1", "bass_2", "low_mid_1", "low_mid_2", 
              "mid_1", "mid_2", "high_1", "high_2", "air_1"]
windows = [8, 16, 32]

for window in windows:
    for band in band_names:
        print(f'    "band_pulse{window}_{band}": 0,')

print("\n# Handlers:")
for window in windows:
    for band in band_names:
        print(f'    elif address == "/audio/band_pulse{window}_{band}":')
        print(f'        audio_data["band_pulse{window}_{band}"] = int(value)')
        print(f'        socketio.emit("audio_data", audio_data)')

print("\n# Dispatcher mappings:")
for window in windows:
    for band in band_names:
        print(f'    dispatcher.map("/audio/band_pulse{window}_{band}", osc_handler)')
