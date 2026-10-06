import pytest

from app.features.auth.models import User
from app.features.rag.repository import (
    create_query,
    get_citations_for_query,
    get_query_for_user,
    list_queries_by_user,
)


@pytest.fixture
def other_user(db):
    u = User(email="other@example.com", password_hash="not-a-real-hash", role="user")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def citation(name="policy.pdf", **overrides):
    values = dict(
        document_id=1, chunk_id=1, document_name=name, page_number=1, snippet="some text", score=0.5,
    )
    values.update(overrides)
    return values


# ---------- list_queries_by_user ----------

def test_list_returns_only_the_users_own_queries(db, user, other_user):
    create_query(db, user.id, "mine 1", "answered")
    create_query(db, user.id, "mine 2", "no_evidence")
    create_query(db, other_user.id, "theirs", "answered")

    mine = list_queries_by_user(db, user.id)

    assert sorted(q.question for q in mine) == ["mine 1", "mine 2"]
    assert [q.question for q in list_queries_by_user(db, other_user.id)] == ["theirs"]


def test_list_is_newest_first(db, user):
    for text in ["first", "second", "third"]:
        create_query(db, user.id, text, "answered")

    assert [q.question for q in list_queries_by_user(db, user.id)] == ["third", "second", "first"]


def test_list_respects_limit(db, user):
    for i in range(5):
        create_query(db, user.id, f"q{i}", "answered")

    result = list_queries_by_user(db, user.id, limit=2)

    assert [q.question for q in result] == ["q4", "q3"]


def test_list_is_empty_when_the_user_has_no_queries(db, user, other_user):
    create_query(db, other_user.id, "theirs", "answered")

    assert list_queries_by_user(db, user.id) == []


# ---------- get_query_for_user ----------

def test_get_own_query(db, user):
    created = create_query(db, user.id, "mine", "answered")

    found = get_query_for_user(db, created.id, user.id)

    assert found is not None
    assert found.id == created.id


def test_get_someone_elses_query_returns_none(db, user, other_user):
    theirs = create_query(db, other_user.id, "theirs", "answered")

    assert get_query_for_user(db, theirs.id, user.id) is None


def test_get_unknown_query_returns_none(db, user):
    assert get_query_for_user(db, 999, user.id) is None


# ---------- get_citations_for_query ----------

def test_citations_come_back_in_creation_order(db, user):
    q = create_query(
        db, user.id, "q", "answered",
        citations=[citation("a.pdf"), citation("b.pdf"), citation("c.pdf")],
    )

    assert [c.document_name for c in get_citations_for_query(db, q.id)] == ["a.pdf", "b.pdf", "c.pdf"]


def test_citations_belong_only_to_their_query(db, user):
    q1 = create_query(db, user.id, "q1", "answered", citations=[citation("one.pdf")])
    q2 = create_query(db, user.id, "q2", "answered", citations=[citation("two.pdf"), citation("three.pdf")])

    assert [c.document_name for c in get_citations_for_query(db, q1.id)] == ["one.pdf"]
    assert [c.document_name for c in get_citations_for_query(db, q2.id)] == ["two.pdf", "three.pdf"]


def test_query_without_citations_returns_empty_list(db, user):
    q = create_query(db, user.id, "q", "no_evidence")

    assert get_citations_for_query(db, q.id) == []
