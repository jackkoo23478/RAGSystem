from fastapi import APIRouter, Depends, File, HTTPException , UploadFile
from app.features.auth.dependencies import require_admin
from app.features.auth.models import User
from app.features.documents import service
from app.features.ingestion.service import ingest_document
from app.features.documents.repository import get_document_by_id, list_documents
from app.features.ingestion.exceptions import DocumentNotFoundError, EmptyDocumentError
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
    return service.upload_document(db, file, admin.id)

@router.get("",response_model=list[DocumentResponse])
def get_all_documents(db : Session = Depends(get_db)):
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = get_document_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document

@router.post("/{document_id}/ingest", response_model=DocumentResponse)
def ingest(
    document_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        return ingest_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.")
    except EmptyDocumentError:
        raise HTTPException(status_code=422, detail="Document is empty and cannot be ingested.")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stored file is missing on disk.")
    
@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id : int , db : Session = Depends(get_db)):
    document = get_document_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document