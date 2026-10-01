from app.db.base import Base
from app.db.session import engine 
from app.features.auth.models import User
from app.features.documents.models import Document

def init_db():
    Base.metadata.create_all(bind=engine)
    
if __name__ == "__main__":
    init_db()