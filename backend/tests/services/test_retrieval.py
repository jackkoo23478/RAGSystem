import pytest

from app.features.documents.models import DocumentChunk
from app.features.documents.repository import (
    create_chunks,
    create_document,
    update_document_status,
)
from app.features.rag.retrieval import rank_by_cosine, search_chunks


# ---------- rank_by_cosine (pure maths, no DB) ----------

def test_same_direction_scores_one():
    result = rank_by_cosine([1.0, 0.0], [[2.0, 0.0]])

    assert result[0][0] == 0
    assert result[0][1] == pytest.approx(1.0)


def test_orthogonal_scores_zero():
    result = rank_by_cosine([1.0, 0.0], [[0.0, 1.0]])

    assert result[0][1] == pytest.approx(0.0)


def test_sorted_best_first_and_top_k():
    vectors = [[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]  # scores: 0, 1, ~0.707

    result = rank_by_cosine([1.0, 0.0], vectors, top_k=2)

    assert [i for i, _ in result] == [1, 2]


def test_min_score_filters_out_weak_matches():
    result = rank_by_cosine([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]], min_score=0.5)

    assert [i for i, _ in result] == [0]


def test_nothing_passes_the_threshold():
    assert rank_by_cosine([1.0, 0.0], [[0.0, 1.0]], min_score=0.5) == []


def test_empty_vectors():
    assert rank_by_cosine([1.0, 0.0], []) == []


def test_top_k_larger_than_number_of_vectors():
    result = rank_by_cosine([1.0, 0.0], [[1.0, 0.0]], top_k=10)

    assert len(result) == 1


def test_zero_vector_does_not_crash_or_give_nan():
    result = rank_by_cosine([1.0, 0.0], [[0.0, 0.0]])

    assert result == [(0, 0.0)]


# ---------- search_chunks (reads the DB) ----------

def add_doc(db, user, name, chunks, status="processed", page_numbers=None):
    """Create a document with 2-dim chunk vectors: chunks = [(text, [x, y]), ...]."""
    doc = create_document(
        db, original_name=name, filename=f"stored-{name}", file_type="pdf", uploaded_by=user.id
    )
    create_chunks(
        db,
        doc.id,
        [text for text, _ in chunks],
        [vec for _, vec in chunks],
        page_numbers,
    )
    update_document_status(db, doc, status)
    return doc


def test_search_returns_best_chunk_with_document_info(db, user):
    doc = add_doc(
        db, user, "policy.pdf",
        [("leave rules", [1.0, 0.0]), ("expense rules", [0.0, 1.0])],
        page_numbers=[3, 4],
    )

    results = search_chunks(db, [1.0, 0.0], top_k=1, min_score=0.5)

    assert len(results) == 1
    hit = results[0]
    assert hit.content == "leave rules"
    assert hit.document_id == doc.id
    assert hit.document_name == "policy.pdf"
    assert hit.page_number == 3
    assert hit.chunk_index == 0
    assert hit.score == pytest.approx(1.0)


def test_search_orders_results_across_documents(db, user):
    add_doc(db, user, "a.pdf", [("weak", [1.0, 1.0])])
    add_doc(db, user, "b.pdf", [("strong", [1.0, 0.0])])

    results = search_chunks(db, [1.0, 0.0], top_k=5, min_score=0.0)

    assert [r.content for r in results] == ["strong", "weak"]
    assert [r.document_name for r in results] == ["b.pdf", "a.pdf"]


def test_search_ignores_documents_that_are_not_processed(db, user):
    add_doc(db, user, "done.pdf", [("ready", [1.0, 0.0])], status="processed")
    add_doc(db, user, "todo.pdf", [("pending chunk", [1.0, 0.0])], status="pending")
    add_doc(db, user, "broken.pdf", [("failed chunk", [1.0, 0.0])], status="failed")

    results = search_chunks(db, [1.0, 0.0], min_score=0.0)

    assert [r.content for r in results] == ["ready"]


def test_search_skips_chunks_without_embedding(db, user):
    doc = add_doc(db, user, "a.pdf", [("has vector", [1.0, 0.0])])
    db.add(DocumentChunk(document_id=doc.id, chunk_index=1, content="no vector", embedding=None))
    db.commit()

    results = search_chunks(db, [1.0, 0.0], min_score=0.0)

    assert [r.content for r in results] == ["has vector"]


def test_search_keeps_none_page_number_for_txt(db, user):
    add_doc(db, user, "note.txt", [("plain text", [1.0, 0.0])])

    results = search_chunks(db, [1.0, 0.0], min_score=0.0)

    assert results[0].page_number is None


def test_search_below_threshold_returns_nothing(db, user):
    add_doc(db, user, "a.pdf", [("unrelated", [0.0, 1.0])])

    assert search_chunks(db, [1.0, 0.0], min_score=0.5) == []


def test_search_on_empty_database(db):
    assert search_chunks(db, [1.0, 0.0]) == []


def test_search_respects_top_k(db, user):
    add_doc(db, user, "a.pdf", [(f"chunk {i}", [1.0, 0.0]) for i in range(5)])

    assert len(search_chunks(db, [1.0, 0.0], top_k=3, min_score=0.0)) == 3
