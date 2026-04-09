"""Auth schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.schemas_base import SchemaBase


class TelegramLoginRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    auth_date: int | None = None
    hash: str | None = None


class TokenResponse(SchemaBase):
    access_token: str
    expires_at: datetime
    user_id: uuid.UUID
