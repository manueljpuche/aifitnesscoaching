"""Notifications domain models."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.db.utils import new_uuid, utcnow


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    silent_from: Mapped[time | None] = mapped_column(Time)
    silent_until: Mapped[time | None] = mapped_column(Time)
    max_daily_messages: Mapped[int] = mapped_column(Integer, default=10)
    meal_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    workout_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    water_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    supplement_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_checkin: Mapped[bool] = mapped_column(Boolean, default=True)
    progress_photos: Mapped[bool] = mapped_column(Boolean, default=True)
    expiry_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    streak_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    pr_celebrations: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
