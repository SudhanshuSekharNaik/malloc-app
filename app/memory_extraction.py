"""
Day 2: memory extraction.

After each chat turn, ask the LLM whether anything in it is worth
remembering long-term, and get back structured JSON validated by
Pydantic (per the engineering rule: validate structured LLM output,
never let the LLM directly execute a DB mutation - this module only
returns a validated decision; app/routers/chat.py decides what to do
with it).

Failure mode: if extraction fails (bad JSON, LLM error, whatever),
that must NEVER break the chat response the user is waiting on. Every
call site treats extraction as best-effort and logs-and-continues on
failure. This is why extraction happens AFTER the chat reply is
already generated and returned to the request, not before.
"""
import json
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from app.llm import call_llm, LLMError

logger = logging.getLogger("memora.memory_extraction")

EXTRACTION_SYSTEM_PROMPT = """You extract durable, worth-remembering facts from a single \
conversation turn for a personal AI assistant called malloc().

Rules:
- Only extract facts that would still be useful to know in future, unrelated conversations \
(preferences, identity facts, ongoing projects, commitments, relationships).
- Do NOT extract small talk, one-off statements with no future relevance, or anything already \
obvious from context (e.g. "I am drinking coffee" -> IGNORE).
- Do NOT fabricate anything not actually stated by the user.
- If nothing worth storing is present, action must be IGNORE and content must be null.
- Respond with ONLY a single JSON object, no markdown fences, no explanation, matching exactly:

{"action": "STORE" | "IGNORE", "memory_type": "semantic" | "episodic" | "temporal" | null, \
"content": string | null, "importance": number between 0 and 1 | null, \
"confidence": number between 0 and 1 | null}

memory_type guide: "semantic" = general fact/preference (e.g. "prefers Python"), \
"episodic" = a specific event (e.g. "interviewed at Company X on a date"), \
"temporal" = a fact with a validity window (e.g. "currently interning at Company Y").
"""


class MemoryExtraction(BaseModel):
    action: Literal["STORE", "IGNORE"]
    memory_type: Optional[Literal["semantic", "episodic", "temporal"]] = None
    content: Optional[str] = Field(default=None, max_length=2000)
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ExtractionError(RuntimeError):
    """Raised when extraction fails. Callers should catch, log, and continue."""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


def extract_memory(user_message: str, assistant_reply: str) -> MemoryExtraction:
    """
    Runs one extraction call over a single chat turn.
    Raises ExtractionError on any failure (LLM call, bad JSON, schema
    mismatch) - callers must catch this and continue without storing
    anything, per the "extraction never breaks chat" rule.
    """
    turn_text = f"User: {user_message}\nAssistant: {assistant_reply}"

    try:
        raw = call_llm(
            history=[{"role": "user", "content": turn_text}],
            system=EXTRACTION_SYSTEM_PROMPT,
        )
    except LLMError as exc:
        raise ExtractionError(f"LLM call failed: {exc}") from exc

    cleaned = _strip_code_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Model did not return valid JSON: {raw!r}") from exc

    try:
        return MemoryExtraction.model_validate(parsed)
    except ValidationError as exc:
        raise ExtractionError(f"Extraction JSON failed schema validation: {exc}") from exc
