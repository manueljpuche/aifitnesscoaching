"""Notifications service — user notification preferences + n8n batch queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.body.models import ProgressPhoto
from app.modules.notifications.models import NotificationPreference
from app.modules.nutrition.models import MealTimingRule, NutritionPlan
from app.modules.tracking.models import WaterLog
from app.modules.users.models import User
from app.modules.wellness.models import SleepLog, SymptomLog, UserStatus
from app.modules.workouts.models import WorkoutPlan


async def get_preferences(db: AsyncSession, user_id: uuid.UUID) -> NotificationPreference | None:
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> NotificationPreference:
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        prefs = NotificationPreference(user_id=user_id, **data)
        db.add(prefs)
    else:
        for key, value in data.items():
            if value is not None:
                setattr(prefs, key, value)

    await db.flush()
    return prefs


# ----- n8n batch functions -----


async def get_daily_plan_batch(db: AsyncSession) -> list[dict]:
    """Users with active plans who should receive their daily plan summary."""
    result = await db.execute(
        select(
            User.telegram_id, User.first_name,
            NutritionPlan.calories_target,
            WorkoutPlan.name.label("workout_name"),
        )
        .outerjoin(NutritionPlan, and_(
            NutritionPlan.user_id == User.id,
            NutritionPlan.is_active.is_(True),
        ))
        .outerjoin(WorkoutPlan, and_(
            WorkoutPlan.user_id == User.id,
            WorkoutPlan.is_active.is_(True),
        ))
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(or_(NutritionPlan.id.isnot(None), WorkoutPlan.id.isnot(None)))
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "calories_target": r.calories_target,
            "workout_name": r.workout_name,
            "reminder_text": (
                "🌅 Buenos días"
                + (f", {r.first_name}" if r.first_name else "")
                + "!\n\n"
                + (f"🍽 Objetivo: {r.calories_target} kcal\n"
                   if r.calories_target else "")
                + (f"🏋️ {r.workout_name}\n"
                   if r.workout_name else "")
                + "\nCuéntame qué desayunas hoy."
            ),
        }
        for r in rows
    ]


async def get_morning_sleep_batch(db: AsyncSession) -> list[dict]:
    """Users who haven't logged sleep today and have notifications enabled."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    logged = (
        select(SleepLog.user_id)
        .where(SleepLog.created_at >= today_start)
        .subquery()
    )
    result = await db.execute(
        select(User.telegram_id, User.first_name)
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(User.id.notin_(select(logged.c.user_id)))
        .where(or_(
            NotificationPreference.id.is_(None),
            NotificationPreference.weekly_checkin.is_(True),
        ))
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "reminder_text": "😴 ¿Cómo dormiste anoche? Dime las horas y calidad (1-5).",
        }
        for r in rows
    ]


async def get_workout_nutrition_batch(db: AsyncSession) -> list[dict]:
    """Users with workout timing rules for pre/post nutrition."""
    result = await db.execute(
        select(
            User.telegram_id, User.first_name,
            MealTimingRule.workout_time,
            MealTimingRule.pre_workout_window_min,
        )
        .join(MealTimingRule, MealTimingRule.user_id == User.id)
        .outerjoin(
            NotificationPreference,
            NotificationPreference.user_id == User.id,
        )
        .where(MealTimingRule.workout_time.isnot(None))
        .where(or_(
            NotificationPreference.id.is_(None),
            NotificationPreference.workout_reminders.is_(True),
        ))
    )
    rows = result.all()
    reminders = []
    for r in rows:
        if r.workout_time:
            reminders.append({
                "telegram_id": r.telegram_id,
                "first_name": r.first_name,
                "workout_time": str(r.workout_time),
                "reminder_text": (
                    f"🥗 Tu entrenamiento es a las {r.workout_time.strftime('%H:%M')}. "
                    f"Recuerda comer algo {r.pre_workout_window_min or 60} min antes."
                ),
            })
    return reminders


async def get_hydration_batch(db: AsyncSession) -> list[dict]:
    """Users below their daily water goal."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    water_today = (
        select(WaterLog.user_id, func.sum(WaterLog.amount_ml).label("total_ml"))
        .where(WaterLog.created_at >= today_start)
        .group_by(WaterLog.user_id)
        .subquery()
    )
    result = await db.execute(
        select(User.telegram_id, User.first_name, User.water_goal_ml, water_today.c.total_ml)
        .outerjoin(water_today, water_today.c.user_id == User.id)
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(User.water_goal_ml.isnot(None))
        .where(User.water_goal_ml > 0)
        .where(or_(
            water_today.c.total_ml.is_(None),
            water_today.c.total_ml < User.water_goal_ml,
        ))
        .where(or_(
            NotificationPreference.id.is_(None),
            NotificationPreference.water_reminders.is_(True),
        ))
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "water_goal_ml": r.water_goal_ml,
            "current_ml": float(r.total_ml or 0),
            "reminder_text": (
                f"💧 Llevas {int(r.total_ml or 0)} ml de {int(r.water_goal_ml)} ml. "
                "¡No olvides hidratarte!"
            ),
        }
        for r in rows
    ]


async def get_progress_photo_batch(db: AsyncSession) -> list[dict]:
    """Users whose last progress photo is > 28 days ago (or never)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=28)
    latest_photo = (
        select(ProgressPhoto.user_id, func.max(ProgressPhoto.created_at).label("last_photo"))
        .group_by(ProgressPhoto.user_id)
        .subquery()
    )
    result = await db.execute(
        select(User.telegram_id, User.first_name)
        .outerjoin(latest_photo, latest_photo.c.user_id == User.id)
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(or_(
            latest_photo.c.last_photo.is_(None),
            latest_photo.c.last_photo < cutoff,
        ))
        .where(or_(
            NotificationPreference.id.is_(None),
            NotificationPreference.progress_photos.is_(True),
        ))
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "reminder_text": (
                "\U0001f4f8 \u00a1Es hora de tu foto de progreso "
                "mensual! Env\u00edame una foto."
            ),
        }
        for r in rows
    ]


async def get_symptom_followup_batch(db: AsyncSession) -> list[dict]:
    """Symptom logs from ~3h ago that haven't been followed up."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=3, minutes=30)
    window_end = now - timedelta(hours=2, minutes=30)
    result = await db.execute(
        select(User.telegram_id, User.first_name, SymptomLog.id, SymptomLog.symptom)
        .join(User, User.id == SymptomLog.user_id)
        .where(SymptomLog.followup_sent.is_(False))
        .where(SymptomLog.resolved.is_(False))
        .where(SymptomLog.created_at.between(window_start, window_end))
    )
    rows = result.all()
    items = []
    for r in rows:
        items.append({
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "symptom_log_id": str(r.id),
            "followup_text": f"🩺 Hace unas horas reportaste: {r.symptom}. ¿Cómo te sientes ahora?",
        })
    # Mark followup_sent
    for r in rows:
        await db.execute(
            SymptomLog.__table__.update().where(SymptomLog.id == r.id).values(followup_sent=True)
        )
    await db.commit()
    return items


async def get_recovery_followup_batch(db: AsyncSession) -> list[dict]:
    """Users with active sick/injured status not followed up in 3+ days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    result = await db.execute(
        select(
            User.telegram_id, User.first_name,
            User.id.label("user_id"),
            UserStatus.status, UserStatus.reason,
        )
        .join(User, User.id == UserStatus.user_id)
        .where(UserStatus.status.in_(["sick", "injured"]))
        .where(or_(UserStatus.ends_at.is_(None), UserStatus.ends_at > datetime.now(timezone.utc)))
        .where(UserStatus.started_at <= cutoff)
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "user_id": str(r.user_id),
            "followup_text": (
                f"🤒 Hola{', ' + r.first_name if r.first_name else ''}. "
                f"Sigues en estado {'enfermo' if r.status == 'sick' else 'lesionado'}. "
                "¿Cómo te encuentras hoy?"
            ),
        }
        for r in rows
    ]
