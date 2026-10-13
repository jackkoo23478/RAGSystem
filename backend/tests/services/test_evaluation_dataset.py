"""The evaluation dataset must stay usable: a typo here would silently make every score wrong."""
import pytest

from app.features.ingestion.pipeline.chunker import chunk_pages
from app.features.ingestion.pipeline.safety import scan_for_injection
from evaluation.run import load_dataset


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


def test_question_ids_are_unique(dataset):
    ids = [q["id"] for q in dataset["questions"]]

    assert len(ids) == len(set(ids))


def test_every_question_has_the_fields_the_runner_reads(dataset):
    for q in dataset["questions"]:
        assert q["question"].strip(), q["id"]
        assert q["kind"] in ("answerable", "unanswerable"), q["id"]
        assert q["group"], q["id"]
        assert isinstance(q["evidence"], list) and isinstance(q["must_contain"], list), q["id"]


def test_answerable_questions_name_a_document_evidence_and_facts(dataset):
    files = {doc["file"] for doc in dataset["documents"]}

    for q in dataset["questions"]:
        if q["kind"] == "answerable":
            assert q["document"] in files, q["id"]
            assert q["evidence"], q["id"]
            assert q["must_contain"] and all(group for group in q["must_contain"]), q["id"]
        else:
            assert q["document"] is None and not q["evidence"], q["id"]


def test_the_evidence_sits_inside_one_chunk_of_its_document(dataset):
    """If the chunker cut the evidence in two, no retrieval could ever be counted as a hit."""
    texts = {doc["file"]: doc["text"] for doc in dataset["documents"]}

    for q in dataset["questions"]:
        if q["kind"] != "answerable":
            continue
        chunks = [text for _, text in chunk_pages([(None, texts[q["document"]])])]
        assert any(phrase in chunk for phrase in q["evidence"] for chunk in chunks), q["id"]


def test_no_document_would_be_flagged_by_the_safety_scan(dataset):
    for doc in dataset["documents"]:
        assert scan_for_injection(doc["text"]) == [], doc["file"]


def test_the_dataset_covers_both_languages_and_unanswerable_questions(dataset):
    groups = {q["group"] for q in dataset["questions"]}

    assert {"en-en", "zh-zh", "zh-en", "en-zh"} <= groups
    assert any(q["kind"] == "unanswerable" for q in dataset["questions"])
