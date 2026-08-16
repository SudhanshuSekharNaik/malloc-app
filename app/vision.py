"""
Image-to-text via BLIP image captioning.

Same lazy-load-once pattern as speech.py. This gives a short natural-
language description of an image (e.g. "a person holding a coffee cup")
-- it is a caption model, not OCR. If you need to read text *in* an
image (receipts, screenshots), that is a different model
(e.g. microsoft/trocr) and a separate function; don't conflate the two.
"""
import logging
from functools import lru_cache

logger = logging.getLogger("memora.vision")

CAPTION_MODEL_NAME = "Salesforce/blip-image-captioning-base"


class CaptionError(RuntimeError):
    """Raised when image captioning fails."""


@lru_cache(maxsize=1)
def _get_pipeline():
    from transformers import pipeline

    logger.info("Loading image captioning model (%s) - first call only", CAPTION_MODEL_NAME)
    return pipeline("image-to-text", model=CAPTION_MODEL_NAME)


def caption_image(image_path: str) -> str:
    """
    image_path: path to a local image file.
    Returns a short caption describing the image's contents.
    Raises CaptionError on failure.
    """
    try:
        captioner = _get_pipeline()
        result = captioner(image_path)
    except Exception as exc:
        logger.exception("Image captioning failed")
        raise CaptionError(str(exc)) from exc

    if not result:
        raise CaptionError("Model returned no caption")
    return result[0]["generated_text"].strip()
