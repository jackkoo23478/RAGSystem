import re
import zlib

import pytest

from app.features.rag.llm import LLMError
from app.features.rag.prompt import NO_ANSWER_TEXT
from evaluation.answer_eval import contains_answer, evaluate_answers_at_scale, render

DOCUMENTS = [
    {"id": "a", "title": "Refunds", "text": "Refunds are possible within 30 days of delivery."},
    {"id": "b", "title": "Shipping", "text": "Express shipping costs 12 dollars extra."},
    {"id": "c", "title": "Warranty", "text": "The warranty on electronics lasts 2 years."},
]


def span_of(document: str, phrase: str):
    text = next(d["text"] for d in DOCUMENTS if d["id"] == document)
    start = text.index(phrase)
    return [(start, start + len(phrase))]


QUESTIONS = [
    {"id": "q1", "question": "refund within how many days", "document": "a", "answer_spans": span_of("a", "30 days")},
    {"id": "q2", "question": "express shipping dollars", "document": "b", "answer_spans": span_of("b", "12 dollars")},
    {"id": "q3", "question": "warranty electronics years", "document": "c", "answer_spans": span_of("c", "2 years")},
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


class ScriptedLLM:
    """Answers each question with a prepared reply, keyed by a word of the question; remembers what it was asked."""
    model = "scripted"

    def __init__(self, replies):
        self.replies = replies
        self.prompts = []

    def generate(self, messages):
        self.prompts.append(messages)
        question = messages[1]["content"].rsplit("Question: ", 1)[-1]
        for word, reply in self.replies.items():
            if word in question:
                if isinstance(reply, Exception):
                    raise reply
                return reply
        raise AssertionError(f"no reply prepared for {question!r}")


def run(replies, **kwargs):
    kwargs.setdefault("min_score", 0.0)
    kwargs.setdefault("rerank", None)
    return evaluate_answers_at_scale(DATASET, ScriptedLLM(replies), embed=bag_of_words, **kwargs)


def statuses(report):
    return {r["id"]: r["status"] for r in report["details"]}


# ---------- contains_answer ----------

def test_the_answer_is_found_whatever_the_case_spacing_punctuation_or_script():
    assert contains_answer("You have 30 DAYS.", ["30 days"])
    assert contains_answer("在 蒙哥馬里,建立首都", ["蒙哥馬里"])
    assert contains_answer("在蒙哥马里建立首都", ["蒙哥馬里"])  # simplified characters in the answer
    assert not contains_answer("You have 14 days.", ["30 days"])
    assert not contains_answer("anything", [""])  # an empty answer never matches


# ---------- the steps of one question ----------

def test_a_right_answer_with_a_citation_is_correct():
    report = run({"refund": "You have 30 days. [1]", "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    assert statuses(report) == {"q1": "answered", "q2": "answered", "q3": "answered"}
    assert report["summary"]["correct"] == 1.0
    assert report["summary"]["answer_in_the_chunks_given"] == 1.0


def test_a_right_answer_without_a_citation_is_not_shown_and_not_correct():
    report = run({"refund": "You have 30 days.", "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    assert statuses(report)["q1"] == "invalid_answer"
    assert report["summary"]["correct"] == pytest.approx(2 / 3)


def test_a_refusal_counts_as_refused_even_when_the_chunks_held_the_answer():
    report = run({"refund": NO_ANSWER_TEXT, "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    assert statuses(report)["q1"] == "no_evidence"
    assert report["summary"]["refused_by_the_llm_though_the_answer_was_given"] == 1  # the search did its job, the LLM did not


def test_a_wrong_answer_is_counted_apart_from_a_search_that_missed():
    report = run({"refund": "You have 14 days. [1]", "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    assert report["summary"]["wrong_answer_though_the_answer_was_given"] == 1
    assert report["summary"]["correct"] == pytest.approx(2 / 3)


def test_a_question_below_the_threshold_never_reaches_the_llm():
    llm = ScriptedLLM({})

    report = evaluate_answers_at_scale(DATASET, llm, embed=bag_of_words, rerank=None, min_score=0.99)

    assert set(statuses(report).values()) == {"below_threshold"}
    assert llm.prompts == []
    assert report["summary"]["correct"] == 0.0


def test_an_unreachable_llm_is_a_failed_question_not_a_crash():
    report = run({"refund": LLMError("down"), "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    assert statuses(report)["q1"] == "failed"


def test_simplified_characters_written_by_the_llm_are_turned_into_traditional_ones_before_checking():
    dataset = {
        "documents": [{"id": "z", "title": "首都", "text": "邦聯在蒙哥馬里建立首都。"}],
        "questions": [{"id": "z1", "question": "capital", "document": "z", "answer_spans": [(4, 8)]}],
    }
    llm = ScriptedLLM({"capital": "邦联在蒙哥马里建立首都。[1]"})

    report = evaluate_answers_at_scale(dataset, llm, embed=bag_of_words, rerank=None, min_score=0.0)

    assert report["details"][0]["correct"] is True
    assert "蒙哥馬里" in report["details"][0]["answer"]


# ---------- the reranker ----------

def test_the_reranker_chooses_which_chunks_the_llm_sees():
    seen = []

    def prefer_shipping(question, passages):
        seen.append(len(passages))
        return [1.0 if "shipping" in p.lower() else 0.0 for p in passages]

    llm = ScriptedLLM({"refund": "x [1]", "shipping": "x [1]", "warranty": "x [1]"})
    evaluate_answers_at_scale(DATASET, llm, embed=bag_of_words, rerank=prefer_shipping, top_k=1, candidates=3, min_score=0.0)

    assert seen == [3, 3, 3]  # three candidates each time
    assert all("Express shipping" in prompt[1]["content"] for prompt in llm.prompts)  # and the shipping passage always goes first


def test_without_a_reranker_the_first_chunks_of_the_search_are_used_as_they_are():
    llm = ScriptedLLM({"refund": "x [1]", "shipping": "x [1]", "warranty": "x [1]"})

    report = evaluate_answers_at_scale(DATASET, llm, embed=bag_of_words, rerank=None, top_k=1, min_score=0.0)

    assert report["config"]["reranker"] is None
    assert len(llm.prompts) == 3


# ---------- the report ----------

def test_the_summary_has_an_interval_and_the_table_names_it():
    report = run({"refund": "You have 30 days. [1]", "shipping": "It costs 12 dollars. [1]", "warranty": "It lasts 2 years. [1]"})

    low, high = report["summary"]["correct_interval_95"]
    assert 0.0 <= low <= 1.0 <= high + 1e-9
    text = render("A test set", report)
    assert "answer correct" in text and "95% interval" in text
