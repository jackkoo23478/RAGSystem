from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from app.db.base import Base


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=True)  # how long answering took; empty for queries from before it was recorded
    created_at = Column(DateTime, default=datetime.utcnow)


class QueryCitation(Base):
    __tablename__ = "query_citations"

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    document_id = Column(Integer, nullable=True)
    chunk_id = Column(Integer, nullable=True)
    document_name = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    snippet = Column(Text, nullable=False)
    score = Column(Float, nullable=False)