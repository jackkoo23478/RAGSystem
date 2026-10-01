from fastapi import APIRouter, Depends, File , UploadFile, HTTPException, status
from app.features.auth.dependencies import require_admin
from app.features.auth.models import User
from app.features.documents import service
from app.features.documents.repository import get_document_by_id, list_documents
from app.features.documents.schemas import DocumentResponse
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
    return get_document_by_id(db, document_id)
