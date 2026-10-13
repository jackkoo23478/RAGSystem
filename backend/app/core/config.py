from pydantic import field_validator
from pydantic_settings import BaseSettings , SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_num_gpu: int | None = None
    llm_timeout_seconds: float = 120.0
    # the model that turns text into vectors (a Hugging Face name). After changing it, run: python -m scripts.rebuild_index
    embedding_model: str = "BAAI/bge-m3"
    # a passage must score at least this (cosine similarity) to be handed to the LLM; the scale depends on the model.
    # 0.5 for bge-m3: keeps 84% of the answerable questions and stops about half of the unrelated ones
    # (the LLM refuses most of the rest). 0.55 would stop more, but loses 8 more points of real answers.
    rag_min_score: float = 0.5
    # search by keywords (BM25) as well as by meaning, and merge the two rankings; false = by meaning only
    rag_hybrid_search: bool = True
    # after the search, a second model reads the question together with each of the best passages and puts them in a better
    # order. The search hands it rag_candidates passages and the LLM gets the best 4. false = the search order is used as it is
    rag_rerank: bool = True
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rag_candidates: int = 10
    # the addresses of web pages that may call this API, separated by commas (the frontend's own address)
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("ollama_num_gpu", mode="before")
    @classmethod
    def empty_means_not_set(cls, value):
        # docker compose passes an unset optional variable as an empty string; that must mean "not set", not an error
        return None if value == "" else value
    
settings = Settings()
