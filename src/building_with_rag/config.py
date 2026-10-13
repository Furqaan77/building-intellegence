from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment settings. Every secret is optional so the app starts without credentials."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    mongodb_uri: str | None = None
    mongodb_db_name: str = "building_with_rag"
    mongodb_test_db_name: str = "building_with_rag_test"
    voyage_api_key: str | None = None
    capstone_api_key: str | None = None
    webui_demo_caller_id: str = "demo-public"
    generation_api_base_url: str | None = None
    generation_api_key: str | None = None
    generation_model_name: str = "gpt-4o-mini"
    rerank_api_key: str | None = None
    rerank_api_base_url: str = "https://api.voyageai.com/v1"
    rerank_model_name: str = "rerank-2.5"
    rerank_request_timeout_seconds: int = 30
    rerank_candidate_limit: int = 20
    rerank_send_limit: int = 10
    rerank_return_limit: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
