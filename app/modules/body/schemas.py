"""Body schemas — measurements and progress photos."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class BodyMeasurementCreate(BaseModel):
    waist_cm: float | None = Field(None, ge=20, le=300)
    hip_cm: float | None = Field(None, ge=20, le=300)
    chest_cm: float | None = Field(None, ge=20, le=300)
    arm_cm: float | None = Field(None, ge=5, le=100)
    thigh_cm: float | None = Field(None, ge=10, le=150)
    body_fat_pct: float | None = Field(None, ge=1, le=70)
    body_fat_method: str | None = None
    notes: str | None = Field(None, max_length=1000)


class BodyMeasurementResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    waist_cm: float | None
    hip_cm: float | None
    chest_cm: float | None
    arm_cm: float | None
    thigh_cm: float | None
    body_fat_pct: float | None
    body_fat_method: str | None
    lean_mass_kg: float | None
    fat_mass_kg: float | None
    notes: str | None
    created_at: datetime
