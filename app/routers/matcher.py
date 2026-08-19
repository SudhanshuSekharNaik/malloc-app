"""
Resume vs. Job Description Matcher Router.

Provides endpoints for:
- Fetching & extracting job postings from URLs (LinkedIn, Greenhouse, Lever, etc.)
- Uploading & parsing resume files (PDF, TXT)
- Master resume persistence per user
- AI Comparative scoring & analysis
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserResume, JobMatch
from app.services.scraper import fetch_job_from_url, ScrapedJob
from app.services.resume_parser import extract_resume_text, ResumeParseError
from app.services.job_matcher import analyze_resume_vs_job, MatchAnalysisResult, MatcherError

logger = logging.getLogger("memora.matcher.router")
router = APIRouter(prefix="/matcher", tags=["matcher"])


class FetchJobRequest(BaseModel):
    url: str


class AnalyzeRequest(BaseModel):
    user_external_id: str
    resume_text: Optional[str] = None
    job_description: str
    job_url: Optional[str] = None
    company: Optional[str] = None
    role_title: Optional[str] = None


from app.schemas import ResumeCreate, ResumeOut

class SaveResumeRequest(BaseModel):
    user_external_id: str
    title: str = "Master Resume"
    resume_text: str
    file_name: Optional[str] = "manual_entry.txt"
    is_primary: bool = False


def _get_or_create_user(db: Session, external_id: str) -> User:
    user = db.query(User).filter(User.external_id == external_id).first()
    if user is None:
        user = User(external_id=external_id)
        db.add(user)
        db.flush()
    return user


@router.post("/fetch-job", response_model=ScrapedJob)
def fetch_job(payload: FetchJobRequest):
    """
    Fetches job details from a given URL.
    """
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    return fetch_job_from_url(url)


@router.get("/resumes/{user_external_id}", response_model=list[ResumeOut])
def list_user_resumes(user_external_id: str, db: Session = Depends(get_db)) -> list[UserResume]:
    """
    Lists all saved resumes for the user.
    """
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if not user:
        return []
    return (
        db.query(UserResume)
        .filter(UserResume.user_id == user.id)
        .order_by(UserResume.updated_at.desc())
        .all()
    )


@router.post("/upload-resume")
async def upload_resume(
    user_external_id: str = Form(...),
    title: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads a resume file (PDF/TXT), extracts text, and saves it to user's resumes.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        resume_text = extract_resume_text(contents, file.filename or "resume.pdf")
    except ResumeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = _get_or_create_user(db, user_external_id)
    resume_title = title.strip() if title and title.strip() else (file.filename or "Master Resume")

    # If this is the user's first resume, mark as primary
    existing_count = db.query(UserResume).filter(UserResume.user_id == user.id).count()

    user_resume = UserResume(
        user_id=user.id,
        title=resume_title,
        file_name=file.filename,
        resume_text=resume_text,
        is_primary=(existing_count == 0)
    )
    db.add(user_resume)
    db.commit()
    db.refresh(user_resume)

    return {
        "status": "success",
        "id": user_resume.id,
        "title": user_resume.title,
        "file_name": file.filename,
        "char_count": len(resume_text),
        "preview": resume_text[:300] + ("..." if len(resume_text) > 300 else ""),
        "resume_text": resume_text
    }


@router.post("/save-resume")
def save_resume_text(payload: SaveResumeRequest, db: Session = Depends(get_db)):
    """
    Saves or updates user's resume text directly from an editor or text paste.
    """
    user = _get_or_create_user(db, payload.user_external_id)
    existing_count = db.query(UserResume).filter(UserResume.user_id == user.id).count()

    user_resume = UserResume(
        user_id=user.id,
        title=payload.title or "Master Resume",
        file_name=payload.file_name,
        resume_text=payload.resume_text,
        is_primary=(existing_count == 0 or payload.is_primary)
    )
    db.add(user_resume)
    db.commit()
    db.refresh(user_resume)

    return {
        "status": "saved",
        "id": user_resume.id,
        "title": user_resume.title,
        "char_count": len(payload.resume_text)
    }


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_user_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(UserResume).filter(UserResume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return None


@router.get("/resume/{user_external_id}")
def get_user_resume(user_external_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the user's primary or most recently updated master resume.
    """
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if not user:
        return {"has_resume": False, "resume_text": "", "file_name": None, "title": None}

    user_resume = (
        db.query(UserResume)
        .filter(UserResume.user_id == user.id)
        .order_by(UserResume.is_primary.desc(), UserResume.updated_at.desc())
        .first()
    )
    if not user_resume:
        return {"has_resume": False, "resume_text": "", "file_name": None, "title": None}

    return {
        "has_resume": True,
        "id": user_resume.id,
        "title": user_resume.title,
        "file_name": user_resume.file_name,
        "resume_text": user_resume.resume_text,
        "updated_at": user_resume.updated_at
    }


@router.post("/analyze", response_model=MatchAnalysisResult)
def analyze_match(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Compares candidate resume against job description and generates a match score + actionable breakdown.
    """
    user = _get_or_create_user(db, payload.user_external_id)

    resume_text = payload.resume_text
    if not resume_text or not resume_text.strip():
        user_resume = db.query(UserResume).filter(UserResume.user_id == user.id).first()
        if not user_resume or not user_resume.resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No resume provided and no saved resume found. Please upload or paste your resume."
            )
        resume_text = user_resume.resume_text

    try:
        result = analyze_resume_vs_job(
            resume_text=resume_text,
            job_description=payload.job_description,
            company_hint=payload.company,
            role_hint=payload.role_title
        )
    except MatcherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Persist match record
    match_record = JobMatch(
        user_id=user.id,
        job_url=payload.job_url,
        company=result.company or payload.company,
        role_title=result.role_title or payload.role_title,
        job_description=payload.job_description[:4000],
        match_score=float(result.match_score),
        verdict=result.verdict,
        analysis_json=result.model_dump_json()
    )
    db.add(match_record)
    db.commit()

    return result


from app.schemas import SuggestEditsRequest, SuggestEditsOut
from app.services.resume_editor import generate_resume_edits

@router.post("/suggest-edits", response_model=SuggestEditsOut)
def suggest_resume_edits(payload: SuggestEditsRequest, db: Session = Depends(get_db)):
    """
    Generates actionable, opt-in resume edits (bullet rewrites, evidenced keyword surfacing, grammar polish)
    with strict programmatic fabrication validation.
    """
    user = _get_or_create_user(db, payload.user_external_id)

    resume_text = payload.resume_text
    if not resume_text or not resume_text.strip():
        user_resume = db.query(UserResume).filter(UserResume.user_id == user.id).first()
        if not user_resume or not user_resume.resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No resume provided and no saved resume found. Please upload or paste your resume."
            )
        resume_text = user_resume.resume_text

    try:
        result = generate_resume_edits(
            resume_text=resume_text,
            job_description=payload.job_description,
            company_hint=payload.company,
            role_hint=payload.role_title
        )
        return result
    except Exception as exc:
        logger.error("Error generating resume edits: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

