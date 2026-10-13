from evaluation.drcd import build_dataset
from evaluation.run import run_evaluation
from tests.services.test_evaluation_run import bag_of_words

ROWS = [
    {
        "title": "Alpha",
        "id": "1",
        "paragraphs": [
            {"context": "refund policy covers thirty days", "id": "1-1",
             "qas": [{"id": "1-1-1", "question": "refund days", "answers": [{"text": "thirty"}, {"text": "thirty"}]}]},
            {"context": "shipping takes five days", "id": "1-2",
             "qas": [{"id": "1-2-1", "question": "shipping days", "answers": [{"text": "five"}]},
                     {"id": "1-2-2", "question": "shipping how long", "answers": []}]},
        ],
    },
    {
        "title": "Beta",
        "id": "2",
        "paragraphs": [
            {"context": "warranty lasts two years", "id": "2-1",
             "qas": [{"id": "2-1-1", "question": "warranty years", "answers": [{"text": "two"}]}]},
        ],
    },
]


def test_every_article_becomes_a_document_whose_chunks_are_its_paragraphs():
    dataset = build_dataset(ROWS)

    assert [d["file"] for d in dataset["documents"]] == ["Alpha (1)", "Beta (2)"]
    assert dataset["documents"][0]["chunks"] == ["refund policy covers thirty days", "shipping takes five days"]


def test_a_question_points_at_the_paragraph_it_was_written_from():
    dataset = build_dataset(ROWS)

    question = next(q for q in dataset["questions"] if q["id"] == "drcd-1-2-1")
    assert question["evidence"] == ["shipping takes five days"]
    assert question["document"] == "Alpha (1)"
    assert question["must_contain"] == [["five"]]
    assert question["kind"] == "answerable"


def test_a_question_without_answers_is_kept_with_no_required_fact():
    dataset = build_dataset(ROWS)

    question = next(q for q in dataset["questions"] if q["id"] == "drcd-1-2-2")
    assert question["must_contain"] == []


def test_the_same_seed_samples_the_same_questions():
    first = build_dataset(ROWS, max_questions=2, seed=3)
    second = build_dataset(ROWS, max_questions=2, seed=3)

    assert len(first["questions"]) == 2
    assert [q["id"] for q in first["questions"]] == [q["id"] for q in second["questions"]]
    assert len(first["documents"]) == 2  # sampling questions never shrinks the collection


def test_the_runner_searches_the_given_paragraphs_as_they_are():
    dataset = build_dataset(ROWS)

    report = run_evaluation(dataset, embed=bag_of_words, llm=None, top_k=2)

    assert report["config"]["documents"] == 2
    assert report["retrieval"]["overall"]["answerable"] == 4
    assert report["retrieval"]["overall"]["hit_at_k"] >= 0.75


# ---------- Cantonese rewrites ----------

import pytest

from evaluation.drcd import DATA_DIR, load_cantonese_rewrites, with_cantonese


def test_each_rewritten_question_is_asked_as_written_and_in_cantonese():
    dataset = build_dataset(ROWS)
    rewrites = {"drcd-1-1-1": "退款幾多日呀"}

    result = with_cantonese(dataset, rewrites)

    assert [(q["id"], q["group"], q["question"]) for q in result["questions"]] == [
        ("drcd-1-1-1", "written", "refund days"),
        ("drcd-1-1-1-yue", "cantonese", "退款幾多日呀"),
    ]
    assert result["questions"][0]["evidence"] == result["questions"][1]["evidence"]  # the same passage is right for both
    assert result["documents"] == dataset["documents"]  # the collection is untouched


def test_the_cantonese_rewrites_file_is_complete():
    rewrites = load_cantonese_rewrites()

    assert len(rewrites) == 60
    assert all(text.strip() for text in rewrites.values())
    assert all(question_id.startswith("drcd-") for question_id in rewrites)


def test_every_rewrite_belongs_to_a_real_drcd_question():
    path = DATA_DIR / "drcd_dev.json"
    if not path.exists():
        pytest.skip("the DRCD dev split has not been downloaded")

    import json

    ids = {q["id"] for q in build_dataset(json.loads(path.read_text(encoding="utf-8")), max_questions=10**9)["questions"]}

    assert set(load_cantonese_rewrites()) <= ids
