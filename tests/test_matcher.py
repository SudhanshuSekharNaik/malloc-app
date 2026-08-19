"""
Tests for AI Resume vs Job Matcher.
"""
import io
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.services.scraper import parse_job_html
from app.services.resume_parser import extract_resume_text

client = TestClient(app)

SAMPLE_RESUME_TEXT = """
Jane Doe
Senior Full-Stack & AI Engineer
Email: jane.doe@example.com

SKILLS:
- Languages: Python, JavaScript, TypeScript, SQL
- Frameworks: FastAPI, React, Node.js, Next.js
- Tools: Docker, Git, PostgreSQL, Redis, Linux
- AI & ML: LangChain, Groq, Whisper, Vector Databases (FAISS)

EXPERIENCE:
Senior Software Engineer at TechCorp (2021 - Present)
- Architected asynchronous REST and GraphQL APIs using FastAPI handling 50k req/min.
- Integrated AI conversational assistants with RAG memory retrieval.
- Led a team of 4 engineers and improved release velocity by 35%.
"""

SAMPLE_JOB_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Senior AI Backend Engineer at TechNova</title>
  <meta property="og:title" content="Senior AI Backend Engineer at TechNova">
  <meta property="og:description" content="We are looking for a Senior AI Backend Engineer proficient in Python, FastAPI, and Docker.">
</head>
<body>
  <div class="job-description">
    <h1>Senior AI Backend Engineer</h1>
    <p>TechNova is building next-generation intelligent agent systems.</p>
    <h3>Requirements:</h3>
    <ul>
      <li>5+ years of experience with Python and FastAPI</li>
      <li>Strong database design with PostgreSQL</li>
      <li>Experience with Docker and Kubernetes</li>
      <li>Familiarity with LLMs and Vector Search</li>
    </ul>
  </div>
</body>
</html>
"""

MOCK_MATCH_JSON = json.dumps({
    "match_score": 88,
    "verdict": "Strong Match",
    "company": "TechNova",
    "role_title": "Senior AI Backend Engineer",
    "summary": "Candidate matches strong technical background in Python, FastAPI, and Vector Search.",
    "skills_matched": ["Python", "FastAPI", "PostgreSQL", "Docker", "Vector Search"],
    "missing_skills": ["Kubernetes"],
    "experience_fit": "Candidate has 5+ years matching the Senior Engineer seniority requirement.",
    "key_strengths": [
        "Direct experience building high-throughput FastAPI microservices",
        "Hands-on AI and vector search integration"
    ],
    "recommendations": [
        "Highlight familiarity with container orchestration in the technical summary."
    ],
    "tailored_pitch": "With proven experience architecting scalable FastAPI microservices and AI agent memory systems, I am excited to help TechNova scale its intelligent agent platform."
})


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_html_job_parser():
    scraped = parse_job_html("https://example.com/job/123", SAMPLE_JOB_HTML)
    assert scraped.success is True
    assert "TechNova" in scraped.company or "TechNova" in scraped.role_title
    assert "Senior AI Backend Engineer" in scraped.role_title
    assert "Python" in scraped.description


def test_resume_text_extractor():
    text = extract_resume_text(SAMPLE_RESUME_TEXT.encode("utf-8"), "resume.txt")
    assert "Senior Full-Stack & AI Engineer" in text
    assert "FastAPI" in text


def test_save_and_get_user_resume():
    # Save resume text
    resp = client.post("/matcher/save-resume", json={
        "user_external_id": "test-user-1",
        "resume_text": SAMPLE_RESUME_TEXT,
        "file_name": "master_resume.txt"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"

    # Retrieve resume
    get_resp = client.get("/matcher/resume/test-user-1")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["has_resume"] is True
    assert "Jane Doe" in data["resume_text"]


def test_upload_resume_file():
    file_bytes = io.BytesIO(SAMPLE_RESUME_TEXT.encode("utf-8"))
    resp = client.post(
        "/matcher/upload-resume",
        data={"user_external_id": "test-user-2"},
        files={"file": ("my_resume.txt", file_bytes, "text/plain")}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert "Jane Doe" in resp.json()["resume_text"]


@patch("app.services.job_matcher.call_llm", return_value=MOCK_MATCH_JSON)
def test_analyze_match_endpoint(mock_llm):
    # First save resume
    client.post("/matcher/save-resume", json={
        "user_external_id": "test-user-3",
        "resume_text": SAMPLE_RESUME_TEXT
    })

    # Run analysis
    resp = client.post("/matcher/analyze", json={
        "user_external_id": "test-user-3",
        "job_description": "We need a Senior AI Backend Engineer proficient in Python and FastAPI.",
        "company": "TechNova",
        "role_title": "Senior AI Backend Engineer"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_score"] == 88
    assert data["verdict"] == "Strong Match"
    assert "Python" in data["skills_matched"]
    assert "Kubernetes" in data["missing_skills"]
    assert len(data["recommendations"]) > 0
    assert len(data["tailored_pitch"]) > 10
    mock_llm.assert_called_once()


def test_multi_resume_management():
    # Save first resume
    resp1 = client.post("/matcher/save-resume", json={
        "user_external_id": "test-multi-user",
        "title": "Full-Stack Resume",
        "resume_text": SAMPLE_RESUME_TEXT,
        "is_primary": True
    })
    assert resp1.status_code == 200
    res1_id = resp1.json()["id"]

    # Save second resume
    resp2 = client.post("/matcher/save-resume", json={
        "user_external_id": "test-multi-user",
        "title": "AI/ML Specialist Resume",
        "resume_text": "AI/ML Engineer with PyTorch, TensorFlow, LLMs, and RAG.",
        "is_primary": False
    })
    assert resp2.status_code == 200
    res2_id = resp2.json()["id"]

    # List resumes
    list_resp = client.get("/matcher/resumes/test-multi-user")
    assert list_resp.status_code == 200
    resumes = list_resp.json()
    assert len(resumes) == 2
    titles = [r["title"] for r in resumes]
    assert "Full-Stack Resume" in titles
    assert "AI/ML Specialist Resume" in titles

    # Delete second resume
    del_resp = client.delete(f"/matcher/resumes/{res2_id}")
    assert del_resp.status_code == 204

    # Verify count is now 1
    list_resp2 = client.get("/matcher/resumes/test-multi-user")
    assert len(list_resp2.json()) == 1


def test_heuristic_fallback_matcher_without_api_key():
    # Without mock_llm, calls fallback heuristic matcher if key unconfigured
    resp = client.post("/matcher/analyze", json={
        "user_external_id": "test-fallback-user",
        "resume_text": "Senior Python and FastAPI backend engineer with Docker and PostgreSQL.",
        "job_description": "We are seeking a Python engineer experienced with FastAPI, Docker, PostgreSQL, and Kubernetes.",
        "company": "NextGen Systems",
        "role_title": "Senior Backend Engineer"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_score"] >= 50
    assert "Python" in data["skills_matched"]
    assert "FastAPI" in data["skills_matched"]
    assert "Kubernetes" in data["missing_skills"]
    assert len(data["tailored_pitch"]) > 10

