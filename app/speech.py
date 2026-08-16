"""
Speech-to-text via faster-whisper.

Model loads lazily on first use and is cached for the process lifetime
(loading is slow, ~seconds; keep it out of the request hot path after
the first call). Runs on CPU by default -- fine for short voice memos,
not tuned for long-form transcription.
"""
import logging
from functools import lru_cache

logger = logging.getLogger("memora.speech")

# "tiny" / "base" / "small" - tradeoff between speed and accuracy.
# "base" is a reasonable default for short voice commands.
WHISPER_MODEL_SIZE = "base"


class TranscriptionError(RuntimeError):
    """Raised when audio transcription fails."""


@lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel

    logger.info("Loading faster-whisper model (%s) - first call only", WHISPER_MODEL_SIZE)
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio_path: str) -> str:
    """
    audio_path: path to a local audio file (wav/mp3/m4a/etc).
    Returns the transcribed text. Raises TranscriptionError on failure.
    """
    try:
        model = _get_model()
        segments, _info = model.transcribe(audio_path)
        text = " ".join(segment.text.strip() for segment in segments)
    except Exception as exc:  # faster-whisper doesn't expose a narrow exception type
        logger.exception("Transcription failed")
        raise TranscriptionError(str(exc)) from exc

    if not text.strip():
        raise TranscriptionError("No speech detected in audio")
    return text.strip()
