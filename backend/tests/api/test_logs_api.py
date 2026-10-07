from datetime import datetime

import pytest

from app.features.rag.repository import create_query

PREFIX = "/api/v1/logs"


# ---------- who may look ----------

def test_a_normal_user_is_forbidden(client, user_headers):
    assert client.get(PREFIX, headers=user_headers).status_code == 403
    assert client.get(f"{PREFIX}/1", headers=user_headers).status_code == 403


def test_without_a_token_the_request_is_rejected(client):
    # 403 on FastAPI 0.115 (pinned), 401 on newer versions
    assert client.get(PREFIX).status_code in (401, 403)
    assert client.get(f"{PREFIX}/1").status_code in (401, 403)


# ---------- list ----------

def test_empty_list(client, admin_headers):
    res = client.get(PREFIX, headers=admin_headers)

    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_list_shows_every_users_queries_newest_first(client, admin_headers, user, add_query):
    add_query(user, "older", created_at=datetime(2026, 1, 1), latency_ms=100)
    add_query(user, "newer", created_at=datetime(2026, 2, 1), latency_ms=200)

    body = client.get(PREFIX, headers=admin_headers).json()

    assert [i["question"] for i in body["items"]] == ["newer", "older"]
    first = body["items"][0]
    assert first["user_email"] == "admin@example.com"
    assert first["latency_ms"] == 200
    assert set(first) == {"id", "user_id", "user_email", "question", "status", "latency_ms", "created_at"}  # no answer


def test_filter_by_status_and_search(client, admin_headers, user, add_query):
    add_query(user, "leave answered", status="answered")
    add_query(user, "leave refused", status="no_evidence")
    add_query(user, "printer refused", status="no_evidence")

    body = client.get(f"{PREFIX}?status=no_evidence&search=leave", headers=admin_headers).json()

    assert [i["question"] for i in body["items"]] == ["leave refused"]
    assert body["total"] == 1


def test_pagination(client, admin_headers, user, add_query):
    for i in range(5):
        add_query(user, f"q{i}", created_at=datetime(2026, 1, 1 + i))

    body = client.get(f"{PREFIX}?limit=2&offset=2", headers=admin_headers).json()

    assert [i["question"] for i in body["items"]] == ["q2", "q1"]
    assert (body["total"], body["limit"], body["offset"]) == (5, 2, 2)


def test_unknown_status_is_rejected(client, admin_headers):
    assert client.get(f"{PREFIX}?status=bogus", headers=admin_headers).status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_paging_values_out_of_range_are_rejected(client, admin_headers, query):
    assert client.get(f"{PREFIX}?{query}", headers=admin_headers).status_code == 422


def test_search_text_that_is_too_long_is_rejected(client, admin_headers):
    assert client.get(f"{PREFIX}?search={'x' * 101}", headers=admin_headers).status_code == 422


# ---------- detail ----------

def test_detail_shows_the_answer_and_citations_of_any_user(client, admin_headers, db, user):
    query = create_query(
        db, user.id, "How many leave days?", "answered", answer="You get 14 days. [1]",
        citations=[dict(document_id=1, chunk_id=1, document_name="policy.pdf", page_number=3, snippet="14 days", score=0.8)],
        latency_ms=250,
    )

    body = client.get(f"{PREFIX}/{query.id}", headers=admin_headers).json()

    assert body["answer"] == "You get 14 days. [1]"
    assert body["user_email"] == "admin@example.com"
    assert body["latency_ms"] == 250
    assert body["citations"][0]["document_name"] == "policy.pdf"
    assert body["citations"][0]["page_number"] == 3


def test_an_invalid_answer_stays_hidden_from_the_admin_too(client, admin_headers, db, user):
    query = create_query(db, user.id, "q", "invalid_answer", answer="PWNED")

    body = client.get(f"{PREFIX}/{query.id}", headers=admin_headers).json()

    assert body["answer"] is None
    assert "PWNED" not in client.get(f"{PREFIX}/{query.id}", headers=admin_headers).text


def test_detail_of_a_missing_query_is_404(client, admin_headers):
    assert client.get(f"{PREFIX}/999", headers=admin_headers).status_code == 404
