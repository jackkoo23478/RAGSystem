import pytest
from sqlalchemy.exc import IntegrityError

from app.features.rag.models import Query, QueryCitation
from app.features.rag.repository import create_query


def citation(**overrides):
    values = dict(
        document_id=1,
        chunk_id=1,
        document_name="policy.pdf",
        page_number=3,
        snippet="Employees get 14 days of annual leave.",
        score=0.61,
    )
    values.update(overrides)
    return values


def test_saves_query_with_its_citations(db, user):
    query = create_query(
        db, user.id, "How many leave days?", "answered", answer="14 days [1][2]",
        citations=[citation(), citation(document_name="note.txt", page_number=None, score=0.4)],
    )

    saved = db.query(Query).one()
    rows = db.query(QueryCitation).filter_by(query_id=saved.id).order_by(QueryCitation.id).all()
    assert saved.id == query.id
    assert saved.question == "How many leave days?"
    assert saved.answer == "14 days [1][2]"
    assert saved.status == "answered"
    assert [r.document_name for r in rows] == ["policy.pdf", "note.txt"]
    assert [r.page_number for r in rows] == [3, None]


def test_returned_query_has_an_id(db, user):
    assert create_query(db, user.id, "q", "no_evidence").id is not None


def test_query_without_citations(db, user):
    create_query(db, user.id, "q", "no_evidence")

    assert db.query(Query).count() == 1
    assert db.query(QueryCitation).count() == 0


def test_answer_can_be_none(db, user):
    create_query(db, user.id, "q", "failed", answer=None)

    assert db.query(Query).one().answer is None


def test_citation_is_all_or_nothing_with_its_query(db, user):
    bad = citation()
    del bad["snippet"]  # snippet is required

    with pytest.raises(IntegrityError):
        create_query(db, user.id, "q", "answered", answer="x [1]", citations=[citation(), bad])

    assert db.query(Query).count() == 0  # the query was rolled back too
    assert db.query(QueryCitation).count() == 0
