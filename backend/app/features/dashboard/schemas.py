from datetime import date

from pydantic import BaseModel


class DocumentCounts(BaseModel):
    total: int
    pending: int
    processing: int
    processed: int
    failed: int
    flagged: int


class QueryCounts(BaseModel):
    total: int
    answered: int
    no_evidence: int
    invalid_answer: int
    failed: int


class DashboardSummary(BaseModel):
    documents: DocumentCounts
    queries: QueryCounts
    answer_rate: float | None  # answered / all queries; empty when nothing was asked yet
    avg_latency_ms: int | None  # over the queries that have a recorded latency


class DailyActivity(BaseModel):
    date: date  # a UTC day
    queries: int
    answered: int
    avg_latency_ms: int | None  # empty on a day without queries
