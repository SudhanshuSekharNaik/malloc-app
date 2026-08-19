"""
ATS (Applicant Tracking System) Checker Router.

Provides endpoints for auditing a resume's parseability, formatting,
and structural compatibility with ATS ingestion engines.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserResume
from app.services.resume_parser import extract_resume_text, ResumeParseError
from app.services.ats_checker import (
    calculate_ats_audit,
    ATSCheckResult,
    ATSCheckItem
)

logger = logging.getLogger("memora.ats.router")
router = APIRouter(prefix="/ats", tags=["ats"])


class ATSCheckRequest(BaseModel):
    user_external_id: Optional[str] = None
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None
    file_name: Optional[str] = "resume.pdf"


@router.post("/check", response_model=ATSCheckResult)
def check_ats(payload: ATSCheckRequest, db: Session = Depends(get_db)):
    """
    Audits resume parseability, formatting structure, and entity signals.
    Accepts raw resume text or a saved resume_id reference.
    """
    resume_text = payload.resume_text
    file_name = payload.file_name or "resume.pdf"

    # If resume_id is provided, fetch from database
    if payload.resume_id:
        saved_resume = db.query(UserResume).filter(UserResume.id == payload.resume_id).first()
        if not saved_resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved resume not found")
        resume_text = saved_resume.resume_text
        file_name = saved_resume.file_name or saved_resume.title or "resume.pdf"
    elif payload.user_external_id and not resume_text:
        user = db.query(User).filter(User.external_id == payload.user_external_id).first()
        if user:
            saved_resume = db.query(UserResume).filter(UserResume.user_id == user.id).order_by(UserResume.is_primary.desc(), UserResume.updated_at.desc()).first()
            if saved_resume:
                resume_text = saved_resume.resume_text
                file_name = saved_resume.file_name or "resume.pdf"

    if not resume_text or not resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume text provided. Please upload a resume file (PDF/TXT) or provide resume_text."
        )

    try:
        return calculate_ats_audit(resume_text, file_name)
    except Exception as exc:
        logger.exception("ATS audit calculation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/check-file", response_model=ATSCheckResult)
async def check_ats_file(
    file: UploadFile = File(...),
    user_external_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Directly uploads a resume file (PDF/TXT), extracts text, and runs the ATS audit.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    filename = file.filename or "resume.pdf"

    try:
        resume_text = extract_resume_text(contents, filename)
    except ResumeParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not resume_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable text could be extracted from this file.")

    return calculate_ats_audit(resume_text, filename)
