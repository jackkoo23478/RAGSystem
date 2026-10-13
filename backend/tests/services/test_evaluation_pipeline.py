import re
import zlib

from evaluation.pipeline_eval import STEPS, evaluate_pipeline, render

DOCUMENTS = [
    {"id": "a", "text": "Refunds are possible within 30 days of delivery."},
    {"id": "b", "text": "Express shipping costs 12 dollars extra."},
    {"id": "c", "text": "The warranty on electronics lasts 2 years."},
]
def span_of(document: str, phrase: str) -> list[tuple[int, int]]:
    text = next(d["text"] for d in DOCUMENTS if d["id"] == document)
    start = text.index(phrase)
    return [(start, start + len(phrase))]


QUESTIONS = [
    {"question": "refund within how many days", "document": "a", "answer_spans": span_of("a", "within 30 days")},
    {"question": "express shipping dollars", "document": "b", "answer_spans": span_of("b", "12 dollars")},
    {"question": "warranty electronics years", "document": "c", "answer_spans": span_of("c", "2 years")},
]
DATASET = {"documents": DOCUMENTS, "questions": QUESTIONS}


def bag_of_words(texts):
    vectors = []
    for text in texts:
        vector = [0.0] * 256
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vector[zlib.crc32(token.encode()) % 256] += 1.0
        vectors.append(vector)
    return vectors


def never_asked(question, passages):
    raise AssertionError("the reranker must only be used by the last step")


def test_every_step_is_reported_with_the_same_questions():
    report = evaluate_pipeline(DATASET, embed=bag_of_words, rerank=lambda q, passages: [0.0] * len(passages), min_score=0.0)

    assert report["questions"] == 3 and report["chunks"] == 3
    assert list(report["results"]) == STEPS
    for result in report["results"].values():
        assert result["hit_at_1"] == 1.0 and result["hit_at_k"] == 1.0


def test_the_reranker_can_spoil_or_save_the_last_step_and_the_first_two_do_not_depend_on_it():
    # a reranker that prefers the shipping passage whatever the question: the refund and warranty questions lose their passage at top 1
    def shipping_first(question, passages):
        return [1.0 if "shipping" in p.lower() else 0.0 for p in passages]

    report = evaluate_pipeline(DATASET, embed=bag_of_words, rerank=shipping_first, top_k=1, candidates=3, min_score=0.0)

    meaning, hybrid, app = (report["results"][step] for step in STEPS)
    assert meaning["hit_at_1"] == 1.0 and hybrid["hit_at_1"] == 1.0
    assert app["hit_at_1"] == 1 / 3
    assert app["vs_hybrid"] == {"gained": 0, "lost": 2, "p": app["vs_hybrid"]["p"]}


def test_a_question_below_the_threshold_is_not_counted_as_found_by_the_app():
    report = evaluate_pipeline(DATASET, embed=bag_of_words, rerank=lambda q, passages: [0.0] * len(passages), min_score=0.99)

    assert report["kept_by_threshold"] < 1.0
    assert all(r["found_by_app"] <= r["hit_at_k"] for r in report["results"].values())


def test_the_table_has_a_row_per_step_and_names_the_comparisons():
    report = evaluate_pipeline(DATASET, embed=bag_of_words, rerank=lambda q, passages: [0.0] * len(passages), min_score=0.0)

    text = render("A test set", report)

    for step in STEPS:
        assert step in text
    assert "hit@4" in text and "against hybrid" in text
