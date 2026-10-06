import pytest
from sqlalchemy.exc import IntegrityError

from app.features.documents.repository import (
    create_chunks,
    create_document,
    delete_chunks_by_document,
    delete_document,
)
from app.features.rag.models import Query, QueryCitation


def make_query(db, user, status="answered", answer="14 days.", question="How many leave days?"):
    q = Query(user_id=user.id, question=question, answer=answer, status=status)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def make_citation(db, query, **overrides):
    values = dict(
        query_id=query.id,
        document_id=1,
        chunk_id=1,
        document_name="policy.pdf",
        page_number=3,
        snippet="Employees get 14 days of annual leave.",
        score=0.61,
    )
    values.update(overrides)
    c = QueryCitation(**values)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_query_with_citations_round_trip(db, user):
    q = make_query(db, user)
    make_citation(db, q, page_number=3, score=0.61)
    make_citation(db, q, page_number=None, score=0.44, document_name="note.txt")

    saved = db.query(Query).one()
    citations = db.query(QueryCitation).filter_by(query_id=saved.id).order_by(QueryCitation.id).all()

    assert saved.user_id == user.id
    assert saved.question == "How many leave days?"
    assert saved.answer == "14 days."
    assert saved.status == "answered"
    assert [c.page_number for c in citations] == [3, None]
    assert [c.document_name for c in citations] == ["policy.pdf", "note.txt"]
    assert citations[0].score == pytest.approx(0.61)


def test_created_at_is_filled_automatically(db, user):
    assert make_query(db, user).created_at is not None


@pytest.mark.parametrize("status", ["no_evidence", "failed"])
def test_answer_can_be_empty_for_refused_or_failed_queries(db, user, status):
    q = make_query(db, user, status=status, answer=None)

    assert db.query(Query).one().answer is None
    assert db.query(Query).one().status == status
    assert db.query(QueryCitation).filter_by(query_id=q.id).count() == 0


def test_question_is_required(db, user):
    db.add(Query(user_id=user.id, question=None, status="answered"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_status_is_required(db, user):
    db.add(Query(user_id=user.id, question="hi", status=None))

    with pytest.raises(IntegrityError):
        db.commit()


def test_citation_needs_a_query(db):
    db.add(QueryCitation(
        query_id=None, document_name="a.pdf", snippet="text", score=0.5,
    ))

    with pytest.raises(IntegrityError):
        db.commit()


def test_citation_needs_snippet_and_score(db, user):
    q = make_query(db, user)
    db.add(QueryCitation(query_id=q.id, document_name="a.pdf", snippet=None, score=0.5))

    with pytest.raises(IntegrityError):
        db.commit()


def test_citation_snapshot_survives_deleting_the_document(db, user):
    # the history must still show what was cited after the source document is gone
    doc = create_document(
        db, original_name="policy.pdf", filename="stored.pdf", file_type="pdf", uploaded_by=user.id
    )
    create_chunks(db, doc.id, ["Employees get 14 days of annual leave."], [[1.0]], [3])
    q = make_query(db, user)
    make_citation(db, q, document_id=doc.id, chunk_id=1)

    delete_chunks_by_document(db, doc.id)
    delete_document(db, doc.id)

    kept = db.query(QueryCitation).one()
    assert kept.document_name == "policy.pdf"
    assert kept.snippet == "Employees get 14 days of annual leave."
    assert kept.page_number == 3
