# theListener2 Viewer

A web-based viewer for visualizing audio bands and beat detection from theListener2 audio service.

## Features

- **Audio Band Visualizer**: Real-time visualization of bass, mid, and treble frequency bands
- **Beat Detection Visualization**: Visual representation of beat detection from aubio, showing BPM, confidence, and beat events
- **Message Log**: Running log of all OSC messages received, with color-coded message types

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure OSC port (optional):
   - The viewer reads the OSC port from `../config.json`
   - By default, it listens on port 9000 (same as audio_service sends to)
   - Make sure the `osc.port` in `config.json` matches between audio_service and viewer

3. Start the viewer:
```bash
python server.py
```

4. Open your browser to:
```
http://127.0.0.1:5000
```

## Configuration

The viewer automatically reads the OSC configuration from `../config.json`. The OSC server will listen on the same port that the audio_service sends to.

To change the web server port, set the `VIEWER_PORT` environment variable:
```bash
set VIEWER_PORT=8080  # Windows
export VIEWER_PORT=8080  # Linux/Mac
python server.py
```

## Usage

1. Start the audio_service first:
```bash
cd ../audio_service
python -m audio_service.main
```

2. Then start the viewer:
```bash
python server.py
```

3. The viewer will automatically receive and display:
   - Audio band data (bass, mid, treble)
   - Beat detection data (BPM, confidence, beat events)
   - All OSC messages in the log

## Message Types

- **Clock messages** (`/clock/*`): Beat detection data from aubio
- **Audio messages** (`/audio/*`): Frequency band and audio feature data
- **Phrase messages** (`/phrase/*`): Phrase detection data
