import re
import zlib

import pytest

from app.features.rag.llm import FakeLLM, LLMError
from evaluation.run import render_markdown, run_evaluation

DATASET = {
    "documents": [
        {"file": "refunds.txt", "language": "en", "text": "Refunds are possible within 30 days of delivery."},
        {"file": "shipping.txt", "language": "en", "text": "Express shipping costs 12 dollars extra."},
    ],
    "questions": [
        {"id": "q1", "group": "en-en", "kind": "answerable", "question": "How many days do I have for a refund?",
         "document": "refunds.txt", "evidence": ["within 30 days"], "must_contain": [["30"]]},
        {"id": "q2", "group": "en-en", "kind": "answerable", "question": "How much does express shipping cost?",
         "document": "shipping.txt", "evidence": ["12 dollars"], "must_contain": [["12"]]},
        {"id": "q3", "group": "unanswerable-en", "kind": "unanswerable", "question": "zebra xylophone",
         "document": None, "evidence": [], "must_contain": []},
    ],
}


STOP_WORDS = {"how", "many", "much", "do", "does", "i", "have", "for", "are", "is", "of", "the", "a", "me", "my"}


def bag_of_words(texts):
    """A tiny deterministic embedder: the words (without stop words and a plural s) hashed into 1024 counters.
    It only needs to tell texts that share words from texts that do not; there is no model to download."""
    vectors = []
    for text in texts:
        vector = [0.0] * 1024
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            if token in STOP_WORDS:
                continue
            if token.endswith("s") and len(token) > 3:
                token = token[:-1]
            vector[zlib.crc32(token.encode()) % 1024] += 1.0
        vectors.append(vector)
    return vectors


def test_retrieval_finds_the_right_passage_and_gives_no_evidence_for_nonsense():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=2, min_score=0.3)

    overall = report["retrieval"]["overall"]
    assert overall["answerable"] == 2 and overall["unanswerable"] == 1
    assert overall["hit_at_1"] == 1.0
    assert overall["mrr"] == 1.0
    assert overall["found_by_app"] == 1.0
    assert overall["false_evidence"] == 0.0
    assert "answers" not in report  # no LLM was given


def test_the_threshold_sweep_shows_the_trade_off():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=2, min_score=0.3)

    sweep = report["retrieval"]["sweep"]
    assert [row["min_score"] for row in sweep] == sorted(row["min_score"] for row in sweep)
    assert sweep[0]["found_by_app"] >= sweep[-1]["found_by_app"]  # a stricter threshold can only lose answers


def test_answers_are_scored_for_correctness_and_refusal():
    llm = FakeLLM(answer="Refunds are possible within 30 days. [1]")

    report = run_evaluation(DATASET, embed=bag_of_words, llm=llm, top_k=2, min_score=0.3)

    answers = report["answers"]["overall"]
    assert answers["correct"] == 0.5  # q1 has the fact, q2 does not
    assert answers["answered"] == 1.0
    assert answers["refused"] == 1.0  # nothing relevant: refused without calling the LLM
    assert answers["wrong_answer_shown"] == 0.0
    assert len(llm.calls) == 2  # the nonsense question never reached the model


def test_an_answer_without_a_citation_is_counted_as_invalid_not_correct():
    llm = FakeLLM(answer="Refunds are possible within 30 days.")  # no [1]

    report = run_evaluation(DATASET, embed=bag_of_words, llm=llm, top_k=2, min_score=0.3)

    answers = report["answers"]["overall"]
    assert answers["invalid_answer"] == 1.0
    assert answers["correct"] == 0.0
    invalid = [d for d in report["answers"]["details"] if d["status"] == "invalid_answer"]
    assert invalid[0]["raw_answer"] == "Refunds are possible within 30 days."  # kept for diagnosis


def test_a_failing_llm_is_recorded_not_raised():
    llm = FakeLLM(error=LLMError("cannot reach the LLM server"))

    report = run_evaluation(DATASET, embed=bag_of_words, llm=llm, top_k=2, min_score=0.3)

    assert report["answers"]["overall"]["statuses"].get("failed") == 2


def test_the_report_renders_as_markdown_tables():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=FakeLLM(answer="30 [1]"), top_k=2, min_score=0.3)

    text = render_markdown(report)

    assert "## Retrieval" in text and "## Answers" in text
    assert "| en-en |" in text and "| unanswerable-en |" in text
    assert "min_score" in text


# ---------- searching like the app: keywords, the reranker and the threshold on the best meaning score ----------

def test_by_default_the_chunks_are_found_by_meaning_only():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=2, min_score=0.3)

    assert report["config"]["search"] == "by meaning only"


def test_like_the_app_the_report_names_the_search_and_the_reranker():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=2, min_score=0.3, like_the_app=True,
                            rerank=lambda question, passages: [0.0] * len(passages))

    assert "keywords" in report["config"]["search"] and "reranked" in report["config"]["search"]
    assert "meaning + keywords" in render_markdown(report)


def test_the_reranker_changes_what_the_retrieval_table_measures():
    # a reranker that always puts the shipping passage first: the refund question then loses its right passage at top 1
    def shipping_first(question, passages):
        return [1.0 if "shipping" in p.lower() else 0.0 for p in passages]

    plain = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=1, min_score=0.0, like_the_app=True)
    spoiled = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=1, min_score=0.0, like_the_app=True, rerank=shipping_first)

    assert plain["retrieval"]["overall"]["hit_at_1"] == 1.0
    assert spoiled["retrieval"]["overall"]["hit_at_1"] == 0.5  # q1 lost, q2 kept


def test_like_the_app_the_threshold_looks_at_the_best_meaning_score_of_the_question():
    report = run_evaluation(DATASET, embed=bag_of_words, llm=None, top_k=2, min_score=0.3, like_the_app=True)

    for record in report["retrieval"]["details"]:
        assert "best_meaning" in record
        if record["kind"] == "answerable" and record["rank"] is not None:
            assert record["gate_score"] == pytest.approx(record["best_meaning"], abs=1e-3)  # the same number for every chunk of the question
