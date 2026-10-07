from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.features.auth.dependencies import require_admin
from app.features.logs import service
from app.features.logs.schemas import QueryLogDetail, QueryLogPage

# every route in this file is for admins only
router = APIRouter(dependencies=[Depends(require_admin)])

QueryStatus = Literal["answered", "no_evidence", "invalid_answer", "failed"]


@router.get("", response_model=QueryLogPage)
def list_logs(
    status: QueryStatus | None = None,
    search: str | None = QueryParam(None, max_length=100, description="Part of the question or of the asker's email"),
    limit: int = QueryParam(20, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.get_page(db, status, search, limit, offset)


@router.get("/{query_id}", response_model=QueryLogDetail)
def get_log(query_id: int, db: Session = Depends(get_db)):
    detail = service.get_detail(db, query_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Query not found.")
    return detail
