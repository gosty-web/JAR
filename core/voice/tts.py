"""Text-to-Speech using local Kokoro v1.0 via kokoro-onnx."""

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class TTSEngine:
    """Handles local text-to-speech generation using Kokoro-ONNX."""
    
    def __init__(self, models_dir: str = "models", voice: str = "af_heart"):
        """Initialize the TTS Engine.
        
        Args:
            models_dir: Directory containing kokoro.onnx and voices.json.
            voice: Default voice profile to use.
        """
        self.models_dir = os.path.abspath(models_dir)
        self.model_path = os.path.join(self.models_dir, "kokoro.onnx")
        self.voices_path = os.path.join(self.models_dir, "voices.json")
        self.default_voice = voice
        self.kokoro = None
        
        # We will lazy-load the model to avoid blocking on startup
        # or failing immediately if weights aren't downloaded yet.
        self._is_initialized = False

    def _initialize(self):
        if self._is_initialized:
            return
            
        if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
            logger.warning(f"Kokoro weights not found at {self.models_dir}. Please download kokoro.onnx and voices.json.")
            # For this MVP, if weights are missing, we just log and skip instead of crashing
            return
            
        try:
            from kokoro_onnx import Kokoro
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            self._is_initialized = True
            logger.info("Kokoro TTS initialized successfully.")
        except ImportError:
            logger.error("Failed to import kokoro_onnx. Ensure it is installed.")
        except Exception as e:
            logger.error(f"Failed to load Kokoro model: {e}")

    def speak(self, text: str, voice: Optional[str] = None):
        """Synthesize and play speech locally.
        
        This method blocks until playback completes. For non-blocking, run in a thread.
        
        Args:
            text: The text to speak.
            voice: Optional voice profile override.
        """
        self._initialize()
        
        if not self._is_initialized or not self.kokoro:
            logger.warning(f"TTS skipped (not initialized): {text}")
            return
            
        v = voice or self.default_voice
        logger.info(f"Speaking (voice={v}): '{text}'")
        
        try:
            import sounddevice as sd
            import numpy as np
            
            # Generate audio samples (generator for long texts, but we'll collect it here)
            samples, sample_rate = self.kokoro.create(text, voice=v, speed=1.0, lang="en-us")
            
            # Play audio through sounddevice
            sd.play(samples, sample_rate)
            sd.wait() # Block until done
        except Exception as e:
            logger.error(f"TTS playback failed: {e}")
            
    def speak_async(self, text: str, voice: Optional[str] = None):
        """Synthesize and play speech in a background thread."""
        threading.Thread(target=self.speak, args=(text, voice), daemon=True).start()
