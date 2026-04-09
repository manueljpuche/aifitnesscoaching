"""Versioning schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.api.schemas_base import SchemaBase


class PlanVersionResponse(SchemaBase):
    id: uuid.UUID
    plan_type: str
    plan_id: uuid.UUID
    change_reason: str | None
    created_at: datetime
