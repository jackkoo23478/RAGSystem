from datetime import datetime

import pytest

from app.features.documents.repository import create_document, update_document_status

PREFIX = "/api/v1/dashboard"
ENDPOINTS = ["/summary", "/activity", "/recent-documents", "/recent-queries"]


def add_document(db, user, name, status="processed"):
    doc = create_document(db, original_name=name, filename=f"stored-{name}", file_type="pdf", uploaded_by=user.id)
    update_document_status(db, doc, status)
    return doc


# ---------- who may look ----------

@pytest.mark.parametrize("path", ENDPOINTS)
def test_a_normal_user_is_forbidden(client, user_headers, path):
    assert client.get(f"{PREFIX}{path}", headers=user_headers).status_code == 403


@pytest.mark.parametrize("path", ENDPOINTS)
def test_without_a_token_the_request_is_rejected(client, path):
    # 403 on FastAPI 0.115 (pinned), 401 on newer versions
    assert client.get(f"{PREFIX}{path}").status_code in (401, 403)


# ---------- summary ----------

def test_summary_of_an_empty_system(client, admin_headers):
    res = client.get(f"{PREFIX}/summary", headers=admin_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["documents"]["total"] == 0
    assert body["queries"]["total"] == 0
    assert body["answer_rate"] is None
    assert body["avg_latency_ms"] is None


def test_summary_with_data(client, admin_headers, db, user, add_query):
    add_document(db, user, "a.pdf", "processed")
    add_document(db, user, "b.pdf", "failed")
    add_query(user, status="answered", latency_ms=200)
    add_query(user, status="no_evidence", latency_ms=400)

    body = client.get(f"{PREFIX}/summary", headers=admin_headers).json()

    assert body["documents"] == {"total": 2, "pending": 0, "processing": 0, "processed": 1, "failed": 1, "flagged": 0}
    assert body["queries"] == {"total": 2, "answered": 1, "no_evidence": 1, "invalid_answer": 0, "failed": 0}
    assert body["answer_rate"] == 0.5
    assert body["avg_latency_ms"] == 300


# ---------- activity ----------

def test_activity_defaults_to_14_days(client, admin_headers):
    res = client.get(f"{PREFIX}/activity", headers=admin_headers)

    assert res.status_code == 200
    assert len(res.json()) == 14
    assert set(res.json()[0]) == {"date", "queries", "answered", "avg_latency_ms"}


def test_activity_counts_todays_queries(client, admin_headers, user, add_query):
    add_query(user, status="answered", latency_ms=120, created_at=datetime.utcnow())

    last_day = client.get(f"{PREFIX}/activity?days=3", headers=admin_headers).json()[-1]

    assert last_day["queries"] == 1
    assert last_day["answered"] == 1
    assert last_day["avg_latency_ms"] == 120


@pytest.mark.parametrize("days", [0, 91, -1])
def test_activity_rejects_a_window_out_of_range(client, admin_headers, days):
    assert client.get(f"{PREFIX}/activity?days={days}", headers=admin_headers).status_code == 422


# ---------- recent ----------

def test_recent_documents_newest_first(client, admin_headers, db, user):
    for name in ["a.pdf", "b.pdf", "c.pdf"]:
        add_document(db, user, name)

    res = client.get(f"{PREFIX}/recent-documents?limit=2", headers=admin_headers)

    assert [d["original_name"] for d in res.json()] == ["c.pdf", "b.pdf"]


def test_recent_queries_show_who_asked(client, admin_headers, user, add_query):
    add_query(user, "How many leave days?", status="answered", latency_ms=90)

    item = client.get(f"{PREFIX}/recent-queries", headers=admin_headers).json()[0]

    assert item["question"] == "How many leave days?"
    assert item["user_email"] == "admin@example.com"
    assert item["status"] == "answered"
    assert item["latency_ms"] == 90


def test_recent_queries_never_include_an_answer(client, admin_headers, user, add_query):
    add_query(user, status="answered", answer="secret text [1]")

    item = client.get(f"{PREFIX}/recent-queries", headers=admin_headers).json()[0]

    assert "answer" not in item


@pytest.mark.parametrize("path", ["/recent-documents", "/recent-queries"])
def test_recent_lists_reject_a_limit_out_of_range(client, admin_headers, path):
    assert client.get(f"{PREFIX}{path}?limit=0", headers=admin_headers).status_code == 422
    assert client.get(f"{PREFIX}{path}?limit=21", headers=admin_headers).status_code == 422
