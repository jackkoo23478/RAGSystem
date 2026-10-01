import os 
import uuid 

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.features.documents.exceptions import InvalidFileTypeError
from app.features.documents.models import Document   
from app.features.documents.repository import create_document, get_document_by_id, list_documents  

UPLOAD_DIR = "data/uploads"
ALLOWED_FILE_TYPES = ["pdf", "txt"]


def upload_document(db : Session, file : UploadFile , uploaded_by : int) -> Document:
    # Validate file type
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        raise InvalidFileTypeError(f"File type '{file_extension}' is not supported. Allowed types: {ALLOWED_FILE_TYPES}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return create_document(db, original_name=file.filename, filename=stored_filename, file_type=file_extension, uploaded_by=uploaded_by)
    


