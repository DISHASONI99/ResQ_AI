"""
Transcription Service - Audio to Text using OpenAI Whisper
"""
import logging
import os
from typing import BinaryIO, Union
import whisper
import torch

MODEL_SIZE = "base"  # "tiny", "base", "small", "medium", "large"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Service for transcribing audio files using OpenAI Whisper locally.
    """

    def __init__(self):
        logger.info(f"Loading OpenAI Whisper model: {MODEL_SIZE} on {DEVICE}...")
        try:
            self._model = whisper.load_model(MODEL_SIZE, device=DEVICE)
            logger.info("OpenAI Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e

    @property
    def model(self):
        """Return the preloaded model."""
        return self._model

    def transcribe(self, audio_file: Union[str, BinaryIO]) -> str:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_file: Path to file (str). 
            
        Returns:
            str: The transcribed text.
        """
        try:
            # OpenAI Whisper's transcribe method handles loading and processing
            result = self.model.transcribe(audio_file, fp16=False)
            
            text = result.get("text", "").strip()
            logger.info(f"Transcription complete: {len(text)} chars")
            return text

        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise e

# Singleton instance
_transcription_service = None

def get_transcription_service() -> TranscriptionService:
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service