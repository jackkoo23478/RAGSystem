from datetime import date, datetime

import pytest

from app.features.dashboard.service import build_activity, build_summary
from app.features.documents.repository import create_document, update_document_status


def add_document(db, user, name, status):
    doc = create_document(db, original_name=name, filename=f"stored-{name}", file_type="pdf", uploaded_by=user.id)
    update_document_status(db, doc, status)


# ---------- build_summary ----------

def test_summary_of_an_empty_system(db):
    summary = build_summary(db)

    assert summary.documents.total == 0
    assert summary.queries.total == 0
    assert summary.answer_rate is None  # not 0%: nothing was asked, so there is no rate
    assert summary.avg_latency_ms is None


def test_summary_counts_documents_by_status(db, user):
    add_document(db, user, "a.pdf", "processed")
    add_document(db, user, "b.pdf", "processed")
    add_document(db, user, "c.pdf", "failed")
    add_document(db, user, "d.pdf", "flagged")
    add_document(db, user, "e.pdf", "pending")

    docs = build_summary(db).documents

    assert (docs.total, docs.processed, docs.failed, docs.flagged, docs.pending, docs.processing) == (5, 2, 1, 1, 1, 0)


def test_summary_counts_queries_and_computes_the_answer_rate_and_latency(db, user, add_query):
    add_query(user, status="answered", latency_ms=1000)
    add_query(user, status="answered", latency_ms=3000)
    add_query(user, status="no_evidence", latency_ms=50)
    add_query(user, status="failed", latency_ms=None)

    summary = build_summary(db)

    q = summary.queries
    assert (q.total, q.answered, q.no_evidence, q.invalid_answer, q.failed) == (4, 2, 1, 0, 1)
    assert summary.answer_rate == 0.5
    assert summary.avg_latency_ms == 1350  # (1000 + 3000 + 50) / 3, the query without a latency is left out


def test_an_unknown_status_still_counts_in_the_total(db, user, add_query):
    add_query(user, status="answered")
    add_query(user, status="something_new")

    q = build_summary(db).queries

    assert q.total == 2
    assert q.answered == 1


def test_average_latency_is_rounded_to_whole_milliseconds(db, user, add_query):
    add_query(user, latency_ms=100)
    add_query(user, latency_ms=101)

    assert build_summary(db).avg_latency_ms in (100, 101)
    assert isinstance(build_summary(db).avg_latency_ms, int)


# ---------- build_activity ----------

TODAY = date(2026, 3, 10)


def test_activity_has_one_entry_per_day_oldest_first(db):
    result = build_activity(db, days=7, today=TODAY)

    assert [a.date for a in result] == [date(2026, 3, d) for d in range(4, 11)]


def test_days_without_queries_are_zero_not_missing(db, user, add_query):
    add_query(user, status="answered", latency_ms=200, created_at=datetime(2026, 3, 8, 12, 0))

    by_day = {a.date: a for a in build_activity(db, days=5, today=TODAY)}

    assert by_day[date(2026, 3, 8)].queries == 1
    assert by_day[date(2026, 3, 8)].avg_latency_ms == 200
    for empty in [date(2026, 3, 6), date(2026, 3, 7), date(2026, 3, 9), date(2026, 3, 10)]:
        assert by_day[empty].queries == 0
        assert by_day[empty].answered == 0
        assert by_day[empty].avg_latency_ms is None


def test_activity_counts_answered_separately(db, user, add_query):
    add_query(user, status="answered", created_at=datetime(2026, 3, 10, 8, 0))
    add_query(user, status="no_evidence", created_at=datetime(2026, 3, 10, 9, 0))

    today = build_activity(db, days=1, today=TODAY)[0]

    assert (today.queries, today.answered) == (2, 1)


def test_queries_outside_the_window_are_not_counted(db, user, add_query):
    add_query(user, created_at=datetime(2026, 3, 3, 23, 59))  # one day before a 7 day window ending on the 10th

    assert sum(a.queries for a in build_activity(db, days=7, today=TODAY)) == 0


@pytest.mark.parametrize("days", [1, 14, 90])
def test_activity_length_matches_the_requested_days(db, days):
    assert len(build_activity(db, days=days, today=TODAY)) == days
