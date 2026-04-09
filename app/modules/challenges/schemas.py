"""Challenges schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.schemas_base import SchemaBase


class ChallengeResponse(SchemaBase):
    id: uuid.UUID
    title: str
    description: str | None
    challenge_type: str
    duration_days: int
    locale: str


class UserChallengeCreate(BaseModel):
    challenge_id: uuid.UUID


class UserChallengeResponse(SchemaBase):
    id: uuid.UUID
    challenge_id: uuid.UUID
    started_at: datetime
    ends_at: datetime | None
    completed: bool
    progress: dict | None
    created_at: datetime
