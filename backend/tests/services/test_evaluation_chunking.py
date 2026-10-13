import numpy as np
import pytest

from app.features.ingestion.pipeline.chunker import chunk_text
from evaluation import chunking


def texts(text, spans):
    return [text[s:e] for s, e in spans]


# ---------- fixed ----------

@pytest.mark.parametrize("size, overlap", [(500, 50), (30, 3), (7, 0)])
def test_fixed_spans_cut_exactly_like_the_apps_chunker(size, overlap):
    text = "Refunds are possible within thirty days.  Shipping takes five days。 保養期係兩年。 " * 12

    assert texts(text, chunking.fixed_spans(text, size, overlap)) == chunk_text(text, size, overlap)


def test_fixed_spans_reject_an_overlap_that_is_not_smaller_than_the_size():
    with pytest.raises(ValueError):
        chunking.fixed_spans("anything", 10, 10)


def test_fixed_spans_of_an_empty_or_blank_text_are_empty():
    assert chunking.fixed_spans("", 10, 1) == []
    assert chunking.fixed_spans("   \n  ", 10, 1) == []


# ---------- recursive ----------

SENTENCES = "第一句係關於退款。第二句係關於運送。第三句係關於保養。第四句係關於密碼。"


def test_recursive_cuts_at_sentence_ends_when_a_sentence_fits():
    spans = chunking.recursive_spans(SENTENCES, size=20, overlap=0)

    assert texts(SENTENCES, spans) == ["第一句係關於退款。第二句係關於運送。", "第三句係關於保養。第四句係關於密碼。"]


def test_recursive_prefers_the_bigger_break():
    text = "Alpha one. Alpha two.\n\nBeta one. Beta two."

    spans = chunking.recursive_spans(text, size=25, overlap=0)

    assert texts(text, spans) == ["Alpha one. Alpha two.", "Beta one. Beta two."]  # cut at the blank line, not mid-sentence


def test_recursive_chunks_never_exceed_the_size_and_cover_the_whole_text():
    text = "短句。" * 40 + "沒有任何標點的一長串文字" * 30

    spans = chunking.recursive_spans(text, size=60, overlap=10)

    assert all(e - s <= 60 for s, e in spans)
    covered = np.zeros(len(text), dtype=bool)
    for s, e in spans:
        covered[s:e] = True
    assert covered.all()


def test_recursive_hard_cuts_text_without_any_break():
    text = "字" * 250

    spans = chunking.recursive_spans(text, size=100, overlap=0)

    assert [e - s for s, e in spans] == [100, 100, 50]


def test_recursive_overlap_repeats_the_end_of_the_previous_chunk():
    text = "一二三四五。六七八九十。甲乙丙丁戊。"

    spans = chunking.recursive_spans(text, size=12, overlap=6)

    assert len(spans) >= 2
    for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
        assert s2 < e1  # the next chunk begins before the previous one ends
        assert e2 > e1


def test_recursive_text_that_already_fits_is_one_chunk():
    assert chunking.recursive_spans("Short text.", size=100, overlap=10) == [(0, 11)]


# ---------- sentences ----------

def test_sentences_end_at_chinese_and_western_stops_and_at_line_breaks():
    text = "第一句。第二句！Third one. Fourth?\n第五行"

    assert texts(text, chunking.sentence_spans(text)) == ["第一句。", "第二句！", "Third one.", "Fourth?", "第五行"]


def test_sentence_spans_of_blank_text_are_empty():
    assert chunking.sentence_spans("  \n ") == []


# ---------- semantic ----------

def topic_embed(texts_):
    """Sentences about cats point one way, sentences about tax the other."""
    return [[1.0, 0.0] if "貓" in t else [0.0, 1.0] for t in texts_]


TWO_TOPICS = "貓喜歡食魚。貓喺屋頂瞓覺。貓會捉老鼠。稅款要喺四月前申報。稅務局會寄出通知。稅率視乎收入而定。"


def test_semantic_cuts_where_the_topic_changes():
    spans = chunking.semantic_spans(TWO_TOPICS, topic_embed, percentile=70, max_chars=500, min_chars=0)

    assert texts(TWO_TOPICS, spans) == [
        "貓喜歡食魚。貓喺屋頂瞓覺。貓會捉老鼠。",
        "稅款要喺四月前申報。稅務局會寄出通知。稅率視乎收入而定。",
    ]


def test_semantic_cuts_a_group_that_is_too_long():
    spans = chunking.semantic_spans(TWO_TOPICS, topic_embed, percentile=70, max_chars=12, min_chars=0)

    assert len(spans) > 2
    assert all(e - s <= 12 for s, e in spans)


def test_semantic_joins_a_group_that_is_too_short_to_the_next_one():
    text = "貓。稅款要喺四月前申報。稅務局會寄出通知。"

    spans = chunking.semantic_spans(text, topic_embed, percentile=40, max_chars=500, min_chars=8)

    assert texts(text, spans) == ["貓。稅款要喺四月前申報。稅務局會寄出通知。"]


def test_semantic_of_one_sentence_is_that_sentence():
    assert chunking.semantic_spans("只有一句。", topic_embed) == [(0, 5)]


# ---------- semantic with a fixed gap ----------

def test_a_fixed_gap_cuts_only_where_the_topic_really_changes():
    spans = chunking.semantic_spans(TWO_TOPICS, topic_embed, gap_limit=0.5, max_chars=500, min_chars=0)

    assert texts(TWO_TOPICS, spans) == [
        "貓喜歡食魚。貓喺屋頂瞓覺。貓會捉老鼠。",
        "稅款要喺四月前申報。稅務局會寄出通知。稅率視乎收入而定。",
    ]


def test_a_text_that_stays_on_one_topic_is_not_cut_by_a_fixed_gap():
    one_topic = "貓喜歡食魚。貓喺屋頂瞓覺。貓會捉老鼠。貓都鍾意曬太陽。"

    assert chunking.semantic_spans(one_topic, topic_embed, gap_limit=0.5, max_chars=500, min_chars=0) == [(0, len(one_topic))]
    # a percentile always finds something to cut, even when nothing changed: the weak point of that method
    # (all gaps are equal here, so the top gap ties with the rest and nothing is strictly above the limit)


def test_a_gap_limit_above_every_gap_gives_one_chunk():
    assert chunking.semantic_spans(TWO_TOPICS, topic_embed, gap_limit=2.0, max_chars=500, min_chars=0) == [(0, len(TWO_TOPICS))]
