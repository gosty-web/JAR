"""Tests for the Voice Modules."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.voice.stt import STTEngine
from core.voice.tts import TTSEngine

async def test_modules():
    print("Testing TTS module...")
    tts = TTSEngine()
    # If the user hasn't downloaded weights yet, this will just log a warning and skip
    tts.speak("Hello, this is a test of the text to speech engine.")
    print("TTS module test completed.")

    print("\nTesting STT module...")
    # This requires GROQ_API_KEY to be set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set. Skipping real STT test.")
    else:
        stt = STTEngine()
        # In a real test, we'd provide a sample WAV file.
        print("STT Engine initialized.")

if __name__ == "__main__":
    asyncio.run(test_modules())
