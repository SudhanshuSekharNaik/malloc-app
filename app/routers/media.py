"""
Endpoints for non-text input: voice transcription and image captioning.

Both take an uploaded file, save it to a temp path, run the relevant
model, and return text. Callers (e.g. the Streamlit frontend) are
expected to feed that text into the existing /chat endpoint themselves
-- these routes do NOT call the LLM. Keeping transcription/captioning
separate from the chat flow means either can be tested and swapped
independently.
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.speech import transcribe, TranscriptionError
from app.vision import caption_image, CaptionError

logger = logging.getLogger("memora.media")
router = APIRouter(prefix="/media", tags=["media"])


def _save_upload(upload: UploadFile, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.file.read())
        return tmp.name


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    tmp_path = _save_upload(file, suffix)
    try:
        text = transcribe(tmp_path)
    except TranscriptionError as exc:
        logger.error("Transcription request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Transcription failed") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"text": text}


@router.post("/caption")
async def caption_uploaded_image(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    tmp_path = _save_upload(file, suffix)
    try:
        caption = caption_image(tmp_path)
    except CaptionError as exc:
        logger.error("Captioning request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Image captioning failed") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"caption": caption}
