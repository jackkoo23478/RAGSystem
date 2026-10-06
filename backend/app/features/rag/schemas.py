from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int | None = None
    document_id: int | None
    document_name: str
    page_number: int | None
    snippet: str
    score: float


class QueryResponse(BaseModel):
    query_id: int
    status: str
    answer: str | None
    citations: list[CitationResponse]


class QueryHistoryItem(BaseModel):
    id: int
    question: str
    status: str
    answer: str | None
    created_at: datetime


class QueryDetailResponse(QueryHistoryItem):
    citations: list[CitationResponse]