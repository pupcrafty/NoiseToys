from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

# Load config to get OSC port
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Data storage
audio_data = {
    "bass": 0.0,
    "mid": 0.0,
    "treble": 0.0,
    # Detailed bands for analyzer-style visualization (fast channels)
    "band_sub_1": 0.0,
    "band_sub_2": 0.0,
    "band_bass_1": 0.0,
    "band_bass_2": 0.0,
    "band_low_mid_1": 0.0,
    "band_low_mid_2": 0.0,
    "band_mid_1": 0.0,
    "band_mid_2": 0.0,
    "band_high_1": 0.0,
    "band_high_2": 0.0,
    "band_air_1": 0.0,
    # EMA variants of detailed bands (used by analyzer viewer)
    "band_ema_sub_1": 0.0,
    "band_ema_sub_2": 0.0,
    "band_ema_bass_1": 0.0,
    "band_ema_bass_2": 0.0,
    "band_ema_low_mid_1": 0.0,
    "band_ema_low_mid_2": 0.0,
    "band_ema_mid_1": 0.0,
    "band_ema_mid_2": 0.0,
    "band_ema_high_1": 0.0,
    "band_ema_high_2": 0.0,
    "band_ema_air_1": 0.0,
    # Baseline (context) for each analyzer band
    "band_baseline_sub_1": 0.0,
    "band_baseline_sub_2": 0.0,
    "band_baseline_bass_1": 0.0,
    "band_baseline_bass_2": 0.0,
    "band_baseline_low_mid_1": 0.0,
    "band_baseline_low_mid_2": 0.0,
    "band_baseline_mid_1": 0.0,
    "band_baseline_mid_2": 0.0,
    "band_baseline_high_1": 0.0,
    "band_baseline_high_2": 0.0,
    "band_baseline_air_1": 0.0,
    # Presence indicators for detailed bands
    "band_presence_sub_1": False,
    "band_presence_sub_2": False,
    "band_presence_bass_1": False,
    "band_presence_bass_2": False,
    "band_presence_low_mid_1": False,
    "band_presence_low_mid_2": False,
    "band_presence_mid_1": False,
    "band_presence_mid_2": False,
    "band_presence_high_1": False,
    "band_presence_high_2": False,
    "band_presence_air_1": False,
    "total_energy": 0.0,
    "beat": False,
    "pulse": False,
    "movement": 0.0,
}

beat_data = {
    "bpm": 120.0,
    "confidence": 0.0,
    "beat_id": 0,
    "last_beat_time": 0.0,
    "beat_detected": False,
}

# Latest values per OSC endpoint
latest_messages: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_message(address: str, value: Any) -> Dict[str, Any]:
    """Format a message for the log."""
    return {
        "timestamp": time.time(),
        "address": address,
        "value": value,
        "time_str": time.strftime("%H:%M:%S", time.localtime()),
    }


def osc_handler(address: str, *args):
    """Handle incoming OSC messages."""
    if not args:
        return
    
    value = args[0]
    msg = format_message(address, value)
    # Track the most recent message per endpoint
    latest_messages[address] = msg

    # Emit to all connected clients so they can update their per-endpoint view
    socketio.emit("osc_message", msg)
    
    # Handle specific message types
    if address == "/clock/beat":
        beat_data["beat_id"] = int(value)
        beat_data["last_beat_time"] = time.time()
        beat_data["beat_detected"] = True
        socketio.emit("beat", {"beat_id": int(value), "time": time.time()})
        # Reset beat flag after a short delay
        def reset_beat():
            beat_data["beat_detected"] = False
        threading.Timer(0.1, reset_beat).start()
    
    elif address == "/clock/bpm":
        beat_data["bpm"] = float(value)
        socketio.emit("beat_data", beat_data)
    
    elif address == "/clock/conf":
        beat_data["confidence"] = float(value)
        socketio.emit("beat_data", beat_data)
    
    elif address == "/clock/beat_id":
        beat_data["beat_id"] = int(value)
        socketio.emit("beat_data", beat_data)
    
    elif address == "/clock/time":
        beat_data["last_beat_time"] = float(value)
        socketio.emit("beat_data", beat_data)
    
    elif address == "/audio/bass":
        audio_data["bass"] = float(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/mid":
        audio_data["mid"] = float(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/treble":
        audio_data["treble"] = float(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/beat":
        audio_data["beat"] = bool(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/pulse":
        audio_data["pulse"] = bool(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/movement":
        audio_data["movement"] = float(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/total_energy":
        audio_data["total_energy"] = float(value)
        socketio.emit("audio_data", audio_data)

    # Detailed band endpoints
    elif address == "/audio/band_sub_1":
        audio_data["band_sub_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_sub_2":
        audio_data["band_sub_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_bass_1":
        audio_data["band_bass_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_bass_2":
        audio_data["band_bass_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_low_mid_1":
        audio_data["band_low_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_low_mid_2":
        audio_data["band_low_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_mid_1":
        audio_data["band_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_mid_2":
        audio_data["band_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_high_1":
        audio_data["band_high_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_high_2":
        audio_data["band_high_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_air_1":
        audio_data["band_air_1"] = float(value)
        socketio.emit("audio_data", audio_data)

    # EMA band endpoints (preferred for analyzer viewer)
    elif address == "/audio/band_ema_sub_1":
        audio_data["band_ema_sub_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_sub_2":
        audio_data["band_ema_sub_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_bass_1":
        audio_data["band_ema_bass_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_bass_2":
        audio_data["band_ema_bass_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_low_mid_1":
        audio_data["band_ema_low_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_low_mid_2":
        audio_data["band_ema_low_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_mid_1":
        audio_data["band_ema_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_mid_2":
        audio_data["band_ema_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_high_1":
        audio_data["band_ema_high_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_high_2":
        audio_data["band_ema_high_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_ema_air_1":
        audio_data["band_ema_air_1"] = float(value)
        socketio.emit("audio_data", audio_data)

    # Baseline band endpoints
    elif address == "/audio/band_baseline_sub_1":
        audio_data["band_baseline_sub_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_sub_2":
        audio_data["band_baseline_sub_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_bass_1":
        audio_data["band_baseline_bass_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_bass_2":
        audio_data["band_baseline_bass_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_low_mid_1":
        audio_data["band_baseline_low_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_low_mid_2":
        audio_data["band_baseline_low_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_mid_1":
        audio_data["band_baseline_mid_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_mid_2":
        audio_data["band_baseline_mid_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_high_1":
        audio_data["band_baseline_high_1"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_high_2":
        audio_data["band_baseline_high_2"] = float(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_baseline_air_1":
        audio_data["band_baseline_air_1"] = float(value)
        socketio.emit("audio_data", audio_data)

    # Presence band endpoints
    elif address == "/audio/band_presence_sub_1":
        audio_data["band_presence_sub_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_sub_2":
        audio_data["band_presence_sub_2"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_bass_1":
        audio_data["band_presence_bass_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_bass_2":
        audio_data["band_presence_bass_2"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_low_mid_1":
        audio_data["band_presence_low_mid_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_low_mid_2":
        audio_data["band_presence_low_mid_2"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_mid_1":
        audio_data["band_presence_mid_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_mid_2":
        audio_data["band_presence_mid_2"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_high_1":
        audio_data["band_presence_high_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_high_2":
        audio_data["band_presence_high_2"] = bool(value)
        socketio.emit("audio_data", audio_data)
    elif address == "/audio/band_presence_air_1":
        audio_data["band_presence_air_1"] = bool(value)
        socketio.emit("audio_data", audio_data)
    
    elif address == "/audio/standardized":
        # Parse JSON payload
        try:
            payload = json.loads(value) if isinstance(value, str) else value
            # Core fields
            audio_data.update({
                "bass": float(payload.get("bass", 0.0)),
                "mid": float(payload.get("mid", 0.0)),
                "treble": float(payload.get("treble", 0.0)),
                "total_energy": float(payload.get("total_energy", 0.0)),
                "beat": bool(payload.get("beat", False)),
                "pulse": bool(payload.get("pulse", False)),
                "movement": float(payload.get("movement", 0.0)),
            })
            # Detailed band energies (fast)
            for key in [
                "band_sub_1",
                "band_sub_2",
                "band_bass_1",
                "band_bass_2",
                "band_low_mid_1",
                "band_low_mid_2",
                "band_mid_1",
                "band_mid_2",
                "band_high_1",
                "band_high_2",
                "band_air_1",
            ]:
                if key in payload:
                    audio_data[key] = float(payload.get(key, 0.0))
            # EMA band energies
            for key in [
                "band_ema_sub_1",
                "band_ema_sub_2",
                "band_ema_bass_1",
                "band_ema_bass_2",
                "band_ema_low_mid_1",
                "band_ema_low_mid_2",
                "band_ema_mid_1",
                "band_ema_mid_2",
                "band_ema_high_1",
                "band_ema_high_2",
                "band_ema_air_1",
            ]:
                if key in payload:
                    audio_data[key] = float(payload.get(key, 0.0))
            # Baseline (context) band energies
            for key in [
                "band_baseline_sub_1",
                "band_baseline_sub_2",
                "band_baseline_bass_1",
                "band_baseline_bass_2",
                "band_baseline_low_mid_1",
                "band_baseline_low_mid_2",
                "band_baseline_mid_1",
                "band_baseline_mid_2",
                "band_baseline_high_1",
                "band_baseline_high_2",
                "band_baseline_air_1",
            ]:
                if key in payload:
                    audio_data[key] = float(payload.get(key, 0.0))
            # Presence indicators for detailed bands
            for key in [
                "band_presence_sub_1",
                "band_presence_sub_2",
                "band_presence_bass_1",
                "band_presence_bass_2",
                "band_presence_low_mid_1",
                "band_presence_low_mid_2",
                "band_presence_mid_1",
                "band_presence_mid_2",
                "band_presence_high_1",
                "band_presence_high_2",
                "band_presence_air_1",
            ]:
                if key in payload:
                    audio_data[key] = bool(payload.get(key, False))

            socketio.emit("audio_data", audio_data)
        except Exception as e:
            logger.error(f"Error parsing standardized audio payload: {e}")


def start_osc_server(host: str = "127.0.0.1", port: int = 9001):
    """Start the OSC server in a separate thread."""
    dispatcher = Dispatcher()
    dispatcher.map("/clock/bpm", osc_handler)
    dispatcher.map("/clock/conf", osc_handler)
    dispatcher.map("/clock/beat_id", osc_handler)
    dispatcher.map("/clock/time", osc_handler)
    dispatcher.map("/clock/beat", osc_handler)
    dispatcher.map("/audio/bass", osc_handler)
    dispatcher.map("/audio/mid", osc_handler)
    dispatcher.map("/audio/treble", osc_handler)
    dispatcher.map("/audio/beat", osc_handler)
    dispatcher.map("/audio/pulse", osc_handler)
    dispatcher.map("/audio/movement", osc_handler)
    dispatcher.map("/audio/total_energy", osc_handler)
    # Detailed band endpoints
    dispatcher.map("/audio/band_sub_1", osc_handler)
    dispatcher.map("/audio/band_sub_2", osc_handler)
    dispatcher.map("/audio/band_bass_1", osc_handler)
    dispatcher.map("/audio/band_bass_2", osc_handler)
    dispatcher.map("/audio/band_low_mid_1", osc_handler)
    dispatcher.map("/audio/band_low_mid_2", osc_handler)
    dispatcher.map("/audio/band_mid_1", osc_handler)
    dispatcher.map("/audio/band_mid_2", osc_handler)
    dispatcher.map("/audio/band_high_1", osc_handler)
    dispatcher.map("/audio/band_high_2", osc_handler)
    dispatcher.map("/audio/band_air_1", osc_handler)
    # EMA band endpoints
    dispatcher.map("/audio/band_ema_sub_1", osc_handler)
    dispatcher.map("/audio/band_ema_sub_2", osc_handler)
    dispatcher.map("/audio/band_ema_bass_1", osc_handler)
    dispatcher.map("/audio/band_ema_bass_2", osc_handler)
    dispatcher.map("/audio/band_ema_low_mid_1", osc_handler)
    dispatcher.map("/audio/band_ema_low_mid_2", osc_handler)
    dispatcher.map("/audio/band_ema_mid_1", osc_handler)
    dispatcher.map("/audio/band_ema_mid_2", osc_handler)
    dispatcher.map("/audio/band_ema_high_1", osc_handler)
    dispatcher.map("/audio/band_ema_high_2", osc_handler)
    dispatcher.map("/audio/band_ema_air_1", osc_handler)
    # Baseline band endpoints
    dispatcher.map("/audio/band_baseline_sub_1", osc_handler)
    dispatcher.map("/audio/band_baseline_sub_2", osc_handler)
    dispatcher.map("/audio/band_baseline_bass_1", osc_handler)
    dispatcher.map("/audio/band_baseline_bass_2", osc_handler)
    dispatcher.map("/audio/band_baseline_low_mid_1", osc_handler)
    dispatcher.map("/audio/band_baseline_low_mid_2", osc_handler)
    dispatcher.map("/audio/band_baseline_mid_1", osc_handler)
    dispatcher.map("/audio/band_baseline_mid_2", osc_handler)
    dispatcher.map("/audio/band_baseline_high_1", osc_handler)
    dispatcher.map("/audio/band_baseline_high_2", osc_handler)
    dispatcher.map("/audio/band_baseline_air_1", osc_handler)
    # Presence band endpoints
    dispatcher.map("/audio/band_presence_sub_1", osc_handler)
    dispatcher.map("/audio/band_presence_sub_2", osc_handler)
    dispatcher.map("/audio/band_presence_bass_1", osc_handler)
    dispatcher.map("/audio/band_presence_bass_2", osc_handler)
    dispatcher.map("/audio/band_presence_low_mid_1", osc_handler)
    dispatcher.map("/audio/band_presence_low_mid_2", osc_handler)
    dispatcher.map("/audio/band_presence_mid_1", osc_handler)
    dispatcher.map("/audio/band_presence_mid_2", osc_handler)
    dispatcher.map("/audio/band_presence_high_1", osc_handler)
    dispatcher.map("/audio/band_presence_high_2", osc_handler)
    dispatcher.map("/audio/band_presence_air_1", osc_handler)
    dispatcher.map("/audio/standardized", osc_handler)
    dispatcher.set_default_handler(osc_handler)  # Catch all other messages
    
    server = ThreadingOSCUDPServer((host, port), dispatcher)
    logger.info(f"OSC server listening on {host}:{port}")
    
    def run_server():
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server


@app.route("/")
def index():
    """Serve the main viewer page."""
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    # Send current state
    emit("audio_data", audio_data)
    emit("beat_data", beat_data)
    # Send latest values per endpoint so the viewer can initialize
    emit("message_log", list(latest_messages.values()))


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    # Load config to get OSC port (should match audio_service's OSC target port)
    config = load_config()
    osc_cfg = config.get("osc", {})
    osc_host = osc_cfg.get("host", "127.0.0.1")
    osc_port = int(osc_cfg.get("port", 9000))
    
    # Start OSC server on the same port that audio_service sends to
    logger.info(f"Starting OSC server on {osc_host}:{osc_port}")
    logger.info("Note: Make sure audio_service is configured to send OSC to this port")
    start_osc_server(osc_host, osc_port)
    
    # Start Flask server
    web_port = int(os.environ.get("VIEWER_PORT", 5000))
    logger.info(f"Starting web viewer server on http://127.0.0.1:{web_port}")
    socketio.run(app, host="127.0.0.1", port=web_port, debug=False)
