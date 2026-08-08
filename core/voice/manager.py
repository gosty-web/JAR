"""Orchestrates the Voice Layer."""

import logging
import asyncio
import wave
import time
import os
import tempfile
import numpy as np

from core.voice.wake_word import WakeWordListener
from core.voice.stt import STTEngine
from core.voice.tts import TTSEngine
from core.voice.speaker_verification import SpeakerVerifier

logger = logging.getLogger(__name__)

class VoiceManager:
    """Coordinates wake word detection, verification, and STT transcription."""
    
    def __init__(self, use_mock_llm: bool = False):
        self.wake_word = WakeWordListener()
        self.stt = STTEngine()
        self.tts = TTSEngine()
        self.verifier = SpeakerVerifier()
        
        # Audio recording config
        self.sample_rate = 16000
        self.recording_duration = 5 # Record for 5 seconds after wake
        
    def _record_audio(self, duration: int, filepath: str):
        """Record audio to a file for `duration` seconds."""
        import sounddevice as sd
        logger.info(f"Recording {duration}s to {filepath}...")
        
        recording = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='int16')
        sd.wait() # Wait until recording is finished
        
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(recording.tobytes())
            
        logger.info("Recording finished.")

    async def _handle_wake_async(self):
        """Async handler triggered when the wake word is detected."""
        logger.info("Wake word triggered. Processing command...")
        self.tts.speak("Yes?")
        
        # 1. Record command
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, "jar_command.wav")
        
        # Run recording in a separate thread so we don't block the async loop
        await asyncio.to_thread(self._record_audio, self.recording_duration, audio_path)
        
        # 2. Verify speaker
        is_verified = await self.verifier.verify(audio_path)
        if not is_verified:
            logger.warning("Speaker verification failed. Ignoring command.")
            # Optionally play an error sound
            self.wake_word.resume()
            return
            
        # 3. Transcribe
        try:
            transcription = await self.stt.transcribe(audio_path)
            logger.info(f"Command transcribed: {transcription}")
            
            if transcription.strip():
                self.tts.speak("Processing.")
                # Here we would normally yield or pass the text to the ExecutionLoop
                # For now, we just log it.
            else:
                logger.info("Empty transcription.")
        except Exception as e:
            logger.error(f"Failed to process command: {e}")
            self.tts.speak("Sorry, I encountered an error.")
            
        # 4. Resume listening
        self.wake_word.resume()

    def _on_wake_sync(self):
        """Synchronous wrapper to launch the async handler."""
        # Create a new event loop if necessary, or run in the existing one
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(self._handle_wake_async(), loop)
        except RuntimeError:
            asyncio.run(self._handle_wake_async())

    def start(self):
        """Start the Voice Manager."""
        logger.info("Starting Voice Manager...")
        self.wake_word.start(on_wake=self._on_wake_sync)
        
    def stop(self):
        """Stop the Voice Manager."""
        self.wake_word.stop()
