from sqlalchemy import case, func

from app.features.documents.models import Document
from app.features.rag.models import Query


def count_documents_by_status(db) -> dict[str, int]:
    rows = db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    return {status: count for status, count in rows}


def count_queries_by_status(db) -> dict[str, int]:
    rows = db.query(Query.status, func.count(Query.id)).group_by(Query.status).all()
    return {status: count for status, count in rows}


def average_latency_ms(db) -> float | None:
    # avg() skips the rows without a latency, so old queries do not pull the number down
    return db.query(func.avg(Query.latency_ms)).scalar()


def queries_per_day(db, since):
    """(day as 'YYYY-MM-DD', queries, answered, average latency) for every day that has queries, from `since` on."""
    answered = func.sum(case((Query.status == "answered", 1), else_=0))
    day = func.date(Query.created_at)
    rows = (
        db.query(day, func.count(Query.id), answered, func.avg(Query.latency_ms))
        .filter(Query.created_at >= since)
        .group_by(day)
        .order_by(day)
        .all()
    )
    return [(str(d), total, int(ok or 0), avg) for d, total, ok, avg in rows]


def list_recent_documents(db, limit=5) -> list[Document]:
    return (
        db.query(Document)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .all()
    )
