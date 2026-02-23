"""
Whisper Service - Audio transcription for emergency calls

Uses Groq Whisper API for fast, free transcription.
Fallback: Returns placeholder if API fails.
"""
import os
import httpx
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribe audio using Groq Whisper API.
    
    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename (for format detection)
        
    Returns:
        Transcribed text, or error message if failed
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        logger.warning("GROQ_API_KEY not set, audio transcription unavailable")
        return "[Audio transcription unavailable - no API key]"
    
    try:
        # Determine content type from filename
        ext = Path(filename).suffix.lower()
        content_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".webm": "audio/webm",
        }
        content_type = content_types.get(ext, "audio/wav")
        
        # Prepare multipart form data
        files = {
            "file": (filename, audio_bytes, content_type),
            "model": (None, "whisper-large-v3"),
            "language": (None, "en"),
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("text", "").strip()
                logger.info(f"✅ Audio transcribed: {transcript[:50]}...")
                return transcript
            else:
                logger.error(f"Whisper API error: {response.status_code} - {response.text}")
                return f"[Audio transcription failed: {response.status_code}]"
                
    except httpx.TimeoutException:
        logger.error("Whisper API timeout")
        return "[Audio transcription timeout]"
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        return f"[Audio transcription error: {str(e)}]"


async def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribe audio from a file path.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Transcribed text
    """
    path = Path(file_path)
    if not path.exists():
        return "[Audio file not found]"
    
    audio_bytes = path.read_bytes()
    return await transcribe_audio(audio_bytes, path.name)
