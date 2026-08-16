"""
Memora — Email Outreach & Apply via Email Router.
Endpoints for informal JD parsing, role selection, resume-grounded drafting,
fabrication review, Gmail OAuth2 authentication (gmail.send scope), and user-initiated sending.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserResume, JobApplication, UserGmailToken
from app.schemas import (
    ParseJDRequest, ParseJDResponse, ParsedJDSchema,
    DraftEmailRequest, DraftEmailResponse,
    GmailAuthStatusResponse, SendEmailRequest, SendEmailResponse
)
from app.services.email_outreach import (
    parse_informal_jd,
    recommend_role_for_resume,
    draft_application_email,
    create_gmail_oauth_url,
    exchange_oauth_code,
    refresh_access_token_if_needed,
    send_gmail_message,
    GMAIL_SEND_SCOPE
)

logger = logging.getLogger("memora.routers.outreach")

router = APIRouter(prefix="/outreach", tags=["outreach"])


def _get_or_create_user(db: Session, external_id: str) -> User:
    """Helper to retrieve or create a user by external ID."""
    user = db.query(User).filter(User.external_id == external_id).first()
    if not user:
        user = User(external_id=external_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ============================================================================
# Step 1: Parse Informal Job Posting
# ============================================================================

@router.post("/parse-jd", response_model=ParseJDResponse)
def parse_job_description(payload: ParseJDRequest, db: Session = Depends(get_db)):
    """
    Step 1: Parses an informal or emoji-bulleted job posting text or URL into structured fields.
    If a resume is available, also evaluates which listed role is the closest match.
    """
    input_text = payload.text or payload.raw_text or payload.job_text or payload.job_description
    input_url = payload.url or payload.job_url
    if not input_text and not input_url:
        raise HTTPException(status_code=400, detail="Please provide either job posting text or a job URL.")

    # 1. Parse informal JD text / URL
    parsed_data = parse_informal_jd(text=input_text, url=input_url)

    # 2. Check if a resume is available to recommend role fit
    resume_text = ""
    if payload.resume_id:
        res_record = db.query(UserResume).filter(UserResume.id == payload.resume_id).first()
        if res_record:
            resume_text = res_record.resume_text
    elif payload.user_external_id:
        user = db.query(User).filter(User.external_id == payload.user_external_id).first()
        if user:
            res_record = (
                db.query(UserResume)
                .filter(UserResume.user_id == user.id)
                .order_by(UserResume.is_primary.desc(), UserResume.created_at.desc())
                .first()
            )
            if res_record:
                resume_text = res_record.resume_text

    # 3. Recommend role if multiple positions exist and resume text is available
    if parsed_data.get("open_positions") and resume_text:
        rec_role, rec_reason = recommend_role_for_resume(parsed_data["open_positions"], resume_text)
        parsed_data["recommended_role"] = rec_role
        parsed_data["recommendation_reason"] = rec_reason

    parsed_schema = ParsedJDSchema(**parsed_data)
    return ParseJDResponse(
        parsed=parsed_schema,
        raw_text_length=len(input_text) if input_text else 0
    )


# ============================================================================
# Step 3: Draft Grounded Application Email
# ============================================================================

@router.post("/draft-email", response_model=DraftEmailResponse)
@router.post("/draft", response_model=DraftEmailResponse)
def generate_email_draft(payload: DraftEmailRequest, db: Session = Depends(get_db)):
    """
    Step 3: Drafts a concise, humanly written application email grounded strictly in the user's resume.
    Enforces anti-cliché blocklists, evaluates fabrication flags, and computes weak secondary detector signals.
    
    IMPORTANT ARCHITECTURAL REQUIREMENT:
    Drafting an email NEVER sends it. Sending is a completely separate, user-initiated action.
    """
    if not payload.selected_role:
        raise HTTPException(status_code=400, detail="Please select a target role before drafting an email.")

    # 1. Resolve resume text
    resume_text = (payload.resume_text or "").strip()
    if not resume_text and payload.resume_id:
        res_record = db.query(UserResume).filter(UserResume.id == payload.resume_id).first()
        if res_record:
            resume_text = res_record.resume_text

    if not resume_text and payload.user_external_id:
        user = db.query(User).filter(User.external_id == payload.user_external_id).first()
        if user:
            res_record = (
                db.query(UserResume)
                .filter(UserResume.user_id == user.id)
                .order_by(UserResume.is_primary.desc(), UserResume.created_at.desc())
                .first()
            )
            if res_record:
                resume_text = res_record.resume_text

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="Resume content is required to ground the application email. Please upload or select a resume."
        )

    # 2. Draft email
    draft_result = draft_application_email(
        resume_text=resume_text,
        selected_role=payload.selected_role,
        parsed_jd=payload.parsed_jd.model_dump(),
        applicant_name=payload.applicant_name,
        custom_instructions=payload.custom_instructions
    )

    return DraftEmailResponse(**draft_result)


# ============================================================================
# Step 4: Google OAuth2 & Gmail Authentication
# ============================================================================

@router.get("/gmail/connect")
def gmail_connect(
    user_external_id: str = Query(..., description="User external ID"),
    redirect_uri: Optional[str] = Query(None, description="Optional custom OAuth callback URI"),
    db: Session = Depends(get_db)
):
    """
    Initiates the Google OAuth2 flow with 'gmail.send' scope only.
    Returns the Google authorization URL for user consent.
    """
    user = _get_or_create_user(db, user_external_id)
    auth_url, state_param = create_gmail_oauth_url(user.id, redirect_uri)

    is_configured = bool(settings.google_client_id and settings.google_client_id.strip())
    return {
        "auth_url": auth_url,
        "configured": is_configured,
        "scope": GMAIL_SEND_SCOPE,
        "message": "Visit auth_url in browser to grant gmail.send access." if is_configured else "Google Client ID is not configured in .env."
    }


@router.get("/gmail/callback")
def gmail_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handles the Google OAuth2 callback, exchanges authorization code for tokens,
    and persists UserGmailToken record.
    """
    if error:
        logger.warning("Google OAuth callback returned error: %s", error)
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;background:#0d1117;color:#fff;padding:40px;text-align:center;">
                <h2 style="color:#ff5555;">Google Authentication Failed</h2>
                <p>{error}</p>
                <button onclick="window.close()" style="padding:10px 20px;background:#333;color:#fff;border:none;cursor:pointer;">Close Window</button>
            </body></html>
            """,
            status_code=400
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code in callback.")

    try:
        # Decode user_id from state parameter if present
        import base64
        import json
        user_id = None
        if state:
            try:
                state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                user_id = state_data.get("user_id")
            except Exception:
                pass

        tokens = exchange_oauth_code(code, redirect_uri)

        # If user_id wasn't in state, find or create default
        if not user_id:
            user = db.query(User).first()
            if not user:
                user = _get_or_create_user(db, "default-user")
            user_id = user.id

        # Update or create UserGmailToken
        token_record = db.query(UserGmailToken).filter(UserGmailToken.user_id == user_id).first()
        if not token_record:
            token_record = UserGmailToken(
                user_id=user_id,
                email=tokens.get("email"),
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_at=tokens.get("expires_at"),
                scopes=tokens.get("scopes", GMAIL_SEND_SCOPE)
            )
            db.add(token_record)
        else:
            token_record.access_token = tokens["access_token"]
            if tokens.get("refresh_token"):
                token_record.refresh_token = tokens.get("refresh_token")
            token_record.expires_at = tokens.get("expires_at")
            if tokens.get("email"):
                token_record.email = tokens.get("email")

        db.commit()

        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;background:#0d1117;color:#fff;padding:40px;text-align:center;">
                <h2 style="color:#00ffcc;">✓ Gmail Connected Successfully!</h2>
                <p>Connected Account: <strong>{tokens.get('email') or 'Your Gmail Account'}</strong></p>
                <p style="color:#8b949e;font-size:13px;">Permission granted: Send-only (<code>gmail.send</code>). No read access granted.</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'GMAIL_CONNECTED', email: '{tokens.get('email')}' }}, '*');
                    }}
                    setTimeout(function() {{ window.close(); }}, 2000);
                </script>
                <button onclick="window.close()" style="padding:10px 20px;background:#00ffcc;color:#000;font-weight:bold;border:none;cursor:pointer;margin-top:15px;">Close Window</button>
            </body></html>
            """
        )
    except Exception as exc:
        logger.error("OAuth token exchange failed: %s", exc)
        return HTMLResponse(
            content=f"""
            <html><body style="font-family:sans-serif;background:#0d1117;color:#fff;padding:40px;text-align:center;">
                <h2 style="color:#ff5555;">Authentication Failed</h2>
                <p>{str(exc)}</p>
                <button onclick="window.close()" style="padding:10px 20px;background:#333;color:#fff;border:none;cursor:pointer;">Close Window</button>
            </body></html>
            """,
            status_code=500
        )


@router.get("/gmail/status", response_model=GmailAuthStatusResponse)
def get_gmail_status(user_external_id: str = Query(..., description="User external ID"), db: Session = Depends(get_db)):
    """
    Checks if the user has an active, valid Gmail connection.
    """
    user = db.query(User).filter(User.external_id == user_external_id).first()
    is_configured = bool(settings.google_client_id and settings.google_client_id.strip())

    if not user:
        return GmailAuthStatusResponse(
            connected=False,
            configured=is_configured,
            config_note=None if is_configured else "Google OAuth credentials not configured in settings."
        )

    token_record = db.query(UserGmailToken).filter(UserGmailToken.user_id == user.id).first()
    if not token_record or not token_record.access_token:
        return GmailAuthStatusResponse(
            connected=False,
            configured=is_configured,
            config_note=None if is_configured else "Google OAuth credentials not configured in settings."
        )

    return GmailAuthStatusResponse(
        connected=True,
        email=token_record.email,
        scopes=token_record.scopes,
        configured=is_configured
    )


@router.post("/gmail/disconnect")
def disconnect_gmail(user_external_id: str = Query(..., description="User external ID"), db: Session = Depends(get_db)):
    """
    Revokes and removes stored Gmail credentials for the user.
    """
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if user:
        tokens = db.query(UserGmailToken).filter(UserGmailToken.user_id == user.id).all()
        for t in tokens:
            db.delete(t)
        db.commit()

    return {"success": True, "message": "Gmail access disconnected successfully."}


# ============================================================================
# Step 4: Explicit User Send Action
# ============================================================================

@router.post("/send", response_model=SendEmailResponse)
def send_application_email(payload: SendEmailRequest, db: Session = Depends(get_db)):
    """
    Step 4: Explicitly sends the reviewed application email via the official Gmail API.
    
    NON-NEGOTIABLE SAFETY CONSTRAINTS:
    1. This endpoint is ONLY called when the user explicitly clicks the Send button.
    2. Requires active, authenticated Gmail token (gmail.send scope).
    3. Option to attach resume file and automatically log the application in Job Tracker.
    """
    user = _get_or_create_user(db, payload.user_external_id)

    # 1. Retrieve user's Gmail token
    token_record = db.query(UserGmailToken).filter(UserGmailToken.user_id == user.id).first()
    if not token_record or not token_record.access_token:
        raise HTTPException(
            status_code=401,
            detail="Gmail account is not connected. Please connect your Gmail account before sending."
        )

    # 2. Refresh token if expired
    access_token = refresh_access_token_if_needed(token_record, db)

    # 3. Check for optional resume attachment
    attachment_bytes = None
    attachment_filename = None

    if payload.attach_resume_id:
        resume = db.query(UserResume).filter(UserResume.id == payload.attach_resume_id).first()
        if resume and resume.resume_text:
            attachment_bytes = resume.resume_text.encode("utf-8")
            attachment_filename = resume.file_name or f"{resume.title or 'Resume'}.txt"

    # 4. Send message via Gmail API
    try:
        send_result = send_gmail_message(
            access_token=access_token,
            to_email=payload.to_email,
            subject=payload.subject,
            body_text=payload.body,
            attachment_bytes=attachment_bytes,
            attachment_filename=attachment_filename
        )
    except Exception as exc:
        logger.error("Failed to send email via Gmail API: %s", exc)
        raise HTTPException(status_code=502, detail=f"Failed to send email via Gmail: {str(exc)}")

    # 5. Automatically log to Job Tracker if requested
    job_app_id = None
    if payload.log_to_tracker:
        try:
            now = datetime.now(timezone.utc)
            comp = (payload.company_name or "Direct Employer").strip()
            role = (payload.role_title or "Job Position").strip()

            job_app = JobApplication(
                user_id=user.id,
                company=comp,
                role_title=role,
                status="applied",
                applied_date=now,
                follow_up_date=now + (datetime.now() - datetime.now()), # placeholder handled below
                notes=f"Application email sent directly via Gmail to {payload.to_email} on {now.strftime('%Y-%m-%d %H:%M')}.\nSubject: {payload.subject}",
                tailored_pitch=payload.body[:400]
            )
            from datetime import timedelta
            job_app.follow_up_date = now + timedelta(days=5)
            db.add(job_app)
            db.commit()
            db.refresh(job_app)
            job_app_id = job_app.id
            logger.info("Logged application to Job Tracker (ID: %s) for %s - %s", job_app_id, comp, role)
        except Exception as exc:
            logger.warning("Could not auto-log to Job Tracker: %s", exc)

    return SendEmailResponse(
        success=True,
        message_id=send_result.get("message_id"),
        timestamp=send_result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        recipient=payload.to_email,
        subject=payload.subject,
        job_application_id=job_app_id,
        detail="Application email sent successfully via Gmail API."
    )
