from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import tempfile
from src.services.transcription_service import get_transcription_service

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Endpoint to transcribe uploaded audio files using local Whisper model.
    """
    try:
        # Create a temporary file to save the uploaded audio
        suffix = os.path.splitext(file.filename)[1] or ".webm"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Call the service
        service = get_transcription_service()
        transcription_text = service.transcribe(tmp_path)
        
        return {"text": transcription_text}

    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up the temp file
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)