"""Challenges service — challenges catalogue and user participation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.challenges.models import Challenge, UserChallenge
from app.modules.users.models import User


async def list_challenges(db: AsyncSession, locale: str = "es") -> list[Challenge]:
    result = await db.execute(
        select(Challenge).where(Challenge.locale == locale).order_by(Challenge.title)
    )
    return list(result.scalars().all())


async def start_challenge(
    db: AsyncSession, user_id: uuid.UUID, challenge_id: uuid.UUID
) -> UserChallenge:
    # Get challenge details
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise ValueError("Challenge not found")

    now = datetime.now(timezone.utc)
    entry = UserChallenge(
        user_id=user_id,
        challenge_id=challenge_id,
        started_at=now,
        ends_at=now + timedelta(days=challenge.duration_days),
        progress={},
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_user_challenges(
    db: AsyncSession, user_id: uuid.UUID
) -> list[UserChallenge]:
    result = await db.execute(
        select(UserChallenge)
        .where(UserChallenge.user_id == user_id)
        .order_by(UserChallenge.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active_challenge(
    db: AsyncSession, user_id: uuid.UUID
) -> UserChallenge | None:
    result = await db.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == user_id,
            UserChallenge.completed.is_(False),
            UserChallenge.ends_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


# ---- n8n batch ----


async def get_daily_progress_batch(db: AsyncSession) -> list[dict]:
    """Active challenges: compute elapsed days and send progress update."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(
            User.telegram_id,
            User.first_name,
            Challenge.title,
            UserChallenge.started_at,
            UserChallenge.ends_at,
            Challenge.duration_days,
        )
        .join(UserChallenge, UserChallenge.user_id == User.id)
        .join(Challenge, Challenge.id == UserChallenge.challenge_id)
        .where(UserChallenge.completed.is_(False))
        .where(UserChallenge.ends_at > now)
    )
    rows = result.all()
    items = []
    for r in rows:
        elapsed = (now - r.started_at).days
        remaining = r.duration_days - elapsed
        pct = min(100, int((elapsed / r.duration_days) * 100))
        items.append(
            {
                "telegram_id": r.telegram_id,
                "first_name": r.first_name,
                "challenge_title": r.title,
                "elapsed_days": elapsed,
                "remaining_days": max(0, remaining),
                "progress_pct": pct,
                "reminder_text": (
                    f"🏆 Reto «{r.title}» — Día {elapsed}/{r.duration_days} ({pct}%)\n"
                    f"{'¡Quedan ' + str(remaining) + ' días!' if remaining > 0 else '¡Último día!'}"
                ),
            }
        )
    return items
