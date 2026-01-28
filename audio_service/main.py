from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

import aubio

from audio_service.audio_input import AudioConfig, AudioInput
from audio_service.features import FeatureConfig, FeatureExtractor, clamp, lerp
from audio_service.osc_out import OscOut


CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def run() -> None:
    config = load_config()
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO").upper())
    log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_date_format = log_config.get("date_format", "%Y-%m-%d %H:%M:%S")

    logging.basicConfig(level=log_level, format=log_format, datefmt=log_date_format)
    logger = logging.getLogger("audio_service")

    osc_cfg = config.get("osc", {})
    osc_host = osc_cfg.get("host", "127.0.0.1")
    osc_port = int(osc_cfg.get("port", 9000))
    osc = OscOut(osc_host, osc_port)

    audio_cfg_raw = config.get("audio", {})
    audio_cfg = AudioConfig(
        samplerate=int(audio_cfg_raw.get("samplerate", 44100)),
        hop_size=int(audio_cfg_raw.get("hop_size", 512)),
        win_size=int(audio_cfg_raw.get("win_size", 1024)),
        channels=int(audio_cfg_raw.get("channels", 1)),
        device=audio_cfg_raw.get("device", None),
    )

    tempo_cfg = config.get("tempo", {})
    conf_min = float(tempo_cfg.get("conf_min", 0.25))
    bpm_min = float(tempo_cfg.get("bpm_min", 70.0))
    bpm_max = float(tempo_cfg.get("bpm_max", 180.0))
    bpm_ema_alpha = float(tempo_cfg.get("bpm_ema_alpha", 0.08))
    bpm_resend_hz = float(tempo_cfg.get("bpm_resend_hz", 10.0))

    feature_config = FeatureConfig(**config.get("features", {}))
    extractor = FeatureExtractor(audio_cfg.samplerate, audio_cfg.win_size, audio_cfg.hop_size, feature_config)

    tempo = aubio.tempo("default", audio_cfg.win_size, audio_cfg.hop_size, audio_cfg.samplerate)

    beat_id = 0
    bpm_est = 120.0
    conf_est = 0.0
    last_state_send = 0.0

    logger.info("Starting audio service -> OSC bridge")
    logger.info("OSC target: %s:%s", osc_host, osc_port)
    logger.info(
        "Audio: %s Hz, hop=%s, win=%s, channels=%s",
        audio_cfg.samplerate,
        audio_cfg.hop_size,
        audio_cfg.win_size,
        audio_cfg.channels,
    )

    def on_audio(samples, _dt):
        nonlocal beat_id, bpm_est, conf_est, last_state_send
        if samples.size == 0:
            return

        is_beat = tempo(samples)
        bpm_raw = float(tempo.get_bpm())
        conf_raw = float(tempo.get_confidence())

        conf_est = lerp(conf_est, clamp(conf_raw, 0.0, 1.0), 0.15)
        now = time.time()

        if bpm_min <= bpm_raw <= bpm_max and conf_raw >= conf_min:
            bpm_est = lerp(bpm_est, bpm_raw, bpm_ema_alpha)

        osc_beat = False
        if is_beat:
            beat_id += 1
            osc_beat = True
            osc.send_clock_beat(beat_id)
            osc.send_clock_state(bpm_est, conf_est, beat_id, now)

        if now - last_state_send >= (1.0 / bpm_resend_hz):
            last_state_send = now
            osc.send_clock_state(bpm_est, conf_est, beat_id, now)

        payload = extractor.process(samples)
        if not payload:
            return
        osc.send_audio_payload(payload)

    AudioInput(audio_cfg).start(on_audio)


if __name__ == "__main__":
    run()
