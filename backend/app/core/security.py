import bcrypt
import jwt 
from datetime import datetime, timedelta , timezone
from app.core.config import settings


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(subject:str) -> str :
    expire = datetime.now(timezone.utc) + timedelta(minutes = settings.access_token_expire_minutes)
    payload = {
        "sub" : subject,
        "exp" : expire
    }
    return jwt.encode(payload, settings.secret_key, algorithm = settings.algorithm)
    
