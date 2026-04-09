"""Tracking schemas — meals, weight, water."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class MealItemCreate(BaseModel):
    food_name: str = Field(..., min_length=1, max_length=200)
    quantity: float | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=30)
    calories: float | None = Field(None, ge=0, le=15000)
    protein: float | None = Field(None, ge=0, le=1000)
    carbs: float | None = Field(None, ge=0, le=1500)
    fat: float | None = Field(None, ge=0, le=1000)


class MealLogCreate(BaseModel):
    description: str | None = Field(None, max_length=500)
    total_calories: float | None = Field(None, ge=0, le=15000)
    source: str = "text"
    is_cheat: bool = False
    context: str | None = None
    items: list[MealItemCreate] = []


class MealItemResponse(SchemaBase):
    id: uuid.UUID
    food_name: str
    quantity: float | None
    unit: str | None
    calories: float | None
    protein: float | None
    carbs: float | None
    fat: float | None


class MealLogResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    description: str | None
    total_calories: float | None
    source: str
    is_cheat: bool
    context: str | None
    created_at: datetime
    items: list[MealItemResponse] = []


class WeightLogCreate(BaseModel):
    weight: float = Field(..., ge=0.5, le=500)
    source: str = "manual"
    note: str | None = Field(None, max_length=200)


class WeightLogResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    weight: float
    source: str
    note: str | None
    created_at: datetime


class WaterLogCreate(BaseModel):
    amount_ml: float = Field(..., ge=1, le=5000)


class WaterLogResponse(SchemaBase):
    id: uuid.UUID
    amount_ml: float
    created_at: datetime
