from evaluation import wikiqa
from evaluation.run import run_evaluation
from tests.services.test_evaluation_run import bag_of_words


def _row(article_id, title, context, question, answers):
    return {"id": article_id, "title": title, "context": context, "question": question, "answers": answers}


REFUND = "Refunds are possible within 30 days of delivery."
ROWS = [
    _row("a", "Policy", REFUND, "refund how many days", ["30 days"]),
    _row("a", "Policy", REFUND, "the answer is nowhere", ["nonexistent"]),
    _row("b", "Policy", "Warranty refunds are possible within 30 days too.", "warranty refund days", ["30 days"]),
    _row("c", "Long", "ok " * 600, "what", ["ok"]),  # the answer is in every chunk: too vague
]


def test_every_article_becomes_one_document_with_a_unique_name():
    dataset = wikiqa.build_dataset(ROWS)

    names = [d["file"] for d in dataset["documents"]]
    assert len(names) == 3 and len(set(names)) == 3  # "Policy" appears twice as a title
    assert dataset["documents"][0]["language"] == "yue"


def test_questions_whose_answer_is_missing_or_too_vague_are_dropped():
    dataset = wikiqa.build_dataset(ROWS)

    questions = [q["question"] for q in dataset["questions"]]
    assert questions == ["refund how many days", "warranty refund days"]


def test_a_question_points_at_its_own_article_and_every_answer_text():
    dataset = wikiqa.build_dataset(ROWS)

    q = dataset["questions"][0]
    assert q["same_document"] is True
    assert q["document"] == dataset["documents"][0]["file"]
    assert q["evidence"] == ["30 days"]
    assert q["group"] == "wiki-yue"


def test_the_same_seed_samples_the_same_questions():
    first = wikiqa.build_dataset(ROWS, max_questions=1, seed=5)
    second = wikiqa.build_dataset(ROWS, max_questions=1, seed=5)

    assert [q["id"] for q in first["questions"]] == [q["id"] for q in second["questions"]]
    assert len(first["documents"]) == 3  # sampling questions never shrinks the collection


def test_a_chunk_of_another_article_does_not_count_even_if_it_has_the_answer_text():
    dataset = wikiqa.build_dataset(ROWS)

    report = run_evaluation(dataset, embed=bag_of_words, llm=None, top_k=3, min_score=0.0)

    details = {d["question"]: d for d in report["retrieval"]["details"]}
    refund = details["refund how many days"]
    # both articles say "30 days", but only the first one is the question's own article
    assert sum(1 for hit in refund["retrieved"] if hit["relevant"]) == 1
    assert refund["rank"] == 1
