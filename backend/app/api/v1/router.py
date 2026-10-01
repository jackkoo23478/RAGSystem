from fastapi import APIRouter
from app.features.auth.router import router as auth_router
from app.features.documents.router import router as document_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
router = api_router

