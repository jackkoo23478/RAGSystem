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
from app.features.ingestion.exceptions import DocumentNotFoundError, EmptyDocumentError
from app.features.ingestion.pipeline.chunker import chunk_text
from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.ingestion.pipeline.extract import extract_text 


def ingest_document(db: Session , document_id : int) -> Document :
    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document with ID {document_id} not found.")
    update_document_status(db, document, "processing")
    try :
        file_path = os.path.join(UPLOAD_DIR , document.filename)
        text = extract_text(file_path, document.file_type)
        if not text.strip():
            raise EmptyDocumentError(f"Document with ID {document_id} is empty.")
        chunks = chunk_text(text)
        embeddings = embed_texts(chunks)
        delete_chunks_by_document(db, document_id)
        create_chunks(db, document_id, chunks, embeddings)
        update_document_status(db, document, "processed")
    except Exception :
        update_document_status(db, document, "failed")
        raise 
    
    return document
        