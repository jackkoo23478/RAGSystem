import json

from app.features.documents.models import DocumentChunk
from app.features.documents.repository import (
    create_chunks,
    create_document,
    delete_chunks_by_document,
    get_document_by_id,
)


def make_document(db, user, name="policy.txt"):
    return create_document(
        db,
        original_name=name,
        filename=f"stored-{name}",
        file_type="txt",
        uploaded_by=user.id,
    )


def test_create_and_get_document(db, user):
    created = make_document(db, user)

    found = get_document_by_id(db, created.id)

    assert found is not None
    assert found.original_name == "policy.txt"
    assert found.status == "pending"


def test_get_document_returns_none_when_missing(db):
    assert get_document_by_id(db, 999) is None


def test_create_chunks_stores_one_embedding_per_chunk(db, user):
    # regression: once the WHOLE embeddings list was stored in every row
    doc = make_document(db, user)
    contents = ["first chunk", "second chunk"]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    create_chunks(db, doc.id, contents, embeddings)

    rows = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    assert [r.chunk_index for r in rows] == [0, 1]
    assert [r.content for r in rows] == contents
    assert [json.loads(r.embedding) for r in rows] == embeddings


def test_delete_chunks_only_affects_that_document(db, user):
    doc_a = make_document(db, user, "a.txt")
    doc_b = make_document(db, user, "b.txt")
    create_chunks(db, doc_a.id, ["a1", "a2"], [[1.0], [2.0]])
    create_chunks(db, doc_b.id, ["b1"], [[3.0]])

    delete_chunks_by_document(db, doc_a.id)

    remaining = db.query(DocumentChunk).all()
    assert [r.content for r in remaining] == ["b1"]


def test_create_chunks_stores_page_numbers(db, user):
    doc = make_document(db, user)

    create_chunks(db, doc.id, ["p1 text", "p2 text"], [[0.1], [0.2]], page_numbers=[1, 2])

    rows = db.query(DocumentChunk).order_by(DocumentChunk.chunk_index).all()
    assert [r.page_number for r in rows] == [1, 2]


def test_create_chunks_page_numbers_default_to_none(db, user):
    # the old 4-argument call must keep working
    doc = make_document(db, user)

    create_chunks(db, doc.id, ["a", "b"], [[0.1], [0.2]])

    rows = db.query(DocumentChunk).all()
    assert [r.page_number for r in rows] == [None, None]


def test_create_chunks_allows_none_page_number_per_chunk(db, user):
    # txt documents have no pages
    doc = make_document(db, user)

    create_chunks(db, doc.id, ["a", "b"], [[0.1], [0.2]], page_numbers=[None, None])

    rows = db.query(DocumentChunk).all()
    assert [r.page_number for r in rows] == [None, None]


def test_create_chunks_page_number_stays_with_its_chunk(db, user):
    doc = make_document(db, user)

    create_chunks(db, doc.id, ["a", "b", "c"], [[1.0], [2.0], [3.0]], page_numbers=[1, 1, 2])

    rows = db.query(DocumentChunk).order_by(DocumentChunk.chunk_index).all()
    assert [(r.content, r.page_number) for r in rows] == [("a", 1), ("b", 1), ("c", 2)]
