from app.features.ingestion.pipeline.embedder import embed_texts
from app.features.rag.llm import LLM , OllamaClient

def get_llm() -> LLM :
    return OllamaClient()

def get_embedder() :
    return embed_texts