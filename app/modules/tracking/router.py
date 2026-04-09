"""Tracking router — meals, weight, water."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracking.schemas import (
    MealLogCreate,
    MealLogResponse,
    WaterLogCreate,
    WaterLogResponse,
    WeightLogCreate,
    WeightLogResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.tracking.service import (
    copy_meals_from_date,
    create_meal_log,
    get_meals_by_date,
    get_water_today,
    get_weight_history,
    log_water,
    log_weight,
)

router = APIRouter()


# ---- Meals ----


@router.post("/meals", response_model=MealLogResponse, status_code=201)
async def create_meal(
    body: MealLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meal = await create_meal_log(db, user.id, body.model_dump())
    return meal


@router.get("/meals", response_model=list[MealLogResponse])
async def list_meals(
    target_date: date = Query(default_factory=date.today),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_meals_by_date(db, user.id, target_date)


@router.post("/meals/copy-from-date", response_model=list[MealLogResponse])
async def copy_meals(
    source_date: date = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await copy_meals_from_date(db, user.id, source_date)


# ---- Weight ----


@router.post("/weight", response_model=WeightLogResponse, status_code=201)
async def create_weight(
    body: WeightLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_weight(db, user.id, body.model_dump())


@router.get("/weight", response_model=list[WeightLogResponse])
async def list_weight(
    limit: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_weight_history(db, user.id, limit)


# ---- Water ----


@router.post("/water", response_model=WaterLogResponse, status_code=201)
async def create_water(
    body: WaterLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_water(db, user.id, body.amount_ml)


@router.get("/water/today")
async def water_today(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await get_water_today(db, user.id)
    goal = user.water_goal_ml or 2500
    return {
        "total_ml": total,
        "goal_ml": goal,
        "percentage": round(total / goal * 100, 1),
    }
