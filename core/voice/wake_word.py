"""Wake Word detection using openWakeWord."""

import logging
import numpy as np
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class WakeWordListener:
    """Continuously listens for a wake word using openWakeWord and sounddevice."""
    
    def __init__(self, model_paths: Optional[list[str]] = None, threshold: float = 0.5):
        """Initialize the wake word listener.
        
        Args:
            model_paths: Optional list of paths to custom .onnx wake word models.
                         If None, uses default models (e.g., 'hey jarvis').
            threshold: Confidence threshold (0.0 to 1.0) to trigger detection.
        """
        try:
            import openwakeword
            from openwakeword.model import Model
            import sounddevice as sd
            self.sd = sd
            
            # Initialize openwakeword model
            openwakeword.utils.download_models()
            self.model = Model(wakeword_models=model_paths or ["hey jarvis"], inference_framework="onnx")
        except ImportError:
            logger.error("Failed to import openwakeword or sounddevice. Ensure they are installed.")
            raise
            
        self.threshold = threshold
        self.is_listening = False
        self._stream = None
        self._thread = None
        self._on_wake = None
        
    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
            
        if not self.is_listening:
            return
            
        # Convert float32 audio to int16 for openWakeWord
        audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
        
        # Feed to model
        prediction = self.model.predict(audio_int16)
        
        # Check if any model exceeds the threshold
        for mdl, score in prediction.items():
            if score >= self.threshold:
                logger.info(f"Wake word detected! Model: {mdl}, Score: {score:.3f}")
                self.is_listening = False # Pause listening to handle the command
                if self._on_wake:
                    # Fire the callback in a separate thread so we don't block the audio stream
                    threading.Thread(target=self._on_wake, daemon=True).start()
                break

    def start(self, on_wake: Callable[[], None]):
        """Start listening for the wake word in the background.
        
        Args:
            on_wake: Callback function to execute when the wake word is heard.
        """
        self._on_wake = on_wake
        self.is_listening = True
        
        if self._stream is None:
            # openWakeWord expects 16kHz audio
            self._stream = self.sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=self._audio_callback,
                blocksize=1280  # 80ms chunks
            )
            self._stream.start()
            logger.info("Wake word listener started (waiting for 'hey jarvis').")
        else:
            logger.info("Wake word listener resumed.")

    def stop(self):
        """Stop listening and close the audio stream."""
        self.is_listening = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("Wake word listener stopped.")
            
    def resume(self):
        """Resume listening after a wake word was processed."""
        self.is_listening = True
        logger.info("Wake word listener resumed.")
