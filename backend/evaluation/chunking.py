"""Ways to cut a document into chunks, written to return character ranges (start, end) of the original text.

Ranges (not just the text) let the evaluation ask "does this chunk contain the answer, which sits at characters
a..b of the document?", a question that has the same answer whatever the chunker did.

    fixed      a window of `size` characters every `size - overlap` characters (what the app did before)
    recursive  cut at the biggest natural break that fits: paragraph, line, sentence end, comma, space, then a hard cut
               (what the app does now: it lives in app.features.ingestion.pipeline.chunker and is imported here)
    semantic   embed every sentence and cut where the meaning jumps (the neighbours are least alike)
"""
import re

import numpy as np

from app.features.ingestion.pipeline.chunker import recursive_spans, trim_span  # noqa: F401  (recursive_spans is re-exported)

SENTENCE = re.compile(r"(?s).*?(?:[。！？!?；;]+[」』”’）)]*|\n+|(?<=\w)\.(?=\s)|\Z)\s*")


def fixed_spans(text: str, size: int = 500, overlap: int = 50) -> list[tuple[int, int]]:
    """The same chunks as app.features.ingestion.pipeline.chunker.chunk_text, as ranges."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    spans, start, step = [], 0, size - overlap
    while start < len(text):
        s, e = trim_span(text, start, min(start + size, len(text)))
        if s < e:
            spans.append((s, e))
        start += step
    return spans


def sentence_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in SENTENCE.finditer(text):
        s, e = trim_span(text, match.start(), match.end())
        if s < e:
            spans.append((s, e))
    return spans


def semantic_spans(text: str, embed, percentile: float = 85, max_chars: int = 800, min_chars: int = 100,
                   gap_limit: float | None = None) -> list[tuple[int, int]]:
    """Cut where the meaning changes: embed every sentence and measure how unlike each neighbour is (the gap, 1 minus
    the cosine similarity). Two ways to decide what counts as a change:

        percentile  cut after the sentences whose gap is in the top (100 - percentile)% of THIS document. Every document
                    is cut at about the same rate, even one that never changes topic.
        gap_limit   cut after every sentence whose gap is bigger than this fixed number (it depends on the model: a gap of
                    0.4 means something else for another embedding model). A document that stays on one topic is not cut.

    Groups that come out longer than `max_chars` are cut again with the recursive splitter, and groups shorter than
    `min_chars` join the next one."""
    sentences = sentence_spans(text)
    if len(sentences) <= 1:
        return sentences

    vectors = np.array(embed([text[s:e] for s, e in sentences]), dtype=float)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    gaps = 1.0 - np.sum(vectors[:-1] * vectors[1:], axis=1)  # gaps[i]: how unlike sentence i and i+1 are
    limit = gap_limit if gap_limit is not None else np.percentile(gaps, percentile)

    groups, group_start = [], 0
    for i, gap in enumerate(gaps):
        if gap > limit:
            groups.append((sentences[group_start][0], sentences[i][1]))
            group_start = i + 1
    groups.append((sentences[group_start][0], sentences[-1][1]))

    merged = []
    for s, e in groups:  # a very short group has too little to say: it joins the one after it
        if merged and merged[-1][1] - merged[-1][0] < min_chars:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    if len(merged) > 1 and merged[-1][1] - merged[-1][0] < min_chars:
        merged[-2:] = [(merged[-2][0], merged[-1][1])]

    spans = []
    for s, e in merged:
        if e - s > max_chars:
            spans.extend(recursive_spans(text, size=max_chars, overlap=0, start=s, end=e))
        else:
            spans.append((s, e))
    return spans
