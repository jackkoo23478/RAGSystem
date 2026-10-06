import os

from sqlalchemy.orm import Session
from app.features.documents.models import Document
from app.features.documents.repository import (
    create_chunks,
    delete_chunks_by_document,
    get_document_by_id,
    update_document_status
)
from app.features.documents.service import UPLOAD_DIR
from app.features.ingestion.exceptions import (
    DocumentNotFoundError,
    EmptyDocumentError,
    SuspiciousDocumentError,
)
from app.features.ingestion.pipeline.chunker import chunk_pages
from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.ingestion.pipeline.extract import extract_pages
from app.features.ingestion.pipeline.safety import scan_for_injection


def ingest_document(db: Session , document_id : int, allow_suspicious: bool = False) -> Document :
    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document with ID {document_id} not found.")
    update_document_status(db, document, "processing")
    try :
        file_path = os.path.join(UPLOAD_DIR , document.filename)
        pages = extract_pages(file_path, document.file_type)
        if not any(text.strip() for _, text in pages):
            raise EmptyDocumentError(f"Document with ID {document_id} is empty.")
        signals = scan_for_injection("\n".join(text for _, text in pages))
        if signals and not allow_suspicious:
            raise SuspiciousDocumentError(signals)
        pieces = chunk_pages(pages)
        contents = [text for _, text in pieces]
        page_numbers = [page for page, _ in pieces]
        embeddings = embed_texts(contents)
        delete_chunks_by_document(db, document_id)
        create_chunks(db, document_id, contents, embeddings, page_numbers)
        update_document_status(db, document, "processed")
    except SuspiciousDocumentError:
        delete_chunks_by_document(db, document_id)  # an earlier ingest must not stay searchable
        update_document_status(db, document, "flagged")
        raise
    except Exception :
        update_document_status(db, document, "failed")
        raise 
    
    return document
        