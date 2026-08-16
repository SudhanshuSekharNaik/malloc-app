import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm import call_llm, LLMError
from app.memory_extraction import extract_memory, ExtractionError
from app.models import User, Conversation, Message, Memory
from app.schemas import ChatRequest, ChatResponse, ConversationOut

logger = logging.getLogger("memora.chat")
router = APIRouter(prefix="/chat", tags=["chat"])


def _get_or_create_user(db: Session, external_id: str) -> User:
    user = db.query(User).filter(User.external_id == external_id).first()
    if user is None:
        user = User(external_id=external_id)
        db.add(user)
        db.flush()
    return user


def _get_or_create_conversation(db: Session, user: User, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
            .first()
        )
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found for this user")
        return conv

    conv = Conversation(user_id=user.id)
    db.add(conv)
    db.flush()
    return conv


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    user = _get_or_create_user(db, payload.user_external_id)
    conversation = _get_or_create_conversation(db, user, payload.conversation_id)

    user_message = Message(conversation_id=conversation.id, role="user", content=payload.message)
    db.add(user_message)
    db.flush()

    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    ]

    try:
        reply_text = call_llm(history)
    except LLMError as exc:
        db.rollback()
        logger.error("Chat request failed: %s", exc)
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable") from exc

    assistant_message = Message(conversation_id=conversation.id, role="assistant", content=reply_text)
    db.add(assistant_message)
    db.commit()

    _try_extract_and_store_memory(db, user, conversation, payload.message, reply_text)

    return ChatResponse(conversation_id=conversation.id, reply=reply_text)


def _try_extract_and_store_memory(
    db: Session, user: User, conversation: Conversation, user_message: str, assistant_reply: str
) -> None:
    """
    Best-effort. Extraction failures are logged and swallowed - the
    chat response has already been returned to the user by the time
    this runs, and it must never turn a successful chat turn into a
    failed request.
    """
    try:
        result = extract_memory(user_message, assistant_reply)
    except ExtractionError as exc:
        logger.warning("Memory extraction skipped: %s", exc)
        return

    if result.action != "STORE":
        return
    if not result.content or result.memory_type is None:
        logger.warning("Extractor said STORE but content/memory_type missing: %s", result)
        return

    memory = Memory(
        user_id=user.id,
        memory_type=result.memory_type,
        content=result.content,
        importance=result.importance if result.importance is not None else 0.5,
        confidence=result.confidence if result.confidence is not None else 0.5,
        source_conversation_id=conversation.id,
    )
    db.add(memory)
    db.commit()
    logger.info("Stored memory for user %s: %s", user.external_id, result.content)


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv
