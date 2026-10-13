import pytest

from evaluation import metrics


def test_a_chunk_is_relevant_when_it_has_any_evidence_phrase():
    assert metrics.is_relevant("Refund within 30 days.", ["30 days"])
    assert metrics.is_relevant("Refund within 30 days.", ["nothing here", "30 DAYS"])  # case does not matter
    assert not metrics.is_relevant("Refund within 14 days.", ["30 days"])
    assert not metrics.is_relevant("anything", [])


def test_first_relevant_rank_is_one_based():
    contents = ["unrelated", "has the evidence", "also has the evidence"]

    assert metrics.first_relevant_rank(contents, ["the evidence"]) == 2
    assert metrics.first_relevant_rank(contents, ["missing"]) is None
    assert metrics.first_relevant_rank([], ["x"]) is None


def test_hit_at_and_reciprocal_rank():
    assert metrics.hit_at(1, 1)
    assert metrics.hit_at(3, 4)
    assert not metrics.hit_at(5, 4)
    assert not metrics.hit_at(None, 4)

    assert metrics.reciprocal_rank(1) == 1.0
    assert metrics.reciprocal_rank(4) == 0.25
    assert metrics.reciprocal_rank(None) == 0.0


def test_an_answer_needs_one_alternative_from_every_group():
    must = [["locked"], ["30", "thirty"]]

    assert metrics.answer_is_correct("The account is locked for 30 minutes.", must)
    assert metrics.answer_is_correct("It stays LOCKED for thirty minutes", must)
    assert not metrics.answer_is_correct("The account is locked.", must)  # the second group is missing
    assert metrics.answer_is_correct("anything", [])  # no required facts


def test_citations_must_point_at_a_chunk_with_the_evidence():
    assert metrics.citations_are_supported(["wrong chunk", "the 30 days chunk"], ["30 days"])
    assert not metrics.citations_are_supported(["wrong chunk"], ["30 days"])
    assert not metrics.citations_are_supported([], ["30 days"])


def test_mean_and_rate():
    assert metrics.mean([1, 2, 3]) == 2
    assert metrics.mean([]) is None
    assert metrics.rate([True, False, True, True]) == 0.75
    assert metrics.rate([]) is None


def test_percentile_uses_the_nearest_rank():
    values = [10, 20, 30, 40, 50]

    assert metrics.percentile(values, 50) == 30
    assert metrics.percentile(values, 95) == 50
    assert metrics.percentile(values, 0) == 10
    assert metrics.percentile([], 50) is None
    assert metrics.percentile([7], 95) == 7


def test_an_answer_must_be_in_the_language_of_the_question():
    assert metrics.language_matches("How long is the warranty?", "The warranty lasts 2 years. [1]")
    assert not metrics.language_matches("How long is the warranty?", "保固期為2年。[1]")
    assert metrics.language_matches("保養期幾耐?", "保養期係 2 年。[1]")
    assert not metrics.language_matches("保養期幾耐?", "The warranty lasts 2 years. [1]")


def test_the_interval_of_a_rate_is_wide_with_few_questions_and_narrow_with_many():
    few = metrics.wilson_interval(26, 27)
    many = metrics.wilson_interval(960, 1000)

    assert few[1] - few[0] > 0.1 > many[1] - many[0]  # 26 of 27 could really be 82% to 99%
    assert few[0] < 26 / 27 < few[1] + 1e-9


def test_the_interval_stays_inside_zero_and_one_and_handles_no_questions():
    assert metrics.wilson_interval(0, 10)[0] == 0.0
    assert metrics.wilson_interval(10, 10)[1] == 1.0
    assert metrics.wilson_interval(0, 0) == (None, None)
