from sqlalchemy.orm import Session
from app.features.documents.models import Document , DocumentChunk
import json


def get_document_by_id(db: Session, document_id: int) -> Document:
    return db.query(Document).filter(Document.id == document_id).first()

def delete_document(db: Session, document_id: int) -> None:
    db.query(Document).filter(Document.id == document_id).delete()
    db.commit()
    
def delete_chunks_by_document(db : Session, document_id: int) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.commit()
    
def create_chunks(
    db: Session,
    document_id: int,
    contents: list[str],
    embeddings: list[list[float]],
    page_numbers: list[int | None] | None = None,
) -> None:
    if page_numbers is None:
        page_numbers = [None] * len(contents)
    rows = [
        DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            content=content,
            embedding=json.dumps(embedding),
            page_number=page,
        )
        for i, (content, embedding, page) in enumerate(zip(contents, embeddings, page_numbers))
    ]
    db.add_all(rows)
    db.commit()

def update_document_status(db: Session , document : Document , status : str) -> Document :
    document.status = status 
    db.commit()
    db.refresh(document)
    return document
    

def list_documents(db: Session) -> list[Document]:
    return db.query(Document).all()

def create_document(db: Session, original_name: str, filename: str, file_type: str, uploaded_by: int) -> Document:
    new_document = Document(
        original_name=original_name,
        filename=filename,
        file_type=file_type,
        uploaded_by=uploaded_by
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document
