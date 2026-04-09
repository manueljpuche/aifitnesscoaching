"""Workouts schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class WorkoutPlanCreate(BaseModel):
    name: str | None = Field(None, max_length=200)
    days_per_week: int = Field(..., ge=1, le=7)
    goal: str = Field(..., max_length=30)
    level: str = Field(..., max_length=20)
    equipment: str = "gym"
    phase: str = "hypertrophy"
    phase_total_weeks: int = 4
    total_phases: int | None = None
    ai_generated: bool = True


class WorkoutPlanResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None
    days_per_week: int
    goal: str
    level: str
    equipment: str
    phase: str
    phase_week: int
    phase_total_weeks: int
    total_phases: int | None
    current_phase_index: int
    start_date: date | None
    is_active: bool
    ai_generated: bool
    created_at: datetime


class WorkoutPlanDayCreate(BaseModel):
    day_number: int = Field(..., ge=1, le=7)
    name: str = Field(..., max_length=100)
    muscle_groups: list[str] | None = None
    order_index: int = 0


class WorkoutPlanDayResponse(SchemaBase):
    id: uuid.UUID
    plan_id: uuid.UUID
    day_number: int
    name: str
    muscle_groups: list[str] | None
    order_index: int


class WorkoutPlanExerciseCreate(BaseModel):
    exercise_id: uuid.UUID
    order_index: int = 0
    sets: int = Field(..., ge=1, le=20)
    reps_min: int = Field(..., ge=1, le=200)
    reps_max: int | None = Field(None, ge=1, le=200)
    weight_kg: float | None = Field(None, ge=0, le=1000)
    rest_seconds: int = Field(90, ge=0, le=600)
    rpe_target: float | None = Field(None, ge=1, le=10)
    notes: str | None = None


class WorkoutPlanExerciseResponse(SchemaBase):
    id: uuid.UUID
    plan_day_id: uuid.UUID
    exercise_id: uuid.UUID
    order_index: int
    sets: int
    reps_min: int
    reps_max: int | None
    weight_kg: float | None
    rest_seconds: int
    rpe_target: float | None
    notes: str | None


class WorkoutLogCreate(BaseModel):
    plan_day_id: uuid.UUID | None = None
    type: str | None = None
    duration_minutes: int | None = Field(None, ge=1, le=600)
    intensity: str | None = None
    location: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    notes: str | None = Field(None, max_length=1000)


class WorkoutLogResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_day_id: uuid.UUID | None
    type: str | None
    duration_minutes: int | None
    intensity: str | None
    location: str | None
    skipped: bool
    skip_reason: str | None
    notes: str | None
    created_at: datetime


class WorkoutSetLogCreate(BaseModel):
    exercise_id: uuid.UUID
    set_number: int = Field(..., ge=1, le=20)
    reps_done: int = Field(..., ge=1, le=200)
    weight_kg: float | None = Field(None, ge=0, le=1000)
    rpe_actual: float | None = Field(None, ge=1, le=10)
    completed: bool = True
    notes: str | None = Field(None, max_length=1000)


class WorkoutSetLogResponse(SchemaBase):
    id: uuid.UUID
    workout_log_id: uuid.UUID
    exercise_id: uuid.UUID
    set_number: int
    reps_done: int
    weight_kg: float | None
    rpe_actual: float | None
    completed: bool
    notes: str | None
    created_at: datetime


class PersonalRecordResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    exercise_id: uuid.UUID
    record_type: str
    value: float
    workout_log_id: uuid.UUID | None
    created_at: datetime


class CardioLogCreate(BaseModel):
    type: str = Field(..., max_length=30)
    duration_minutes: int = Field(..., ge=1, le=600)
    distance_km: float | None = Field(None, ge=0)
    avg_heart_rate: int | None = Field(None, ge=30, le=250)
    calories_burned: float | None = Field(None, ge=0)
    location: str | None = None
    notes: str | None = Field(None, max_length=1000)


class CardioLogResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    duration_minutes: int
    distance_km: float | None
    avg_heart_rate: int | None
    calories_burned: float | None
    location: str | None
    notes: str | None
    created_at: datetime
