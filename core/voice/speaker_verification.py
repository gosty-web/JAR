"""Speaker Verification client via AWS-hosted SpeechBrain."""

import os
import logging
import json
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

class SpeakerVerifier:
    """Client for checking audio against the AWS SpeechBrain microservice."""
    
    def __init__(self, endpoint_url: Optional[str] = None):
        """Initialize the Speaker Verifier.
        
        Args:
            endpoint_url: The AWS API Gateway URL. If None, looks for SPEECHBRAIN_URL env var.
        """
        self.endpoint_url = endpoint_url or os.getenv("SPEECHBRAIN_URL")
        
        if not self.endpoint_url:
            logger.warning("No SPEECHBRAIN_URL provided. Speaker verification will be mocked to always succeed.")
            
    async def verify(self, audio_filepath: str, reference_filepath: Optional[str] = None) -> bool:
        """Verify if the audio matches the registered user's voiceprint.
        
        Args:
            audio_filepath: Path to the recorded audio.
            reference_filepath: Optional reference audio (normally the server has it cached).
            
        Returns:
            True if verified, False otherwise.
        """
        if not self.endpoint_url:
            # Mock success for local dev without AWS
            logger.info("Mocking successful speaker verification (No endpoint configured).")
            return True
            
        if not os.path.exists(audio_filepath):
            logger.error(f"Audio file not found: {audio_filepath}")
            return False
            
        logger.info(f"Sending audio to SpeechBrain for verification: {audio_filepath}")
        
        try:
            async with httpx.AsyncClient() as client:
                files = {'file': open(audio_filepath, 'rb')}
                if reference_filepath and os.path.exists(reference_filepath):
                    files['reference'] = open(reference_filepath, 'rb')
                    
                response = await client.post(
                    f"{self.endpoint_url}/verify",
                    files=files,
                    timeout=5.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Assume the API returns {"match": true, "score": 0.85}
                match = result.get("match", False)
                score = result.get("score", 0.0)
                
                logger.info(f"Speaker verification result: {match} (score: {score:.3f})")
                return match
                
        except Exception as e:
            logger.error(f"Speaker verification failed: {e}")
            return False
