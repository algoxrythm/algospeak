import os
import threading
import time
import queue
from typing import Optional, Callable
import numpy as np
from faster_whisper import WhisperModel

# Fix for pip-installed CUDA libraries
# Fix for pip-installed CUDA libraries
# Handled in run.sh via LD_LIBRARY_PATH


class TranscriptionEngine(threading.Thread):
    def __init__(self, 
                 model_size: str = "large-v3-turbo", 
                 device: str = "auto", 
                 compute_type: str = "default",
                 on_segment_callback: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.on_segment_callback = on_segment_callback
        self.audio_queue = queue.Queue()
        self.running = True
        self.model = None
        self.daemon = True  # Daemon thread to exit when main program exits
        
        # Buffer for accumulating audio
        self.audio_buffer = np.array([], dtype=np.float32)
        self.sample_rate = 16000
        # Process every N seconds of audio or when buffer is full enough
        self.min_duration = 0.5 

    def initialize_model(self):
        print(f"Loading model {self.model_size} on {self.device} with {self.compute_type}...")
        try:
            # Adjust compute_type based on device if 'default' is passed
            if self.compute_type == "default":
                if self.device == "cuda" or (self.device == "auto" and self._check_cuda()):
                    self.compute_type = "float16"
                else:
                    self.compute_type = "int8"

            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            # Verify model works with a dummy transcription
            # This catches CUDA errors that only happen during inference
            print("Verifying model...")
            self.model.transcribe(np.zeros(16000, dtype=np.float32), beam_size=1)
            print("Model loaded and verified successfully.")
        except Exception as e:
            print(f"Error loading/verifying model: {e}")
            # Fallback to CPU int8 if CUDA fails
            if self.device != "cpu":
                print("Falling back to CPU int8...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type
                )

    def _check_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def push_audio(self, audio_data: np.ndarray):
        self.audio_queue.put(audio_data)

    def run(self):
        self.initialize_model()
        
        while self.running:
            try:
                # Get audio chunks from queue
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    if chunk.ndim > 1:
                        chunk = chunk.flatten()
                    self.audio_buffer = np.concatenate((self.audio_buffer, chunk))
                except queue.Empty:
                    pass
                
                # If we have enough audio, transcribe
                # Note: This is a simplified streaming logic. 
                # Real-time streaming with faster-whisper usually involves VAD and accumulating chunks.
                # Here we rely on the VAD filter in transcribe() and accumulate a bit of buffer.
                
                # To make it truly "real-time" with faster-whisper, we typically feed larger chunks 
                # or use a sliding window. For this implementation, we'll process when we have > 1s 
                # of audio, but we need to be careful not to cut words.
                # A better approach for "overlay" is to process continuously but only finalize when silence is detected.
                
                # However, faster-whisper is designed for file/segment transcription.
                # We will use a simple accumulation strategy:
                # 1. Accumulate audio.
                # 2. If audio > 1.0s, run transcription with VAD.
                # 3. If VAD detects speech, we get segments.
                
                if len(self.audio_buffer) >= self.sample_rate * 1.0: # 1 second
                    segments, info = self.model.transcribe(
                        self.audio_buffer, 
                        beam_size=5,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500)
                    )
                    
                    text_output = ""
                    for segment in segments:
                        text_output += segment.text + " "
                    
                    if text_output.strip():
                        if self.on_segment_callback:
                            self.on_segment_callback(text_output.strip())
                        
                        # In a real streaming scenario, we might want to keep the buffer 
                        # if the sentence isn't finished, but faster-whisper doesn't give partials easily.
                        # For this "Overlay" app, we'll clear the buffer after successful transcription
                        # to keep it "real-time" and responsive, assuming short commands/sentences.
                        # For continuous dictation, this logic might need a sliding window.
                        self.audio_buffer = np.array([], dtype=np.float32)
                    
                    # Prevent buffer from growing too large if no speech detected
                    if len(self.audio_buffer) > self.sample_rate * 10: # 10 seconds cap
                         self.audio_buffer = self.audio_buffer[-self.sample_rate * 5:] # Keep last 5s

            except Exception as e:
                print(f"Error in transcription loop: {e}")
                time.sleep(0.1)

    def stop(self):
        self.running = False
