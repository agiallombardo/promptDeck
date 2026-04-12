from __future__ import annotations

import uuid

from app.db.models.user import AuthProvider, UserRole
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: UserRole
    auth_provider: AuthProvider

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class MessageResponse(BaseModel):
    message: str


class AuthConfigResponse(BaseModel):
    local_password_auth_enabled: bool
    entra_enabled: bool
    entra_login_url: str | None = None


class UserSettingsRead(BaseModel):
    llm_provider: str | None = None
    openai_api_base: str | None = None
    anthropic_api_base: str | None = None
    litellm_api_base: str | None = None
    openai_api_key_configured: bool = False
    anthropic_api_key_configured: bool = False
    litellm_api_key_configured: bool = False
    llm_api_key_configured: bool = Field(
        default=False,
        description="True if any per-provider or legacy API key is stored.",
    )


class UserSettingsUpdate(BaseModel):
    llm_provider: str | None = Field(
        default=None,
        max_length=16,
        description="openai | claude | litellm (omit to leave unchanged).",
    )
    clear_llm_provider: bool = Field(
        default=False,
        description="When true, clear personal provider override (use organization defaults only).",
    )
    openai_api_base: str | None = Field(default=None, max_length=512)
    anthropic_api_base: str | None = Field(default=None, max_length=512)
    litellm_api_base: str | None = Field(default=None, max_length=512)
    openai_api_key: str | None = Field(default=None, max_length=4096)
    anthropic_api_key: str | None = Field(default=None, max_length=4096)
    litellm_api_key: str | None = Field(default=None, max_length=4096)
    clear_openai_api_key: bool = False
    clear_anthropic_api_key: bool = False
    clear_litellm_api_key: bool = False
    clear_openai_api_base: bool = False
    clear_anthropic_api_base: bool = False
    clear_litellm_api_base: bool = False
    llm_api_key: str | None = Field(
        default=None,
        max_length=4096,
        description="Deprecated: use openai_api_key / anthropic_api_key / litellm_api_key.",
    )
    clear_llm_api_key: bool = False

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip().lower()
        if not s:
            return None
        if s not in ("openai", "claude", "litellm"):
            raise ValueError("llm_provider must be openai, claude, or litellm")
        return s

    @model_validator(mode="after")
    def _clear_llm_provider_wins(self) -> UserSettingsUpdate:
        if self.clear_llm_provider:
            self.llm_provider = None
        return self
