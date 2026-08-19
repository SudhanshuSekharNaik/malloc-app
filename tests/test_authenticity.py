"""
Unit & Integration Tests for Job Post Authenticity Checker.

Tests:
1. All-clear legitimate job posting (low risk)
2. Layer 1 critical red flags detection (high risk)
3. Layer 2 ML classifier mock & unavailable fallback handling
4. Layer 3 LLM malformed JSON & failure handling
5. URL fetch degradation and error response
6. API endpoint route testing
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.authenticity_checker import (
    analyze_job_authenticity,
    run_layer1_checks,
    classify_job_posting_ml,
    run_llm_reasoning_layer,
    compute_overall_authenticity_risk,
    ClassifierSignal,
    LLMReasoningSignal,
    AuthenticityCheckItem
)

client = TestClient(app)

LEGITIMATE_JOB_TEXT = """
Senior Software Engineer - Cloud Platforms
Acme Technologies Inc. (careers@acme.com)
Location: San Francisco, CA (Hybrid)

About the Role:
We are looking for a Senior Software Engineer with 5+ years of experience in Python, FastAPI, and Kubernetes.
You will architect high-throughput microservices, optimize PostgreSQL queries, and collaborate with product teams.

Requirements:
- Strong proficiency in Python 3.10+ and async frameworks
- Experience with Docker, Kubernetes, and CI/CD pipelines
- Excellent problem-solving and communication skills
- Bachelor's degree in Computer Science or equivalent practical experience

Compensation: $160,000 - $195,000 base salary + equity + comprehensive health benefits.
"""

SCAM_JOB_TEXT = """
URGENT WORK FROM HOME DATA ENTRY - EARN $5000 A WEEK NO EXPERIENCE NEEDED!!!!
Contact HR Manager directly on Telegram: @hiring_agent_fast or email jobs-hiring@gmail.com
You will receive an immediate job offer today!
We will mail you a $3500 equipment check to purchase home office hardware from our approved vendor.
A $50 administrative processing fee is required upfront for background clearance.
"""


def test_layer1_all_clear():
    checks = run_layer1_checks(LEGITIMATE_JOB_TEXT, "https://acme.com/jobs/senior-engineer")
    fails = [c for c in checks if c.status == "fail"]
    assert len(fails) == 0
    assert any(c.name == "contact_email_domain" and c.status == "pass" for c in checks)


def test_layer1_red_flags_detection():
    checks = run_layer1_checks(SCAM_JOB_TEXT, "http://bit.ly/urgent-job-offer")
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]

    # Free email domain, telegram contact, upfront fee, URL shortener
    assert len(fails) >= 2
    assert any(c.name == "contact_email_domain" and c.status == "fail" for c in checks)
    assert any(c.name == "messaging_channel_screening" and c.status == "fail" for c in checks)
    assert any(c.name == "upfront_fees_and_equipment" and c.status == "fail" for c in checks)


def test_layer2_classifier_mock():
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_torch = MagicMock()

    # Mock output logits for Real Job (index 0)
    mock_logits = MagicMock()
    mock_model.return_value.logits = mock_logits
    mock_torch.no_grad.return_value.__enter__.return_value = None
    mock_torch.softmax.return_value = [MagicMock(argmax=MagicMock(return_value=0), __getitem__=lambda s, i: 0.95)]

    with patch("app.services.authenticity_checker._get_bert_classifier", return_value=(mock_tokenizer, mock_model, mock_torch)):
        signal = classify_job_posting_ml(LEGITIMATE_JOB_TEXT)
        assert signal.status == "completed"
        assert signal.predicted_label == "Real Job"
        assert signal.confidence == 0.95


def test_layer2_classifier_unavailable_graceful_fallback():
    with patch("app.services.authenticity_checker._get_bert_classifier", side_effect=RuntimeError("Model download failed")):
        signal = classify_job_posting_ml(LEGITIMATE_JOB_TEXT)
        assert signal.status == "unavailable"
        assert signal.predicted_label is None
        assert "unavailable" in signal.detail.lower()


def test_layer3_llm_reasoning_success():
    mock_json = """
    {
      "risk_level": "high",
      "matched_patterns": [
        {
          "pattern": "Upfront Equipment Check Scam",
          "evidence": "mail you a $3500 equipment check",
          "explanation": "Requesting candidate to cash check and purchase from third party vendor."
        }
      ],
      "reasoning_summary": "Posting displays high-risk indicators matching advance check overpayment fraud."
    }
    """
    with patch("app.services.authenticity_checker.call_llm", return_value=mock_json):
        signal = run_llm_reasoning_layer(SCAM_JOB_TEXT, [{"title": "Equipment Check", "category": "Fraud", "description": "..."}])
        assert signal.status == "completed"
        assert signal.risk_level == "high"
        assert len(signal.matched_patterns) == 1
        assert "equipment check" in signal.matched_patterns[0].evidence


def test_layer3_llm_malformed_json_fallback():
    with patch("app.services.authenticity_checker.call_llm", return_value="Not valid JSON text output from LLM"):
        signal = run_llm_reasoning_layer(SCAM_JOB_TEXT, [{"title": "Equipment Check", "category": "Fraud", "description": "..."}])
        assert signal.status == "unavailable"
        assert signal.risk_level is None


def test_layer3_llm_call_failure_fallback():
    with patch("app.services.authenticity_checker.call_llm", side_effect=RuntimeError("Groq API rate limit")):
        signal = run_llm_reasoning_layer(SCAM_JOB_TEXT, [{"title": "Equipment Check", "category": "Fraud", "description": "..."}])
        assert signal.status == "unavailable"
        assert signal.risk_level is None


def test_full_pipeline_low_risk_integration():
    sample_patterns = [{"title": "Equipment Check", "category": "Fraud", "description": "..."}]
    with patch("app.services.authenticity_checker.retrieve_relevant_fraud_patterns", return_value=sample_patterns):
        with patch("app.services.authenticity_checker.classify_job_posting_ml", return_value=ClassifierSignal(status="completed", predicted_label="Real Job", confidence=0.92)):
            with patch("app.services.authenticity_checker.call_llm", return_value='{"risk_level": "low", "matched_patterns": [], "reasoning_summary": "Legitimate professional posting."}'):
                report = analyze_job_authenticity(LEGITIMATE_JOB_TEXT, "https://acme.com/careers/engineer")
                assert report.risk_level == "low"
                assert report.risk_score <= 30
                assert "Low Risk" in report.verdict_label


def test_api_endpoint_authenticity_check():
    payload = {
        "job_text": LEGITIMATE_JOB_TEXT,
        "company": "Acme Inc",
        "role_title": "Senior Engineer"
    }

    sample_patterns = [{"title": "Equipment Check", "category": "Fraud", "description": "..."}]
    with patch("app.services.authenticity_checker.retrieve_relevant_fraud_patterns", return_value=sample_patterns):
        with patch("app.services.authenticity_checker.classify_job_posting_ml", return_value=ClassifierSignal(status="completed", predicted_label="Real Job", confidence=0.88)):
            with patch("app.services.authenticity_checker.call_llm", return_value='{"risk_level": "low", "matched_patterns": [], "reasoning_summary": "Standard posting."}'):
                resp = client.post("/authenticity/check", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert "risk_level" in data
                assert "layer1_heuristics" in data
                assert "disclaimer" in data
                assert len(data["layer1_heuristics"]) >= 5


def test_api_endpoint_alias_jobs_authenticity_check():
    payload = {
        "job_text": SCAM_JOB_TEXT,
        "url": "http://bit.ly/fake-job"
    }

    sample_patterns = [{"title": "Equipment Check", "category": "Fraud", "description": "..."}]
    with patch("app.services.authenticity_checker.retrieve_relevant_fraud_patterns", return_value=sample_patterns):
        with patch("app.services.authenticity_checker.classify_job_posting_ml", return_value=ClassifierSignal(status="completed", predicted_label="Fake Job", confidence=0.85)):
            with patch("app.services.authenticity_checker.call_llm", return_value='{"risk_level": "high", "matched_patterns": [{"pattern": "Equipment Check", "evidence": "$3500 equipment check", "explanation": "Fraud"}], "reasoning_summary": "High risk signals."}'):
                resp = client.post("/api/jobs/authenticity-check", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data["risk_level"] == "high"
                assert data["risk_score"] >= 70


def test_api_endpoint_empty_input_400():
    resp = client.post("/authenticity/check", json={"job_text": "   "})
    assert resp.status_code == 400
    assert "No job posting content provided" in resp.json()["detail"]


def test_api_endpoint_url_fetch_failure_degradation():
    with patch("app.routers.authenticity.fetch_job_from_url") as mock_fetch:
        mock_fetch.return_value = MagicMock(success=False, description="", message="Access denied by site bot blocker")
        resp = client.post("/authenticity/check", json={"url": "https://linkedin.com/jobs/view/12345"})
        assert resp.status_code == 400
        assert "Access denied by site bot blocker" in resp.json()["detail"]
