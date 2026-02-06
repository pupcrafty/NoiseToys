from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def lerp(old: float, new: float, alpha: float) -> float:
    return (1.0 - alpha) * old + alpha * new


@dataclass
class FeatureConfig:
    bass_lo: float = 40.0
    bass_hi: float = 160.0
    mid_lo: float = 160.0
    mid_hi: float = 1200.0
    treble_lo: float = 1200.0
    treble_hi: float = 8000.0
    gain: float = 1.5
    smooth: float = 0.25
    auto_normalize: bool = True
    loudness_smooth: float = 0.08
    target_level: float = 0.08
    min_norm: float = 0.25
    max_norm: float = 8.0
    silence_gate: float = 0.0006
    noise_floor: float = 0.002
    noise_floor_ratio_of_target: float = 0.04
    beat_flux_thresh: float = 0.010
    beat_refractory: float = 0.22
    pulse_flux_thresh: float = 0.016
    pulse_refractory: float = 0.08
    movement_smooth: float = 0.10
    # Extra-slow EMA for analyzer bands (viewer channels)
    band_ema_smooth: float = 0.06
    # Very slow baseline EMA for each analyzer band (context-aware "normal")
    # slow_alpha in ~0.005–0.01 → roughly 10–20 seconds adaptation depending on hop.
    band_baseline_slow_alpha: float = 0.005
    # Threshold for counting a "normalized energy pulse" (for per-band 4‑beat stats)
    normalized_pulse_threshold: float = 1.2


class FeatureExtractor:
    def __init__(self, sample_rate: int, win_size: int, hop_size: int, config: FeatureConfig):
        self.sample_rate = sample_rate
        self.win_size = win_size
        self.hop_size = hop_size
        self.config = config
        self._window = np.hanning(win_size).astype(np.float32)
        self._buffer = np.zeros(win_size, dtype=np.float32)
        self._freqs = np.fft.rfftfreq(win_size, 1.0 / sample_rate)
        self._beat_cd = 0.0
        self._pulse_cd = 0.0
        self._b_s = 0.0
        self._m_s = 0.0
        self._t_s = 0.0
        self._b_prev = 0.0
        self._t_prev = 0.0
        self._energy_s = 0.0
        self._movement_s = 0.0
        self._loudness_ema = 0.0
        self._energy_var_ema = 0.0

        # Detailed analyzer-style bands (Hz ranges)
        # Names are lower_snake_case; viewer can display prettier labels.
        self._detailed_bands = [
            ("sub_1", 20.0, 40.0),        # true sub / rumble
            ("sub_2", 40.0, 70.0),        # kick fundamental territory + sub notes
            ("bass_1", 70.0, 120.0),      # bass fundamentals
            ("bass_2", 120.0, 200.0),     # bass body / warmth
            ("low_mid_1", 200.0, 350.0),  # mud / lower synth body
            ("low_mid_2", 350.0, 600.0),  # snare body, synth thickness
            ("mid_1", 600.0, 1200.0),     # vocal core, lead presence
            ("mid_2", 1200.0, 2400.0),    # bite, intelligibility
            ("high_1", 2400.0, 4000.0),   # snare crack / bite
            ("high_2", 4000.0, 6500.0),   # hi-hat “tick”
            ("air_1", 6500.0, 10000.0),   # sparkle
        ]
        # Smoothed values for those bands (fast-ish for responsiveness)
        self._detailed_s = {name: 0.0 for name, _, _ in self._detailed_bands}
        # Additional slow EMA values, intended for analyzer viewer channels
        self._detailed_ema = {name: 0.0 for name, _, _ in self._detailed_bands}
        # Even slower baseline that tracks "current normal" per band
        self._detailed_baseline = {name: 0.0 for name, _, _ in self._detailed_bands}
        # Presence state per band (hysteresis-based "this thing exists right now")
        self._detailed_presence = {name: False for name, _, _ in self._detailed_bands}

    @property
    def detailed_band_names(self) -> list[str]:
        """
        Public accessor for the ordered list of detailed band names.

        This lets other parts of the system (e.g. beat statistics in main.py)
        reason about bands in a stable index order without duplicating config.
        """
        return [name for name, _, _ in self._detailed_bands]

    def process(self, samples: np.ndarray) -> Dict[str, float | bool]:
        if samples.size == 0:
            return {}
        if samples.size > self.win_size:
            samples = samples[-self.win_size :]
        shift = samples.size
        self._buffer = np.roll(self._buffer, -shift)
        self._buffer[-shift:] = samples
        windowed = self._buffer * self._window
        spectrum = np.fft.rfft(windowed)
        magnitude = np.abs(spectrum)

        b_raw = self._band_energy(magnitude, self.config.bass_lo, self.config.bass_hi)
        m_raw = self._band_energy(magnitude, self.config.mid_lo, self.config.mid_hi)
        t_raw = self._band_energy(magnitude, self.config.treble_lo, self.config.treble_hi)
        energy_raw = b_raw + m_raw + t_raw

        # Raw energies for detailed analyzer bands
        detailed_raw: Dict[str, float] = {}
        for name, lo, hi in self._detailed_bands:
            detailed_raw[name] = self._band_energy(magnitude, lo, hi)

        self._loudness_ema = lerp(self._loudness_ema, energy_raw, self.config.loudness_smooth)

        norm = 1.0
        if self.config.auto_normalize:
            if self._loudness_ema <= self.config.silence_gate:
                norm = 0.0
            else:
                norm = self.config.target_level / max(self._loudness_ema, 1e-6)
                norm = clamp(norm, self.config.min_norm, self.config.max_norm)

        b = b_raw * self.config.gain * norm
        m = m_raw * self.config.gain * norm
        t = t_raw * self.config.gain * norm

        adaptive_floor = max(self.config.noise_floor, self.config.target_level * self.config.noise_floor_ratio_of_target)
        if b < adaptive_floor:
            b = 0.0
        if m < adaptive_floor:
            m = 0.0
        if t < adaptive_floor:
            t = 0.0

        # Apply same gain / normalization / floor / smoothing to detailed bands
        for name, raw in detailed_raw.items():
            v = raw * self.config.gain * norm
            if v < adaptive_floor:
                v = 0.0
            # Fast smoothing (used for raw / immediate band_* channels)
            self._detailed_s[name] = lerp(self._detailed_s[name], v, self.config.smooth)
            # Slower EMA specifically for analyzer viewer: band_ema_* channels
            self._detailed_ema[name] = lerp(self._detailed_ema[name], v, self.config.band_ema_smooth)
            # Very slow baseline that tracks the "context" of each band
            # baseline[b] = slow_alpha * smoothed[b] + (1 - slow_alpha) * baseline[b]
            self._detailed_baseline[name] = lerp(
                self._detailed_baseline[name],
                self._detailed_ema[name],
                self.config.band_baseline_slow_alpha,
            )
            
            # Presence detection with hysteresis (on_threshold=1.6, off_threshold=1.3)
            # Goal: Turn "energy" into "this thing exists right now"
            on_threshold = 1.6
            off_threshold = 1.3
            baseline = self._detailed_baseline[name]
            smoothed = self._detailed_ema[name]
            
            if baseline > 1e-6:  # Avoid division by zero
                if not self._detailed_presence[name] and smoothed > baseline * on_threshold:
                    self._detailed_presence[name] = True
                elif self._detailed_presence[name] and smoothed < baseline * off_threshold:
                    self._detailed_presence[name] = False

        self._b_s = lerp(self._b_s, b, self.config.smooth)
        self._m_s = lerp(self._m_s, m, self.config.smooth)
        self._t_s = lerp(self._t_s, t, self.config.smooth)

        bass_flux = max(self._b_s - self._b_prev, 0.0)
        treble_flux = max(self._t_s - self._t_prev, 0.0)
        self._b_prev = self._b_s
        self._t_prev = self._t_s

        dt = self.hop_size / float(self.sample_rate)
        self._beat_cd = max(self._beat_cd - dt, 0.0)
        self._pulse_cd = max(self._pulse_cd - dt, 0.0)

        beat = False
        if self._beat_cd <= 0.0 and bass_flux >= self.config.beat_flux_thresh:
            beat = True
            self._beat_cd = self.config.beat_refractory

        pulse = False
        if self._pulse_cd <= 0.0 and treble_flux >= self.config.pulse_flux_thresh:
            pulse = True
            self._pulse_cd = self.config.pulse_refractory

        energy = self._b_s + self._m_s + self._t_s
        prev_energy = self._energy_s
        self._energy_s = lerp(self._energy_s, energy, self.config.movement_smooth)
        movement = self._energy_s - prev_energy
        self._movement_s = lerp(self._movement_s, movement, 0.35)

        energy_dev = energy - self._energy_s
        self._energy_var_ema = lerp(self._energy_var_ema, energy_dev * energy_dev, 0.15)

        total_energy = self._b_s + self._m_s + self._t_s
        total_safe = max(total_energy, 1e-6)
        bass_ratio = self._b_s / total_safe
        mid_ratio = self._m_s / total_safe
        treble_ratio = self._t_s / total_safe
        energy_delta = total_energy - prev_energy
        mean_band = total_energy / 3.0
        band_variance = ((self._b_s - mean_band) ** 2 + (self._m_s - mean_band) ** 2 + (self._t_s - mean_band) ** 2) / 3.0
        band_balance = 1.0 - clamp(band_variance / max(total_energy * total_energy, 1e-6), 0.0, 1.0)
        base_payload: Dict[str, float | bool] = {
            "bass": self._b_s,
            "mid": self._m_s,
            "treble": self._t_s,
            "total_energy": total_energy,
            "energy_delta": energy_delta,
            "movement": self._movement_s,
            "energy_variance": self._energy_var_ema,
            "bass_ratio": bass_ratio,
            "mid_ratio": mid_ratio,
            "treble_ratio": treble_ratio,
            "band_balance": band_balance,
            "beat": beat,
            "pulse": pulse,
        }

        # Add detailed band energies to payload with explicit keys
        for name, _, _ in self._detailed_bands:
            key = f"band_{name}"
            base_payload[key] = self._detailed_s[name]
            ema_key = f"band_ema_{name}"
            base_payload[ema_key] = self._detailed_ema[name]
            # Context-aware baseline (rolling "normal" for this band)
            baseline_key = f"band_baseline_{name}"
            base_payload[baseline_key] = self._detailed_baseline[name]
            # Scale-normalized energy value (EMA / baseline, scaled around baseline)
            baseline = self._detailed_baseline[name]
            ema = self._detailed_ema[name]
            if baseline > 1e-6:
                normalized_key = f"band_normalized_{name}"
                base_payload[normalized_key] = ema / baseline
            else:
                normalized_key = f"band_normalized_{name}"
                base_payload[normalized_key] = 1.0  # Default to 1.0 when baseline is too small
            # Presence indicator (hysteresis-based "this thing exists right now")
            presence_key = f"band_presence_{name}"
            base_payload[presence_key] = self._detailed_presence[name]

        return base_payload

    def _band_energy(self, magnitude: np.ndarray, lo_hz: float, hi_hz: float) -> float:
        mask = (self._freqs >= lo_hz) & (self._freqs < hi_hz)
        if not np.any(mask):
            return 0.0
        return float(np.sum(magnitude[mask]))
