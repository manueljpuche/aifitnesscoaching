"""Tracking service — meals, weight, water, workout logs."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracking.models import (
    MealItem,
    MealLog,
    WeightLog,
    WaterLog,
)


# ---- Meals ----


async def create_meal_log(db: AsyncSession, user_id: uuid.UUID, data: dict) -> MealLog:
    items_data = data.pop("items", [])
    meal = MealLog(user_id=user_id, **data)
    db.add(meal)
    await db.flush()

    for item_data in items_data:
        item = MealItem(meal_id=meal.id, **item_data)
        db.add(item)

    # Compute total calories from items if not provided
    if meal.total_calories is None and items_data:
        meal.total_calories = sum((i.get("calories") or 0) for i in items_data)

    await db.flush()
    return meal


async def get_meals_by_date(
    db: AsyncSession, user_id: uuid.UUID, target_date: date
) -> list[MealLog]:
    start = datetime(
        target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
    )
    end = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        23,
        59,
        59,
        tzinfo=timezone.utc,
    )
    result = await db.execute(
        select(MealLog)
        .where(
            MealLog.user_id == user_id,
            MealLog.created_at >= start,
            MealLog.created_at <= end,
        )
        .order_by(MealLog.created_at)
    )
    return list(result.scalars().all())


async def copy_meals_from_date(
    db: AsyncSession, user_id: uuid.UUID, source_date: date
) -> list[MealLog]:
    """Copy all meals from source_date to today."""
    source_meals = await get_meals_by_date(db, user_id, source_date)
    new_meals = []
    for meal in source_meals:
        new_meal = MealLog(
            user_id=user_id,
            description=meal.description,
            total_calories=meal.total_calories,
            source="copy",
            is_cheat=meal.is_cheat,
            context=meal.context,
        )
        db.add(new_meal)
        await db.flush()

        for item in meal.items:
            new_item = MealItem(
                meal_id=new_meal.id,
                food_name=item.food_name,
                quantity=item.quantity,
                unit=item.unit,
                calories=item.calories,
                protein=item.protein,
                carbs=item.carbs,
                fat=item.fat,
            )
            db.add(new_item)

        new_meals.append(new_meal)

    return new_meals


# ---- Weight ----


async def log_weight(db: AsyncSession, user_id: uuid.UUID, data: dict) -> WeightLog:
    today = date.today()
    result = await db.execute(
        select(WeightLog).where(
            WeightLog.user_id == user_id,
            func.date(WeightLog.created_at) == today,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.weight = data["weight"]
        existing.source = data.get("source", "manual")
        existing.note = data.get("note")
        return existing

    entry = WeightLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_weight_history(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 30
) -> list[WeightLog]:
    result = await db.execute(
        select(WeightLog)
        .where(WeightLog.user_id == user_id)
        .order_by(WeightLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- Water ----


async def log_water(db: AsyncSession, user_id: uuid.UUID, amount_ml: float) -> WaterLog:
    entry = WaterLog(user_id=user_id, amount_ml=amount_ml)
    db.add(entry)
    await db.flush()
    return entry


async def get_water_today(db: AsyncSession, user_id: uuid.UUID) -> float:
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    result = await db.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0.0)).where(
            WaterLog.user_id == user_id,
            WaterLog.created_at >= start,
        )
    )
    return float(result.scalar())
