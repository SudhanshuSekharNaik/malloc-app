"""
Tests for ATS (Applicant Tracking System) Checker Service and Router.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.services.ats_checker import (
    calculate_ats_audit,
    run_layer1_checks,
    run_ml_checks,
    check_standard_sections,
    check_contact_info,
    check_file_format,
    check_filename_conventions,
    check_length,
    check_bullet_density,
    check_multi_column_tables,
)

client = TestClient(app)

SAMPLE_PERFECT_RESUME = """
John Doe
Senior Software Engineer
Email: john.doe@example.com | Phone: (555) 123-4567 | Location: San Francisco, CA
LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

PROFESSIONAL SUMMARY
Experienced Full-Stack and Backend Engineer with 6+ years of expertise in Python, FastAPI, Docker, and distributed cloud microservices.

WORK EXPERIENCE
Senior Backend Engineer at TechCorp (2021 - Present)
• Architected asynchronous REST APIs using FastAPI handling 50k requests per minute.
• Implemented caching layers using Redis, reducing latency by 45%.
• Led migration of core services to containerized Docker and Kubernetes environments.
• Mentored 4 junior engineers and conducted weekly code architecture reviews.

Software Engineer at CloudScale Inc (2018 - 2021)
• Developed scalable backend services in Python and PostgreSQL.
• Automated CI/CD deployment pipelines using GitHub Actions.
• Optimized database queries, cutting response times from 350ms to 80ms.

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley (2014 - 2018)

TECHNICAL SKILLS
• Languages: Python, JavaScript, TypeScript, SQL, Go
• Frameworks & Libraries: FastAPI, Django, Flask, React, Node.js
• Databases & Tools: PostgreSQL, Redis, Docker, Kubernetes, Git, AWS
"""

SAMPLE_POOR_RESUME = """
Jane
I love making websites. I worked at a company for 2 years doing random tasks.
Contact me on Instagram: @janedev.
"""

MOCK_NER_OUTPUT = [
    {"entity_group": "Skill", "word": "Python"},
    {"entity_group": "Skill", "word": "FastAPI"},
    {"entity_group": "Skill", "word": "Docker"},
    {"entity_group": "Skill", "word": "Kubernetes"},
    {"entity_group": "Skill", "word": "PostgreSQL"},
    {"entity_group": "Designation", "word": "Senior Backend Engineer"},
    {"entity_group": "Designation", "word": "Software Engineer"},
    {"entity_group": "Degree", "word": "Bachelor of Science"},
]

MOCK_ROLE_CLASSIFIER_OUTPUT = [
    {"label": "Software Developer", "score": 0.92}
]


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_rule_based_check_components():
    # 1. Standard sections
    sec_pass = check_standard_sections(SAMPLE_PERFECT_RESUME)
    assert sec_pass.status == "pass"
    assert "Experience" in sec_pass.detail

    sec_fail = check_standard_sections(SAMPLE_POOR_RESUME)
    assert sec_fail.status == "fail"

    # 2. Contact info
    contact_pass = check_contact_info(SAMPLE_PERFECT_RESUME)
    assert contact_pass.status == "pass"

    contact_fail = check_contact_info(SAMPLE_POOR_RESUME)
    assert contact_fail.status == "fail"

    # 3. File format & filename
    assert check_file_format("resume.pdf").status == "pass"
    assert check_file_format("resume.doc").status == "warn"

    assert check_filename_conventions("John_Doe_Resume.pdf").status == "pass"
    assert check_filename_conventions("My#Resume%Final(1).pdf").status == "warn"

    # 4. Length & Bullet density
    assert check_length(SAMPLE_PERFECT_RESUME).status == "pass"
    assert check_length(SAMPLE_POOR_RESUME).status == "warn"  # Too short

    assert check_bullet_density(SAMPLE_PERFECT_RESUME).status == "pass"
    assert check_bullet_density(SAMPLE_POOR_RESUME).status == "warn"


@patch("app.services.ats_checker._get_role_classifier_pipeline")
@patch("app.services.ats_checker._get_ner_pipeline")
def test_ats_all_pass(mock_get_ner, mock_get_role):
    mock_ner = MagicMock(return_value=MOCK_NER_OUTPUT)
    mock_get_ner.return_value = mock_ner

    mock_role = MagicMock(return_value=MOCK_ROLE_CLASSIFIER_OUTPUT)
    mock_get_role.return_value = mock_role

    resp = client.post("/ats/check", json={
        "resume_text": SAMPLE_PERFECT_RESUME,
        "file_name": "John_Doe_Resume.pdf"
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] >= 85
    assert data["label"] == "ATS-Friendly"
    assert data["layer1_score"] >= 85
    assert data["layer2_score"] >= 85

    # Check rule checks
    rule_names = [c["name"] for c in data["rule_based_checks"]]
    assert "standard_sections" in rule_names
    assert "contact_info" in rule_names

    # Check ML checks
    ml_names = [c["name"] for c in data["ml_checks"]]
    assert "skills_extractable" in ml_names
    assert "role_coherence" in ml_names


@patch("app.services.ats_checker._get_role_classifier_pipeline")
@patch("app.services.ats_checker._get_ner_pipeline")
def test_ats_missing_sections_and_penalties(mock_get_ner, mock_get_role):
    mock_ner = MagicMock(return_value=[])
    mock_get_ner.return_value = mock_ner

    mock_role = MagicMock(return_value=[{"label": "Other", "score": 0.35}])
    mock_get_role.return_value = mock_role

    resp = client.post("/ats/check", json={
        "resume_text": SAMPLE_POOR_RESUME,
        "file_name": "resume#bad.doc"
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] < 50
    assert data["label"] == "High Risk"
    assert len(data["recommendations"]) > 0


@patch("app.services.ats_checker._get_role_classifier_pipeline", side_effect=RuntimeError("Download failed"))
@patch("app.services.ats_checker._get_ner_pipeline", side_effect=RuntimeError("OOM error"))
def test_ats_ml_models_unavailable_graceful_fallback(mock_get_ner, mock_get_role):
    """
    Critical requirement: If HuggingFace ML models fail, ATS checker MUST still
    return 200 OK with Layer 1 rule checks and ML checks marked 'unavailable'.
    """
    resp = client.post("/ats/check", json={
        "resume_text": SAMPLE_PERFECT_RESUME,
        "file_name": "John_Doe_Resume.pdf"
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] >= 70
    assert data["layer2_score"] is None

    for check in data["ml_checks"]:
        assert check["status"] == "unavailable"


def test_ats_empty_upload_400():
    resp = client.post("/ats/check", json={"resume_text": "   "})
    assert resp.status_code == 400


@patch("app.services.ats_checker._get_role_classifier_pipeline", side_effect=Exception("ML offline"))
@patch("app.services.ats_checker._get_ner_pipeline", side_effect=Exception("ML offline"))
def test_ats_check_file_upload(mock_ner, mock_role):
    file_bytes = io.BytesIO(SAMPLE_PERFECT_RESUME.encode("utf-8"))
    resp = client.post(
        "/ats/check-file",
        files={"file": ("John_Doe_Resume.txt", file_bytes, "text/plain")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] >= 70


@patch("app.services.ats_checker._get_role_classifier_pipeline", side_effect=Exception("ML offline"))
@patch("app.services.ats_checker._get_ner_pipeline", side_effect=Exception("ML offline"))
def test_ats_saved_resume_reference(mock_ner, mock_role):
    # First save a resume
    save_resp = client.post("/matcher/save-resume", json={
        "user_external_id": "test-ats-user",
        "title": "Backend Resume",
        "resume_text": SAMPLE_PERFECT_RESUME,
        "is_primary": True
    })
    assert save_resp.status_code == 200
    resume_id = save_resp.json()["id"]

    # Call ATS check by resume_id
    resp = client.post("/ats/check", json={"resume_id": resume_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] >= 70


@patch("app.services.ats_checker._get_role_classifier_pipeline", side_effect=Exception("ML offline"))
@patch("app.services.ats_checker._get_ner_pipeline", side_effect=Exception("ML offline"))
def test_api_ats_check_alias(mock_ner, mock_role):
    resp = client.post("/api/ats/check", json={
        "resume_text": SAMPLE_PERFECT_RESUME,
        "file_name": "John_Doe_Resume.pdf"
    })
    assert resp.status_code == 200
    assert resp.json()["overall_score"] >= 70
