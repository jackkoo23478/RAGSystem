from app.features.logs import repository
from app.features.logs.schemas import QueryLogDetail, QueryLogItem, QueryLogPage
from app.features.rag.repository import get_citations_for_query
from app.features.rag.schemas import CitationResponse
from app.features.rag.service import visible_answer


def to_log_item(query, email) -> QueryLogItem:
    return QueryLogItem(
        id=query.id,
        user_id=query.user_id,
        user_email=email,
        question=query.question,
        status=query.status,
        latency_ms=query.latency_ms,
        created_at=query.created_at,
    )


def get_page(db, status=None, search=None, limit=20, offset=0) -> QueryLogPage:
    rows, total = repository.list_logs(db, status, search, limit, offset)
    return QueryLogPage(
        items=[to_log_item(query, email) for query, email in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_detail(db, query_id) -> QueryLogDetail | None:
    found = repository.get_log(db, query_id)
    if found is None:
        return None

    query, email = found
    citations = get_citations_for_query(db, query.id)
    return QueryLogDetail(
        **to_log_item(query, email).model_dump(),
        answer=visible_answer(query),
        citations=[CitationResponse.model_validate(c) for c in citations],
    )


def recent_queries(db, limit=5) -> list[QueryLogItem]:
    return get_page(db, limit=limit).items
