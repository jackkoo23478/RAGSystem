from sqlalchemy.orm import Session
from app.features.documents.models import Document


def get_document_by_id(db: Session, document_id: int) -> Document:
    return db.query(Document).filter(Document.id == document_id).first()


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
