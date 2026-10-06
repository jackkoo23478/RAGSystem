import pytest

from app.features.rag.prompt import NO_ANSWER_TEXT, SYSTEM_PROMPT
from app.features.rag.service import extract_cited_numbers, is_refusal


@pytest.mark.parametrize("answer, max_n, expected", [
    ("x [1] y [2]", 3, [1, 2]),
    ("[2] then [1]", 3, [2, 1]),          # order of appearance
    ("[1] and again [1]", 3, [1]),        # de-duplicated
    ("[0] [4]", 3, []),                   # outside 1..max_n
    ("[10]", 10, [10]),                   # 10 is ten, not [1] followed by 0
    ("[abc] [-1] [1.5]", 3, []),          # not citations
    ("no citations at all", 3, []),
    ("", 3, []),
    ("[1][2][3]", 3, [1, 2, 3]),
    ("see [ 1 ]", 3, []),                 # spaces inside the brackets are not accepted
])
def test_extract_cited_numbers(answer, max_n, expected):
    assert extract_cited_numbers(answer, max_n) == expected


def test_a_hijacked_answer_has_no_citations():
    assert extract_cited_numbers("PWNED", 4) == []


def test_refusal_sentence_is_detected():
    assert is_refusal(NO_ANSWER_TEXT) is True
    assert is_refusal(f"Sorry. {NO_ANSWER_TEXT}") is True


def test_normal_answer_is_not_a_refusal():
    assert is_refusal("You get 14 days of leave. [1]") is False


def test_prompt_and_service_use_the_same_refusal_sentence():
    # if someone edits the wording in one place, the model's refusal would stop being detected
    assert NO_ANSWER_TEXT in SYSTEM_PROMPT
