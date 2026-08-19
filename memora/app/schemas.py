from datetime import datetime
from typing import Optional, Literal, Any, List, Dict

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_external_id: str = Field(..., description="Caller-supplied stable ID for the user")
    conversation_id: Optional[str] = Field(
        None, description="Existing conversation to continue. Omit to start a new one."
    )
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryOut(BaseModel):
    id: str
    memory_type: str
    content: str
    importance: float
    confidence: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class ConversationOut(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    messages: list[MessageOut]

    model_config = {"from_attributes": True}


JobStatus = Literal["applied", "interview", "offer", "rejected", "no_response"]


class JobApplicationCreate(BaseModel):
    user_external_id: str
    company: str = Field(..., min_length=1, max_length=200)
    role_title: str = Field(..., min_length=1, max_length=200)
    status: JobStatus = "applied"
    job_url: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=4000)
    match_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    tailored_pitch: Optional[str] = Field(None, max_length=4000)
    applied_date: Optional[datetime] = None  # defaults to now if omitted
    follow_up_days: int = Field(7, ge=1, le=90, description="Days after applied_date to remind for follow-up")


class JobApplicationUpdate(BaseModel):
    """All fields optional - only send what's changing."""
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    role_title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[JobStatus] = None
    job_url: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=4000)
    match_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    tailored_pitch: Optional[str] = Field(None, max_length=4000)
    follow_up_date: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None


class JobApplicationOut(BaseModel):
    id: str
    company: str
    role_title: str
    status: str
    job_url: Optional[str]
    notes: Optional[str]
    match_score: Optional[float] = None
    tailored_pitch: Optional[str] = None
    applied_date: datetime
    follow_up_date: Optional[datetime]
    last_contact_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeCreate(BaseModel):
    user_external_id: str
    title: str = Field("Master Resume", min_length=1, max_length=100)
    file_name: Optional[str] = None
    resume_text: str = Field(..., min_length=1)
    is_primary: bool = False


class ResumeOut(BaseModel):
    id: str
    title: str
    file_name: Optional[str]
    resume_text: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SuggestEditsRequest(BaseModel):
    user_external_id: str
    resume_text: Optional[str] = None
    job_description: str
    company: Optional[str] = None
    role_title: Optional[str] = None


class ResumeEditSuggestionOut(BaseModel):
    type: str  # "bullet_rewrite" | "missing_keyword" | "grammar_fix"
    section: str
    original: Optional[str] = None
    suggested: str
    reason: str
    flagged_for_review: bool = False
    warning_message: Optional[str] = None


class SuggestEditsOut(BaseModel):
    suggestions: list[ResumeEditSuggestionOut]
    unavailable_layers: list[str] = []


# ============================================================================
# Company Insights Models
# ============================================================================

class CompanyInsightsRequest(BaseModel):
    company: Optional[str] = None
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    url: Optional[str] = None
    about_text: Optional[str] = None
    role_title: Optional[str] = None
    role_hint: Optional[str] = None
    user_external_id: Optional[str] = None


class CompanyFactsOut(BaseModel):
    employee_count_estimate: str = "unknown"
    founded_year: Optional[int] = None


class CompanyClassificationOut(BaseModel):
    label: str
    confidence: float
    all_scores: dict[str, float]
    industry: Optional[str] = None
    industry_confidence: Optional[float] = None
    facts: CompanyFactsOut
    disagreement_flag: bool = False
    low_confidence_data: bool = False
    data_quality_note: Optional[str] = None
    url_mismatch_warning: Optional[str] = None


class SentimentBreakdownOut(BaseModel):
    positive_count: int = 0
    negative_count: int = 0
    total: int = 0
    signal_strength: str = "moderate"  # "low" | "moderate" | "high"
    signal_strength_note: Optional[str] = None


class CultureSynthesisOut(BaseModel):
    status: str = "available"
    sentiment_breakdown: SentimentBreakdownOut
    praised_aspects: list[str] = []
    criticized_aspects: list[str] = []


class InterviewInsightsOut(BaseModel):
    focus_areas: list[str] = []
    process_stages: list[str] = []
    prep_tips: list[str] = []


class InterviewPrepOut(BaseModel):
    technical_focus_areas: list[str] = []
    behavioral_focus_areas: list[str] = []
    suggested_questions_to_ask: list[str] = []


class CompanyInsightsOut(BaseModel):
    company: Optional[str] = None
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    classification: CompanyClassificationOut
    culture_synthesis: CultureSynthesisOut
    interview_insights: Optional[InterviewInsightsOut] = None
    interview_prep: Optional[InterviewPrepOut] = None
    summary: Optional[str] = None
    url_mismatch_warning: Optional[str] = None
    generated_at: Optional[str] = None


# ============================================================================
# Outreach & Apply via Email Models
# ============================================================================

class ParsedRoleOption(BaseModel):
    role_title: str
    experience_level: Optional[str] = None
    primary_skills: list[str] = []
    location: Optional[str] = None
    employment_type: Optional[str] = None  # Full-time, Internship, etc.


class ParsedJDSchema(BaseModel):
    company_name: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    hr_email: Optional[str] = None
    open_positions: list[str] = []
    roles: list[Any] = []
    experience_required: Optional[str] = None
    working_days: Optional[str] = None
    contact_phone: Optional[str] = None
    raw_text: Optional[str] = None
    overall_skills_required: list[str] = []
    application_deadline: Optional[str] = None
    is_informal: bool = False
    extraction_confidence: str = "high"  # "high" | "moderate" | "low"
    recommended_role: Optional[str] = None
    recommendation_reason: Optional[str] = None


class ParseJDRequest(BaseModel):
    text: Optional[str] = None
    raw_text: Optional[str] = None
    job_text: Optional[str] = None
    job_description: Optional[str] = None
    url: Optional[str] = None
    job_url: Optional[str] = None
    user_external_id: Optional[str] = None
    resume_id: Optional[str] = None


class ParseJDResponse(BaseModel):
    parsed: ParsedJDSchema
    raw_text_length: int = 0


class FabricationFlag(BaseModel):
    term: str
    reason: str
    snippet: str


class DraftEmailRequest(BaseModel):
    user_external_id: Optional[str] = None
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None
    selected_role: str
    parsed_jd: ParsedJDSchema
    applicant_name: Optional[str] = None
    custom_instructions: Optional[str] = None


class DraftEmailResponse(BaseModel):
    subject: str
    body: str
    recipient: Optional[str] = None
    selected_role: str
    company_name: Optional[str] = None
    flagged_fabrications: list[FabricationFlag] = []
    cliches_detected: list[str] = []
    ai_detector_score: Optional[float] = None
    ai_detector_note: Optional[str] = None


class GmailAuthStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None
    scopes: Optional[str] = None
    auth_url: Optional[str] = None
    configured: bool = True
    config_note: Optional[str] = None


class SendEmailRequest(BaseModel):
    user_external_id: str
    to_email: str
    subject: str
    body: str
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    attach_resume_id: Optional[str] = None
    log_to_tracker: bool = True


class SendEmailResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    timestamp: str
    recipient: str
    subject: str
    job_application_id: Optional[str] = None
    detail: Optional[str] = None


