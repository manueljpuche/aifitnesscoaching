"""Exercises schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class ExerciseCreate(BaseModel):
    name: str = Field(..., max_length=200)
    muscle_group: str = Field(..., max_length=30)
    muscle_secondary: list[str] | None = None
    equipment: str = Field(..., max_length=30)
    movement_pattern: str | None = None
    demo_url: str | None = None
    notes: str | None = None


class ExerciseResponse(SchemaBase):
    id: uuid.UUID
    name: str
    muscle_group: str
    muscle_secondary: list[str] | None
    equipment: str
    movement_pattern: str | None
    demo_url: str | None
    notes: str | None
