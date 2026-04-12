from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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
    static_site_dir: Path | None = Field(
        default=None,
        validation_alias="STATIC_SITE_DIR",
        description="If set, serve the Vite production build and SPA fallback from this directory",
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

    # Optional SMTP (env fallback; admin UI persists overrides in system_settings)
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True
    smtp_implicit_tls: bool = False
    smtp_validate_certs: bool = True
    smtp_auth_mode: Literal["login", "none"] = "login"

    # Deck LLM (system defaults; admin UI persists overrides in system_settings)
    deck_llm_provider: str | None = Field(
        default=None,
        validation_alias="DECK_LLM_PROVIDER",
        description="litellm | openai | claude (default: litellm)",
    )
    litellm_api_base: str | None = Field(
        default=None,
        validation_alias="LITELLM_API_BASE",
        description="OpenAI-compatible base URL, e.g. https://litellm.example.com/v1",
    )
    litellm_api_key: str | None = Field(
        default=None,
        validation_alias="LITELLM_API_KEY",
        description="Optional bearer token for LiteLLM / OpenAI-compatible proxy",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        description="OpenAI API key when deck_llm_provider=openai",
    )
    openai_api_base: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_BASE",
        description="Optional OpenAI API base URL override",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
        description="Anthropic API key when deck_llm_provider=claude",
    )
    anthropic_api_base: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_BASE",
        description="Optional Anthropic API base URL override",
    )
    deck_llm_model: str | None = Field(
        default=None,
        validation_alias="DECK_LLM_MODEL",
        description=(
            "Optional: same model id for all providers. If unset, use per-provider env or "
            "code defaults (gpt-5.4 / claude-sonnet-4-6 / litellm→Sonnet)."
        ),
    )
    deck_llm_model_openai: str | None = Field(
        default=None,
        validation_alias="DECK_LLM_MODEL_OPENAI",
        description="OpenAI model id for deck jobs (default: gpt-5.4 non-pro alias)",
    )
    deck_llm_model_anthropic: str | None = Field(
        default=None,
        validation_alias="DECK_LLM_MODEL_ANTHROPIC",
        description="Anthropic model id for deck jobs (default: claude-sonnet-4-6)",
    )
    deck_llm_model_litellm: str | None = Field(
        default=None,
        validation_alias="DECK_LLM_MODEL_LITELLM",
        description="Model for LiteLLM / OpenAI-compatible HTTP (default: claude-sonnet-4-6)",
    )

    @field_validator("static_site_dir", mode="before")
    @classmethod
    def _coerce_static_site_dir(cls, v: object) -> Path | None:
        if v is None:
            return None
        if isinstance(v, Path):
            return v if str(v).strip() else None
        s = str(v).strip()
        return Path(s) if s else None

    @field_validator("smtp_auth_mode", mode="before")
    @classmethod
    def _coerce_smtp_auth_mode(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "login"
        s = str(v).strip().lower()
        if s in ("none", "relay", "anonymous"):
            return "none"
        return "login"

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
