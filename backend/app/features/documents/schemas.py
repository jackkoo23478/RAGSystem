from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id : int
    original_name: str
    file_type: str
    status: str = "pending"
    created_at: datetime
    uploaded_by: int  # User ID of the uploader