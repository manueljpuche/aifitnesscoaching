"""Nutrition domain models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.utils import new_uuid, utcnow

if TYPE_CHECKING:
    from app.modules.users.models import User


class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calories_target: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    meals_per_day: Mapped[int] = mapped_column(Integer, default=4)
    start_date: Mapped[date | None] = mapped_column(Date)
    duration_weeks: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped[User] = relationship(back_populates="nutrition_plans")
    meal_schedules: Mapped[list[MealSchedule]] = relationship(
        back_populates="plan", lazy="selectin"
    )


class MealSchedule(Base):
    __tablename__ = "meal_schedule"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_time: Mapped[time | None] = mapped_column(Time)
    calories_target: Mapped[float | None] = mapped_column(Float)
    protein_target: Mapped[float | None] = mapped_column(Float)
    carbs_target: Mapped[float | None] = mapped_column(Float)
    fat_target: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    plan: Mapped[NutritionPlan] = relationship(back_populates="meal_schedules")
    planned_meals: Mapped[list[PlannedMeal]] = relationship(
        back_populates="schedule", lazy="selectin"
    )


class PlannedMeal(Base):
    __tablename__ = "planned_meals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meal_schedule.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(30))
    calories: Mapped[float | None] = mapped_column(Float)
    protein: Mapped[float | None] = mapped_column(Float)
    carbs: Mapped[float | None] = mapped_column(Float)
    fat: Mapped[float | None] = mapped_column(Float)

    schedule: Mapped[MealSchedule] = relationship(back_populates="planned_meals")


class MealTimingRule(Base):
    __tablename__ = "meal_timing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    workout_time: Mapped[time | None] = mapped_column(Time)
    pre_workout_window_min: Mapped[int] = mapped_column(Integer, default=60)
    post_workout_window_min: Mapped[int] = mapped_column(Integer, default=30)
    early_morning_fast: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class TDEELog(Base):
    __tablename__ = "tdee_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tdee_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    bmr_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    activity_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    trigger: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
