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
