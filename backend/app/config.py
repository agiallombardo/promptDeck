from __future__ import annotations

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
            "http://127.0.0.1:5174",
            "http://localhost:5174",
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
        default="http://127.0.0.1:5174",
        description=(
            "Origin for absolute embed URLs (no trailing slash); defaults to Vite dev server"
        ),
    )
    public_api_url: str = Field(
        default="http://127.0.0.1:8005",
        description="Public API origin for OAuth callbacks (no trailing slash)",
    )
    argon2_time_cost: int = Field(default=3, ge=1, le=10, description="Argon2id time cost")
    argon2_memory_cost: int = Field(
        default=65536,
        ge=8192,
        description="Argon2id memory cost (KiB)",
    )
    argon2_parallelism: int = Field(default=1, ge=1, le=8, description="Argon2id parallelism")

    local_password_auth_enabled: bool = True
    entra_enabled: bool = False
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    entra_client_secret: str | None = None
    entra_authority_host: str = "https://login.microsoftonline.com"
    entra_token_encryption_key: str | None = None

    @property
    def entra_redirect_uri(self) -> str:
        return f"{self.public_api_url.rstrip('/')}/api/v1/auth/entra/callback"

    @property
    def entra_authority(self) -> str:
        tenant = (self.entra_tenant_id or "common").strip()
        return f"{self.entra_authority_host.rstrip('/')}/{tenant}/oauth2/v2.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
