"""Nutrition router — plans and meal schedules."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nutrition.schemas import (
    MealScheduleCreate,
    MealScheduleResponse,
    NutritionPlanCreate,
    NutritionPlanResponse,
    NutritionPlanUpdate,
)
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.nutrition.service import (
    create_plan,
    create_schedule,
    get_active_plan,
    get_pending_meal_reminders,
    get_schedules,
    update_plan,
)

router = APIRouter()


@router.get("/plans/active", response_model=NutritionPlanResponse | None)
async def active_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_plan(db, user.id)


@router.post("/plans", response_model=NutritionPlanResponse, status_code=201)
async def create_nutrition_plan(
    body: NutritionPlanCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_plan(db, user.id, body.model_dump())


@router.patch("/plans/active", response_model=NutritionPlanResponse)
async def update_nutrition_plan(
    body: NutritionPlanUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_active_plan(db, user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active nutrition plan")
    return await update_plan(db, plan, body.model_dump(exclude_unset=True))


@router.get("/schedule/{plan_id}", response_model=list[MealScheduleResponse])
async def list_schedules(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_schedules(db, plan_id)


@router.post("/schedule/{plan_id}", response_model=MealScheduleResponse, status_code=201)
async def add_schedule(
    plan_id: uuid.UUID,
    body: MealScheduleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_schedule(db, plan_id, body.model_dump())


# ---- n8n batch endpoints ----


@router.get("/schedule/pending-reminders", dependencies=[Depends(verify_n8n_secret)])
async def pending_meal_reminders(db: AsyncSession = Depends(get_db)):
    return await get_pending_meal_reminders(db)
