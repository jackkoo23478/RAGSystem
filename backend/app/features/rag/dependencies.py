from app.core.config import settings
from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.rag.llm import LLM , OllamaClient
from app.features.rag.rerank import rerank_scores

def get_llm() -> LLM :
    return OllamaClient()

def get_embedder() :
    return embed_texts

def get_reranker() :
    """The reranker, or None when RAG_RERANK is off (the search order is then used as it is)."""
    return rerank_scores if settings.rag_rerank else None
