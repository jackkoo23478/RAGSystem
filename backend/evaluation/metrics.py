"""Pure scoring functions: no database, no model, no network, so they are easy to test."""
import math

from app.features.rag.language import is_chinese


def language_matches(question: str, answer: str) -> bool:
    """The answer is in the language of the question: Chinese for a Chinese question, English for an English one.
    Facts are judged separately (answer_is_correct), so a right fact in the wrong language shows up as its own problem."""
    return is_chinese(question) == is_chinese(answer)


def is_relevant(content: str, evidence: list[str]) -> bool:
    """A chunk is relevant when it contains any of the evidence phrases (case does not matter)."""
    text = content.lower()
    return any(phrase.lower() in text for phrase in evidence)


def first_relevant_rank(contents: list[str], evidence: list[str]) -> int | None:
    """1-based position of the first relevant chunk in a ranked list, or None."""
    for position, content in enumerate(contents, start=1):
        if is_relevant(content, evidence):
            return position
    return None


def first_true_rank(flags: list[bool]) -> int | None:
    """1-based position of the first True in a ranked list of yes/no judgements, or None."""
    for position, flag in enumerate(flags, start=1):
        if flag:
            return position
    return None


def hit_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def reciprocal_rank(rank: int | None) -> float:
    return 0.0 if rank is None else 1.0 / rank


def answer_is_correct(answer: str, must_contain: list[list[str]]) -> bool:
    """Correct when, for EVERY group, the answer contains at least one of its alternatives."""
    text = answer.lower()
    return all(any(option.lower() in text for option in group) for group in must_contain)


def citations_are_supported(cited_contents: list[str], evidence: list[str]) -> bool:
    """The answer cites at least one chunk that really holds the evidence."""
    return any(is_relevant(content, evidence) for content in cited_contents)


def sign_test_p(gained: int, lost: int) -> float:
    """Two-sided p-value of "the questions gained and the questions lost are equally likely", for a paired comparison.
    Small (below 0.05) means the difference is unlikely to be chance."""
    changed = gained + lost
    if changed == 0:
        return 1.0
    smaller = min(gained, lost)
    tail = sum(math.comb(changed, i) for i in range(smaller + 1)) / 2 ** changed
    return min(1.0, 2 * tail)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    """95% interval of a rate measured on n questions: where the true rate probably lies (Wilson score interval).
    With few questions it is wide, which is the honest answer to "how sure are these percentages"."""
    if n == 0:
        return None, None
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def rate(flags: list[bool]) -> float | None:
    return mean([1.0 if flag else 0.0 for flag in flags])


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile (p from 0 to 100)."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(p / 100 * len(ordered)) - 1)
    return ordered[index]
