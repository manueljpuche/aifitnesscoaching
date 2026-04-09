"""Shared Pydantic base schema for all modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
