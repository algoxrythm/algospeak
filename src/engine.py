import os
import threading
import time
import queue
import collections
import numpy as np
from typing import Optional, Callable, Tuple
from faster_whisper import WhisperModel

class TranscriptionEngine(threading.Thread):
    def __init__(self, 
                 model_size: str = "large-v3-turbo", 
                 device: str = "auto", 
                 compute_type: str = "default",
                 on_segment_callback: Optional[Callable[[str, bool], None]] = None,
                 on_feedback_callback: Optional[Callable[[str], None]] = None): # New callback
        super().__init__()
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.on_segment_callback = on_segment_callback
        self.on_feedback_callback = on_feedback_callback
        
        self.audio_queue = queue.Queue()
        self.running = True
        self.daemon = True
        
        # Audio Config
        self.sample_rate = 16000
        self.audio_buffer = np.array([], dtype=np.float32)
        
        # VAD & Commit Config
        self.vad_threshold = 0.008      # Slightly lowered to be more sensitive to soft speech
        self.buffer_energy = 0.0        # Energy of current buffer
        self.silence_duration = 0.0    
        self.min_silence_to_commit = 0.8
        
        # Hallucination Filters
        self.min_logprob = -0.8        # Discard if confidence < 45% approx
        self.min_no_speech_prob = 0.4  # Discard if model thinks probability of no speech is high? 
                                       # Actually `no_speech_prob` > 0.6 means "likely silence".
                                       # Faster-whisper returns info.no_speech_prob.
        self.banned_phrases = {
            "thank you", "thanks", "you", "subs by", "subtitle", "copyright", "caption"
        }
        
        # Process Config
        self.transcription_interval = 0.25 # Faster polls
        self.last_process_time = 0
        self.max_buffer_size = self.sample_rate * 30 
        
        # State
        self.last_partial_text = ""

    def initialize_model(self):
        print(f"Loading model {self.model_size} on {self.device}...")
        try:
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
            # Warmup
            self.model.transcribe(np.zeros(16000), beam_size=1)
            print("Model loaded.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.device = "cpu"
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

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
            # 1. Ingest
            try:
                chunks = []
                while True:
                    try:
                        chunk = self.audio_queue.get_nowait()
                        chunks.append(chunk)
                    except queue.Empty:
                        break
                
                if chunks:
                    new_data = np.concatenate(chunks)
                    if new_data.ndim > 1:
                        new_data = new_data.flatten()
                    
                    self.audio_buffer = np.concatenate((self.audio_buffer, new_data))
                else:
                    time.sleep(0.01)

            except Exception as e:
                print(f"Ingest Error: {e}")
            
            # 2. Process
            now = time.time()
            if now - self.last_process_time > self.transcription_interval:
                # Only process if buffer has data
                if len(self.audio_buffer) > 0:
                     self.process_logic()
                        
                self.last_process_time = now

    def process_logic(self):
        try:
            # Transcribe with Word Timestamps
            segments, info = self.model.transcribe(
                self.audio_buffer,
                beam_size=5,
                language="en",
                initial_prompt="Cyberdeck stream log. Python code.",
                condition_on_previous_text=False,
                word_timestamps=True 
            )
            
            # Flatten words
            all_words = []
            for s in segments:
                if s.words:
                    all_words.extend(s.words)
            
            if not all_words:
                return

            # --- Command Parsing ---
            # Create a clean list for string matching
            # Filter out punctuation for command checks
            words_text = [w.word.strip().lower().translate(str.maketrans('', '', '.,!?')) for w in all_words]
            
            trigger_action = None 
            
            # check for "clear this" (multi-word, check end of list)
            if len(words_text) >= 2 and words_text[-2] == "clear" and words_text[-1] == "this":
                trigger_action = "CLEAR"
            
            # check for "inject" (anywhere? usually end)
            if not trigger_action:
                if "inject" in words_text:
                    trigger_action = "INJECT"
            
            # Logic Execution
            if trigger_action == "CLEAR":
                print("Command: CLEAR THIS")
                if self.on_feedback_callback: self.on_feedback_callback("DELETE")
                
                self.audio_buffer = np.array([], dtype=np.float32)
                self.last_partial_text = ""
                if self.on_segment_callback:
                    self.on_segment_callback("", True) 
                return

            if trigger_action == "INJECT":
                print("Command: INJECT")
                if self.on_feedback_callback: self.on_feedback_callback("SUCCESS")
                
                # find first occurrence
                try:
                    inject_index = words_text.index("inject")
                except ValueError:
                    return # Should not happen

                valid_words_objs = all_words[:inject_index]
                final_text = "".join([w.word for w in valid_words_objs]).strip()
                
                # Prevent empty commit
                if final_text:
                    if self.on_segment_callback:
                        self.on_segment_callback(final_text, True) 
                
                # Clear buffer IMMEDIATELY after commit
                self.audio_buffer = np.array([], dtype=np.float32)
                self.last_partial_text = ""
                return

            # Check for "Cut"
            cut_count = 0
            i = len(words_text) - 1
            while i >= 0 and words_text[i] == "cut":
                cut_count += 1
                i -= 1
            
            if cut_count > 0:
                print(f"Command: CUT ({cut_count})")
                if self.on_feedback_callback: self.on_feedback_callback("DELETE")

                # Remove 'cut' words themselves + 'cut_count' words before them
                total_to_remove = cut_count * 2
                target_len = len(all_words) - total_to_remove
                
                if target_len <= 0:
                    # Clear all
                    self.audio_buffer = np.array([], dtype=np.float32)
                    self.last_partial_text = ""
                    if self.on_segment_callback:
                        self.on_segment_callback("", False)
                    return
                else:
                    last_kept_word = all_words[target_len - 1]
                    cut_time = last_kept_word.end
                    
                    # Convert time to samples
                    # We keep audio up to cut_time.
                    # Add small margin (0.05s) to preserve the word end, but avoid capturing the next word start.
                    new_sample_count = int((cut_time + 0.05) * self.sample_rate)
                    
                    if new_sample_count < len(self.audio_buffer):
                         self.audio_buffer = self.audio_buffer[:new_sample_count]
                         
                         # Update partial immediately
                         valid_words_objs = all_words[:target_len]
                         text = "".join([w.word for w in valid_words_objs]).strip()
                         
                         if text != self.last_partial_text:
                             self.last_partial_text = text
                             if self.on_segment_callback:
                                self.on_segment_callback(text, False)
                         return

            # Normal Partial Update
            valid_words_objs = []
            for i, w in enumerate(all_words):
                wt = words_text[i]
                if wt in self.banned_phrases:
                    continue
                valid_words_objs.append(w)
            
            text = "".join([w.word for w in valid_words_objs]).strip()
            
            if text != self.last_partial_text:
                self.last_partial_text = text
                if self.on_segment_callback:
                    self.on_segment_callback(text, False)
                        
        except Exception as e:
            print(f"Process Exception: {e}")

    def stop(self):
        self.running = False
