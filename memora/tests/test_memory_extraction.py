"""
Unit tests for the extraction module itself, independent of the chat
endpoint. The LLM call is mocked - these test the parsing/validation
logic, not real model output quality (that needs a real API key and
manual review, per the eventual Day-12 evaluation harness).
"""
from unittest.mock import patch

import pytest

from app.memory_extraction import extract_memory, ExtractionError, MemoryExtraction


@patch("app.memory_extraction.call_llm")
def test_extract_store_valid_json(mock_llm):
    mock_llm.return_value = (
        '{"action": "STORE", "memory_type": "semantic", '
        '"content": "User prefers Python for backend development", '
        '"importance": 0.8, "confidence": 0.9}'
    )
    result = extract_memory("I always use Python for backends", "Got it, noted.")
    assert isinstance(result, MemoryExtraction)
    assert result.action == "STORE"
    assert result.memory_type == "semantic"
    assert result.content == "User prefers Python for backend development"


@patch("app.memory_extraction.call_llm")
def test_extract_ignore(mock_llm):
    mock_llm.return_value = '{"action": "IGNORE", "memory_type": null, "content": null, "importance": null, "confidence": null}'
    result = extract_memory("I'm drinking coffee right now", "Enjoy!")
    assert result.action == "IGNORE"
    assert result.content is None


@patch("app.memory_extraction.call_llm")
def test_extract_strips_markdown_fences(mock_llm):
    mock_llm.return_value = (
        '```json\n{"action": "STORE", "memory_type": "semantic", '
        '"content": "test fact", "importance": 0.5, "confidence": 0.5}\n```'
    )
    result = extract_memory("some message", "some reply")
    assert result.action == "STORE"
    assert result.content == "test fact"


@patch("app.memory_extraction.call_llm")
def test_extract_invalid_json_raises(mock_llm):
    mock_llm.return_value = "not json at all"
    with pytest.raises(ExtractionError):
        extract_memory("hi", "hello")


@patch("app.memory_extraction.call_llm")
def test_extract_schema_violation_raises(mock_llm):
    # "action" must be STORE or IGNORE - "MAYBE" should fail validation
    mock_llm.return_value = '{"action": "MAYBE", "memory_type": null, "content": null, "importance": null, "confidence": null}'
    with pytest.raises(ExtractionError):
        extract_memory("hi", "hello")


@patch("app.memory_extraction.call_llm")
def test_extract_llm_failure_raises(mock_llm):
    from app.llm import LLMError

    mock_llm.side_effect = LLMError("simulated outage")
    with pytest.raises(ExtractionError):
        extract_memory("hi", "hello")
