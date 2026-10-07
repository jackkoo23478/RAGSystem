from sqlalchemy import func, or_

from app.features.auth.models import User
from app.features.rag.models import Query


def _filtered(db, status, search):
    """Every query with its author's email, narrowed by the optional filters."""
    rows = db.query(Query, User.email).join(User, User.id == Query.user_id)

    if status is not None:
        rows = rows.filter(Query.status == status)

    if search:
        needle = search.lower()
        rows = rows.filter(
            or_(
                # autoescape: a "%" or "_" typed by the admin is searched for literally, not used as a wildcard
                func.lower(Query.question).contains(needle, autoescape=True),
                func.lower(User.email).contains(needle, autoescape=True),
            )
        )
    return rows


def list_logs(db, status=None, search=None, limit=20, offset=0):
    """One page of queries from all users, newest first, plus how many match in total."""
    rows = _filtered(db, status, search)
    total = rows.count()
    page = (
        rows.order_by(Query.created_at.desc(), Query.id.desc())  # newest first; id breaks ties
        .limit(limit)
        .offset(offset)
        .all()
    )
    return page, total


def get_log(db, query_id):
    """(Query, author email) for any user's query, or None."""
    return _filtered(db, None, None).filter(Query.id == query_id).first()
