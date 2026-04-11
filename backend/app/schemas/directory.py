from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class DirectoryUserRead(BaseModel):
    entra_object_id: str = Field(min_length=1)
    email: EmailStr
    display_name: str | None = None
    user_type: str | None = None


class DirectoryUserListResponse(BaseModel):
    items: list[DirectoryUserRead]
