"""Notifications schemas."""

from __future__ import annotations

import uuid
from datetime import time

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class NotificationPreferenceUpdate(BaseModel):
    silent_from: time | None = None
    silent_until: time | None = None
    max_daily_messages: int | None = Field(None, ge=1, le=50)
    meal_reminders: bool | None = None
    workout_reminders: bool | None = None
    water_reminders: bool | None = None
    supplement_reminders: bool | None = None
    weekly_checkin: bool | None = None
    progress_photos: bool | None = None
    expiry_alerts: bool | None = None
    streak_alerts: bool | None = None
    pr_celebrations: bool | None = None


class NotificationPreferenceResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    silent_from: time | None
    silent_until: time | None
    max_daily_messages: int
    meal_reminders: bool
    workout_reminders: bool
    water_reminders: bool
    supplement_reminders: bool
    weekly_checkin: bool
    progress_photos: bool
    expiry_alerts: bool
    streak_alerts: bool
    pr_celebrations: bool
