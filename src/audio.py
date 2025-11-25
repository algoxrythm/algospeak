import queue
import sys
import threading
import time
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd

class AudioPipeline:
    def __init__(self, sample_rate: int = 16000, block_size: int = 1024, channels: int = 1):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def _callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags):
        """
        Non-blocking callback for sounddevice.
        """
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        
        if self.is_recording:
            # Copy data to avoid buffer issues and put into queue
            self.audio_queue.put(indata.copy())

    def start(self):
        """Starts the audio stream."""
        with self._lock:
            if self.stream is None:
                try:
                    self.stream = sd.InputStream(
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        channels=self.channels,
                        dtype="float32",
                        callback=self._callback
                    )
                    self.stream.start()
                    self.is_recording = True
                    print("Audio pipeline started.")
                except Exception as e:
                    print(f"Error starting audio stream: {e}", file=sys.stderr)

    def stop(self):
        """Stops the audio stream."""
        with self._lock:
            self.is_recording = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                print("Audio pipeline stopped.")

    def get_audio_chunk(self) -> Optional[np.ndarray]:
        """
        Retrieves the next audio chunk from the queue.
        Non-blocking, returns None if empty.
        """
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def clear_queue(self):
        """Clears the audio queue."""
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
