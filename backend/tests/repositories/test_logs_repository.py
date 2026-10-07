from datetime import datetime

import pytest

from app.features.auth.models import User
from app.features.logs.repository import get_log, list_logs


@pytest.fixture
def other_user(db):
    u = User(email="Other.Person@example.com", password_hash="not-a-real-hash", role="user")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def questions(rows):
    return [query.question for query, _email in rows]


# ---------- list_logs ----------

def test_lists_the_queries_of_all_users_with_the_email_of_the_asker(db, user, other_user, add_query):
    add_query(user, "from admin")
    add_query(other_user, "from other")

    rows, total = list_logs(db)

    assert total == 2
    assert {(q.question, email) for q, email in rows} == {
        ("from admin", "admin@example.com"),
        ("from other", "Other.Person@example.com"),
    }


def test_newest_first(db, user, add_query):
    add_query(user, "old", created_at=datetime(2026, 1, 1))
    add_query(user, "new", created_at=datetime(2026, 3, 1))
    add_query(user, "middle", created_at=datetime(2026, 2, 1))

    rows, _ = list_logs(db)

    assert questions(rows) == ["new", "middle", "old"]


def test_filter_by_status(db, user, add_query):
    add_query(user, "good", status="answered")
    add_query(user, "refused", status="no_evidence")
    add_query(user, "broken", status="failed")

    rows, total = list_logs(db, status="no_evidence")

    assert questions(rows) == ["refused"]
    assert total == 1


def test_search_matches_part_of_the_question_ignoring_case(db, user, add_query):
    add_query(user, "How many Leave days do I get?")
    add_query(user, "Where is the printer?")

    rows, _ = list_logs(db, search="LEAVE")

    assert questions(rows) == ["How many Leave days do I get?"]


def test_search_matches_the_email_of_the_asker(db, user, other_user, add_query):
    add_query(user, "mine")
    add_query(other_user, "theirs")

    rows, _ = list_logs(db, search="other.person")

    assert questions(rows) == ["theirs"]


def test_percent_and_underscore_in_the_search_are_not_wildcards(db, user, add_query):
    add_query(user, "100% sure")
    add_query(user, "a_b")
    add_query(user, "unrelated")

    assert questions(list_logs(db, search="%")[0]) == ["100% sure"]
    assert questions(list_logs(db, search="_")[0]) == ["a_b"]


def test_filters_combine(db, user, add_query):
    add_query(user, "leave answered", status="answered")
    add_query(user, "leave refused", status="no_evidence")
    add_query(user, "other refused", status="no_evidence")

    rows, total = list_logs(db, status="no_evidence", search="leave")

    assert questions(rows) == ["leave refused"]
    assert total == 1


def test_pagination_returns_a_page_and_the_total_of_all_matches(db, user, add_query):
    for i in range(5):
        add_query(user, f"q{i}", created_at=datetime(2026, 1, 1 + i))  # q4 is the newest

    first, total = list_logs(db, limit=2, offset=0)
    second, _ = list_logs(db, limit=2, offset=2)
    last, _ = list_logs(db, limit=2, offset=4)

    assert total == 5
    assert questions(first) == ["q4", "q3"]
    assert questions(second) == ["q2", "q1"]
    assert questions(last) == ["q0"]


def test_empty_result(db):
    rows, total = list_logs(db)

    assert rows == []
    assert total == 0


# ---------- get_log ----------

def test_get_log_returns_the_query_of_any_user(db, other_user, add_query):
    query = add_query(other_user, "theirs")

    found_query, email = get_log(db, query.id)

    assert found_query.id == query.id
    assert email == "Other.Person@example.com"


def test_get_log_of_a_missing_id_is_none(db):
    assert get_log(db, 999) is None
