"""Check-ins schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class WeeklyCheckinCreate(BaseModel):
    week_start: date
    weight_kg: float | None = Field(None, ge=0.5, le=500)
    energy_level: int | None = Field(None, ge=1, le=5)
    mood_score: int | None = Field(None, ge=1, le=5)
    adherence_diet: float | None = Field(None, ge=0, le=100)
    adherence_workout: float | None = Field(None, ge=0, le=100)
    notes: str | None = Field(None, max_length=1000)


class WeeklyCheckinResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    week_start: date
    weight_kg: float | None
    energy_level: int | None
    mood_score: int | None
    adherence_diet: float | None
    adherence_workout: float | None
    notes: str | None
    plan_adjustment_suggested: dict | None
    plan_adjusted: bool
    created_at: datetime
