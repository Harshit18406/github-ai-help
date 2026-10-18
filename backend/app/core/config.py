from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "GitHub AI Help"
    env: str = "development"

    # Security
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database / cache
    database_url: str = "sqlite:///./github_ai_help.db"
    redis_url: str = "redis://localhost:6379/0"

    # Local repository storage
    repo_storage_path: str = "./workspace/repos"
    max_repository_files: int = 12000
    max_file_size_bytes: int = 2_000_000

    # CORS
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )

    # OpenRouter
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_model: str = Field(
        default="openrouter/free",
        validation_alias="OPENROUTER_MODEL",
    )
    llm_max_attempts: int = 3
    llm_timeout_seconds: int = 90

    # Optional legacy OpenAI settings
    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    openai_model: str = Field(
        default="gpt-5.6-sol",
        validation_alias="OPENAI_MODEL",
    )

    # Test execution
    sandbox_image: str = "python:3.12-slim"
    sandbox_timeout_seconds: int = 120
    sandbox_memory: str = "512m"
    sandbox_cpus: float = 1.0
    test_execution_mode: str = Field(
        default="local",
        validation_alias="TEST_EXECUTION_MODE",
    )

    # Agent
    agent_max_iterations: int = 3

    # Embeddings
    embedding_dim: int = 384

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    def ensure_paths(self) -> None:
        Path(self.repo_storage_path).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_paths()
    return settings


settings = get_settings()
