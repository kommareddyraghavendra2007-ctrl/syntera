from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SYNTERA"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR / 'data' / 'syntera.db').as_posix()}"
    )

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_path: str = Field(default_factory=lambda: str(BACKEND_DIR / "data" / "qdrant"))
    qdrant_collection: str = "syntera_code_units"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 60.0

    embedding_provider: str = "hash"
    embedding_model: str = "syntera-hash-v1"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_dimensions: int | None = None
    embedding_batch_size: int = 32

    work_dir: str = Field(default_factory=lambda: str(BACKEND_DIR / "data" / "work"))
    max_repository_size_bytes: int = 80 * 1024 * 1024
    max_file_size_bytes: int = 1_500_000
    max_zip_files: int = 20_000
    clone_timeout_seconds: int = 120
    parse_concurrency: int = 4

    top_k: int = 20
    sparse_top_k: int = 20
    symbol_top_k: int = 20
    rerank_top_k: int = 12
    graph_expansion_depth: int = 2
    graph_expansion_limit: int = 24
    max_context_chars: int = 24_000

    allow_config_inspect: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
