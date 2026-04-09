"""Nutrition service — plans, schedules, planned meals."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nutrition.models import MealSchedule, NutritionPlan, PlannedMeal
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import User


async def get_active_plan(db: AsyncSession, user_id: uuid.UUID) -> NutritionPlan | None:
    result = await db.execute(
        select(NutritionPlan).where(
            NutritionPlan.user_id == user_id,
            NutritionPlan.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def create_plan(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> NutritionPlan:
    # Deactivate any existing active plan
    result = await db.execute(
        select(NutritionPlan).where(
            NutritionPlan.user_id == user_id,
            NutritionPlan.is_active.is_(True),
        )
    )
    for old_plan in result.scalars().all():
        old_plan.is_active = False

    plan = NutritionPlan(
        user_id=user_id,
        start_date=date.today(),
        **data,
    )
    db.add(plan)
    await db.flush()
    return plan


async def update_plan(
    db: AsyncSession, plan: NutritionPlan, data: dict
) -> NutritionPlan:
    for key, value in data.items():
        if value is not None:
            setattr(plan, key, value)
    return plan


async def get_schedules(db: AsyncSession, plan_id: uuid.UUID) -> list[MealSchedule]:
    result = await db.execute(
        select(MealSchedule)
        .where(MealSchedule.plan_id == plan_id)
        .order_by(MealSchedule.meal_number)
    )
    return list(result.scalars().all())


async def create_schedule(
    db: AsyncSession, plan_id: uuid.UUID, data: dict
) -> MealSchedule:
    schedule = MealSchedule(plan_id=plan_id, **data)
    db.add(schedule)
    await db.flush()
    return schedule


# ---- n8n batch ----


async def get_pending_meal_reminders(db: AsyncSession) -> list[dict]:
    """Users with meal schedules due in the current hour."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    current_hour = now.hour

    result = await db.execute(
        select(
            User.telegram_id,
            User.first_name,
            MealSchedule.name,
            MealSchedule.target_time,
        )
        .join(NutritionPlan, NutritionPlan.user_id == User.id)
        .join(MealSchedule, MealSchedule.plan_id == NutritionPlan.id)
        .outerjoin(
            NotificationPreference,
            NotificationPreference.user_id == User.id,
        )
        .where(NutritionPlan.is_active.is_(True))
        .where(MealSchedule.target_time.isnot(None))
        .where(
            or_(
                NotificationPreference.id.is_(None),
                NotificationPreference.meal_reminders.is_(True),
            )
        )
    )
    rows = result.all()
    reminders = []
    for r in rows:
        if r.target_time and r.target_time.hour == current_hour:
            reminders.append(
                {
                    "telegram_id": r.telegram_id,
                    "first_name": r.first_name,
                    "meal_name": r.name,
                    "target_time": str(r.target_time),
                    "reminder_text": (
                        f"🍽 Es hora de tu {r.name} "
                        f"({r.target_time.strftime('%H:%M')}). "
                        "¡Cuéntame qué comes!"
                    ),
                }
            )
    return reminders


async def get_planned_meals(
    db: AsyncSession, schedule_id: uuid.UUID
) -> list[PlannedMeal]:
    result = await db.execute(
        select(PlannedMeal).where(PlannedMeal.schedule_id == schedule_id)
    )
    return list(result.scalars().all())


async def create_planned_meal(
    db: AsyncSession, schedule_id: uuid.UUID, data: dict
) -> PlannedMeal:
    meal = PlannedMeal(schedule_id=schedule_id, **data)
    db.add(meal)
    await db.flush()
    return meal


# ---- TDEE Calculation ----

_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


async def calculate_and_log_tdee(
    db: AsyncSession,
    user_id: uuid.UUID,
    trigger: str = "manual",
) -> dict | None:
    """Calculate TDEE using Mifflin-St Jeor and log it.

    Returns {"bmr": float, "tdee": float, "multiplier": float} or None if missing data.
    """
    from app.modules.users.service import get_user
    from app.modules.nutrition.models import TDEELog

    user = await get_user(db, user_id)
    if not user or not user.weight_kg or not user.height_cm or not user.age or not user.gender:
        return None

    # Mifflin-St Jeor
    if user.gender.lower() in ("m", "male", "masculino", "hombre"):
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + 5
    else:
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age - 161

    multiplier = _ACTIVITY_MULTIPLIERS.get(
        (user.activity_level or "moderate").lower(), 1.55
    )
    tdee = round(bmr * multiplier)
    bmr = round(bmr)

    entry = TDEELog(
        user_id=user_id,
        tdee_kcal=tdee,
        bmr_kcal=bmr,
        activity_multiplier=multiplier,
        trigger=trigger,
    )
    db.add(entry)
    await db.flush()

    return {"bmr": bmr, "tdee": tdee, "multiplier": multiplier}
