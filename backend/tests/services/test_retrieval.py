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


# ---------- vectors from another embedding model ----------

def test_search_refuses_to_compare_vectors_of_different_sizes(db, user):
    from app.features.rag.retrieval import EmbeddingMismatchError

    add_doc(db, user, "old.pdf", [("made by the old model", [1.0, 0.0])])  # 2 numbers per vector

    with pytest.raises(EmbeddingMismatchError, match="rebuild_index"):
        search_chunks(db, [1.0, 0.0, 0.0], top_k=1, min_score=0.0)  # a question from a model with 3 numbers


# ---------- hybrid search: meaning and keywords ----------

def two_chunks(db, user):
    """Chunk 0 is closer to the question in meaning; chunk 1 is the one that uses the words of the question."""
    add_doc(db, user, "policy.pdf", [
        ("退款要喺三十日內申請", [1.0, 0.0]),
        ("國道施工路段要減速慢行", [0.8, 0.6]),
    ])


def test_keywords_move_up_a_chunk_that_uses_the_words_of_the_question(db, user):
    two_chunks(db, user)

    by_meaning = search_chunks(db, [1.0, 0.1], top_k=1, min_score=0.0)
    hybrid = search_chunks(db, [1.0, 0.1], top_k=1, min_score=0.0, query_text="國道施工路段")

    assert by_meaning[0].content == "退款要喺三十日內申請"
    assert hybrid[0].content == "國道施工路段要減速慢行"


def test_the_score_of_a_hybrid_result_is_still_its_cosine_similarity(db, user):
    two_chunks(db, user)

    hit = search_chunks(db, [1.0, 0.0], top_k=1, min_score=0.0, query_text="國道施工路段")[0]

    assert hit.content == "國道施工路段要減速慢行"
    assert hit.score == pytest.approx(0.8)  # cos([1,0], [0.8,0.6]); not the fused rank score


def test_nothing_is_returned_when_not_even_the_best_chunk_is_similar_in_meaning(db, user):
    two_chunks(db, user)

    # the question is orthogonal to both chunks (score 0), although it shares every word with chunk 1
    assert search_chunks(db, [0.0, 0.0, 0.0][:2], top_k=4, min_score=0.5, query_text="國道施工路段要減速慢行") == []


def test_a_chunk_with_no_word_in_common_is_not_ranked_by_the_order_it_is_stored_in(db, user):
    add_doc(db, user, "a.pdf", [("first stored", [0.1, 1.0]), ("second stored", [0.5, 1.0]), ("third stored", [1.0, 1.0])])

    hits = search_chunks(db, [1.0, 0.0], top_k=3, min_score=0.0, query_text="zebra xylophone")

    assert [h.content for h in hits] == ["third stored", "second stored", "first stored"]  # the meaning order, nothing else


def test_the_keyword_index_is_built_once_and_again_only_when_the_chunks_change(db, user, monkeypatch):
    from app.features.rag import retrieval

    built = []
    real = retrieval.BM25

    def counting(*args, **kwargs):
        built.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(retrieval, "BM25", counting)
    monkeypatch.setattr(retrieval, "_keyword_index_cache", None)
    two_chunks(db, user)

    search_chunks(db, [1.0, 0.1], min_score=0.0, query_text="國道")
    search_chunks(db, [1.0, 0.1], min_score=0.0, query_text="退款")
    assert len(built) == 1  # the second question used the index of the first

    add_doc(db, user, "new.pdf", [("a document that arrived later", [0.3, 0.3])])
    search_chunks(db, [1.0, 0.1], min_score=0.0, query_text="國道")
    assert len(built) == 2


def test_hybrid_search_of_an_empty_collection_is_empty(db):
    assert search_chunks(db, [1.0, 0.0], min_score=0.0, query_text="anything") == []


# ---------- reranking: the search takes more chunks, a second model keeps the best ----------

def three_chunks(db, user):
    """By meaning (and with the question's words) the order is first, second, third."""
    add_doc(db, user, "policy.pdf", [
        ("first chunk about leave", [1.0, 0.0]),
        ("second chunk about leave", [0.9, 0.4]),
        ("third chunk about leave", [0.7, 0.7]),
    ])


def test_the_reranker_decides_which_chunks_are_kept(db, user):
    three_chunks(db, user)
    by_content = {"first chunk about leave": 0.1, "second chunk about leave": 0.2, "third chunk about leave": 0.9}

    found = search_chunks(
        db, [1.0, 0.0], top_k=1, min_score=0.0, query_text="leave",
        rerank=lambda question, passages: [by_content[p] for p in passages], candidates=3,
    )

    assert [c.content for c in found] == ["third chunk about leave"]  # without the reranker the first one wins


def test_the_reranker_only_sees_the_candidates_and_gets_the_question_and_their_text(db, user):
    three_chunks(db, user)
    seen = []

    def spy(question, passages):
        seen.append((question, list(passages)))
        return [0.0] * len(passages)

    search_chunks(db, [1.0, 0.0], top_k=1, min_score=0.0, query_text="how much leave", rerank=spy, candidates=2)

    assert len(seen) == 1
    assert seen[0][0] == "how much leave"
    assert seen[0][1] == ["first chunk about leave", "second chunk about leave"]  # 2 candidates, not all 3


def test_equal_reranker_scores_keep_the_order_of_the_search(db, user):
    three_chunks(db, user)

    found = search_chunks(db, [1.0, 0.0], top_k=3, min_score=0.0, query_text="leave",
                          rerank=lambda question, passages: [0.5] * len(passages), candidates=3)

    assert [c.content for c in found] == ["first chunk about leave", "second chunk about leave", "third chunk about leave"]


def test_a_reranked_result_keeps_its_cosine_similarity_as_the_score(db, user):
    three_chunks(db, user)

    found = search_chunks(db, [1.0, 0.0], top_k=1, min_score=0.0, query_text="leave",
                          rerank=lambda question, passages: [0.0, 0.0, 1.0], candidates=3)

    assert found[0].content == "third chunk about leave"
    assert found[0].score == pytest.approx(0.7071, abs=1e-3)  # the cosine of [0.7, 0.7] with [1, 0]


def test_the_reranker_is_not_asked_when_nothing_passes_the_threshold(db, user):
    three_chunks(db, user)

    def must_not_run(question, passages):
        raise AssertionError("nothing is relevant: there is nothing to rerank")

    assert search_chunks(db, [0.0, 1.0], top_k=2, min_score=0.99, query_text="leave", rerank=must_not_run, candidates=3) == []


def test_without_the_question_text_there_is_nothing_to_rerank_with(db, user):
    three_chunks(db, user)

    def must_not_run(question, passages):
        raise AssertionError("reranking needs the question as written")

    found = search_chunks(db, [1.0, 0.0], top_k=2, min_score=0.0, rerank=must_not_run, candidates=3)

    assert len(found) == 2  # the search by meaning alone, as before


def test_candidates_are_never_fewer_than_top_k(db, user):
    three_chunks(db, user)
    seen = []

    def spy(question, passages):
        seen.append(len(passages))
        return [0.0] * len(passages)

    search_chunks(db, [1.0, 0.0], top_k=3, min_score=0.0, query_text="leave", rerank=spy, candidates=1)

    assert seen == [3]
