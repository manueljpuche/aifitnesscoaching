"""Nutrition schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class NutritionPlanCreate(BaseModel):
    calories_target: int = Field(..., ge=0, le=15000)
    protein_g: float = Field(..., ge=0, le=1000)
    carbs_g: float = Field(..., ge=0, le=1500)
    fat_g: float = Field(..., ge=0, le=1000)
    fiber_g: float | None = Field(None, ge=0, le=200)
    meals_per_day: int = Field(4, ge=1, le=10)
    start_date: date | None = None
    duration_weeks: int | None = None


class NutritionPlanUpdate(BaseModel):
    calories_target: int | None = Field(None, ge=0, le=15000)
    protein_g: float | None = Field(None, ge=0, le=1000)
    carbs_g: float | None = Field(None, ge=0, le=1500)
    fat_g: float | None = Field(None, ge=0, le=1000)
    fiber_g: float | None = Field(None, ge=0, le=200)
    meals_per_day: int | None = Field(None, ge=1, le=10)
    is_active: bool | None = None


class NutritionPlanResponse(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    calories_target: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None
    meals_per_day: int
    start_date: date | None
    duration_weeks: int | None
    is_active: bool
    created_at: datetime


class MealScheduleCreate(BaseModel):
    meal_number: int = Field(..., ge=1, le=10)
    name: str = Field(..., max_length=100)
    target_time: time | None = None
    calories_target: float | None = Field(None, ge=0, le=15000)
    protein_target: float | None = Field(None, ge=0, le=1000)
    carbs_target: float | None = Field(None, ge=0, le=1500)
    fat_target: float | None = Field(None, ge=0, le=1000)


class MealScheduleResponse(SchemaBase):
    id: uuid.UUID
    plan_id: uuid.UUID
    meal_number: int
    name: str
    target_time: time | None
    calories_target: float | None
    protein_target: float | None
    carbs_target: float | None
    fat_target: float | None


class MealTimingRuleUpdate(BaseModel):
    workout_time: time | None = None
    pre_workout_window_min: int | None = Field(None, ge=10, le=180)
    post_workout_window_min: int | None = Field(None, ge=10, le=120)
    early_morning_fast: bool | None = None


class MealTimingRuleResponse(SchemaBase):
    id: uuid.UUID
    workout_time: time | None
    pre_workout_window_min: int
    post_workout_window_min: int
    early_morning_fast: bool


class TDEELogResponse(SchemaBase):
    id: uuid.UUID
    tdee_kcal: float
    bmr_kcal: float
    activity_multiplier: float
    trigger: str
    created_at: datetime
