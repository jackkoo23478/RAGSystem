import pytest

from app.features.ingestion.pipeline.chunker import chunk_pages, chunk_recursive, chunk_text, recursive_spans


@pytest.mark.parametrize("text, expected", [
    ("", []),
    ("   ", []),
    ("hello", ["hello"]),
])
def test_chunk_text_input(text, expected):
    assert chunk_text(text) == expected


def test_chunk_size_is_respected():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    assert all(len(c) <= 300 for c in chunks)


def test_adjacent_chunks_overlap():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    # last 30 chars of chunk 0 must be the first 30 chars of chunk 1
    assert chunks[0][-30:] == chunks[1][:30]


def test_no_characters_are_lost():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    # drop the repeated overlap from every chunk except the first, then glue back together
    rebuilt = chunks[0] + "".join(c[30:] for c in chunks[1:])
    assert rebuilt == text


def test_chunk_count_and_lengths():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    # step = 270 -> starts at 0, 270, 540, 810; the last chunk is 1000 - 810 = 190 chars
    assert len(chunks) == 4
    assert [len(c) for c in chunks] == [300, 300, 300, 190]

def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=10, overlap=10)


def test_chunk_pages_short_pages_keep_their_numbers():
    assert chunk_pages([(1, "hello"), (2, "world")]) == [(1, "hello"), (2, "world")]


def test_chunk_pages_long_page_splits_but_keeps_page_number():
    pages = [(7, "abcdefghij" * 100)]

    result = chunk_pages(pages, chunk_size=300, overlap=30)

    assert len(result) == 4
    assert {number for number, _ in result} == {7}


def test_chunk_pages_keeps_page_order_across_pages():
    pages = [(1, "abcdefghij" * 100), (2, "klmnopqrst" * 100)]

    result = chunk_pages(pages, chunk_size=300, overlap=30)

    numbers = [number for number, _ in result]
    assert numbers == sorted(numbers)
    assert set(numbers) == {1, 2}


def test_chunk_pages_skips_blank_pages_without_shifting_numbers():
    pages = [(1, "a"), (2, "   "), (3, "b")]

    assert chunk_pages(pages) == [(1, "a"), (3, "b")]


def test_chunk_pages_keeps_none_page_number_for_txt():
    assert chunk_pages([(None, "hello")]) == [(None, "hello")]


def test_chunk_pages_passes_custom_sizes_through():
    text = "Refunds are possible within thirty days. Shipping takes five days. The warranty lasts two years. " * 12

    result = chunk_pages([(1, text)], chunk_size=300, overlap=30)

    assert [piece for _, piece in result] == chunk_recursive(text, chunk_size=300, overlap=30)
    assert all(len(piece) <= 300 for _, piece in result)


# ---------- recursive chunking (what ingestion uses) ----------

SENTENCES = "第一句係關於退款。第二句係關於運送。第三句係關於保養。第四句係關於密碼。"


@pytest.mark.parametrize("text, expected", [
    ("", []),
    ("   ", []),
    ("hello", ["hello"]),
])
def test_recursive_input(text, expected):
    assert chunk_recursive(text) == expected


def test_recursive_cuts_at_sentence_ends_when_a_sentence_fits():
    assert chunk_recursive(SENTENCES, chunk_size=20, overlap=0) == [
        "第一句係關於退款。第二句係關於運送。",
        "第三句係關於保養。第四句係關於密碼。",
    ]


def test_recursive_prefers_the_bigger_break():
    text = "Alpha one. Alpha two.\n\nBeta one. Beta two."

    assert chunk_recursive(text, chunk_size=25, overlap=0) == ["Alpha one. Alpha two.", "Beta one. Beta two."]


def test_recursive_does_not_cut_a_sentence_in_half_when_it_fits_in_a_chunk():
    text = "The refund period is thirty days from delivery. " * 30

    chunks = chunk_recursive(text, chunk_size=200, overlap=0)

    assert all(c.endswith("delivery.") for c in chunks)  # fixed-size cutting would stop in the middle of a sentence


def test_recursive_chunks_never_exceed_the_size_and_cover_the_whole_text():
    text = "短句。" * 40 + "沒有任何標點的一長串文字" * 30

    spans = recursive_spans(text, size=60, overlap=10)

    assert all(e - s <= 60 for s, e in spans)
    covered = [False] * len(text)
    for s, e in spans:
        covered[s:e] = [True] * (e - s)
    assert all(covered)


def test_recursive_hard_cuts_text_without_any_break_and_then_has_no_overlap():
    chunks = chunk_recursive("字" * 250, chunk_size=100, overlap=10)

    assert [len(c) for c in chunks] == [100, 100, 50]


def test_recursive_overlap_repeats_the_end_of_the_previous_chunk():
    text = "一二三四五。六七八九十。甲乙丙丁戊。"

    spans = recursive_spans(text, size=12, overlap=6)

    assert len(spans) >= 2
    for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
        assert s2 < e1 and e2 > e1  # the next chunk starts before the previous one ends, and goes on past it


def test_recursive_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_recursive("hello world", chunk_size=10, overlap=10)


def test_recursive_keeps_a_page_text_with_line_breaks_in_order():
    text = "Line one of the page\nline two continues\nline three ends here.\n\nSecond paragraph starts here."

    chunks = chunk_recursive(text, chunk_size=40, overlap=0)

    assert "".join(chunks).replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")
    assert chunks[-1] == "Second paragraph starts here."  # the paragraph break is a cut, the line breaks are not


def test_chunk_pages_empty_input():
    assert chunk_pages([]) == []
