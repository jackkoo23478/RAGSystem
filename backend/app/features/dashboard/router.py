from fastapi import APIRouter, Depends
from fastapi import Query as QueryParam
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.features.auth.dependencies import require_admin
from app.features.dashboard import repository, service
from app.features.dashboard.schemas import DailyActivity, DashboardSummary
from app.features.documents.schemas import DocumentResponse
from app.features.logs import service as logs_service
from app.features.logs.schemas import QueryLogItem

# every route in this file is for admins only
router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    return service.build_summary(db)


@router.get("/activity", response_model=list[DailyActivity])
def activity(days: int = QueryParam(14, ge=1, le=90), db: Session = Depends(get_db)):
    return service.build_activity(db, days)


@router.get("/recent-documents", response_model=list[DocumentResponse])
def recent_documents(limit: int = QueryParam(5, ge=1, le=20), db: Session = Depends(get_db)):
    return repository.list_recent_documents(db, limit)


@router.get("/recent-queries", response_model=list[QueryLogItem])
def recent_queries(limit: int = QueryParam(5, ge=1, le=20), db: Session = Depends(get_db)):
    return logs_service.recent_queries(db, limit)
