"""
Thin LLM client wrapper.

A single call_llm() function that takes message history and returns a
reply. No tools, no agent graph yet - those come in a later stage.
Keeping this isolated is what lets a future LangGraph agent swap in
without touching the rest of the app.

call_llm() accepts an optional system prompt override so the same
wrapper serves both plain chat (app/main system prompt) and memory
extraction (app/memory_extraction's own system prompt) without
duplicating provider logic.

Two providers are supported:
- "groq"      - free, no billing setup, OpenAI-compatible API. Default,
                good for getting the MVP running without billing setup.
- "anthropic" - requires a funded console.anthropic.com account.
                Switch to this later by setting LLM_PROVIDER=anthropic.
"""
import logging

from app.config import settings

logger = logging.getLogger("memora.llm")

CHAT_SYSTEM_PROMPT = (
    "You are malloc(), a helpful personal assistant. "
    "In this stage you have no long-term memory yet - "
    "answer only from the current conversation."
)


class LLMError(RuntimeError):
    """Raised when the LLM call fails after retries are exhausted."""


def _call_groq(history: list[dict], model: str | None, system: str) -> str:
    import os
    from groq import Groq, GroqError, RateLimitError

    api_key = (
        settings.groq_api_key 
        or os.environ.get("GROQ_API_KEY") 
        or "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"
    ).strip()

    if not api_key:
        raise LLMError(
            "GROQ_API_KEY is not configured. Get a free key at "
            "https://console.groq.com/keys and configure it in Settings or .env"
        )

    client = Groq(api_key=api_key)
    messages = [{"role": "system", "content": system}] + history

    # Candidate models to try in order on rate limits
    primary = model or settings.groq_model or "llama-3.1-8b-instant"
    candidate_models = [primary]
    for fallback in ["llama-3.1-8b-instant", "gemma2-9b-it", "llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_error = None
    for cand_model in candidate_models:
        try:
            response = client.chat.completions.create(
                model=cand_model,
                messages=messages,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if content:
                return content
        except RateLimitError as exc:
            logger.warning("Groq RateLimitError on model %s: %s. Trying next candidate model...", cand_model, exc)
            last_error = exc
            continue
        except GroqError as exc:
            logger.exception("Groq API call failed on model %s: %s", cand_model, exc)
            raise LLMError(str(exc)) from exc

    if last_error:
        raise LLMError(f"All Groq models exceeded rate limits: {last_error}") from last_error
    raise LLMError("LLM returned no text content")


def _call_anthropic(history: list[dict], model: str | None, system: str) -> str:
    import anthropic

    if not settings.anthropic_api_key:
        raise LLMError(
            "ANTHROPIC_API_KEY is not configured. Create one at "
            "https://console.anthropic.com/settings/keys (requires billing)"
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=model or settings.memora_model,
            max_tokens=1024,
            system=system,
            messages=history,
        )
    except anthropic.APIError as exc:
        logger.exception("Anthropic API call failed")
        raise LLMError(str(exc)) from exc

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise LLMError("LLM returned no text content")
    return "".join(text_blocks)


def call_llm(history: list[dict], model: str | None = None, system: str | None = None) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}, oldest first.
    system: optional system prompt override (defaults to the chat persona).
            Memory extraction passes its own extraction-specific prompt.
    Returns the assistant's reply text.
    Raises LLMError on failure - callers turn this into an HTTP 502 (chat)
    or log-and-skip (extraction - see app/memory_extraction.py).
    """
    system = system or CHAT_SYSTEM_PROMPT

    if settings.llm_provider == "groq":
        return _call_groq(history, model, system)
    elif settings.llm_provider == "anthropic":
        return _call_anthropic(history, model, system)
    else:
        raise LLMError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r} (use 'groq' or 'anthropic')")
