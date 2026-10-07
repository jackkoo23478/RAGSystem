from datetime import datetime

from pydantic import BaseModel

from app.features.rag.schemas import CitationResponse


class QueryLogItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    question: str
    status: str
    latency_ms: int | None  # empty for queries from before latency was recorded
    created_at: datetime


class QueryLogPage(BaseModel):
    items: list[QueryLogItem]
    total: int  # all matches, not only this page
    limit: int
    offset: int


class QueryLogDetail(QueryLogItem):
    answer: str | None  # only a verified answer is ever shown, as for the user who asked
    citations: list[CitationResponse]
