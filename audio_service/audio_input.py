from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd


@dataclass
class AudioConfig:
    samplerate: int = 44100
    hop_size: int = 512
    win_size: int = 1024
    channels: int = 1
    device: int | None = None


class AudioInput:
    def __init__(self, config: AudioConfig):
        self.config = config

    def start(self, callback: Callable[[np.ndarray, float], None]) -> None:
        def stream_callback(indata, frames, time_info, status):
            if status:
                callback(np.array([], dtype=np.float32), 0.0)
                return
            if self.config.channels > 1:
                samples = np.mean(indata, axis=1).astype(np.float32)
            else:
                samples = indata[:, 0].astype(np.float32)
            callback(samples, frames / float(self.config.samplerate))

        with sd.InputStream(
            device=self.config.device,
            channels=self.config.channels,
            samplerate=self.config.samplerate,
            blocksize=self.config.hop_size,
            dtype="float32",
            callback=stream_callback,
        ):
            while True:
                sd.sleep(250)
