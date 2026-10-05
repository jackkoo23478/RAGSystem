import io

import pytest
from fastapi import UploadFile

from app.features.documents.exceptions import InvalidFileTypeError
from app.features.documents.models import Document, DocumentChunk
from app.features.documents.repository import create_chunks
from app.features.documents.service import delete_document, upload_document
from app.features.ingestion.exceptions import DocumentNotFoundError


def make_upload(filename, content=b"hello"):
    return UploadFile(file=io.BytesIO(content), filename=filename)


def test_upload_saves_file_and_creates_record(db, user, upload_dir):
    doc = upload_document(db, make_upload("Policy.TXT", b"leave policy"), user.id)

    assert doc.original_name == "Policy.TXT"
    assert doc.file_type == "txt"  # extension is lower-cased
    assert doc.status == "pending"
    assert doc.uploaded_by == user.id
    stored = upload_dir / doc.filename
    assert stored.read_bytes() == b"leave policy"
    assert doc.filename != "Policy.TXT"  # stored under a random name, not the user's


def test_upload_same_name_twice_does_not_overwrite(db, user, upload_dir):
    a = upload_document(db, make_upload("a.txt", b"one"), user.id)
    b = upload_document(db, make_upload("a.txt", b"two"), user.id)

    assert a.filename != b.filename
    assert (upload_dir / a.filename).read_bytes() == b"one"
    assert (upload_dir / b.filename).read_bytes() == b"two"


def test_upload_rejects_unsupported_type_and_writes_nothing(db, user, upload_dir):
    with pytest.raises(InvalidFileTypeError):
        upload_document(db, make_upload("malware.exe"), user.id)

    assert list(upload_dir.iterdir()) == []


# ---------- delete ----------

def test_delete_removes_record_chunks_and_file(db, user, upload_dir):
    doc = upload_document(db, make_upload("a.txt"), user.id)
    create_chunks(db, doc.id, ["c1", "c2"], [[1.0], [2.0]])

    delete_document(db, doc.id)

    assert db.query(Document).count() == 0
    assert db.query(DocumentChunk).count() == 0
    assert list(upload_dir.iterdir()) == []


def test_delete_leaves_other_documents_alone(db, user, upload_dir):
    keep = upload_document(db, make_upload("keep.txt", b"keep"), user.id)
    drop = upload_document(db, make_upload("drop.txt", b"drop"), user.id)
    create_chunks(db, keep.id, ["k"], [[1.0]])
    create_chunks(db, drop.id, ["d"], [[2.0]])

    delete_document(db, drop.id)

    assert [d.id for d in db.query(Document).all()] == [keep.id]
    assert [c.content for c in db.query(DocumentChunk).all()] == ["k"]
    assert [f.name for f in upload_dir.iterdir()] == [keep.filename]


def test_delete_succeeds_when_file_is_already_gone(db, user, upload_dir):
    doc = upload_document(db, make_upload("a.txt"), user.id)
    (upload_dir / doc.filename).unlink()

    delete_document(db, doc.id)  # must not raise

    assert db.query(Document).count() == 0


def test_delete_unknown_document_raises(db, upload_dir):
    with pytest.raises(DocumentNotFoundError):
        delete_document(db, 999)
