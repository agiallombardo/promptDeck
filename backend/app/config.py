from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/promptdeck",
        description="SQLAlchemy async URL (postgresql+asyncpg://… or sqlite+aiosqlite://…)",
    )
    jwt_secret_key: str = Field(default="dev-change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    cookie_secure: bool = False
    environment: str = "development"
    storage_root: Path = Field(
        default=Path("./data/storage"),
        validation_alias="STORAGE_ROOT",
        description="Root directory for LocalFSStorage (presentations/…)",
    )
    asset_url_ttl_seconds: int = Field(default=3600, description="Signed /a/… URL lifetime")
    public_app_url: str = Field(
        default="http://127.0.0.1:5173",
        description=(
            "Origin for absolute embed URLs (no trailing slash); defaults to Vite dev server"
        ),
    )
    argon2_time_cost: int = Field(default=3, ge=1, le=10, description="Argon2id time cost")
    argon2_memory_cost: int = Field(
        default=65536,
        ge=8192,
        description="Argon2id memory cost (KiB)",
    )
    argon2_parallelism: int = Field(default=1, ge=1, le=8, description="Argon2id parallelism")


@lru_cache
def get_settings() -> Settings:
    return Settings()
