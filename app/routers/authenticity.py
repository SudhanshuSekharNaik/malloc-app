"""
Job Post Authenticity & Fraud Risk Assessment Router.

Provides endpoints for evaluating job postings against known fraud patterns,
running the BERT spam classifier, and generating RAG-augmented LLM reasoning.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.scraper import fetch_job_from_url
from app.services.authenticity_checker import (
    analyze_job_authenticity,
    AuthenticityReport
)

logger = logging.getLogger("memora.authenticity.router")
router = APIRouter(prefix="/authenticity", tags=["authenticity"])

class AuthenticityCheckRequest(BaseModel):
    url: Optional[str] = None
    job_url: Optional[str] = None
    job_text: Optional[str] = None
    job_description: Optional[str] = None
    company: Optional[str] = None
    company_hint: Optional[str] = None
    role_title: Optional[str] = None
    role_hint: Optional[str] = None


@router.post("/check", response_model=AuthenticityReport)
def check_authenticity(payload: AuthenticityCheckRequest):
    """
    Evaluates a job posting for fraud and legitimacy risk signals.
    Accepts a direct job posting URL or raw text description.
    """
    job_text = payload.job_text or payload.job_description
    url = (payload.url or payload.job_url or "").strip() or None
    company = payload.company or payload.company_hint
    role_title = payload.role_title or payload.role_hint

    role_title = payload.role_title

    # 1. If URL provided and no text supplied, auto-fetch
    if url and not (job_text and job_text.strip()):
        scraped = fetch_job_from_url(url)
        if scraped.success and scraped.description:
            job_text = scraped.description
            if not company and scraped.company:
                company = scraped.company
            if not role_title and scraped.role_title:
                role_title = scraped.role_title
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=scraped.message or "Could not automatically extract job text from this URL. Please paste the job description text manually."
            )

    if not job_text or not job_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No job posting content provided. Please enter a valid job URL or paste the job description text."
        )

    try:
        return analyze_job_authenticity(
            job_text=job_text,
            job_url=url,
            company_hint=company,
            role_hint=role_title
        )
    except Exception as exc:
        logger.exception("Authenticity analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authenticity assessment failed: {str(exc)}"
        ) from exc
