"""Supplements schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class SupplementCreate(BaseModel):
    name: str = Field(..., max_length=100)
    default_dose: str | None = Field(None, max_length=50)
    timing: str | None = None


class SupplementResponse(SchemaBase):
    id: uuid.UUID
    name: str
    default_dose: str | None
    timing: str | None


class UserSupplementCreate(BaseModel):
    supplement_id: uuid.UUID
    dose: str | None = Field(None, max_length=50)
    timing: str | None = None
    reminder_enabled: bool = False
    reminder_time: time | None = None


class UserSupplementResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    supplement_id: uuid.UUID
    dose: str | None
    timing: str | None
    reminder_enabled: bool
    reminder_time: time | None
    created_at: datetime


class SupplementLogCreate(BaseModel):
    supplement_id: uuid.UUID


class SupplementLogResponse(SchemaBase):
    id: uuid.UUID
    supplement_id: uuid.UUID
    taken_at: datetime
    created_at: datetime
