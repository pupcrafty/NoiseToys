from __future__ import annotations

import socket
import struct
from typing import Optional

import numpy as np


class AudioStream:
    """Streams raw audio samples via UDP for playback."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9002):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.enabled = False

    def start(self) -> None:
        """Start the audio stream."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.enabled = True
        except Exception as e:
            print(f"Warning: Failed to create audio stream socket: {e}")
            self.enabled = False

    def send_samples(self, samples: np.ndarray) -> None:
        """Send audio samples via UDP."""
        if not self.enabled or self.socket is None:
            return
        
        if samples.size == 0:
            return
        
        try:
            # Packet format: [4 bytes: sample count (uint32)] [samples as float32]
            sample_count = len(samples)
            packet = struct.pack("!I", sample_count) + samples.tobytes()
            self.socket.sendto(packet, (self.host, self.port))
        except Exception:
            # Silently fail - audio streaming is optional
            pass

    def stop(self) -> None:
        """Stop the audio stream."""
        self.enabled = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
