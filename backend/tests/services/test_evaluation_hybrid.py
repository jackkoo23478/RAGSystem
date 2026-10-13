import numpy as np
import pytest

from evaluation import metrics
from evaluation.hybrid import BM25, rank_positions, reciprocal_rank_fusion, tokenize
from evaluation.hybrid_eval import STEM, evaluate_methods


# ---------- tokenizing ----------

def test_chinese_is_cut_into_pairs_of_neighbouring_characters():
    assert tokenize("國道施工") == ["國道", "道施", "施工"]


def test_letters_and_numbers_stay_whole_and_case_does_not_matter():
    assert tokenize("Refund within 30 days") == ["refund", "within", "30", "days"]


def test_punctuation_and_spaces_stop_a_pair_from_crossing_them():
    assert tokenize("國道，施工 路段。") == ["國道", "施工", "路段"]


def test_a_single_chinese_character_is_kept_and_mixed_text_is_split_by_script():
    assert tokenize("A 車 B2") == ["a", "車", "b2"]
    assert tokenize("PDF文件") == ["pdf", "文件"]
    assert tokenize("") == []


# ---------- BM25 ----------

def corpus_with(word_in: int, total: int = 286):
    """`total` chunks of two words each; the word "rare" is in the first `word_in` of them."""
    return [["rare", "x"] if i < word_in else ["other", "y"] for i in range(total)]


def test_the_idf_of_a_rare_word_is_big_and_of_a_common_word_is_small():
    assert BM25(corpus_with(1)).idf["rare"] == pytest.approx(5.254, abs=0.001)
    assert BM25(corpus_with(250)).idf["rare"] == pytest.approx(0.136, abs=0.001)


def test_repeating_a_word_helps_less_and_less_and_never_passes_the_ceiling():
    docs = [["a"] + ["pad"] * 9, ["a"] * 3 + ["pad"] * 7, ["a"] * 10, ["b"] * 10, ["c"] * 10]  # all 10 words long
    bm25 = BM25(docs, k1=1.5, b=0.75)

    once, thrice, tenfold = bm25.scores(["a"])[:3]

    assert once < thrice < tenfold
    assert tenfold - thrice < thrice - once  # the extra 7 repeats add less than the first 2 did
    assert tenfold < bm25.idf["a"] * (1.5 + 1)  # the ceiling


def test_the_same_word_counts_for_more_in_a_short_chunk():
    docs = [["a", "pad"], ["a"] + ["pad"] * 19, ["z"] * 10]
    scores = BM25(docs).scores(["a"])

    assert scores[0] > scores[1]


def test_a_rare_word_beats_a_pile_of_common_words():
    docs = [["common"] * 5, ["common"] * 5, ["common", "rare"]]
    docs += [["common", "filler"] for _ in range(20)]

    scores = BM25(docs).scores(["common", "rare"])

    assert scores.argmax() == 2


def test_a_word_in_the_question_twice_counts_once_and_an_unknown_word_counts_for_nothing():
    bm25 = BM25([["a", "b"], ["c", "d"]])

    assert bm25.scores(["a", "a"]).tolist() == bm25.scores(["a"]).tolist()
    assert bm25.scores(["nothing"]).tolist() == [0.0, 0.0]


def test_the_formula_for_one_word_matches_a_hand_calculation():
    docs = [["a", "b", "b"], ["b", "b", "b"], ["c", "c", "c"]]  # N = 3, "a" is in 1 chunk, every chunk has 3 words
    k1, b = 1.5, 0.75

    idf = np.log((3 - 1 + 0.5) / (1 + 0.5) + 1)
    expected = idf * 1 * (k1 + 1) / (1 + k1 * (1 - b + b * 3 / 3))

    assert BM25(docs, k1, b).scores(["a"])[0] == pytest.approx(expected)


# ---------- merging two rankings ----------

def test_rank_positions_are_one_for_the_best_chunk_of_each_question():
    scores = np.array([[0.1, 0.9, 0.5], [3.0, 1.0, 2.0]])

    assert rank_positions(scores).tolist() == [[3, 1, 2], [1, 3, 2]]


def test_a_chunk_that_is_first_in_both_rankings_wins_the_fusion():
    a = np.array([[9.0, 1.0, 2.0]])
    b = np.array([[0.9, 0.1, 0.2]])  # a different scale, same order

    fused = reciprocal_rank_fusion([a, b])

    assert fused.argmax() == 0


def test_the_fusion_does_not_care_about_the_scale_of_the_scores():
    a = np.array([[0.2, 0.9, 0.5]])
    b = np.array([[400.0, 100.0, 300.0]])

    assert np.allclose(reciprocal_rank_fusion([a, b]), reciprocal_rank_fusion([a * 1000, b / 1000]))


def test_two_weak_votes_can_beat_one_strong_vote():
    # chunk 2 is second for both; chunks 0 and 1 are first for one and last for the other
    a = np.array([[3.0, 1.0, 2.0]])
    b = np.array([[1.0, 3.0, 2.0]])

    fused = reciprocal_rank_fusion([a, b], k=1)  # a small k makes first place count more: 1/2+1/4 against 2 x 1/3

    assert fused[0, 0] > fused[0, 2]


# ---------- the sign test ----------

def test_sign_test_says_chance_when_the_changes_are_balanced():
    assert metrics.sign_test_p(10, 10) == 1.0
    assert metrics.sign_test_p(0, 0) == 1.0


def test_sign_test_says_not_chance_when_nearly_all_changes_go_one_way():
    assert metrics.sign_test_p(31, 9) < 0.002
    assert metrics.sign_test_p(9, 31) == metrics.sign_test_p(31, 9)
    assert 0.3 < metrics.sign_test_p(29, 21) < 0.35  # the Cantonese Wikipedia example from the chunking comparison


# ---------- the comparison ----------

TEXTS = ["國道施工路段要減速", "變換車道要顯示方向燈", "退款要喺三十日內申請"]


def test_keywords_find_the_chunk_that_the_embedding_ranks_wrong():
    question_vectors = [[1.0, 0.0]]
    chunk_vectors = [[0.0, 1.0], [1.0, 0.0], [0.0, 1.0]]  # by meaning the question looks like chunk 1

    results = evaluate_methods(question_vectors, chunk_vectors, TEXTS, ["國道施工路段"], lambda q, c: c == 0, top_k=1)

    assert results["meaning (embedding)"]["hit_at_1"] == 0.0
    assert results["keywords (BM25)"]["hit_at_1"] == 1.0
    assert results["keywords (BM25)"]["gained"] == 1 and results["keywords (BM25)"]["lost"] == 0


def test_the_hybrid_finds_it_in_the_top_results_when_either_side_does():
    results = evaluate_methods([[1.0, 0.0]], [[0.0, 1.0], [1.0, 0.0], [0.0, 1.0]], TEXTS, ["國道施工路段"],
                               lambda q, c: c == 0, top_k=2)

    assert results["hybrid (both, RRF)"]["hit_at_k"] == 1.0


# ---------- questions copied from a question bank ----------

def test_the_text_between_the_number_and_the_first_option_is_the_question():
    text = "831 (3)  汽車駕駛人行駛在慢車道上，下列何項駕駛行為正確？ (1)只要沒車可以直接切入。 (2)不須注意。 832 (2) 另一題？ (1)甲"

    assert [m.group(1) for m in STEM.finditer(text)] == ["汽車駕駛人行駛在慢車道上，下列何項駕駛行為正確？", "另一題？"]
