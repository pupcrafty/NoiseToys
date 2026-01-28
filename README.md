## NoiseToys

NoiseToys is a small audio playground built around a real‑time Python audio service and a web‑based viewer.  
The audio service captures input from your sound device, extracts features (bands, beats, phrases, etc.), and sends them over OSC; the viewer displays those OSC messages in the browser.

### Repository Layout

- `audio_service/` – Python package that:
  - Captures audio from your input device
  - Computes audio features (bands, beats, etc.)
  - Sends data out via OSC according to `config.json`
- `viewer/` – Flask (or similar) web app that:
  - Listens for OSC messages coming from `audio_service`
  - Serves a browser‑based visualizer (`static/app.js`, `static/style.css`, `templates/index.html`)
- `config.json` – Shared configuration (at minimum audio/OSC settings)
- `PHRASE_LOGIC.md` – Design notes about phrase / musical logic
- `requirements.txt` – Python dependencies for the audio service (Windows‑focused notes included)

---

## Prerequisites

- Python 3.11 or 3.12 is recommended on Windows (for aubio wheels)
- A working audio input device (built‑in mic, USB interface, etc.)
- Node.js is **not required**; the viewer is served by Python.

See the Windows notes embedded in `requirements.txt` if you run into build issues for `aubio`.

---

## Installing Dependencies

From the repository root:

```bash
cd audio_service
python -m pip install -r ../requirements.txt
```

Install viewer dependencies:

```bash
cd ../viewer
python -m pip install -r requirements.txt
```

You can also create and activate a virtual environment before installing:

```bash
python -m venv .venv
.venv\Scripts\activate  # PowerShell / CMD on Windows
python -m pip install -r ../requirements.txt
python -m pip install -r viewer/requirements.txt
```

---

## Configuration

The shared `config.json` file controls (at minimum) OSC settings used by both the audio service and the viewer.

- **OSC port** – The audio service sends to this port and the viewer listens on it.
- Make sure the `osc.port` (or equivalent key) is **the same** for both tools.

If you edit `config.json`, restart both the audio service and the viewer so they pick up the new settings.

---

## Running the Audio Service

From the repository root:

```bash
cd audio_service
python -m audio_service.main
```

This should:

- Open your default audio input device
- Start computing audio features
- Begin sending OSC messages to the host/port defined in `config.json`

If there are device‑selection options inside `audio_input.py`, adjust them as needed for your sound card.

---

## Running the Viewer

From the repository root:

```bash
cd viewer
python server.py
```

Then open your browser to:

```text
http://127.0.0.1:5000
```

The viewer:

- Reads OSC configuration from `../config.json`
- Listens on the same OSC port as the audio service is sending to
- Displays:
  - Audio band data (bass, mid, treble)
  - Beat detection data (BPM, confidence, beat events)
  - Any phrase / clock / audio OSC messages in a log

You can change the web server port via the `VIEWER_PORT` environment variable (see `viewer/README.md` for details).

---

## Typical Workflow

1. **Start the audio service**
   ```bash
   cd audio_service
   python -m audio_service.main
   ```
2. **Start the viewer**
   ```bash
   cd ../viewer
   python server.py
   ```
3. **Open the browser** at `http://127.0.0.1:5000` and watch the visualizations respond to live audio.

---

## Development Notes

- Code style is standard Python; no formatter is enforced by default.
- The audio and OSC behavior is primarily defined in:
  - `audio_service/audio_input.py`
  - `audio_service/features.py`
  - `audio_service/osc_out.py`
- The browser‑side visualization lives in `viewer/static/app.js` and `viewer/static/style.css`.

If you experiment with new features or phrases, add high‑level design notes in `PHRASE_LOGIC.md` to keep the logic documented.

---

## License

Add your preferred license information here (MIT, Apache‑2.0, proprietary, etc.).

