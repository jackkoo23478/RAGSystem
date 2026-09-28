from fastapi import APIRouter, Depends, HTTPException, status
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.features.auth import service
from app.features.auth.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.features.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return service.register_user(db, payload.email, payload.password)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        token = service.login_user(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user : User = Depends(get_current_user)) :
    return current_user 