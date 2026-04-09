"""Wellness schemas — sleep, alcohol, cycle, symptoms, status."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class SleepLogCreate(BaseModel):
    hours: float = Field(..., ge=0.5, le=24)
    quality: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=1000)


class SleepLogResponse(SchemaBase):
    id: uuid.UUID
    hours: float
    quality: int | None
    notes: str | None
    created_at: datetime


class AlcoholLogCreate(BaseModel):
    description: str | None = Field(None, max_length=200)
    calories: float | None = Field(None, ge=0)
    units: float | None = Field(None, ge=0.1, le=50)


class AlcoholLogResponse(SchemaBase):
    id: uuid.UUID
    description: str | None
    calories: float | None
    units: float | None
    created_at: datetime


class CycleLogCreate(BaseModel):
    cycle_start: date
    cycle_end: date | None = None
    phase: str | None = None


class CycleLogResponse(SchemaBase):
    id: uuid.UUID
    cycle_start: date
    cycle_end: date | None
    phase: str | None
    created_at: datetime


class SymptomLogCreate(BaseModel):
    symptom: str = Field(..., max_length=50)
    symptom_raw: str | None = Field(None, max_length=1000)
    severity: int = Field(1, ge=1, le=3)


class SymptomLogResponse(SchemaBase):
    id: uuid.UUID
    symptom: str
    symptom_raw: str | None
    severity: int
    recommendations: dict | None
    plan_adjusted: bool
    followup_sent: bool
    resolved: bool
    created_at: datetime


class UserStatusCreate(BaseModel):
    status: str = Field(..., max_length=20)
    reason: str | None = None
    ends_at: datetime | None = None


class UserStatusResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    reason: str | None
    started_at: datetime
    ends_at: datetime | None
    created_at: datetime
