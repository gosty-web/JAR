"""Speech-to-Text using Groq API (Whisper)."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class STTEngine:
    """Handles transcription of audio using Groq's Whisper API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the STT Engine.
        
        Args:
            api_key: Optional Groq API key. If not provided, it looks for GROQ_API_KEY env var.
        """
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        except ImportError:
            logger.error("Failed to import groq. Ensure it is installed.")
            raise
            
        self.model = "whisper-large-v3" # Fast Whisper model on Groq
        
    async def transcribe(self, audio_filepath: str) -> str:
        """Transcribe an audio file to text.
        
        Args:
            audio_filepath: Path to the audio file (e.g., .wav, .m4a).
            
        Returns:
            The transcribed text.
        """
        logger.info(f"Transcribing audio file: {audio_filepath}")
        
        if not os.path.exists(audio_filepath):
            raise FileNotFoundError(f"Audio file not found: {audio_filepath}")
            
        try:
            with open(audio_filepath, "rb") as file:
                transcription = await self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_filepath), file.read()),
                    model=self.model,
                    language="en",
                    response_format="text"
                )
            # The API returns the raw text when response_format="text"
            text = transcription.strip()
            logger.info(f"Transcription result: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise
