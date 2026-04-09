"""Wellness service — sleep, alcohol, cycle, symptoms, user status, mood, steps."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wellness.models import (
    AlcoholLog,
    MenstrualCycleLog,
    MoodLog,
    SleepLog,
    StepLog,
    SymptomLog,
    UserStatus,
)


# ---- Sleep ----


async def log_sleep(db: AsyncSession, user_id: uuid.UUID, data: dict) -> SleepLog:
    entry = SleepLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_sleep_history(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 14
) -> list[SleepLog]:
    result = await db.execute(
        select(SleepLog)
        .where(SleepLog.user_id == user_id)
        .order_by(SleepLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- Alcohol ----


async def log_alcohol(db: AsyncSession, user_id: uuid.UUID, data: dict) -> AlcoholLog:
    entry = AlcoholLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


# ---- Menstrual Cycle ----


async def log_cycle(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> MenstrualCycleLog:
    entry = MenstrualCycleLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_cycle_history(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 6
) -> list[MenstrualCycleLog]:
    result = await db.execute(
        select(MenstrualCycleLog)
        .where(MenstrualCycleLog.user_id == user_id)
        .order_by(MenstrualCycleLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- Symptoms ----


async def log_symptom(db: AsyncSession, user_id: uuid.UUID, data: dict) -> SymptomLog:
    entry = SymptomLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_symptom_history(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[SymptomLog]:
    result = await db.execute(
        select(SymptomLog)
        .where(SymptomLog.user_id == user_id)
        .order_by(SymptomLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- User Status ----


async def set_status(db: AsyncSession, user_id: uuid.UUID, data: dict) -> UserStatus:
    # End the current active status before creating a new one
    current = await get_current_status(db, user_id)
    if current and current.status != data.get("status"):
        from datetime import datetime, timezone
        current.ends_at = datetime.now(timezone.utc)

    entry = UserStatus(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_current_status(db: AsyncSession, user_id: uuid.UUID) -> UserStatus | None:
    result = await db.execute(
        select(UserStatus)
        .where(UserStatus.user_id == user_id)
        .order_by(UserStatus.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ---- Mood ----


async def log_mood(db: AsyncSession, user_id: uuid.UUID, data: dict) -> MoodLog:
    entry = MoodLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_mood_history(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 14
) -> list[MoodLog]:
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == user_id)
        .order_by(MoodLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- Steps ----


async def log_steps(db: AsyncSession, user_id: uuid.UUID, data: dict) -> StepLog:
    entry = StepLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_steps_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    from datetime import date, datetime, timezone

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    result = await db.execute(
        select(StepLog)
        .where(StepLog.user_id == user_id, StepLog.created_at >= today_start)
    )
    return sum(s.steps for s in result.scalars().all())
