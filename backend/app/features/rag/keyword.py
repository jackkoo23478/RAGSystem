"""BM25 keyword search and the fusion of two rankings (hybrid search).

Searching by meaning (the embedding model) finds text that says the same thing in other words, but it is weak on exact words:
numbers, codes, names, and one question out of a hundred similar ones in a question bank. Keyword search is the opposite.
Hybrid search uses both. It was measured to be better than meaning alone on every test set (see "Evaluation" in the README).

BM25 scores a chunk for a question by the words they share, counting rare words more:

    score(D, Q) = sum over the words t of Q of   IDF(t) * f(t, D) * (k1 + 1) / (f(t, D) + k1 * (1 - b + b * |D| / avgdl))
    IDF(t)      = ln((N - n(t) + 0.5) / (n(t) + 0.5) + 1)

f(t, D): how often t occurs in the chunk. |D|: the length of the chunk. avgdl: the average length. N: the number of chunks.
n(t): how many chunks contain t. k1 limits how much repetition counts, b how much length counts.

Chinese has no spaces, so a run of Chinese characters is cut into pairs of neighbouring characters (bigrams): 國道施工 -> 國道 道施 施工.
Words and numbers made of letters and digits stay whole.
"""
import math
import re
from collections import Counter

import numpy as np

TOKEN = re.compile(r"[㐀-鿿]+|[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for match in TOKEN.finditer(text.lower()):
        piece = match.group()
        if piece.isascii():
            tokens.append(piece)
        elif len(piece) == 1:
            tokens.append(piece)
        else:
            tokens.extend(piece[i:i + 2] for i in range(len(piece) - 1))
    return tokens


class BM25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.size = len(documents)
        self.lengths = np.array([len(d) for d in documents], dtype=float)
        self.average_length = float(self.lengths.mean()) if self.size and self.lengths.mean() else 1.0

        postings: dict[str, tuple[list[int], list[int]]] = {}
        for index, document in enumerate(documents):
            for term, count in Counter(document).items():
                where, counts = postings.setdefault(term, ([], []))
                where.append(index)
                counts.append(count)
        self.postings = {t: (np.array(w), np.array(c, dtype=float)) for t, (w, c) in postings.items()}
        self.idf = {t: self.inverse_document_frequency(len(w)) for t, (w, _) in self.postings.items()}

    def inverse_document_frequency(self, containing: int) -> float:
        return math.log((self.size - containing + 0.5) / (containing + 0.5) + 1)

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        """One score for every chunk (0 for a chunk that shares no word with the question)."""
        result = np.zeros(self.size)
        for term in set(query_tokens):  # a word repeated in the question does not count twice
            if term not in self.postings:
                continue
            where, counts = self.postings[term]
            length_factor = self.k1 * (1 - self.b + self.b * self.lengths[where] / self.average_length)
            result[where] += self.idf[term] * counts * (self.k1 + 1) / (counts + length_factor)
        return result


def rank_positions(scores: np.ndarray) -> np.ndarray:
    """For every question (row), the position of each chunk in the ranking: 1 for the best chunk."""
    order = np.argsort(-scores, axis=1, kind="stable")
    positions = np.empty_like(order)
    rows = np.arange(scores.shape[0])[:, None]
    positions[rows, order] = np.arange(1, scores.shape[1] + 1)
    return positions


def reciprocal_rank_fusion(score_matrices: list[np.ndarray], k: int = 60) -> np.ndarray:
    """Merge rankings without comparing their scores (cosine similarity and BM25 are on different scales):
    every chunk gets 1 / (k + its position) from each ranking, and the parts are added.

    A chunk with a score of 0 or less gets nothing from that ranking. This matters for BM25, where most chunks share no
    word with the question: they all tie at 0 and must not be ranked by the order they happen to be stored in."""
    total = 0.0
    for matrix in score_matrices:
        total = total + np.where(matrix > 0, 1.0 / (k + rank_positions(matrix)), 0.0)
    return total
