import pytest

from app.features.ingestion.pipeline.chunker import chunk_pages, chunk_text


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
    text = "abcdefghij" * 100

    result = chunk_pages([(1, text)], chunk_size=300, overlap=30)

    assert [piece for _, piece in result] == chunk_text(text, chunk_size=300, overlap=30)


def test_chunk_pages_empty_input():
    assert chunk_pages([]) == []
