"""Food schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class FoodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    barcode: str | None = Field(None, max_length=50)
    calories_per_100g: float | None = Field(None, ge=0)
    protein_per_100g: float | None = Field(None, ge=0)
    carbs_per_100g: float | None = Field(None, ge=0)
    fat_per_100g: float | None = Field(None, ge=0)
    fiber_per_100g: float | None = Field(None, ge=0)
    source: str | None = None


class FoodResponse(SchemaBase):
    id: uuid.UUID
    name: str
    barcode: str | None
    calories_per_100g: float | None
    protein_per_100g: float | None
    carbs_per_100g: float | None
    fat_per_100g: float | None
    fiber_per_100g: float | None
    source: str | None
    verified: bool


class BarcodeScanResponse(SchemaBase):
    id: uuid.UUID
    barcode: str
    food_id: uuid.UUID | None
    found: bool
    raw_result: dict | None
    created_at: datetime
