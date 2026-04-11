from __future__ import annotations

import uuid

from app.db.models.user import AuthProvider, UserRole
from pydantic import BaseModel, EmailStr, Field


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
