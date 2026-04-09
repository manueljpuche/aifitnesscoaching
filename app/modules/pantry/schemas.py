"""Pantry schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class PantryItemCreate(BaseModel):
    food_name: str = Field(..., min_length=1, max_length=200)
    quantity: float | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=30)
    source: str = "text"
    expires_at: date | None = None


class PantryItemUpdate(BaseModel):
    quantity: float | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=30)
    expires_at: date | None = None


class PantryItemResponse(SchemaBase):
    id: uuid.UUID
    food_name: str
    quantity: float | None
    unit: str | None
    source: str
    expires_at: date | None
    added_at: datetime


class PantryScanResponse(SchemaBase):
    id: uuid.UUID
    scan_type: str
    items_detected: dict | None
    confirmed_by_user: bool
    created_at: datetime
