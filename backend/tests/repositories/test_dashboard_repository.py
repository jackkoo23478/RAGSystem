from datetime import datetime

from app.features.dashboard.repository import (
    average_latency_ms,
    count_documents_by_status,
    count_queries_by_status,
    list_recent_documents,
    queries_per_day,
)
from app.features.documents.repository import create_document, update_document_status


def add_document(db, user, name, status=None):
    doc = create_document(db, original_name=name, filename=f"stored-{name}", file_type="pdf", uploaded_by=user.id)
    if status:
        update_document_status(db, doc, status)
    return doc


# ---------- counts ----------

def test_count_documents_by_status(db, user):
    add_document(db, user, "a.pdf")  # a new document is "pending"
    add_document(db, user, "b.pdf", "processed")
    add_document(db, user, "c.pdf", "processed")

    assert count_documents_by_status(db) == {"pending": 1, "processed": 2}


def test_count_queries_by_status(db, user, add_query):
    add_query(user, status="answered")
    add_query(user, status="answered")
    add_query(user, status="failed")

    assert count_queries_by_status(db) == {"answered": 2, "failed": 1}


def test_counts_are_empty_without_data(db):
    assert count_documents_by_status(db) == {}
    assert count_queries_by_status(db) == {}


# ---------- average latency ----------

def test_average_latency(db, user, add_query):
    add_query(user, latency_ms=100)
    add_query(user, latency_ms=300)

    assert average_latency_ms(db) == 200


def test_average_latency_ignores_queries_without_a_latency(db, user, add_query):
    add_query(user, latency_ms=400)
    add_query(user, latency_ms=None)  # recorded before latency existed

    assert average_latency_ms(db) == 400


def test_average_latency_is_none_without_any_latency(db, user, add_query):
    assert average_latency_ms(db) is None

    add_query(user, latency_ms=None)

    assert average_latency_ms(db) is None


# ---------- queries per day ----------

def test_queries_per_day_groups_by_day(db, user, add_query):
    add_query(user, status="answered", latency_ms=100, created_at=datetime(2026, 3, 1, 9, 0))
    add_query(user, status="failed", latency_ms=300, created_at=datetime(2026, 3, 1, 23, 59))
    add_query(user, status="answered", latency_ms=50, created_at=datetime(2026, 3, 2, 0, 0))

    rows = queries_per_day(db, since=datetime(2026, 3, 1))

    assert rows == [("2026-03-01", 2, 1, 200.0), ("2026-03-02", 1, 1, 50.0)]


def test_queries_per_day_leaves_out_earlier_days(db, user, add_query):
    add_query(user, created_at=datetime(2026, 2, 28, 23, 59))
    add_query(user, created_at=datetime(2026, 3, 1, 0, 0))

    rows = queries_per_day(db, since=datetime(2026, 3, 1))

    assert [day for day, *_ in rows] == ["2026-03-01"]


def test_a_day_without_latencies_has_no_average(db, user, add_query):
    add_query(user, created_at=datetime(2026, 3, 1), latency_ms=None)

    assert queries_per_day(db, since=datetime(2026, 3, 1)) == [("2026-03-01", 1, 1, None)]


# ---------- recent documents ----------

def test_recent_documents_are_newest_first_and_limited(db, user):
    for name in ["a.pdf", "b.pdf", "c.pdf"]:
        add_document(db, user, name)

    recent = list_recent_documents(db, limit=2)

    assert [d.original_name for d in recent] == ["c.pdf", "b.pdf"]
