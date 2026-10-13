from evaluation.compare import best_threshold
from evaluation.embedders import prefixes_for
from evaluation.run import run_evaluation
from tests.services.test_evaluation_run import DATASET, bag_of_words


def _answerable(score, rank=1):
    return {"kind": "answerable", "rank": rank, "scores": [score]}


def _unanswerable(score):
    return {"kind": "unanswerable", "scores": [score]}


def test_the_best_threshold_separates_the_two_kinds_of_question():
    details = [_answerable(0.8), _answerable(0.7), _unanswerable(0.4), _unanswerable(0.3)]

    best = best_threshold(details)

    assert 0.41 <= best["min_score"] <= 0.7  # above every unanswerable score, not above an answerable one
    assert best["found"] == 1.0
    assert best["false_evidence"] == 0.0


def test_the_lowest_threshold_wins_a_tie():
    details = [_answerable(0.8), _unanswerable(0.1)]

    assert best_threshold(details)["min_score"] == 0.11


def test_a_threshold_that_refuses_everything_cannot_win():
    details = [_answerable(0.6), _answerable(0.5), _unanswerable(0.55)]

    best = best_threshold(details)

    assert best["found"] > 0  # not the trivial "refuse all" answer


def test_best_threshold_needs_both_kinds_of_question():
    assert best_threshold([_answerable(0.5)]) is None
    assert best_threshold([]) is None


def test_e5_models_get_their_query_and_passage_prefixes():
    assert prefixes_for("intfloat/multilingual-e5-small") == ("passage: ", "query: ")
    assert prefixes_for("BAAI/bge-m3") == ("", "")
    assert prefixes_for("all-MiniLM-L6-v2") == ("", "")


def test_documents_and_questions_can_use_different_embed_functions():
    seen = {"documents": 0, "questions": 0}

    def embed_documents(texts):
        seen["documents"] += len(texts)
        return bag_of_words(texts)

    def embed_questions(texts):
        seen["questions"] += len(texts)
        return bag_of_words(texts)

    run_evaluation(DATASET, embed=embed_documents, embed_query=embed_questions, top_k=2)

    assert seen["documents"] == 2  # the two chunks
    assert seen["questions"] == 3  # the three questions
