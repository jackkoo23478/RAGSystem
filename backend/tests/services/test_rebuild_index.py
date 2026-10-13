import json

from app.features.documents.models import DocumentChunk
from app.features.documents.repository import create_chunks, create_document, update_document_status
from scripts.rebuild_index import rebuild_index


def add_doc(db, user, name, texts, vector):
    doc = create_document(db, original_name=name, filename=f"stored-{name}", file_type="txt", uploaded_by=user.id)
    create_chunks(db, doc.id, texts, [vector for _ in texts])
    update_document_status(db, doc, "processed")
    return doc


def new_model(texts):
    return [[float(len(text)), 1.0, 2.0] for text in texts]  # 3 numbers: not what was stored


def test_every_chunk_gets_a_vector_from_the_new_model(db, user):
    add_doc(db, user, "a.txt", ["one", "three"], [9.0, 9.0])
    add_doc(db, user, "b.txt", ["seven77"], [9.0, 9.0])

    count = rebuild_index(db, embed=new_model)

    assert count == 3
    vectors = {c.content: json.loads(c.embedding) for c in db.query(DocumentChunk).all()}
    assert vectors == {"one": [3.0, 1.0, 2.0], "three": [5.0, 1.0, 2.0], "seven77": [7.0, 1.0, 2.0]}


def test_the_text_and_the_document_are_left_alone(db, user):
    doc = add_doc(db, user, "a.txt", ["keep this text"], [9.0, 9.0])

    rebuild_index(db, embed=new_model)

    chunk = db.query(DocumentChunk).one()
    assert chunk.content == "keep this text"
    assert chunk.document_id == doc.id
    assert doc.status == "processed"


def test_chunks_are_embedded_in_batches(db, user):
    add_doc(db, user, "a.txt", [f"text {i}" for i in range(5)], [9.0, 9.0])
    batches = []

    def spy(texts):
        batches.append(len(texts))
        return new_model(texts)

    rebuild_index(db, embed=spy, batch_size=2)

    assert batches == [2, 2, 1]


def test_an_empty_database_is_fine(db):
    assert rebuild_index(db, embed=new_model) == 0


# ---------- cutting the documents again ----------

import pytest

from app.features.documents.repository import create_document as _create_document
from app.features.ingestion.pipeline.chunker import chunk_pages, chunk_text
from app.features.ingestion.service import ingest_document
from scripts.rebuild_index import rechunk_documents

SENTENCE = "The refund period is thirty days from delivery. "


def uploaded_document(db, user, upload_dir, name="policy.txt", text=SENTENCE * 30):
    (upload_dir / name).write_text(text, encoding="utf-8")
    doc = _create_document(db, original_name=name, filename=name, file_type="txt", uploaded_by=user.id)
    return doc, text


def contents(db, doc):
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).all()
    return [c.content for c in chunks]


def test_a_document_cut_the_old_way_is_cut_again_with_the_current_chunker(db, user, upload_dir, fake_embedder):
    doc, text = uploaded_document(db, user, upload_dir)
    # stored the old way: fixed-size windows, some of which stop in the middle of a sentence
    create_chunks(db, doc.id, chunk_text(text), [[9.0, 9.0]] * len(chunk_text(text)))
    update_document_status(db, doc, "processed")
    assert any(not c.endswith("delivery.") for c in contents(db, doc))

    done, failed = rechunk_documents(db)

    assert (done, failed) == (1, [])
    assert contents(db, doc) == [piece for _, piece in chunk_pages([(None, text)])]
    assert all(c.endswith("delivery.") for c in contents(db, doc))


def test_every_processed_document_is_done_and_others_are_left_alone(db, user, upload_dir, fake_embedder):
    ingested, _ = uploaded_document(db, user, upload_dir, "a.txt")
    ingest_document(db, ingested.id)
    pending, _ = uploaded_document(db, user, upload_dir, "b.txt")  # uploaded, never processed

    done, failed = rechunk_documents(db)

    assert done == 1 and failed == []
    db.refresh(pending)
    assert pending.status == "pending" and contents(db, pending) == []


def test_a_document_whose_file_is_gone_keeps_its_old_chunks_and_stays_searchable(db, user, upload_dir, fake_embedder):
    doc, _ = uploaded_document(db, user, upload_dir)
    ingest_document(db, doc.id)
    before = contents(db, doc)
    (upload_dir / "policy.txt").unlink()

    done, failed = rechunk_documents(db)

    assert done == 0
    assert failed and failed[0][0] == "policy.txt" and "FileNotFoundError" in failed[0][1]
    db.refresh(doc)
    assert doc.status == "processed"
    assert contents(db, doc) == before


def test_one_bad_document_does_not_stop_the_others(db, user, upload_dir, fake_embedder):
    broken, _ = uploaded_document(db, user, upload_dir, "broken.txt")
    ingest_document(db, broken.id)
    fine, _ = uploaded_document(db, user, upload_dir, "fine.txt")
    ingest_document(db, fine.id)
    (upload_dir / "broken.txt").unlink()

    done, failed = rechunk_documents(db)

    assert done == 1
    assert [name for name, _ in failed] == ["broken.txt"]
