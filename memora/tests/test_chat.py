"""
Chat endpoint tests.

The LLM call and memory extraction are mocked throughout - these test
FastAPI routing, conversation/message persistence, and error handling,
not the real Groq/Anthropic API or extraction quality. A real API key
is only needed for manual end-to-end smoke testing (see README).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_memora.db"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.database import Base, engine
from app.main import app
from app.llm import LLMError
from app.memory_extraction import MemoryExtraction, ExtractionError

client = TestClient(app)

IGNORE_RESULT = MemoryExtraction(action="IGNORE")


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"] or "malloc()" in resp.text


def test_api_info():
    resp = client.get("/api")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "docs" in data


@patch("app.routers.chat.extract_memory", return_value=IGNORE_RESULT)
@patch("app.routers.chat.call_llm", return_value="Hi there!")
def test_chat_creates_conversation(mock_llm, mock_extract):
    resp = client.post("/chat", json={"user_external_id": "u1", "message": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Hi there!"
    assert body["conversation_id"]
    mock_llm.assert_called_once()


@patch("app.routers.chat.extract_memory", return_value=IGNORE_RESULT)
@patch("app.routers.chat.call_llm", return_value="second reply")
def test_chat_continues_conversation(mock_llm, mock_extract):
    first = client.post("/chat", json={"user_external_id": "u2", "message": "first"})
    conv_id = first.json()["conversation_id"]

    second = client.post(
        "/chat",
        json={"user_external_id": "u2", "conversation_id": conv_id, "message": "second"},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conv_id

    history = client.get(f"/chat/{conv_id}")
    assert history.status_code == 200
    roles = [m["role"] for m in history.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_chat_unknown_conversation_returns_404():
    resp = client.post(
        "/chat",
        json={"user_external_id": "u3", "conversation_id": "does-not-exist", "message": "hi"},
    )
    assert resp.status_code == 404


@patch("app.routers.chat.call_llm", side_effect=LLMError("simulated outage"))
def test_chat_llm_failure_returns_502(mock_llm):
    resp = client.post("/chat", json={"user_external_id": "u4", "message": "hello"})
    assert resp.status_code == 502
    # user message should not be orphaned without a matching assistant reply
    # in a broken state — conversation should simply not have advanced.


def test_get_missing_conversation_404():
    resp = client.get("/chat/nonexistent-id")
    assert resp.status_code == 404


@patch("app.routers.chat.extract_memory")
@patch("app.routers.chat.call_llm", return_value="Got it, noted.")
def test_chat_store_action_creates_memory(mock_llm, mock_extract):
    mock_extract.return_value = MemoryExtraction(
        action="STORE",
        memory_type="semantic",
        content="User prefers Python for backend development",
        importance=0.8,
        confidence=0.9,
    )
    resp = client.post(
        "/chat", json={"user_external_id": "u5", "message": "I always use Python for backends"}
    )
    assert resp.status_code == 200

    memories = client.get("/memories/u5")
    assert memories.status_code == 200
    body = memories.json()
    assert len(body) == 1
    assert body[0]["content"] == "User prefers Python for backend development"
    assert body[0]["memory_type"] == "semantic"


@patch("app.routers.chat.extract_memory", return_value=IGNORE_RESULT)
@patch("app.routers.chat.call_llm", return_value="Enjoy!")
def test_chat_ignore_action_stores_nothing(mock_llm, mock_extract):
    resp = client.post("/chat", json={"user_external_id": "u6", "message": "I'm drinking coffee"})
    assert resp.status_code == 200

    memories = client.get("/memories/u6")
    assert memories.status_code == 200
    assert memories.json() == []


@patch("app.routers.chat.extract_memory", side_effect=ExtractionError("simulated extraction failure"))
@patch("app.routers.chat.call_llm", return_value="Sure, here you go.")
def test_chat_succeeds_even_if_extraction_fails(mock_llm, mock_extract):
    """The core rule: a broken extractor must never break the chat response."""
    resp = client.post("/chat", json={"user_external_id": "u7", "message": "anything"})
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Sure, here you go."


def test_memories_empty_for_unknown_user():
    resp = client.get("/memories/no-such-user")
    assert resp.status_code == 200
    assert resp.json() == []


@patch("app.routers.chat.extract_memory")
@patch("app.routers.chat.call_llm", return_value="Noted.")
def test_edit_and_delete_memory(mock_llm, mock_extract):
    mock_extract.return_value = MemoryExtraction(
        action="STORE",
        memory_type="semantic",
        content="Original fact about user",
        importance=0.5,
        confidence=0.8,
    )
    client.post("/chat", json={"user_external_id": "u-edit", "message": "Remember this"})
    memories = client.get("/memories/u-edit").json()
    assert len(memories) == 1
    mem_id = memories[0]["id"]

    # Edit memory
    patch_resp = client.patch(f"/memories/{mem_id}", json={
        "content": "Updated fact about user",
        "importance": 0.9
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["content"] == "Updated fact about user"
    assert patch_resp.json()["importance"] == 0.9

    # Delete memory
    del_resp = client.delete(f"/memories/{mem_id}")
    assert del_resp.status_code == 204

    # Verify deleted
    assert client.get("/memories/u-edit").json() == []

