"""
ORM models.

Conversation history and long-term memory are architecturally separate
systems (see README). users/conversations/messages hold conversation
history. Memory (this file's Memory class, added Day 2) is a distinct,
much smaller table: only durable facts the extractor decided to STORE,
never the raw conversation.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    external_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=_now)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)

    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    """
    A durable fact extracted from conversation, per Day 2's extraction
    step. NOT the same as a Message - this table is meant to stay
    small and curated, one row per distinct fact worth remembering.

    status stays simple for now ("active" only). HISTORICAL/ACTIVE
    temporal tracking and conflict resolution (UPDATE/SUPERSEDE) are a
    later stage - don't add those columns before that logic exists to
    use them.
    """

    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    memory_type = Column(String, nullable=False)  # "semantic" | "episodic" | "temporal"
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="active")
    source_conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User")


class JobApplication(Base):
    """
    One row per job applied to. Reminders/reports (later features) read
    from this table rather than being separate stores - keep this one
    table as the single source of truth for application status.

    status is a plain string, not an enum column, to keep this DB
    portable and migrations simple - validate allowed values in the
    Pydantic schema layer instead (app/schemas.py), not here.
    """

    __tablename__ = "job_applications"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    company = Column(String, nullable=False)
    role_title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="applied")
    # "applied" | "interview" | "offer" | "rejected" | "no_response"
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    applied_date = Column(DateTime, nullable=False)
    follow_up_date = Column(DateTime, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    match_score = Column(Float, nullable=True)
    tailored_pitch = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User")


class UserResume(Base):
    """
    Persists user resumes. Supports multiple named resumes per user
    (e.g., Full Stack, AI/ML, DevOps) with a primary active flag.
    """
    __tablename__ = "user_resumes"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Master Resume")
    file_name = Column(String, nullable=True)
    resume_text = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User")


class JobMatch(Base):
    """
    Stores comparison and match analysis between a user's resume and a job description.
    """
    __tablename__ = "job_matches"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_url = Column(String, nullable=True)
    company = Column(String, nullable=True)
    role_title = Column(String, nullable=True)
    job_description = Column(Text, nullable=False)
    match_score = Column(Float, nullable=False)  # 0 to 100
    verdict = Column(String, nullable=False)     # "Strong Match", etc.
    analysis_json = Column(Text, nullable=False) # Full structured JSON string
    created_at = Column(DateTime, default=_now)

    user = relationship("User")


class UserGmailToken(Base):
    """
    Stores OAuth2 credentials for Gmail API access.
    Scope is strictly restricted to 'https://www.googleapis.com/auth/gmail.send'
    (send-only access, no read or mailbox modification permissions).
    """
    __tablename__ = "user_gmail_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scopes = Column(String, nullable=False, default="https://www.googleapis.com/auth/gmail.send")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User")
