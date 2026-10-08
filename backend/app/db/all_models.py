"""Imports every model, so that Base.metadata knows every table.

SQLAlchemy only learns about a table when its model is imported. Anything that works with the whole
schema (the migrations, create_all in the tests) imports this module instead of listing the models
itself, so a new model has to be added in one place only.
"""
from app.db.base import Base
from app.features.auth.models import User
from app.features.documents.models import Document, DocumentChunk
from app.features.rag.models import Query, QueryCitation

__all__ = ["Base", "User", "Document", "DocumentChunk", "Query", "QueryCitation"]
