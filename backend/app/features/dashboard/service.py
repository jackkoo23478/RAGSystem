from datetime import date, datetime, time, timedelta

from app.features.dashboard import repository
from app.features.dashboard.schemas import DailyActivity, DashboardSummary, DocumentCounts, QueryCounts


def _round(value) -> int | None:
    return None if value is None else round(value)


def build_summary(db) -> DashboardSummary:
    docs = repository.count_documents_by_status(db)
    queries = repository.count_queries_by_status(db)

    # "total" counts every row, so a status the code does not know yet still shows up in it
    queries_total = sum(queries.values())
    answered = queries.get("answered", 0)

    return DashboardSummary(
        documents=DocumentCounts(
            total=sum(docs.values()),
            pending=docs.get("pending", 0),
            processing=docs.get("processing", 0),
            processed=docs.get("processed", 0),
            failed=docs.get("failed", 0),
            flagged=docs.get("flagged", 0),
        ),
        queries=QueryCounts(
            total=queries_total,
            answered=answered,
            no_evidence=queries.get("no_evidence", 0),
            invalid_answer=queries.get("invalid_answer", 0),
            failed=queries.get("failed", 0),
        ),
        answer_rate=answered / queries_total if queries_total else None,
        avg_latency_ms=_round(repository.average_latency_ms(db)),
    )


def build_activity(db, days: int, today: date | None = None) -> list[DailyActivity]:
    """One entry for each of the last `days` UTC days, oldest first. A day without queries is zero, not missing,
    so a chart draws an honest line instead of skipping days."""
    today = today or datetime.utcnow().date()
    first_day = today - timedelta(days=days - 1)

    found = {
        day: (total, answered, avg)
        for day, total, answered, avg in repository.queries_per_day(db, datetime.combine(first_day, time.min))
    }

    result = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        total, answered, avg = found.get(day.isoformat(), (0, 0, None))
        result.append(DailyActivity(date=day, queries=total, answered=answered, avg_latency_ms=_round(avg)))
    return result
