import json

import pytest

from app.features.documents.models import DocumentChunk
from app.features.documents.repository import create_document
from app.features.ingestion.exceptions import DocumentNotFoundError, EmptyDocumentError
from app.features.ingestion.pipeline.chunker import chunk_text
from app.features.ingestion.service import ingest_document


def add_txt_document(db, user, upload_dir, content, filename="stored.txt"):
    """Write a real file into the temp upload dir and register it in the DB."""
    (upload_dir / filename).write_text(content, encoding="utf-8")
    return create_document(
        db, original_name="policy.txt", filename=filename, file_type="txt", uploaded_by=user.id
    )


def chunks_of(db, document_id):
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )


def test_ingest_success_stores_chunks_and_marks_processed(db, user, upload_dir, fake_embedder):
    text = "Employees get 14 days of annual leave. " * 40  # long enough for several chunks
    doc = add_txt_document(db, user, upload_dir, text)

    result = ingest_document(db, doc.id)

    expected = chunk_text(text)
    rows = chunks_of(db, doc.id)
    assert result.status == "processed"
    assert len(expected) > 1
    assert [r.content for r in rows] == expected
    assert [r.chunk_index for r in rows] == list(range(len(expected)))
    assert all(json.loads(r.embedding) == [1.0, 0.0] for r in rows)


def test_ingest_unknown_document_raises(db, upload_dir, fake_embedder):
    with pytest.raises(DocumentNotFoundError):
        ingest_document(db, 999)


def test_ingest_empty_file_marks_failed(db, user, upload_dir, fake_embedder):
    doc = add_txt_document(db, user, upload_dir, "   \n  ")

    with pytest.raises(EmptyDocumentError):
        ingest_document(db, doc.id)

    db.refresh(doc)
    assert doc.status == "failed"
    assert chunks_of(db, doc.id) == []


def test_ingest_missing_file_marks_failed(db, user, upload_dir, fake_embedder):
    doc = create_document(
        db, original_name="ghost.txt", filename="ghost.txt", file_type="txt", uploaded_by=user.id
    )

    with pytest.raises(FileNotFoundError):
        ingest_document(db, doc.id)

    db.refresh(doc)
    assert doc.status == "failed"


def test_ingest_embedder_error_marks_failed_and_reraises(db, user, upload_dir, monkeypatch):
    def broken_embedder(texts):
        raise RuntimeError("model crashed")

    monkeypatch.setattr("app.features.ingestion.service.embed_texts", broken_embedder)
    doc = add_txt_document(db, user, upload_dir, "some real content")

    with pytest.raises(RuntimeError, match="model crashed"):
        ingest_document(db, doc.id)

    db.refresh(doc)
    assert doc.status == "failed"
    assert chunks_of(db, doc.id) == []


def test_reingest_replaces_old_chunks(db, user, upload_dir, fake_embedder):
    text = "Expense claims need a receipt. " * 40
    doc = add_txt_document(db, user, upload_dir, text)

    ingest_document(db, doc.id)
    first_count = len(chunks_of(db, doc.id))
    ingest_document(db, doc.id)

    assert len(chunks_of(db, doc.id)) == first_count  # not doubled


def test_reingest_after_failure_recovers(db, user, upload_dir, fake_embedder):
    doc = create_document(
        db, original_name="late.txt", filename="late.txt", file_type="txt", uploaded_by=user.id
    )
    with pytest.raises(FileNotFoundError):
        ingest_document(db, doc.id)

    (upload_dir / "late.txt").write_text("now the file exists", encoding="utf-8")
    result = ingest_document(db, doc.id)

    assert result.status == "processed"
    assert len(chunks_of(db, doc.id)) == 1


def test_ingest_pdf_records_page_numbers(db, user, upload_dir, fake_embedder, make_pdf):
    make_pdf(upload_dir / "doc.pdf", ["Leave policy on page one", "Expense policy on page two"])
    doc = create_document(
        db, original_name="doc.pdf", filename="doc.pdf", file_type="pdf", uploaded_by=user.id
    )

    ingest_document(db, doc.id)

    rows = chunks_of(db, doc.id)
    assert [r.page_number for r in rows] == [1, 2]
    assert "Leave" in rows[0].content
    assert "Expense" in rows[1].content


def test_ingest_txt_has_no_page_numbers(db, user, upload_dir, fake_embedder):
    doc = add_txt_document(db, user, upload_dir, "plain text without pages")

    ingest_document(db, doc.id)

    assert [r.page_number for r in chunks_of(db, doc.id)] == [None]


def test_ingest_pdf_with_blank_page_keeps_real_page_numbers(db, user, upload_dir, fake_embedder, make_pdf):
    make_pdf(upload_dir / "gap.pdf", ["first page text", "   ", "third page text"])
    doc = create_document(
        db, original_name="gap.pdf", filename="gap.pdf", file_type="pdf", uploaded_by=user.id
    )

    ingest_document(db, doc.id)

    assert [r.page_number for r in chunks_of(db, doc.id)] == [1, 3]


def test_ingest_embeds_text_only_not_page_tuples(db, user, upload_dir, fake_embedder):
    doc = add_txt_document(db, user, upload_dir, "hello world")

    ingest_document(db, doc.id)

    assert fake_embedder == [["hello world"]]  # a list of strings, no (page, text) tuples
