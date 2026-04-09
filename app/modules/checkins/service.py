"""Check-ins service — weekly check-in management."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.checkins.models import WeeklyCheckin
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import User


async def create_checkin(db: AsyncSession, user_id: uuid.UUID, data: dict) -> WeeklyCheckin:
    checkin = WeeklyCheckin(user_id=user_id, **data)
    db.add(checkin)
    await db.flush()
    return checkin


async def get_checkins(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 8
) -> list[WeeklyCheckin]:
    result = await db.execute(
        select(WeeklyCheckin)
        .where(WeeklyCheckin.user_id == user_id)
        .order_by(WeeklyCheckin.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_checkin(db: AsyncSession, user_id: uuid.UUID) -> WeeklyCheckin | None:
    result = await db.execute(
        select(WeeklyCheckin)
        .where(WeeklyCheckin.user_id == user_id)
        .order_by(WeeklyCheckin.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ---- n8n batch ----


async def get_weekly_checkin_batch(db: AsyncSession) -> list[dict]:
    """Users who should receive a weekly check-in prompt (Sunday evening)."""
    this_week_start = date.today() - timedelta(days=date.today().weekday())
    already_checked = (
        select(WeeklyCheckin.user_id)
        .where(WeeklyCheckin.week_start >= this_week_start)
        .subquery()
    )
    result = await db.execute(
        select(User.telegram_id, User.first_name)
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(User.id.notin_(select(already_checked.c.user_id)))
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
            "reminder_text": (
                f"📊 ¡Check-in semanal{', ' + r.first_name if r.first_name else ''}!\n\n"
                "¿Cómo fue tu semana? Cuéntame:\n"
                "• Peso actual\n• Nivel de energía (1-5)\n• Estado de ánimo (1-5)\n"
                "• ¿Seguiste la dieta? ¿El entrenamiento?"
            ),
        }
        for r in rows
    ]
