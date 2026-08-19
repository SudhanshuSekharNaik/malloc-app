"""
Unit tests for Company Insights Engine, Pretrained Transformer Classifiers,
Disagreement Detection Guardrail, Sample Size Confidence Guards, and URL Alignment.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.services.company_insights import (
    classify_company_size,
    classify_industry,
    score_snippets_sentiment,
    detect_size_disagreement,
    extract_company_facts,
    synthesize_culture,
    generate_interview_insights,
    check_url_company_alignment,
    get_company_insights,
    MIN_RELIABLE_SENTIMENT_SAMPLE
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_extract_company_facts():
    # 1. Known prominent company - TCS
    tcs_facts = extract_company_facts("", "tcs")
    assert tcs_facts["founded_year"] == 1968
    assert "615,000+" in tcs_facts["employee_count_estimate"]

    # 2. Known prominent company - Stripe
    stripe_facts = extract_company_facts("", "Stripe")
    assert stripe_facts["founded_year"] == 2010
    assert "7,000" in stripe_facts["employee_count_estimate"]

    # 3. Extracted from raw text
    raw_text = "Founded in 2018, Acme Corp has grown to over 350 employees across 4 continents."
    facts = extract_company_facts(raw_text, "Acme Corp")
    assert facts["founded_year"] == 2018
    assert facts["employee_count_estimate"] == "350"


def test_zero_shot_size_classification_with_mock_model():
    # Mock zero-shot classification pipeline for large company
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "labels": ["large multinational corporation", "established mid-size company", "early-stage startup"],
        "scores": [0.91, 0.07, 0.02]
    }

    with patch("app.services.company_insights._get_size_classifier", return_value=mock_pipeline):
        facts = {"founded_year": 1994, "employee_count_estimate": "1,500,000+"}
        res = classify_company_size("Amazon is a global technology and cloud infrastructure company.", facts, "Amazon")
        assert res["label"] == "Large Multinational Corporation"
        assert res["confidence"] == 0.91
        assert res["disagreement_flag"] is False
        assert "large multinational corporation" in res["all_scores"]


def test_disagreement_flag_triggers_on_fact_conflict():
    # 1. Model says "early-stage startup", but facts indicate 50,000 employees and founded in 1998
    conflict_facts_1 = {"founded_year": 1998, "employee_count_estimate": "50,000+"}
    assert detect_size_disagreement("early-stage startup", conflict_facts_1) is True

    # 2. Model says "large multinational corporation", but facts indicate 10 employees and founded in 2024
    conflict_facts_2 = {"founded_year": 2024, "employee_count_estimate": "10"}
    assert detect_size_disagreement("large multinational corporation", conflict_facts_2) is True

    # 3. Model says "early-stage startup" and facts agree (15 employees, 2023)
    aligned_facts = {"founded_year": 2023, "employee_count_estimate": "15"}
    assert detect_size_disagreement("early-stage startup", aligned_facts) is False

    # 4. Zero-shot size classifier returns disagreement_flag = True on conflict
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "labels": ["early-stage startup", "established mid-size company", "large multinational corporation"],
        "scores": [0.82, 0.12, 0.06]
    }
    with patch("app.services.company_insights._get_size_classifier", return_value=mock_pipeline):
        res = classify_company_size("Enterprise Corp with global offices.", conflict_facts_1, "Enterprise Corp")
        assert res["disagreement_flag"] is True


def test_low_confidence_data_flag_on_missing_facts():
    # When facts are unverified / missing, ensure low_confidence_data is True
    empty_facts = {"founded_year": None, "employee_count_estimate": "unknown"}
    res = classify_company_size("Unknown generic organization with vague description.", empty_facts, "UnknownCorp")
    assert res["low_confidence_data"] is True
    assert res["confidence"] <= 0.40
    assert "Limited" in res["data_quality_note"] or "ungrounded" in res["data_quality_note"].lower()


def test_url_alignment_and_mismatch_detection():
    # 1. Accurate alignment
    aligned, warn = check_url_company_alignment("Stripe", "https://stripe.com")
    assert aligned is True
    assert warn is None

    aligned_tcs, warn_tcs = check_url_company_alignment("tcs", "https://www.tcs.com/")
    assert aligned_tcs is True
    assert warn_tcs is None

    # 2. Mismatch: User enters 'accenture' with 'https://stripe.com'
    misaligned, warn_msg = check_url_company_alignment("accenture", "https://stripe.com")
    assert misaligned is False
    assert warn_msg is not None
    assert "stripe.com" in warn_msg
    assert "accenture" in warn_msg


def test_sentiment_sample_size_guard():
    # 1. Below threshold (total = 2 < 4)
    small_sample = ["Great work atmosphere.", "Fast delivery cycles."]
    res_dict, strength, note = score_snippets_sentiment(small_sample)
    assert res_dict["total"] == 2
    assert strength == "low"
    assert "Limited sample" in note
    assert "directional context" in note

    # 2. High sample (total = 8 >= 4)
    large_sample = [f"Company policy snippet {i} with positive growth" for i in range(8)]
    res_large, strength_large, note_large = score_snippets_sentiment(large_sample)
    assert res_large["total"] == 8
    assert strength_large == "high"


def test_distinct_output_between_tcs_accenture_stripe():
    # Verifies TCS, Accenture, and Stripe return distinct cultural praised points and interview focus areas
    tcs_insights = get_company_insights("tcs", "https://www.tcs.com/")
    acc_insights = get_company_insights("accenture", "https://www.accenture.com/")
    stripe_insights = get_company_insights("stripe", "https://stripe.com/")

    # 1. Facts must be distinct
    assert tcs_insights["classification"]["facts"]["founded_year"] == 1968
    assert acc_insights["classification"]["facts"]["founded_year"] == 1989
    assert stripe_insights["classification"]["facts"]["founded_year"] == 2010

    # 2. Praised aspects must be distinctly tailored
    tcs_praised = " ".join(tcs_insights["culture_synthesis"]["praised_aspects"]).lower()
    acc_praised = " ".join(acc_insights["culture_synthesis"]["praised_aspects"]).lower()
    stripe_praised = " ".join(stripe_insights["culture_synthesis"]["praised_aspects"]).lower()

    assert "tata" in tcs_praised or "stability" in tcs_praised
    assert "consulting" in acc_praised or "client" in acc_praised or "meritocratic" in acc_praised
    assert "craft" in stripe_praised or "memo" in stripe_praised or "api" in stripe_praised

    # 3. Interview stages & focus areas must be distinct
    tcs_focus = " ".join(tcs_insights["interview_insights"]["focus_areas"]).lower()
    acc_focus = " ".join(acc_insights["interview_insights"]["focus_areas"]).lower()
    stripe_focus = " ".join(stripe_insights["interview_insights"]["focus_areas"]).lower()

    assert "sql" in tcs_focus or "fundamentals" in tcs_focus or "qualifier" in " ".join(tcs_insights["interview_insights"]["process_stages"]).lower()
    assert "consulting case" in acc_focus or "transformation" in acc_focus
    assert "idempotency" in stripe_focus or "pair programming" in " ".join(stripe_insights["interview_insights"]["process_stages"]).lower()


def test_company_insights_api_endpoints():
    mock_size = MagicMock(return_value={"labels": ["large multinational corporation", "established mid-size company", "early-stage startup"], "scores": [0.88, 0.09, 0.03]})
    mock_industry = MagicMock(return_value=[{"label": "Financial Technology & Services", "score": 0.85}])
    mock_sentiment = MagicMock(return_value=[{"label": "POSITIVE"}, {"label": "POSITIVE"}, {"label": "NEGATIVE"}])

    with patch("app.services.company_insights._get_size_classifier", return_value=mock_size), \
         patch("app.services.company_insights._get_industry_classifier", return_value=mock_industry), \
         patch("app.services.company_insights._get_sentiment_classifier", return_value=mock_sentiment):

        # 1. Test POST /insights/analyze
        resp = client.post("/insights/analyze", json={
            "company": "Stripe",
            "company_url": "https://stripe.com",
            "role_title": "Senior Backend Engineer"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"] == "Stripe"
        assert "classification" in data
        assert data["classification"]["label"] == "Large Multinational Corporation"
        assert "industry" in data["classification"]
        assert "facts" in data["classification"]
        assert "culture_synthesis" in data
        assert "sentiment_breakdown" in data["culture_synthesis"]
        assert "praised_aspects" in data["culture_synthesis"]
        assert "interview_insights" in data

        # 2. Test alias POST /api/company/insights
        resp_alias = client.post("/api/company/insights", json={
            "company": "Stripe"
        })
        assert resp_alias.status_code == 200
        assert resp_alias.json()["company"] == "Stripe"

        # 3. Test GET /insights/{company_name}
        resp_get = client.get("/insights/Stripe?role_title=Backend+Engineer")
        assert resp_get.status_code == 200
        assert resp_get.json()["company"] == "Stripe"


def test_empty_company_raises_400():
    resp = client.post("/insights/analyze", json={"company": ""})
    assert resp.status_code == 400


def test_heuristic_fallback_when_models_unavailable():
    with patch("app.services.company_insights._get_size_classifier", return_value=None), \
         patch("app.services.company_insights._get_industry_classifier", return_value=None), \
         patch("app.services.company_insights._get_sentiment_classifier", return_value=None):

        insights = get_company_insights("Venture Stealth Labs", about_text="Seed stage AI robotics startup with 12 engineers.")
        assert insights["company"] == "Venture Stealth Labs"
        assert "classification" in insights
        assert insights["classification"]["label"] == "Early-Stage Startup"
        assert "sentiment_breakdown" in insights["culture_synthesis"]
        assert len(insights["culture_synthesis"]["praised_aspects"]) >= 1
