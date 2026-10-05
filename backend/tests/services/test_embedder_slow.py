import math

import pytest

from app.features.ingestion.pipeline.embedder import embed_texts

pytestmark = pytest.mark.slow  # real model: deselect with  -m "not slow"


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def test_embedding_shape():
    vectors = embed_texts(["hello", "world"])

    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)


def test_empty_input_returns_empty_list():
    assert embed_texts([]) == []


def test_related_text_scores_higher_than_unrelated():
    question, related, unrelated = embed_texts([
        "How many days of annual leave do I get?",
        "Employees are entitled to 14 days of paid vacation each year.",
        "The server room temperature must stay below 24 degrees.",
    ])

    assert cosine(question, related) > cosine(question, unrelated)
