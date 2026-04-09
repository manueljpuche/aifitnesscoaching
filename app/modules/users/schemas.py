"""Users schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserUpdate(BaseModel):
    age: int | None = Field(None, ge=10, le=120)
    height_cm: float | None = Field(None, ge=50, le=300)
    weight_kg: float | None = Field(None, ge=0.5, le=500)
    gender: str | None = None
    body_fat_pct: float | None = Field(None, ge=1, le=70)
    activity_level: str | None = None
    goal: str | None = None
    restrictions: str | None = None
    menstrual_cycle_tracking: bool | None = None
    water_goal_ml: float | None = Field(None, ge=0, le=10000)
    locale: str | None = None
    timezone: str | None = None
    weekly_budget: float | None = Field(None, ge=0)


class UserResponse(SchemaBase):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    age: int | None
    height_cm: float | None
    weight_kg: float | None
    gender: str | None
    body_fat_pct: float | None
    activity_level: str | None
    goal: str | None
    restrictions: str | None
    menstrual_cycle_tracking: bool
    water_goal_ml: float | None
    locale: str
    timezone: str
    weekly_budget: float | None
    created_at: datetime


class PreferenceCreate(BaseModel):
    type: str = Field(..., max_length=30)
    category: str = Field(..., max_length=30)
    value: str = Field(..., max_length=200)
    is_temporary: bool = False
    reason: str | None = None
    expires_at: datetime | None = None


class PreferenceResponse(SchemaBase):
    id: uuid.UUID
    type: str
    category: str
    value: str
    is_temporary: bool
    reason: str | None
    expires_at: datetime | None
    created_at: datetime
