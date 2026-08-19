"""
Unit tests for Suggested Resume Edits Engine and Fabrication Guardrail.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.services.resume_editor import (
    generate_resume_edits,
    validate_against_fabrication,
    extract_bullets_with_sections,
    find_evidenced_skills_in_body,
    extract_numbers_and_metrics
)

client = TestClient(app)

SAMPLE_RESUME_WITH_EVIDENCE = """
Alex Morgan
Full-Stack & Cloud Engineer
Email: alex.morgan@example.com

SKILLS:
- Languages: Python, JavaScript, SQL
- Frameworks: FastAPI, React

EXPERIENCE:
Senior Backend Developer at CloudScale (2021 - Present)
- Worked on backend microservices handling 25k req/min using FastAPI and PostgreSQL.
- Implemented containerized deployment workflows with Docker on AWS ECS clusters.
- Optimized query latency by 40% using Redis caching layers.

Software Engineer at AppWorks (2018 - 2021)
- Responsible for building internal administrative dashboards with React and Node.js.
- Helped with database migrations and automated CI/CD unit testing pipelines.
"""

SAMPLE_JOB_DESC = """
Staff Backend Engineer at Enterprise Corp
Requirements:
- 5+ years of experience with Python, FastAPI, and PostgreSQL
- Strong experience with Docker and Kubernetes for container orchestration
- Experience with GraphQL, Go, and Kafka
- Track record of architecting distributed systems
"""


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_extract_bullets_and_sections():
    bullets = extract_bullets_with_sections(SAMPLE_RESUME_WITH_EVIDENCE)
    assert len(bullets) >= 4
    # Verify bullets are extracted cleanly without prefix symbols
    for section, bullet in bullets:
        assert not bullet.startswith("•")
        assert not bullet.startswith("-")
        assert len(bullet) >= 15


def test_find_evidenced_skills_in_body():
    # Docker is mentioned in the Experience bullet but NOT in the Skills section
    # Kubernetes, Go, Kafka are NOT mentioned anywhere in the resume
    missing_skills = ["Docker", "Kubernetes", "Go", "Kafka"]
    evidenced = find_evidenced_skills_in_body(missing_skills, SAMPLE_RESUME_WITH_EVIDENCE)
    
    evidenced_skill_names = [item[0] for item in evidenced]
    # Docker SHOULD be found as evidenced in the body
    assert "Docker" in evidenced_skill_names
    # Kubernetes, Go, Kafka should NOT be found because they are not anywhere in the resume
    assert "Kubernetes" not in evidenced_skill_names
    assert "Go" not in evidenced_skill_names
    assert "Kafka" not in evidenced_skill_names


def test_fabrication_guardrail_catches_hallucinated_metrics():
    original_bullet = "Worked on backend microservices handling 25k req/min using FastAPI and PostgreSQL."
    
    # 1. Clean valid rewrite with existing numbers
    valid_rewrite = "Architected scalable backend microservices handling 25k req/min with FastAPI and PostgreSQL."
    is_valid, warning = validate_against_fabrication(valid_rewrite, original_bullet, SAMPLE_RESUME_WITH_EVIDENCE)
    assert is_valid is True
    assert warning is None

    # 2. Fabricated number (model hallucinates 100k instead of 25k)
    fabricated_rewrite = "Architected high-throughput backend services handling 100k req/min with FastAPI and PostgreSQL."
    is_valid, warning = validate_against_fabrication(fabricated_rewrite, original_bullet, SAMPLE_RESUME_WITH_EVIDENCE)
    assert is_valid is False
    assert "100k" in warning

    # 3. Fabricated percentage (model hallucinates 90% cost reduction)
    fabricated_pct = "Reduced infrastructure overhead by 90% through asynchronous FastAPI microservices."
    is_valid, warning = validate_against_fabrication(fabricated_pct, original_bullet, SAMPLE_RESUME_WITH_EVIDENCE)
    assert is_valid is False
    assert "90" in warning


def test_fabrication_guardrail_flags_transplanted_metric():
    # 40% is in another bullet (Redis caching), not in this bullet
    original_bullet = "Responsible for building internal administrative dashboards with React and Node.js."
    transplanted_rewrite = "Spearheaded internal administrative dashboards with React and Node.js, improving efficiency by 40%."
    
    is_valid, warning = validate_against_fabrication(transplanted_rewrite, original_bullet, SAMPLE_RESUME_WITH_EVIDENCE)
    # 40% exists in the full resume, but wasn't in this bullet: it should pass with a review warning flag
    assert is_valid is True
    assert warning is not None
    assert "40" in warning


@patch("app.services.resume_editor.polish_grammar", side_effect=lambda x: x)
@patch("app.services.resume_editor.rewrite_single_bullet")
def test_clean_rewrite_flow_with_mock_layer2(mock_rewrite, mock_polish):
    mock_rewrite.return_value = "Architected high-throughput backend microservices handling 25k req/min using FastAPI and PostgreSQL."
    
    result = generate_resume_edits(
        resume_text=SAMPLE_RESUME_WITH_EVIDENCE,
        job_description=SAMPLE_JOB_DESC,
        company_hint="Enterprise Corp",
        role_hint="Staff Backend Engineer"
    )
    
    assert len(result.suggestions) >= 1
    # Check that Docker was suggested to be added to Skills because it's evidenced
    skill_suggestions = [s for s in result.suggestions if s.type == "missing_keyword"]
    assert any("Docker" in s.suggested for s in skill_suggestions)
    # Ensure hallucinated skills (Go, Kafka) are never suggested to be added to Skills
    assert not any("Kafka" in s.suggested for s in skill_suggestions)
    assert not any("Go" in s.suggested for s in skill_suggestions)

    # Check bullet rewrites
    rewrites = [s for s in result.suggestions if s.type == "bullet_rewrite"]
    assert len(rewrites) >= 1
    assert rewrites[0].flagged_for_review is False


@patch("app.services.resume_editor.polish_grammar", side_effect=lambda x: x)
@patch("app.services.resume_editor.rewrite_single_bullet")
def test_hallucinated_rewrite_is_dropped(mock_rewrite, mock_polish):
    # Model generates a hallucinated metric ($5M revenue)
    mock_rewrite.return_value = "Generated $5M in enterprise revenue by managing FastAPI microservices."
    
    result = generate_resume_edits(
        resume_text=SAMPLE_RESUME_WITH_EVIDENCE,
        job_description=SAMPLE_JOB_DESC
    )
    
    rewrites = [s for s in result.suggestions if s.type == "bullet_rewrite"]
    # The hallucinated rewrite must be dropped by Layer 3 validation
    for r in rewrites:
        assert "$5m" not in r.suggested.lower()


@patch("app.services.resume_editor.polish_grammar", side_effect=lambda x: x)
@patch("app.services.resume_editor.rewrite_single_bullet")
def test_suggest_edits_endpoints(mock_rewrite, mock_polish):
    mock_rewrite.return_value = "Architected high-throughput backend microservices handling 25k req/min with FastAPI."
    # Save resume first
    client.post("/matcher/save-resume", json={
        "user_external_id": "test-edits-user",
        "resume_text": SAMPLE_RESUME_WITH_EVIDENCE
    })
    
    # 1. Test POST /matcher/suggest-edits
    resp = client.post("/matcher/suggest-edits", json={
        "user_external_id": "test-edits-user",
        "job_description": SAMPLE_JOB_DESC,
        "company": "Enterprise Corp"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) >= 1

    # 2. Test alias POST /api/resume/suggest-edits
    resp_alias = client.post("/api/resume/suggest-edits", json={
        "user_external_id": "test-edits-user",
        "job_description": SAMPLE_JOB_DESC
    })
    assert resp_alias.status_code == 200
    data_alias = resp_alias.json()
    assert "suggestions" in data_alias


def test_suggest_edits_empty_inputs():
    resp = client.post("/matcher/suggest-edits", json={
        "user_external_id": "nonexistent-user",
        "resume_text": "",
        "job_description": SAMPLE_JOB_DESC
    })
    assert resp.status_code == 400


def test_heuristic_fallback_when_model_unavailable():
    # If ML rewrite returns None, heuristic rephraser takes over and produces a clean rewrite
    with patch("app.services.resume_editor.rewrite_single_bullet", return_value=None):
        with patch("app.services.resume_editor.polish_grammar", side_effect=lambda x: x):
            result = generate_resume_edits(
                resume_text=SAMPLE_RESUME_WITH_EVIDENCE,
                job_description=SAMPLE_JOB_DESC
            )
            assert len(result.suggestions) >= 1
