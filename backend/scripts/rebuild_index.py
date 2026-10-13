"""Embed every stored chunk again with the current embedding model.

Run it after changing EMBEDDING_MODEL (the old vectors cannot be compared with the new ones):

    python -m scripts.rebuild_index          # in Docker: docker compose exec backend python -m scripts.rebuild_index

The text of the chunks is kept; only the vectors are replaced. Uploaded files are not read again.

After the way of cutting changed (or the chunk size), the chunks already stored are still cut the old way. Then:

    python -m scripts.rebuild_index --rechunk

reads every processed document from its uploaded file, cuts it again and embeds the new chunks (which also gives new vectors).
"""
import json
import sys

import app.db.all_models  # noqa: F401  registers every table, which a document needs to find its owner
from app.db.session import SessionLocal
from app.features.documents.models import Document, DocumentChunk
from app.features.documents.repository import update_document_status
from app.features.ingestion.pipeline.embedder import MODEL_NAME, embed_texts
from app.features.ingestion.service import ingest_document

BATCH_SIZE = 32


def rebuild_index(db, embed=embed_texts, batch_size: int = BATCH_SIZE) -> int:
    """Replace the vector of every chunk. Returns how many chunks were embedded."""
    chunks = db.query(DocumentChunk).order_by(DocumentChunk.id).all()
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embed([chunk.content for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            chunk.embedding = json.dumps(vector)
        db.commit()  # one batch at a time: an interrupted run keeps what it already did, and can simply be run again
    return len(chunks)


def rechunk_documents(db, ingest=ingest_document) -> tuple[int, list[tuple[str, str]]]:
    """Read every processed document from its stored file again, cut it into chunks with the current chunker and embed
    them. Needed after the way of cutting changed (the chunks already stored were cut the old way).

    Returns (documents done, [(document name, why it failed), ...]). A document that cannot be read again (its file is
    missing, for example) keeps its old chunks and stays searchable."""
    done, failed = 0, []
    for document in db.query(Document).filter(Document.status == "processed").order_by(Document.id).all():
        try:
            ingest(db, document.id)
            done += 1
        except Exception as error:  # report it and go on with the next document
            db.rollback()  # a failed flush leaves the session unusable until this
            failed.append((document.original_name, f"{type(error).__name__}: {error}"))
            db.refresh(document)
            if document.status == "failed" and db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count():
                update_document_status(db, document, "processed")  # ingestion marks it failed; its old chunks are still there
    return done, failed


if __name__ == "__main__":
    session = SessionLocal()
    try:
        if "--rechunk" in sys.argv:
            print(f"Cutting every document again and embedding it with {MODEL_NAME} ...")
            count, problems = rechunk_documents(session)
            print(f"Done: {count} document(s).")
            for name, reason in problems:
                print(f"NOT done: {name}: {reason}")
        else:
            print(f"Embedding every chunk with {MODEL_NAME} ...")
            print(f"Done: {rebuild_index(session)} chunk(s).")
    finally:
        session.close()
