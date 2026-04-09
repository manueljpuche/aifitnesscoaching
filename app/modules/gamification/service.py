"""Gamification service — streaks and achievements."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.models import UserAchievement, UserStreak
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import User

STREAK_MILESTONES = [3, 7, 14, 30, 60, 90]


async def update_streak(
    db: AsyncSession, user_id: uuid.UUID, streak_type: str
) -> UserStreak:
    result = await db.execute(
        select(UserStreak).where(
            UserStreak.user_id == user_id,
            UserStreak.streak_type == streak_type,
        )
    )
    streak = result.scalar_one_or_none()

    today = date.today()

    if streak is None:
        streak = UserStreak(
            user_id=user_id,
            streak_type=streak_type,
            current_streak=1,
            best_streak=1,
            last_activity_date=today,
        )
        db.add(streak)
        await db.flush()

        # Check for first-time achievement
        await _check_streak_milestone(db, user_id, streak_type, 1)
        return streak

    if streak.last_activity_date == today:
        return streak  # Already counted today

    if streak.last_activity_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.last_activity_date = today
    if streak.current_streak > streak.best_streak:
        streak.best_streak = streak.current_streak

    await _check_streak_milestone(db, user_id, streak_type, streak.current_streak)

    return streak


async def _check_streak_milestone(
    db: AsyncSession, user_id: uuid.UUID, streak_type: str, count: int
) -> UserAchievement | None:
    if count not in STREAK_MILESTONES:
        return None

    achievement_type = f"streak_{streak_type}_{count}d"
    # Check if already earned
    result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_type == achievement_type,
        )
    )
    if result.scalar_one_or_none():
        return None

    achievement = UserAchievement(
        user_id=user_id,
        achievement_type=achievement_type,
        title=f"🔥 {count} días en racha de {streak_type}",
        description=f"Has mantenido tu racha de {streak_type} durante {count} días consecutivos.",
    )
    db.add(achievement)
    await db.flush()
    return achievement


async def get_streaks(db: AsyncSession, user_id: uuid.UUID) -> list[UserStreak]:
    result = await db.execute(select(UserStreak).where(UserStreak.user_id == user_id))
    return list(result.scalars().all())


async def get_achievements(
    db: AsyncSession, user_id: uuid.UUID
) -> list[UserAchievement]:
    result = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .order_by(UserAchievement.earned_at.desc())
    )
    return list(result.scalars().all())


async def add_achievement(
    db: AsyncSession,
    user_id: uuid.UUID,
    achievement_type: str,
    title: str,
    description: str | None = None,
) -> UserAchievement:
    achievement = UserAchievement(
        user_id=user_id,
        achievement_type=achievement_type,
        title=title,
        description=description,
    )
    db.add(achievement)
    await db.flush()
    return achievement


# ---- n8n batch ----


async def get_streak_risk_batch(db: AsyncSession) -> list[dict]:
    """Users whose streaks will break tomorrow if they don't log activity today."""
    from datetime import date as date_type, timedelta
    from sqlalchemy import or_

    today = date_type.today()
    yesterday = today - timedelta(days=1)

    result = await db.execute(
        select(
            User.telegram_id,
            User.first_name,
            UserStreak.streak_type,
            UserStreak.current_streak,
        )
        .join(UserStreak, UserStreak.user_id == User.id)
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(UserStreak.current_streak > 0)
        .where(UserStreak.last_activity_date == yesterday)
        .where(
            or_(
                NotificationPreference.id.is_(None),
                NotificationPreference.streak_alerts.is_(True),
            )
        )
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "streak_type": r.streak_type,
            "current_streak": r.current_streak,
            "reminder_text": (
                f"🔥 ¡Tu racha de {r.streak_type} de {r.current_streak} días está en riesgo!\n"
                "Registra tu actividad hoy para no perderla."
            ),
        }
        for r in rows
    ]
