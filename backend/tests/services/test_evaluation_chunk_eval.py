import numpy as np
import pytest

from app.features.rag.retrieval import rank_by_cosine
from evaluation import chunk_eval, chunking, drcd, wikiqa
from tests.services.test_evaluation_run import bag_of_words

TEXT_A = "refund policy covers thirty days. shipping takes five days. warranty lasts two years."
TEXT_B = "password reset link valid fifteen minutes. laptops replaced every four years."
DATASET = {
    "documents": [{"id": "a", "title": "A", "text": TEXT_A}, {"id": "b", "title": "B", "text": TEXT_B}],
    "questions": [
        {"id": "q1", "question": "refund thirty days", "document": "a",
         "answer_spans": [(TEXT_A.index("thirty days"), TEXT_A.index("thirty days") + len("thirty days"))]},
        {"id": "q2", "question": "laptops replaced every years", "document": "b",
         "answer_spans": [(TEXT_B.index("every four years"), TEXT_B.index("every four years") + len("every four years"))]},
    ],
}


def fixed(size):
    return lambda text: chunking.fixed_spans(text, size, 0)


def question_vectors():
    return np.array(bag_of_words([q["question"] for q in DATASET["questions"]]), dtype=float)


def test_covers_needs_every_character_of_the_answer_inside_the_chunk():
    assert chunk_eval.covers((0, 20), [(5, 15)])
    assert chunk_eval.covers((0, 20), [(30, 40), (5, 15)])  # any of the answers will do
    assert not chunk_eval.covers((0, 10), [(5, 15)])        # the chunk stops in the middle of the answer


def test_the_numpy_ranking_gives_the_same_order_and_scores_as_the_apps_cosine():
    rng = np.random.default_rng(1)
    chunks, query = rng.normal(size=(40, 16)), rng.normal(size=(1, 16))

    order, scores = chunk_eval.rank_top_k(query, chunks, top_k=5)

    expected = rank_by_cosine(query[0].tolist(), chunks.tolist(), top_k=5)
    assert order[0].tolist() == [i for i, _ in expected]
    assert np.allclose(scores[0], [s for _, s in expected])


def test_a_big_enough_chunk_finds_the_answer():
    result = chunk_eval.evaluate_chunker(DATASET, fixed(200), bag_of_words, question_vectors(), top_k=2)

    assert result["answer_kept_whole"] == 1.0
    assert result["hit_at_1"] == 1.0
    assert result["mrr"] == 1.0
    assert result["chunks"] == 2  # one chunk per document


def test_a_chunker_that_cuts_through_the_answer_loses_it_whatever_the_ranking():
    result = chunk_eval.evaluate_chunker(DATASET, fixed(5), bag_of_words, question_vectors(), top_k=4)

    assert result["answer_kept_whole"] == 0.0  # both answers are longer than 5 characters
    assert result["hit_at_k"] == 0.0


def test_the_characters_sent_to_the_llm_are_those_of_the_chunks_that_were_returned():
    result = chunk_eval.evaluate_chunker(DATASET, fixed(200), bag_of_words, question_vectors(), top_k=2)

    # top 2 of 2 chunks: every question is sent both documents
    assert result["chars_sent_to_llm"] == len(TEXT_A) + len(TEXT_B)


def test_strategy_names_are_turned_into_chunkers():
    text = "第一句。第二句。" * 20

    assert all(e - s <= 50 for s, e in chunk_eval.make_chunker("fixed-50", None)(text))
    assert all(e - s <= 50 for s, e in chunk_eval.make_chunker("recursive-50", None)(text))
    with pytest.raises(ValueError, match="unknown strategy"):
        chunk_eval.make_chunker("magic-5", None)


def test_every_strategy_runs_and_the_baseline_comparison_is_filled_in(monkeypatch):
    monkeypatch.setattr(chunk_eval, "load_embedder", lambda model: (bag_of_words, bag_of_words))

    results = chunk_eval.run(DATASET, ["fixed-60", "fixed-500", "recursive-60", "semantic-80"], "any-model")

    assert [r["strategy"] for r in results] == ["fixed-60", "fixed-500", "recursive-60", "semantic-80"]
    baseline = next(r for r in results if r["strategy"] == "fixed-500")
    assert baseline["gained_vs_baseline"] == 0 and baseline["lost_vs_baseline"] == 0
    assert "recursive-60" in chunk_eval.render(results, 2, 2, "any-model")


def test_the_cache_embeds_each_text_once():
    calls = []

    def embed(texts):
        calls.append(list(texts))
        return [[float(len(t))] for t in texts]

    embed_cached = chunk_eval.cached(embed)

    assert embed_cached(["aa", "b", "aa"]) == [[2.0], [1.0], [2.0]]
    embed_cached(["aa", "ccc"])
    assert calls == [["aa", "b"], ["ccc"]]


# ---------- the span datasets ----------

def test_wikiqa_questions_keep_only_answers_whose_position_is_right():
    rows = [
        {"id": "x", "title": "T", "context": "tax is due in April.", "question": "when?", "answers": ["April"], "answer_starts": [14]},
        {"id": "x", "title": "T", "context": "tax is due in April.", "question": "wrong", "answers": ["April"], "answer_starts": [3]},
    ]

    dataset = wikiqa.build_span_dataset(rows)

    assert [q["question"] for q in dataset["questions"]] == ["when?"]
    assert dataset["questions"][0]["answer_spans"] == [(14, 19)]
    assert len(dataset["documents"]) == 1


def test_drcd_articles_are_joined_and_answer_positions_move_with_them():
    rows = [{"title": "A", "id": "1", "paragraphs": [
        {"context": "AAAA", "id": "1-1", "qas": []},
        {"context": "tax in April", "id": "1-2", "qas": [
            {"id": "1-2-1", "question": "when?",
             "answers": [{"text": "April", "answer_start": 7}, {"text": "April", "answer_start": 7}]}]},
    ]}]

    dataset = drcd.build_span_dataset(rows)

    document = dataset["documents"][0]
    assert document["text"] == "AAAA\n\ntax in April"
    start, end = dataset["questions"][0]["answer_spans"][0]
    assert document["text"][start:end] == "April"
    assert len(dataset["questions"][0]["answer_spans"]) == 1  # two annotators, one answer


def test_the_gap_strategy_reads_its_number_as_hundredths():
    cats, tax = "貓喜歡食魚。" * 20, "稅款要喺四月前申報。" * 12  # each topic is longer than the minimum chunk (100 characters)
    text = cats + tax

    def embed(texts_):
        return [[1.0, 0.0] if "貓" in t else [0.0, 1.0] for t in texts_]

    assert [text[s:e] for s, e in chunk_eval.make_chunker("gap-50", embed)(text)] == [cats, tax]  # the gap is 1.0: cut
    assert len(chunk_eval.make_chunker("gap-150", embed)(text)) == 1                              # a limit of 1.5: never cut
