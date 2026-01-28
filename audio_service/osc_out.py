from __future__ import annotations

import json
from typing import Dict

from pythonosc.udp_client import SimpleUDPClient


class OscOut:
    def __init__(self, host: str, port: int):
        self.client = SimpleUDPClient(host, port)

    def send_clock_state(self, bpm: float, confidence: float, beat_id: int, now: float) -> None:
        self.client.send_message("/clock/bpm", float(bpm))
        self.client.send_message("/clock/conf", float(confidence))
        self.client.send_message("/clock/beat_id", int(beat_id))
        self.client.send_message("/clock/time", float(now))

    def send_clock_beat(self, beat_id: int) -> None:
        self.client.send_message("/clock/beat", int(beat_id))

    def send_audio_payload(self, payload: Dict[str, float | bool]) -> None:
        self.client.send_message("/audio/standardized", json.dumps(payload))
        # Explicit list so we control which fields get broken out as individual OSC endpoints.
        keys_to_break_out = [
            "bass",
            "mid",
            "treble",
            "beat",
            "pulse",
            "movement",
            "total_energy",
            "energy_delta",
            "energy_variance",
            "bass_ratio",
            "mid_ratio",
            "treble_ratio",
            "band_balance",
            # Detailed frequency bands
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
            # EMA versions of detailed bands (for analyzer viewer)
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
            # Baseline values for detailed bands (context-aware "normal")
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
            # Presence indicators for detailed bands (hysteresis-based)
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
        ]
        for key in keys_to_break_out:
            if key not in payload:
                continue
            value = payload[key]
            if isinstance(value, bool):
                value = 1 if value else 0
            self.client.send_message(f"/audio/{key}", value)
