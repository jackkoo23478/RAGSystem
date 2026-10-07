from app.features.rag.models import Query, QueryCitation


def create_query(db, user_id, question, status, answer=None, citations=(), latency_ms=None) -> Query:
    query = Query(user_id=user_id, question=question, status=status, answer=answer, latency_ms=latency_ms)
    try:
        db.add(query)
        db.flush()  # writes the row (not committed yet) so query.id has a value
        db.add_all([QueryCitation(query_id=query.id, **citation) for citation in citations])
        db.commit()  # one transaction: the query and its citations are saved together or not at all
    except Exception:
        db.rollback()
        raise
    db.refresh(query)
    return query

def list_queries_by_user(db, user_id, limit=20) -> list[Query]:
    return (
        db.query(Query)
        .filter(Query.user_id == user_id)  # only this user's own queries
        .order_by(Query.created_at.desc(), Query.id.desc())  # newest first; id breaks ties
        .limit(limit)
        .all()
    )


def get_query_for_user(db, query_id, user_id) -> Query | None:
    return (
        db.query(Query)
        .filter(Query.id == query_id, Query.user_id == user_id)  # both must match
        .first()
    )


def get_citations_for_query(db, query_id) -> list[QueryCitation]:
    return (
        db.query(QueryCitation)
        .filter(QueryCitation.query_id == query_id)
        .order_by(QueryCitation.id)
        .all()
    )