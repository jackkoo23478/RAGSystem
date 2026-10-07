import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
# every model must be imported, otherwise create_all() does not know the table exists
from app.features.auth.models import User
from app.features.documents.models import Document, DocumentChunk
from app.features.rag.models import Query, QueryCitation
from app.features.rag.models import Query, QueryCitation


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",  # in-memory: a fresh empty DB per test, gone afterwards
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # every connection shares the same in-memory DB
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    """An admin user (the `uploaded_by` owner of documents in tests)."""
    u = User(email="admin@example.com", password_hash="not-a-real-hash", role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Point both services at a temp folder. Patch the name where it is USED, not where it is defined."""
    monkeypatch.setattr("app.features.documents.service.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.features.ingestion.service.UPLOAD_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def fake_embedder(monkeypatch):
    """Replace the real model (slow, ~25s first load) with a fake 2-dim embedder."""
    calls = []

    def fake_embed_texts(texts):
        calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr("app.features.ingestion.service.embed_texts", fake_embed_texts)
    return calls


@pytest.fixture
def make_pdf():
    """Return a function that writes a tiny real PDF (one page per string) to a path."""

    def _make_pdf(path, page_texts):
        n = len(page_texts)
        page_ids = [4 + 2 * i for i in range(n)]
        objects = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {n} >>".encode(),
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        }
        for page_id, text in zip(page_ids, page_texts):
            content_id = page_id + 1
            objects[page_id] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R >> >> >>"
            ).encode()
            stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
            objects[content_id] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"

        out = bytearray(b"%PDF-1.4\n")
        offsets = {}
        for num in sorted(objects):
            offsets[num] = len(out)
            out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"
        xref_pos = len(out)
        size = max(objects) + 1
        out += f"xref\n0 {size}\n".encode() + b"0000000000 65535 f \n"
        for num in range(1, size):
            out += f"{offsets[num]:010d} 00000 n \n".encode()
        out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
        path.write_bytes(bytes(out))

    return _make_pdf


@pytest.fixture
def add_query(db):
    """Save a query directly, so a test can choose the time and the latency (create_query cannot)."""

    def _add_query(user, question="a question", status="answered", latency_ms=None, created_at=None, answer=None):
        values = dict(user_id=user.id, question=question, status=status, latency_ms=latency_ms, answer=answer)
        if created_at is not None:
            values["created_at"] = created_at
        query = Query(**values)
        db.add(query)
        db.commit()
        db.refresh(query)
        return query

    return _add_query
