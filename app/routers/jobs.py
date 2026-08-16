"""
Job application tracker (core structure for the reminders/reports
features that build on top of this).

Reminders here mean: a "what's due" query the frontend polls/displays
on load, NOT a background scheduler (APScheduler/Celery). Deliberately
avoiding a scheduler for now - it's real infrastructure complexity for
a single-user MVP, and "show due follow-ups when the app opens" covers
the actual need. Revisit only if this needs to notify you outside of
opening the app (e.g. push notifications).
"""
import logging
from datetime import datetime, timedelta, timezone

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, JobApplication
from app.schemas import JobApplicationCreate, JobApplicationUpdate, JobApplicationOut

logger = logging.getLogger("memora.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_or_create_user(db: Session, external_id: str) -> User:
    user = db.query(User).filter(User.external_id == external_id).first()
    if user is None:
        user = User(external_id=external_id)
        db.add(user)
        db.flush()
    return user


def _format_name(val: str) -> str:
    val = val.strip()
    if not val:
        return val
    # If all lowercase, title-case it (e.g. accenture -> Accenture, google -> Google)
    if val.islower():
        return val.title()
    return val


@router.post("", response_model=JobApplicationOut)
@router.post("/", response_model=JobApplicationOut)
def create_job(payload: JobApplicationCreate, user_external_id: Optional[str] = Query(None), db: Session = Depends(get_db)) -> JobApplication:
    ext_id = payload.user_external_id or user_external_id or "default_user"
    user = _get_or_create_user(db, ext_id)

    applied_date = payload.applied_date or datetime.now(timezone.utc)
    follow_up_date = applied_date + timedelta(days=payload.follow_up_days or 7)

    company = _format_name(payload.company)
    role_title = _format_name(payload.role_title)

    job = JobApplication(
        user_id=user.id,
        company=company,
        role_title=role_title,
        status=payload.status,
        job_url=payload.job_url,
        notes=payload.notes,
        match_score=payload.match_score,
        tailored_pitch=payload.tailored_pitch,
        applied_date=applied_date,
        follow_up_date=follow_up_date,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobApplicationOut])
@router.get("/", response_model=list[JobApplicationOut])
def list_jobs_by_query(user_external_id: str = Query("default_user"), db: Session = Depends(get_db)) -> list[JobApplication]:
    return list_jobs(user_external_id, db)


@router.get("/{user_external_id}", response_model=list[JobApplicationOut])
def list_jobs(user_external_id: str, db: Session = Depends(get_db)) -> list[JobApplication]:
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if user is None:
        return []
    return (
        db.query(JobApplication)
        .filter(JobApplication.user_id == user.id)
        .order_by(JobApplication.applied_date.desc())
        .all()
    )


@router.get("/{user_external_id}/due-followups", response_model=list[JobApplicationOut])
def due_followups(user_external_id: str, db: Session = Depends(get_db)) -> list[JobApplication]:
    """
    Applications whose follow_up_date has passed and are still in an
    open (non-terminal) status. This is what the frontend should poll
    on load to show a reminder banner.
    """
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if user is None:
        return []

    now = datetime.now(timezone.utc)
    terminal_statuses = ("offer", "rejected")

    return (
        db.query(JobApplication)
        .filter(
            JobApplication.user_id == user.id,
            JobApplication.follow_up_date <= now,
            JobApplication.status.notin_(terminal_statuses),
        )
        .order_by(JobApplication.follow_up_date.asc())
        .all()
    )


@router.patch("/{job_id}", response_model=JobApplicationOut)
def update_job(job_id: str, payload: JobApplicationUpdate, db: Session = Depends(get_db)) -> JobApplication:
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job application not found")

    updates = payload.model_dump(exclude_unset=True)
    if "company" in updates and updates["company"]:
        updates["company"] = _format_name(updates["company"])
    if "role_title" in updates and updates["role_title"]:
        updates["role_title"] = _format_name(updates["role_title"])

    for field, value in updates.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> None:
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job application not found")
    db.delete(job)
    db.commit()
