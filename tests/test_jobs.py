"""
Job tracker tests. No LLM involved in this feature yet - pure CRUD +
the due-followups date logic, so no mocking needed here.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_memora.db"

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_create_job_defaults_applied_date_and_followup():
    resp = client.post(
        "/jobs",
        json={"user_external_id": "j1", "company": "Acme Corp", "role_title": "Backend Engineer"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "applied"
    assert body["applied_date"] is not None
    assert body["follow_up_date"] is not None


def test_list_jobs_for_user():
    client.post("/jobs", json={"user_external_id": "j2", "company": "A", "role_title": "X"})
    client.post("/jobs", json={"user_external_id": "j2", "company": "B", "role_title": "Y"})
    resp = client.get("/jobs/j2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_jobs_unknown_user_returns_empty():
    resp = client.get("/jobs/no-such-user")
    assert resp.status_code == 200
    assert resp.json() == []


def test_update_job_status():
    create = client.post(
        "/jobs", json={"user_external_id": "j3", "company": "Acme", "role_title": "Eng"}
    )
    job_id = create.json()["id"]

    resp = client.patch(f"/jobs/{job_id}", json={"status": "interview"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "interview"


def test_update_unknown_job_404():
    resp = client.patch("/jobs/does-not-exist", json={"status": "offer"})
    assert resp.status_code == 404


def test_delete_job():
    create = client.post(
        "/jobs", json={"user_external_id": "j4", "company": "Acme", "role_title": "Eng"}
    )
    job_id = create.json()["id"]

    resp = client.delete(f"/jobs/{job_id}")
    assert resp.status_code == 204

    listed = client.get("/jobs/j4")
    assert listed.json() == []


def test_due_followups_only_returns_overdue_open_applications():
    now = datetime.now(timezone.utc)

    # overdue, still "applied" -> should show up
    client.post(
        "/jobs",
        json={
            "user_external_id": "j5",
            "company": "Overdue Co",
            "role_title": "Eng",
            "applied_date": (now - timedelta(days=20)).isoformat(),
            "follow_up_days": 7,
        },
    )
    # not yet due -> should NOT show up
    client.post(
        "/jobs",
        json={
            "user_external_id": "j5",
            "company": "Too Soon Co",
            "role_title": "Eng",
            "applied_date": now.isoformat(),
            "follow_up_days": 30,
        },
    )
    # overdue but rejected (terminal) -> should NOT show up
    rejected = client.post(
        "/jobs",
        json={
            "user_external_id": "j5",
            "company": "Rejected Co",
            "role_title": "Eng",
            "applied_date": (now - timedelta(days=20)).isoformat(),
            "follow_up_days": 7,
        },
    )
    client.patch(f"/jobs/{rejected.json()['id']}", json={"status": "rejected"})

    resp = client.get("/jobs/j5/due-followups")
    assert resp.status_code == 200
    companies = [j["company"] for j in resp.json()]
    assert companies == ["Overdue Co"]
