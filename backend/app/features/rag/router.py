from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.rag import repository, service
from app.features.rag.dependencies import get_embedder, get_llm
from app.features.rag.llm import LLMError
from app.features.rag.schemas import (
    CitationResponse,
    QueryDetailResponse,
    QueryHistoryItem,
    QueryRequest,
    QueryResponse,
)

router = APIRouter()


def to_history_item(query) -> QueryHistoryItem:
    return QueryHistoryItem(
        id=query.id,
        question=query.question,
        status=query.status,
        answer=service.visible_answer(query),
        created_at=query.created_at,
    )


@router.post("/query", response_model=QueryResponse)
def ask(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm=Depends(get_llm),
    embed=Depends(get_embedder),
):
    try:
        result = service.answer_question(db, user.id, payload.question, llm, embed=embed)
    except ValueError:
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    except LLMError:
        raise HTTPException(status_code=502, detail="The language model is unavailable.")

    return QueryResponse(
        query_id=result.query_id,
        status=result.status,
        answer=result.answer,
        citations=[CitationResponse(**vars(c)) for c in result.citations],
    )


@router.get("/queries", response_model=list[QueryHistoryItem])
def history(
    limit: int = QueryParam(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [to_history_item(q) for q in repository.list_queries_by_user(db, user.id, limit)]


@router.get("/queries/{query_id}", response_model=QueryDetailResponse)
def detail(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = repository.get_query_for_user(db, query_id, user.id)
    if query is None:  # missing and "belongs to someone else" look exactly the same
        raise HTTPException(status_code=404, detail="Query not found.")

    citations = repository.get_citations_for_query(db, query.id)
    return QueryDetailResponse(
        **to_history_item(query).model_dump(),
        citations=[CitationResponse.model_validate(c) for c in citations],
    )