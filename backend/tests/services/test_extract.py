import pytest

from app.features.ingestion.pipeline.extract import extract_pages


def test_extract_pages_txt_is_one_page_without_number(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("Annual leave is 14 days.", encoding="utf-8")

    assert extract_pages(str(f), "txt") == [(None, "Annual leave is 14 days.")]


def test_extract_pages_txt_is_read_as_utf8(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("年假有十四日 café", encoding="utf-8")

    assert extract_pages(str(f), "txt") == [(None, "年假有十四日 café")]


def test_extract_pages_pdf_numbers_pages_from_one(tmp_path, make_pdf):
    f = tmp_path / "doc.pdf"
    make_pdf(f, ["First page about leave", "Second page about expenses"])

    pages = extract_pages(str(f), "pdf")

    assert [number for number, _ in pages] == [1, 2]
    assert "First page about leave" in pages[0][1]
    assert "Second page about expenses" in pages[1][1]


def test_extract_pages_pdf_text_stays_on_its_own_page(tmp_path, make_pdf):
    f = tmp_path / "doc.pdf"
    make_pdf(f, ["alpha", "beta"])

    (_, first), (_, second) = extract_pages(str(f), "pdf")

    assert "beta" not in first
    assert "alpha" not in second


def test_extract_pages_unsupported_type_raises(tmp_path):
    f = tmp_path / "doc.docx"
    f.write_bytes(b"whatever")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_pages(str(f), "docx")


def test_extract_pages_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_pages(str(tmp_path / "nope.txt"), "txt")
