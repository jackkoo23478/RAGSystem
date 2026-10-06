import pytest

from app.features.documents.models import DocumentChunk

PREFIX = "/api/v1/documents"


def upload(client, headers, name="policy.txt", content=b"Annual leave is 14 days."):
    return client.post(
        f"{PREFIX}/upload",
        headers=headers,
        files={"file": (name, content, "text/plain")},
    )


# ---------- upload ----------

def test_admin_can_upload(client, admin_headers, upload_dir):
    res = upload(client, admin_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["original_name"] == "policy.txt"
    assert body["file_type"] == "txt"
    assert body["status"] == "pending"
    assert "filename" not in body  # response_model hides the stored name


def test_normal_user_cannot_upload(client, user_headers, upload_dir):
    assert upload(client, user_headers).status_code == 403


def test_upload_without_token_is_rejected(client, upload_dir):
    # 403 on FastAPI 0.115 (pinned), 401 on newer versions
    assert upload(client, headers={}).status_code in (401, 403)


def test_upload_unsupported_type_is_400(client, admin_headers, upload_dir):
    res = upload(client, admin_headers, name="malware.exe")

    assert res.status_code == 400
    assert list(upload_dir.iterdir()) == []  # nothing was written to disk


# ---------- read ----------

def test_list_and_get_documents(client, admin_headers, upload_dir):
    doc_id = upload(client, admin_headers).json()["id"]

    listing = client.get(PREFIX, headers=admin_headers)
    single = client.get(f"{PREFIX}/{doc_id}", headers=admin_headers)

    assert [d["id"] for d in listing.json()] == [doc_id]
    assert single.status_code == 200
    assert single.json()["id"] == doc_id


def test_get_unknown_document_is_404(client, admin_headers):
    assert client.get(f"{PREFIX}/999", headers=admin_headers).status_code == 404


def test_status_endpoint(client, admin_headers, upload_dir):
    doc_id = upload(client, admin_headers).json()["id"]

    res = client.get(f"{PREFIX}/{doc_id}/status", headers=admin_headers)

    assert res.status_code == 200
    assert res.json() == {"id": doc_id, "status": "pending"}


def test_status_unknown_document_is_404(client, admin_headers):
    assert client.get(f"{PREFIX}/999/status", headers=admin_headers).status_code == 404


# ---------- ingest ----------

def test_admin_ingest_marks_processed(client, admin_headers, upload_dir, fake_embedder):
    doc_id = upload(client, admin_headers).json()["id"]

    res = client.post(f"{PREFIX}/{doc_id}/ingest", headers=admin_headers)

    assert res.status_code == 200
    assert res.json()["status"] == "processed"
    assert client.get(f"{PREFIX}/{doc_id}/status", headers=admin_headers).json()["status"] == "processed"


def test_normal_user_cannot_ingest(client, admin_headers, user_headers, upload_dir, fake_embedder):
    doc_id = upload(client, admin_headers).json()["id"]

    assert client.post(f"{PREFIX}/{doc_id}/ingest", headers=user_headers).status_code == 403


def test_ingest_unknown_document_is_404(client, admin_headers, upload_dir, fake_embedder):
    assert client.post(f"{PREFIX}/999/ingest", headers=admin_headers).status_code == 404


def test_ingest_empty_document_is_422(client, admin_headers, upload_dir, fake_embedder):
    doc_id = upload(client, admin_headers, content=b"   ").json()["id"]

    res = client.post(f"{PREFIX}/{doc_id}/ingest", headers=admin_headers)

    assert res.status_code == 422
    assert client.get(f"{PREFIX}/{doc_id}/status", headers=admin_headers).json()["status"] == "failed"


def test_ingest_when_file_missing_on_disk_is_404(client, admin_headers, upload_dir, fake_embedder):
    doc_id = upload(client, admin_headers).json()["id"]
    for f in upload_dir.iterdir():
        f.unlink()

    res = client.post(f"{PREFIX}/{doc_id}/ingest", headers=admin_headers)

    assert res.status_code == 404


# ---------- delete ----------

def test_admin_delete_removes_record_chunks_and_file(client, db, admin_headers, upload_dir, fake_embedder):
    doc_id = upload(client, admin_headers).json()["id"]
    client.post(f"{PREFIX}/{doc_id}/ingest", headers=admin_headers)
    assert db.query(DocumentChunk).filter_by(document_id=doc_id).count() > 0
    assert len(list(upload_dir.iterdir())) == 1

    res = client.delete(f"{PREFIX}/{doc_id}", headers=admin_headers)

    assert res.status_code == 204
    assert client.get(f"{PREFIX}/{doc_id}", headers=admin_headers).status_code == 404
    assert db.query(DocumentChunk).filter_by(document_id=doc_id).count() == 0  # no orphan chunks
    assert list(upload_dir.iterdir()) == []  # no orphan file


def test_normal_user_cannot_delete(client, admin_headers, user_headers, upload_dir):
    doc_id = upload(client, admin_headers).json()["id"]

    assert client.delete(f"{PREFIX}/{doc_id}", headers=user_headers).status_code == 403
    assert client.get(f"{PREFIX}/{doc_id}", headers=admin_headers).status_code == 200


def test_delete_without_token_is_rejected(client, admin_headers, upload_dir):
    doc_id = upload(client, admin_headers).json()["id"]

    assert client.delete(f"{PREFIX}/{doc_id}").status_code in (401, 403)


def test_delete_unknown_document_is_404(client, admin_headers):
    assert client.delete(f"{PREFIX}/999", headers=admin_headers).status_code == 404


# ---------- reading documents requires a login ----------

@pytest.mark.parametrize("path", ["", "/1", "/1/status"])
def test_reading_documents_requires_a_token(client, path):
    res = client.get(f"{PREFIX}{path}")

    assert res.status_code in (401, 403)


def test_unknown_document_without_a_token_is_not_a_404(client):
    # authentication must come before the lookup, otherwise anyone could probe which ids exist
    assert client.get(f"{PREFIX}/99999").status_code in (401, 403)


def test_normal_user_can_read_documents(client, admin_headers, user_headers, upload_dir):
    doc_id = upload(client, admin_headers).json()["id"]

    assert client.get(PREFIX, headers=user_headers).status_code == 200
    assert client.get(f"{PREFIX}/{doc_id}", headers=user_headers).status_code == 200
    assert client.get(f"{PREFIX}/{doc_id}/status", headers=user_headers).status_code == 200
