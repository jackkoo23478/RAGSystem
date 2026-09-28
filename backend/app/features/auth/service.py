from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token , hash_password
from app.features.auth.exceptions import EmailAlreadyExistsError , InvalidCredentialsError
from app.features.auth.models import User   
from app.features.auth.repository import get_user_by_email, create_user  


def register_user(db : Session, email: str, password: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyExistsError(f"Email {email} already exists.")
    
    password_hash = hash_password(password)
    return create_user(db, email, password_hash)


def login_user(db: Session, username: str, password: str) -> dict:
    user = get_user_by_email(db, username)
   
    if user is None or not verify_password(password, user.password_hash):
       raise InvalidCredentialsError("Invalid username or password")
   
    return create_access_token(str(user.id))