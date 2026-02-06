from __future__ import annotations

import logging
import socket
import struct
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioPlayback:
    """Handles audio playback from UDP stream."""

    def __init__(
        self,
        udp_host: str = "127.0.0.1",
        udp_port: int = 9002,
        samplerate: int = 44100,
        channels: int = 1,
        device: Optional[int] = None,
        volume: float = 1.0,
        browser_callback: Optional[Callable[[list[float], int], None]] = None,
    ):
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self.volume = max(0.0, min(1.0, volume))  # Clamp to [0, 1]
        self.browser_callback = browser_callback  # Callback to forward audio to browser
        
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stream: Optional[sd.OutputStream] = None
        
        # Audio buffer
        self.buffer_size = 1024
        self.audio_queue: list[np.ndarray] = []
        self.queue_lock = threading.Lock()

    def start(self, start_server_playback: bool = True) -> None:
        """Start the audio playback server.
        
        Args:
            start_server_playback: If True, also start server-side audio playback.
                                 If False, only start UDP receiver for browser forwarding.
        """
        if self.running:
            return
        
        self.running = True
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind((self.udp_host, self.udp_port))
        except OSError as e:
            logger.error(f"Failed to bind UDP socket on {self.udp_host}:{self.udp_port}: {e}")
            self.running = False
            return
        
        logger.info(f"Audio playback UDP server listening on {self.udp_host}:{self.udp_port}")
        logger.info(f"Audio playback: {self.samplerate} Hz, {self.channels} channel(s), volume={self.volume:.2f}")
        
        # Start receiver thread
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        
        # Start playback stream only if requested
        if start_server_playback:
            try:
                self._start_playback_stream()
            except Exception as e:
                logger.error(f"Failed to start audio playback stream: {e}")
                # Don't stop the receiver if server playback fails

    def stop(self) -> None:
        """Stop the audio playback server."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop audio stream
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        
        logger.info("Audio playback stopped")

    def _receive_loop(self) -> None:
        """Receive audio data from UDP and queue it for playback."""
        buffer = bytearray(65536)  # Max UDP packet size
        
        while self.running and self.socket:
            try:
                # Receive UDP packet
                nbytes, addr = self.socket.recvfrom_into(buffer)
                if nbytes < 8:  # Need at least header (4 bytes for length + some data)
                    continue
                
                # Parse packet: first 4 bytes are sample count (as int32)
                sample_count = struct.unpack("!I", buffer[:4])[0]
                if sample_count == 0 or sample_count > 16384:  # Sanity check
                    continue
                
                # Remaining bytes are float32 samples
                expected_bytes = sample_count * 4
                if nbytes < 4 + expected_bytes:
                    continue
                
                # Convert bytes to numpy array
                samples = np.frombuffer(buffer[4:4+expected_bytes], dtype=np.float32)
                
                # Forward to browser if callback is set
                if self.browser_callback:
                    try:
                        # Convert to list for JSON serialization
                        samples_list = samples.tolist()
                        self.browser_callback(samples_list, self.samplerate)
                    except Exception as e:
                        logger.warning(f"Error forwarding audio to browser: {e}")
                
                # Queue for playback (volume will be applied in callback)
                with self.queue_lock:
                    self.audio_queue.append(samples)
                    # Limit queue size to prevent memory issues
                    if len(self.audio_queue) > 100:
                        self.audio_queue.pop(0)
                        
            except socket.error as e:
                if self.running:
                    logger.error(f"UDP receive error: {e}")
                break
            except Exception as e:
                logger.error(f"Error processing audio packet: {e}")

    def _start_playback_stream(self) -> None:
        """Start the sounddevice output stream."""
        def callback(outdata, frames, time_info, status):
            if status:
                logger.warning(f"Audio playback status: {status}")
            
            # Get audio from queue
            with self.queue_lock:
                if not self.audio_queue:
                    # No data available, output silence
                    outdata[:] = 0.0
                    return
                
                # Get first chunk from queue
                samples = self.audio_queue.pop(0)
                
                # Read current volume value
                current_volume = self.volume
                
                # Ensure we have enough samples
                if len(samples) < frames:
                    # Pad with zeros if needed
                    padded = np.zeros(frames, dtype=np.float32)
                    padded[:len(samples)] = samples
                    samples = padded
                elif len(samples) > frames:
                    # Take only what we need, put rest back
                    output_samples = samples[:frames].copy()
                    remaining = samples[frames:]
                    self.audio_queue.insert(0, remaining)
                    # Apply volume to output
                    if current_volume != 1.0:
                        output_samples = output_samples * current_volume
                    # Output samples
                    if self.channels == 1:
                        outdata[:, 0] = output_samples
                    else:
                        outdata[:, 0] = output_samples
                        outdata[:, 1] = output_samples
                    return
                
                # Apply volume to samples
                if current_volume != 1.0:
                    samples = samples * current_volume
                
                # Output samples
                if self.channels == 1:
                    outdata[:, 0] = samples
                else:
                    # Mono to stereo
                    outdata[:, 0] = samples
                    outdata[:, 1] = samples
        
        # Start output stream
        self.stream = sd.OutputStream(
            device=self.device,
            channels=self.channels,
            samplerate=self.samplerate,
            blocksize=self.buffer_size,
            dtype="float32",
            callback=callback,
        )
        self.stream.start()
        logger.info("Audio playback stream started")
