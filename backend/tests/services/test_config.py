import pytest

from app.core.config import Settings


def make_settings(**overrides):
    # _env_file=None: only the values given here count, not the .env of whoever runs the test
    return Settings(_env_file=None, database_url="sqlite://", secret_key="not-a-real-secret", **overrides)


def test_num_gpu_is_not_set_by_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_GPU", raising=False)

    assert make_settings().ollama_num_gpu is None


@pytest.mark.parametrize("value, expected", [("0", 0), ("1", 1), (0, 0)])
def test_num_gpu_accepts_a_number(value, expected):
    assert make_settings(ollama_num_gpu=value).ollama_num_gpu == expected


def test_an_empty_num_gpu_means_not_set():
    """docker compose hands an optional variable that was not set over as an empty string."""
    assert make_settings(ollama_num_gpu="").ollama_num_gpu is None


def test_the_empty_string_also_works_from_an_environment_variable(monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_GPU", "")

    assert make_settings().ollama_num_gpu is None


# ---------- CORS origins ----------

def test_the_default_origin_is_the_local_frontend():
    assert make_settings().cors_origin_list == ["http://localhost:3000"]


def test_several_origins_are_split_on_commas_and_trimmed():
    settings = make_settings(cors_origins=" http://localhost:3100 , https://demo.example.com,, ")

    assert settings.cors_origin_list == ["http://localhost:3100", "https://demo.example.com"]


# ---------- embedding model and threshold ----------

def test_the_default_embedding_model_is_bge_m3():
    assert make_settings().embedding_model == "BAAI/bge-m3"


def test_the_embedding_model_and_threshold_can_be_changed(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.8")

    settings = make_settings()

    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    assert settings.rag_min_score == 0.8


def test_hybrid_search_is_on_by_default_and_can_be_switched_off(monkeypatch):
    monkeypatch.delenv("RAG_HYBRID_SEARCH", raising=False)
    assert make_settings().rag_hybrid_search is True

    monkeypatch.setenv("RAG_HYBRID_SEARCH", "false")
    assert make_settings().rag_hybrid_search is False


def test_reranking_is_on_by_default_with_ten_candidates_and_can_be_changed(monkeypatch):
    for name in ("RAG_RERANK", "RERANK_MODEL", "RAG_CANDIDATES"):
        monkeypatch.delenv(name, raising=False)
    settings = make_settings()
    assert settings.rag_rerank is True
    assert settings.rerank_model == "BAAI/bge-reranker-v2-m3"
    assert settings.rag_candidates == 10

    monkeypatch.setenv("RAG_RERANK", "false")
    monkeypatch.setenv("RAG_CANDIDATES", "20")
    settings = make_settings()
    assert settings.rag_rerank is False
    assert settings.rag_candidates == 20
