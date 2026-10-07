from fastapi import APIRouter
from app.features.auth.router import router as auth_router
from app.features.dashboard.router import router as dashboard_router
from app.features.documents.router import router as document_router
from app.features.logs.router import router as logs_router
from app.features.rag.router import router as rag_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
router = api_router