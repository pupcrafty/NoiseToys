from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

import aubio

from audio_service.audio_input import AudioConfig, AudioInput
from audio_service.audio_stream import AudioStream
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

    # Audio playback streaming (optional)
    playback_cfg = config.get("audio_playback", {})
    playback_enabled = playback_cfg.get("enabled", True)
    playback_host = playback_cfg.get("host", "127.0.0.1")
    playback_port = int(playback_cfg.get("port", 9002))
    audio_stream = AudioStream(playback_host, playback_port)
    if playback_enabled:
        audio_stream.start()
        logger.info(f"Audio playback streaming enabled: {playback_host}:{playback_port}")
    else:
        logger.info("Audio playback streaming disabled")

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

    # Ordered names for detailed bands (used for beat-wise stats)
    detailed_band_names = extractor.detailed_band_names
    # Threshold for counting a normalized "pulse" per band
    normalized_pulse_threshold = feature_config.normalized_pulse_threshold

    beat_id = 0
    bpm_est = 120.0
    conf_est = 0.0
    last_state_send = 0.0

    # Histories of "winner" bands per beat.
    # Each entry is an integer index into detailed_band_names.
    raw_winner_history: list[int] = []
    norm_winner_history: list[int] = []

    # History of per-band normalized "pulses" over recent beats.
    # Each entry is a tuple (is_on_beat: bool, pulses: list[bool])
    # where pulses is a list[bool] of length len(detailed_band_names),
    # indicating whether that band's normalized energy exceeded the
    # configured threshold, and is_on_beat indicates if this occurred on a beat.
    # Keep up to 32 beats worth of pulses for total pulse frequency calculations.
    per_beat_norm_pulses: list[tuple[bool, list[bool]]] = []

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
        nonlocal raw_winner_history, norm_winner_history, per_beat_norm_pulses
        if samples.size == 0:
            return

        # Stream audio for playback
        audio_stream.send_samples(samples)

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

        # Track per-band normalized "pulses" (value > threshold) on every frame,
        # marking whether they occurred on-beat or off-beat.
        band_norm_values = [
            float(payload.get(f"band_normalized_{name}", 0.0)) for name in detailed_band_names
        ]
        if band_norm_values:
            frame_pulses = [
                band_norm_values[i] > normalized_pulse_threshold for i in range(len(detailed_band_names))
            ]
            # Only record if at least one band has a pulse to avoid storing empty entries
            if any(frame_pulses):
                per_beat_norm_pulses.append((osc_beat, frame_pulses))
                # Keep only the most recent 32 beats worth of pulses
                # (this will include both on-beat and off-beat pulses)
                if len(per_beat_norm_pulses) > 32:
                    per_beat_norm_pulses = per_beat_norm_pulses[-32:]

        # On each detected beat, update running tallies of which detailed band
        # "wins" by overall energy and by normalized energy, and per-band pulse
        # frequencies over the last 4 beats.
        if osc_beat:
            # Per-beat winner by overall energy (using EMA of each band).
            # Guard against the "all zeros so index 0 always wins" problem by
            # requiring a small minimum energy before counting a winner.
            band_ema_values = [
                float(payload.get(f"band_ema_{name}", 0.0)) for name in detailed_band_names
            ]
            if band_ema_values:
                max_ema = max(band_ema_values)
                # Only record a winner if there is meaningful energy in at least one band.
                if max_ema > 0.01:
                    raw_winner_index = int(
                        max(range(len(band_ema_values)), key=lambda i: band_ema_values[i])
                    )
                    raw_winner_history.append(raw_winner_index)

            # Per-beat winner by normalized energy (EMA / baseline).
            # Use normalization * energy so that silent sections do not create
            # fake "winners" and we avoid the default-all-1.0 case.
            if band_norm_values and band_ema_values:
                norm_scores = [
                    band_norm_values[i] * band_ema_values[i] for i in range(len(detailed_band_names))
                ]
                max_score = max(norm_scores)
                if max_score > 0.01:
                    norm_winner_index = int(
                        max(range(len(norm_scores)), key=lambda i: norm_scores[i])
                    )
                    norm_winner_history.append(norm_winner_index)

            # Keep only the most recent 90 beats in winner history.
            max_beats = 90
            if len(raw_winner_history) > max_beats:
                raw_winner_history = raw_winner_history[-max_beats:]
            if len(norm_winner_history) > max_beats:
                norm_winner_history = norm_winner_history[-max_beats:]

            # For each window (30/60/90 beats), compute which band has "won" the
            # most beats in that window, separately for raw and normalized energy.
            windows = (30, 60, 90)
            raw_window_winners: dict[int, int] = {}
            norm_window_winners: dict[int, int] = {}

            for w in windows:
                # Use as many beats as we have, up to the window size.
                raw_slice = raw_winner_history[-w:] if raw_winner_history else []
                norm_slice = norm_winner_history[-w:] if norm_winner_history else []

                if raw_slice:
                    counts: dict[int, int] = {}
                    for idx in raw_slice:
                        counts[idx] = counts.get(idx, 0) + 1
                    raw_window_winners[w] = max(counts, key=counts.get)

                if norm_slice:
                    counts_n: dict[int, int] = {}
                    for idx in norm_slice:
                        counts_n[idx] = counts_n.get(idx, 0) + 1
                    norm_window_winners[w] = max(counts_n, key=counts_n.get)

            if raw_window_winners or norm_window_winners:
                osc.send_band_winner_stats(raw_window_winners, norm_window_winners)

            # Compute and broadcast per-band pulse frequency over the last 4, 8, 16, and 32 beats.
            # This includes both on-beat and off-beat pulses.
            if per_beat_norm_pulses:
                for window_size in (4, 8, 16, 32):
                    window_slice = per_beat_norm_pulses[-window_size:] if len(per_beat_norm_pulses) >= window_size else per_beat_norm_pulses
                    per_band_counts: dict[str, int] = {name: 0 for name in detailed_band_names}
                    for is_on_beat, pulse_vec in window_slice:
                        for i, flag in enumerate(pulse_vec):
                            if flag:
                                per_band_counts[detailed_band_names[i]] += 1
                    osc.send_band_pulse_frequency(window_size, per_band_counts)

    AudioInput(audio_cfg).start(on_audio)


if __name__ == "__main__":
    run()
