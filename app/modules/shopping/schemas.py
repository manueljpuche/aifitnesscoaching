"""Shopping schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class ShoppingListCreate(BaseModel):
    week_start: date
    budget: float | None = Field(None, ge=0)
    generated_by: str = "plan"


class ShoppingListResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    week_start: date
    budget: float | None
    items: dict | None
    total_estimated_cost: float | None
    within_budget: bool | None
    generated_by: str
    created_at: datetime
