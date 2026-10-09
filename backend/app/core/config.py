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
