"""Gamification schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from app.api.schemas_base import SchemaBase


class UserAchievementResponse(SchemaBase):
    id: uuid.UUID
    achievement_type: str
    title: str
    description: str | None
    earned_at: datetime


class UserStreakResponse(SchemaBase):
    id: uuid.UUID
    streak_type: str
    current_streak: int
    best_streak: int
    last_activity_date: date | None
