"""
Unit and Integration Tests for Apply via Email (Outreach) Service & Endpoints.
Covers:
1. Exact emoji-format JD parsing into all 7 structured fields.
2. Missing HR email parsing (non-blocking fallback).
3. Multi-position role alignment recommendation via resume skills.
4. Anti-cliché blocklist detection and avoidance.
5. Programmatic fabrication guardrail checking ungrounded technical skills.
6. Gmail OAuth authorization URL and scope verification (gmail.send ONLY).
7. Mocked Gmail API send flow (verifying send is never triggered during drafting).
8. Automatic logging into Job Tracker.
9. FastAPI REST router endpoints (/api/outreach/*).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, UserResume, UserGmailToken, JobApplication
from app.services.email_outreach import (
    parse_informal_jd_regex,
    parse_informal_jd,
    recommend_role_for_resume,
    check_cliches,
    check_email_fabrications,
    draft_application_email,
    create_gmail_oauth_url,
    send_gmail_message,
    GMAIL_SEND_SCOPE,
    CLICHE_BLOCKLIST
)

client = TestClient(app)

RAYO_INNOVATIONS_JD = """
🏢 Company: Rayo Innovations Pvt. Ltd.
💼 Open Positions:
* Web Designer
* Graphic Designer
* Android Developer
* iOS Developer
🎯 Experience: 0–1 Year / Freshers
📍 Location: Shyamal, Ahmedabad
🗓️ Working Days: 5 Days a Week
📧 Apply Via: hr@rayoinnovations.com
📞 Contact: +91 8799493952
"""

SAMPLE_ANDROID_RESUME = """
Jane Doe
Email: jane.doe@example.com | Phone: +1 555 123 4567

SUMMARY
Mobile Application Developer specializing in native Android development with Kotlin, Java, and Android Studio.

SKILLS
Android, Kotlin, Java, Android Studio, Jetpack Compose, XML, Retrofit, SQLite, Git, REST APIs

EXPERIENCE
Android Engineer Intern — TechSpire Labs (2023 - 2024)
- Developed Android features using Kotlin and Jetpack Compose.
- Integrated REST APIs with Retrofit and Coroutines.
- Maintained 99.8% crash-free sessions across 5,000 active devices.
"""

SAMPLE_FRONTEND_RESUME = """
John Smith
Web Developer with 2 years of experience in HTML, CSS, JavaScript, React, and Figma design.
"""


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


# ============================================================================
# Test 1: Successful Parse of Exact Emoji-Format JD
# ============================================================================

def test_parse_exact_rayo_emoji_jd():
    """Verify parsing the exact prompt example JD into all seven structured fields."""
    parsed = parse_informal_jd_regex(RAYO_INNOVATIONS_JD)

    assert parsed["company_name"] == "Rayo Innovations Pvt. Ltd."
    assert len(parsed["open_positions"]) == 4
    assert "Web Designer" in parsed["open_positions"]
    assert "Graphic Designer" in parsed["open_positions"]
    assert "Android Developer" in parsed["open_positions"]
    assert "iOS Developer" in parsed["open_positions"]
    assert "0–1 Year / Freshers" in parsed["experience_required"] or "Freshers" in parsed["experience_required"]
    assert "Shyamal, Ahmedabad" in parsed["location"]
    assert "5 Days a Week" in parsed["working_days"]
    assert parsed["hr_email"] == "hr@rayoinnovations.com"
    assert "8799493952" in parsed["contact_phone"]
    assert parsed["extraction_confidence"] == "high"


# ============================================================================
# Test 2: Parse with Missing / Unextractable HR Email
# ============================================================================

def test_parse_jd_missing_email_non_blocking():
    """Verify parsing when HR email is absent does not block the workflow."""
    jd_no_email = """
    🏢 Company: Stealth AI
    💼 Open Positions:
    - Backend Engineer
    🎯 Experience: 2+ Years
    📍 Location: Remote
    📞 Contact: +1 800 555 0199
    """
    parsed = parse_informal_jd(text=jd_no_email)

    assert parsed["company_name"] == "Stealth AI"
    assert "Backend Engineer" in parsed["open_positions"]
    assert parsed["hr_email"] is None  # Non-blocking: returns None so user can supply manually
    assert parsed["contact_phone"] is not None


# ============================================================================
# Test 3: Multi-Position Role Recommendation via Resume Skills
# ============================================================================

def test_multi_position_role_alignment():
    """Verify recommendation selects the closest role based on candidate resume."""
    positions = ["Web Designer", "Graphic Designer", "Android Developer", "iOS Developer"]

    # Candidate with Android/Kotlin resume
    best_role, reason = recommend_role_for_resume(positions, SAMPLE_ANDROID_RESUME)
    assert best_role == "Android Developer"
    assert "Android Developer" in reason

    # Candidate with Web/React resume
    best_role_web, reason_web = recommend_role_for_resume(positions, SAMPLE_FRONTEND_RESUME)
    assert best_role_web == "Web Designer"


# ============================================================================
# Test 4: Anti-Cliché Blocklist Detection & Avoidance
# ============================================================================

def test_cliche_detection():
    """Verify cliché checker catches overused email tropes."""
    bad_email = (
        "Dear Hiring Manager,\n"
        "I am writing to express my interest in the position. "
        "I believe I would be a great fit for this position and have a proven track record of success. "
        "Please find my resume attached for your consideration.\n"
        "I look forward to hearing from you."
    )
    cliches = check_cliches(bad_email)
    assert len(cliches) >= 4
    assert any("writing to express my interest" in c for c in cliches)
    assert any("great fit" in c for c in cliches)
    assert any("resume attached" in c for c in cliches)


def test_clean_draft_has_no_cliches():
    """Verify clean human draft passes cliché check."""
    good_email = (
        "Hi Rayo Innovations team,\n\n"
        "I saw your opening for the Android Developer role and wanted to reach out directly. "
        "My background centers on native Android development with Kotlin and Jetpack Compose, "
        "including building REST-connected mobile interfaces and local SQLite data storage.\n\n"
        "Given your 0-1 year experience requirement, my recent project and internship work aligns well with your team's stack.\n\n"
        "Happy to share code samples or hop on a quick call.\n\n"
        "Best,\nJane Doe"
    )
    cliches = check_cliches(good_email)
    assert len(cliches) == 0


# ============================================================================
# Test 5: Programmatic Skill Fabrication Guardrail
# ============================================================================

def test_fabrication_guardrail_catches_ungrounded_skills():
    """Verify fabrication guardrail flags technical skills not present in resume or JD."""
    # Draft mentions Kubernetes, AWS, and Flutter, which are NOT in SAMPLE_ANDROID_RESUME
    hallucinated_draft = (
        "Hi team,\n\n"
        "I have extensive experience managing Kubernetes clusters and deploying microservices to AWS Lambda. "
        "I also built cross-platform apps using Flutter and Dart.\n\n"
        "Best,\nJane Doe"
    )

    flags = check_email_fabrications(hallucinated_draft, SAMPLE_ANDROID_RESUME, RAYO_INNOVATIONS_JD)
    flagged_terms = [f["term"].lower() for f in flags]

    assert any("kubernetes" in t for t in flagged_terms)
    assert any("aws" in t for t in flagged_terms)
    assert any("flutter" in t or "dart" in t for t in flagged_terms)


def test_fabrication_guardrail_passes_grounded_skills():
    """Verify fabrication guardrail passes when all mentioned skills exist in resume."""
    grounded_draft = (
        "Hi team,\n\n"
        "My background focuses on Kotlin, Java, and Jetpack Compose on Android, working with SQLite databases and Git.\n\n"
        "Best,\nJane Doe"
    )

    flags = check_email_fabrications(grounded_draft, SAMPLE_ANDROID_RESUME, RAYO_INNOVATIONS_JD)
    assert len(flags) == 0


# ============================================================================
# Test 6: Gmail OAuth Scope & Authorization URL
# ============================================================================

def test_gmail_oauth_scope_is_send_only():
    """Verify that OAuth authorization URL uses 'https://www.googleapis.com/auth/gmail.send' ONLY."""
    assert GMAIL_SEND_SCOPE == "https://www.googleapis.com/auth/gmail.send"

    auth_url, state_param = create_gmail_oauth_url("user-test-123")
    assert "scope=" in auth_url
    assert "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send" in auth_url or "gmail.send" in auth_url
    # Ensure read or full permissions are NOT requested
    assert "gmail.readonly" not in auth_url
    assert "gmail.modify" not in auth_url
    assert "mail.google.com" not in auth_url


# ============================================================================
# Test 7: Send Flow via Gmail API (Drafting NEVER triggers send)
# ============================================================================

@patch("app.services.email_outreach.httpx.Client")
def test_mocked_gmail_send_message(mock_client_cls):
    """Verify Gmail API send message formatting and payload."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "1894abcde7890", "threadId": "1894abcde7890"}
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = send_gmail_message(
        access_token="mock_access_token_xyz",
        to_email="hr@rayoinnovations.com",
        subject="Application for Android Developer — Jane Doe",
        body_text="Hi team, here is my application.",
        attachment_bytes=b"Sample resume binary content",
        attachment_filename="Jane_Doe_Resume.pdf"
    )

    assert result["success"] is True
    assert result["message_id"] == "1894abcde7890"
    assert result["recipient"] == "hr@rayoinnovations.com"

    # Assert POST was made to official Gmail API endpoint
    mock_client.post.assert_called_once()
    call_args, call_kwargs = mock_client.post.call_args
    assert "https://gmail.googleapis.com/gmail/v1/users/me/messages/send" in call_args[0]
    assert call_kwargs["headers"]["Authorization"] == "Bearer mock_access_token_xyz"
    assert "raw" in call_kwargs["json"]


def test_draft_does_not_call_send():
    """Verify that calling draft_application_email NEVER triggers send_gmail_message."""
    with patch("app.services.email_outreach.send_gmail_message") as mock_send, \
         patch("app.services.email_outreach.call_llm") as mock_llm, \
         patch("app.services.email_outreach.evaluate_ai_detector_score") as mock_detector:
        mock_llm.return_value = '{"subject": "Application for Android Developer — Jane Doe", "body": "Hi team, I am applying with Kotlin and Jetpack Compose background. Best, Jane"}'
        mock_detector.return_value = (0.12, "Test detector score")
        draft = draft_application_email(
            resume_text=SAMPLE_ANDROID_RESUME,
            selected_role="Android Developer",
            parsed_jd=parse_informal_jd_regex(RAYO_INNOVATIONS_JD),
            applicant_name="Jane Doe"
        )
        assert "Android Developer" in draft["subject"]
        assert len(draft["body"]) > 10
        # Must never call send
        mock_send.assert_not_called()


# ============================================================================
# Test 8: End-to-End FastAPI Router Integration
# ============================================================================

def test_api_parse_jd_endpoint(setup_db):
    """Test POST /api/outreach/parse-jd."""
    db = setup_db
    # Create test user and resume
    user = User(external_id="test-outreach-user")
    db.add(user)
    db.commit()

    resume = UserResume(
        user_id=user.id,
        title="Android Resume",
        resume_text=SAMPLE_ANDROID_RESUME,
        is_primary=True
    )
    db.add(resume)
    db.commit()

    resp = client.post("/api/outreach/parse-jd", json={
        "text": RAYO_INNOVATIONS_JD,
        "user_external_id": "test-outreach-user"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["parsed"]["company_name"] == "Rayo Innovations Pvt. Ltd."
    assert "Android Developer" in data["parsed"]["open_positions"]
    assert data["parsed"]["recommended_role"] == "Android Developer"


def test_api_draft_email_endpoint(setup_db):
    """Test POST /api/outreach/draft-email."""
    parsed_jd = parse_informal_jd_regex(RAYO_INNOVATIONS_JD)

    with patch("app.services.email_outreach.call_llm") as mock_llm, \
         patch("app.services.email_outreach.evaluate_ai_detector_score") as mock_detector:
        mock_llm.return_value = '{"subject": "Application for Android Developer — Jane Doe", "body": "Hi team, I am applying with Kotlin background. Best, Jane"}'
        mock_detector.return_value = (0.15, "Test detector score")
        resp = client.post("/api/outreach/draft-email", json={
            "resume_text": SAMPLE_ANDROID_RESUME,
            "selected_role": "Android Developer",
            "parsed_jd": parsed_jd,
            "applicant_name": "Jane Doe"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Android Developer" in data["subject"]
        assert len(data["body"]) > 10
        assert data["recipient"] == "hr@rayoinnovations.com"


def test_api_gmail_status_and_disconnect(setup_db):
    """Test GET /api/outreach/gmail/status and POST /api/outreach/gmail/disconnect."""
    db = setup_db
    user = User(external_id="oauth-user-test")
    db.add(user)
    db.commit()

    token = UserGmailToken(
        user_id=user.id,
        email="applicant@gmail.com",
        access_token="valid_access_token_123",
        scopes=GMAIL_SEND_SCOPE
    )
    db.add(token)
    db.commit()

    # Status check
    status_resp = client.get("/api/outreach/gmail/status?user_external_id=oauth-user-test")
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is True
    assert status_resp.json()["email"] == "applicant@gmail.com"

    # Disconnect
    disc_resp = client.post("/api/outreach/gmail/disconnect?user_external_id=oauth-user-test")
    assert disc_resp.status_code == 200

    # Verify status is now disconnected
    status_resp_after = client.get("/api/outreach/gmail/status?user_external_id=oauth-user-test")
    assert status_resp_after.json()["connected"] is False


@patch("app.routers.outreach.send_gmail_message")
def test_api_send_application_and_log_tracker(mock_send, setup_db):
    """Test POST /api/outreach/send logs to tracker and calls Gmail sender."""
    db = setup_db
    user = User(external_id="sender-user-test")
    db.add(user)
    db.commit()

    token = UserGmailToken(
        user_id=user.id,
        email="jane.doe@gmail.com",
        access_token="valid_access_token_abc",
        scopes=GMAIL_SEND_SCOPE
    )
    db.add(token)
    db.commit()

    mock_send.return_value = {
        "success": True,
        "message_id": "msg_gmail_9999",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    send_resp = client.post("/api/outreach/send", json={
        "user_external_id": "sender-user-test",
        "to_email": "hr@rayoinnovations.com",
        "subject": "Application for Android Developer — Jane Doe",
        "body": "Hi team, please review my application.",
        "company_name": "Rayo Innovations Pvt. Ltd.",
        "role_title": "Android Developer",
        "log_to_tracker": True
    })

    assert send_resp.status_code == 200
    data = send_resp.json()
    assert data["success"] is True
    assert data["message_id"] == "msg_gmail_9999"
    assert data["job_application_id"] is not None

    # Verify row was created in JobApplication table
    job_record = db.query(JobApplication).filter(JobApplication.id == data["job_application_id"]).first()
    assert job_record is not None
    assert job_record.company == "Rayo Innovations Pvt. Ltd."
    assert job_record.role_title == "Android Developer"
    assert job_record.status == "applied"
