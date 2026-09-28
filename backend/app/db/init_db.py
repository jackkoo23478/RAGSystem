from app.db.base import Base
from app.db.session import engine 
from app.features.auth.models import User

def init_db():
    Base.metadata.create_all(bind=engine)
    
if __name__ == "__main__":
    init_db()