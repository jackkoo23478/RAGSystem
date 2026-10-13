"""Cutting a document into chunks.

chunk_pages is what ingestion uses: recursive chunking, which cuts at the biggest natural break that still fits
(paragraph, line, sentence end, comma, space) instead of every N characters, so a sentence is rarely cut in half.
It was chosen by measuring: on 500 questions about Cantonese Wikipedia and 500 about Traditional Chinese Wikipedia it was
as good as or better than fixed-size cutting, and it sent about 14% fewer characters to the LLM (see "Evaluation" in the README).

chunk_text is the older fixed-size cutting (a window of N characters every N - overlap characters). It stays as the
baseline the evaluation compares against.
"""

# The biggest break first. "  " (two spaces) is how a few sources, such as the Cantonese Wikipedia text, mark a section.
SEPARATORS = ["\n\n", "\n", "  ", "。", "！", "？", "!", "?", "；", ";", ". ", "，", ",", " "]


def chunk_text (text : str , chunk_size : int = 500 , overlap : int = 50) -> list[str] :
    """Fixed-size cutting."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    packs = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = start + chunk_size
        pack = text[start:end].strip()
        if pack:
            packs.append(pack)
        start += step

    return packs


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Move a range inwards so that it does not begin or end with white space."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split(text: str, start: int, end: int, size: int, separators: list[str]) -> list[tuple[int, int]]:
    """Cut [start, end) into pieces of at most `size` characters, using the biggest separator that is present.
    A separator stays at the end of the piece before it, so consecutive pieces always touch."""
    if end - start <= size:
        return [(start, end)]
    if not separators:  # nothing natural left: a hard cut
        return [(s, min(s + size, end)) for s in range(start, end, size)]

    separator, rest = separators[0], separators[1:]
    pieces, piece_start = [], start
    position = text.find(separator, start, end)
    while position != -1:
        cut = position + len(separator)
        pieces.append((piece_start, cut))
        piece_start = cut
        position = text.find(separator, cut, end)
    if piece_start < end:
        pieces.append((piece_start, end))
    if len(pieces) == 1:  # this separator does not occur: try the next, smaller one
        return _split(text, start, end, size, rest)

    result = []
    for s, e in pieces:
        result.extend(_split(text, s, e, size, rest) if e - s > size else [(s, e)])
    return result


def _merge(text: str, pieces: list[tuple[int, int]], size: int, overlap: int) -> list[tuple[int, int]]:
    """Join neighbouring pieces into chunks of at most `size` characters; a new chunk begins with the last pieces of the
    previous one (up to `overlap` characters)."""
    chunks, group = [], []
    for piece in pieces:
        length = piece[1] - group[0][0] if group else piece[1] - piece[0]
        if group and length > size:
            chunks.append((group[0][0], group[-1][1]))
            tail, total = [], 0
            for previous in reversed(group):
                if total + previous[1] - previous[0] > overlap:
                    break
                tail.insert(0, previous)
                total += previous[1] - previous[0]
            group = tail
            if group and piece[1] - group[0][0] > size:  # the overlap would not leave room for this piece
                group = []
        group.append(piece)
    if group:
        chunks.append((group[0][0], group[-1][1]))

    spans = []
    for s, e in chunks:
        s, e = trim_span(text, s, e)
        if s < e:
            spans.append((s, e))
    return spans


def recursive_spans(text: str, size: int = 500, overlap: int = 50, separators: list[str] | None = None,
                    start: int = 0, end: int | None = None) -> list[tuple[int, int]]:
    """Recursive cutting, as character ranges of the text. Text with no break at all (no space, no punctuation) is cut
    hard every `size` characters, and then there is no overlap."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk_size")
    end = len(text) if end is None else end
    pieces = _split(text, start, end, size, SEPARATORS if separators is None else separators)
    return _merge(text, pieces, size, overlap)


def chunk_recursive(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    return [text[s:e] for s, e in recursive_spans(text, chunk_size, overlap)]


def chunk_pages(
    pages: list[tuple[int | None, str]],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[tuple[int | None, str]]:
    result = []
    for page_number, text in pages:
        for piece in chunk_recursive(text, chunk_size, overlap):
            result.append((page_number, piece))
    return result
