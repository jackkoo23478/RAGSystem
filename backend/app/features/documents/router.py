from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from app.features.auth.dependencies import get_current_user, require_admin
from app.features.auth.models import User
from app.features.documents import service
from app.features.documents.exceptions import InvalidFileTypeError
from app.features.ingestion.service import ingest_document
from app.features.documents.repository import get_document_by_id, list_documents
from app.features.ingestion.exceptions import (
    DocumentNotFoundError,
    EmptyDocumentError,
    SuspiciousDocumentError,
)
from app.features.documents.schemas import DocumentResponse , DocumentStatusResponse
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file : UploadFile = File(...),
    db : Session = Depends(get_db),
    admin : User = Depends(require_admin) ,
):
    try:
        return service.upload_document(db, file, admin.id)
    except InvalidFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=list[DocumentResponse], dependencies=[Depends(get_current_user)])
def get_all_documents(db : Session = Depends(get_db)):
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentResponse, dependencies=[Depends(get_current_user)])
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = get_document_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document

@router.post("/{document_id}/ingest", response_model=DocumentResponse)
def ingest(
    document_id: int,
    allow_suspicious: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        return ingest_document(db, document_id, allow_suspicious=allow_suspicious)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.")
    except EmptyDocumentError:
        raise HTTPException(status_code=422, detail="Document is empty and cannot be ingested.")
    except SuspiciousDocumentError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "The document looks like it contains instructions aimed at an AI model. "
                "Review it, then ingest again with allow_suspicious=true if it is safe.",
                "signals": e.signals,
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stored file is missing on disk.")
    
@router.get("/{document_id}/status", response_model=DocumentStatusResponse, dependencies=[Depends(get_current_user)])
def get_document_status(document_id : int , db : Session = Depends(get_db)):
    document = get_document_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        service.delete_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.")
