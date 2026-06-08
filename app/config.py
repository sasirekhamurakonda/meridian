from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.url_utils import validate_database_url, validate_redis_url


def _normalize_database_url(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("sslmode=require", "ssl=require")
    url = url.replace("sslmode=prefer", "ssl=prefer")
    url = url.replace("sslmode=disable", "ssl=disable")
    return validate_database_url(url)


def _normalize_redis_url(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    # Upstash requires TLS; accept redis:// only when explicitly using local dev.
    if url.startswith("redis://") and "upstash.io" in url:
        url = url.replace("redis://", "rediss://", 1)
    return validate_redis_url(url)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://meridian:meridian@localhost:5432/meridian"
    redis_url: str = "redis://localhost:6379/0"

    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_ssl_verify: bool = True

    api_key: str | None = None

    max_concurrent_jobs: int = 2
    max_query_length: int = 2000
    rate_limit_per_hour: int = 5
    top_k_passages: int = 15
    job_timeout_seconds: int = 600
    max_sub_questions: int = 5
    min_sub_questions: int = 3
    search_timeout_seconds: float = 15.0
    max_results_per_source: int = 5
    max_web_results_per_query: int = 8
    max_passages_for_embedding: int = 40
    embed_batch_size: int = 12
    min_passage_score: float = 0.30

    log_level: str = "INFO"
    event_log_ttl_seconds: int = 86400

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_database_url(value)

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, value: str) -> str:
        return _normalize_redis_url(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
