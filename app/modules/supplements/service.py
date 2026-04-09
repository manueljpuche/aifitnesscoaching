"""Supplements service — catalogue, user supplements, logging."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplements.models import Supplement, SupplementLog, UserSupplement
from app.modules.users.models import User
from app.modules.notifications.models import NotificationPreference


async def list_supplements(db: AsyncSession) -> list[Supplement]:
    result = await db.execute(select(Supplement).order_by(Supplement.name))
    return list(result.scalars().all())


async def create_supplement(db: AsyncSession, data: dict) -> Supplement:
    supp = Supplement(**data)
    db.add(supp)
    await db.flush()
    return supp


async def get_user_supplements(db: AsyncSession, user_id: uuid.UUID) -> list[UserSupplement]:
    result = await db.execute(
        select(UserSupplement).where(UserSupplement.user_id == user_id)
    )
    return list(result.scalars().all())


async def add_user_supplement(db: AsyncSession, user_id: uuid.UUID, data: dict) -> UserSupplement:
    entry = UserSupplement(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def remove_user_supplement(
    db: AsyncSession, supp_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(UserSupplement).where(
            UserSupplement.id == supp_id,
            UserSupplement.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry:
        await db.delete(entry)
        return True
    return False


async def log_supplement(
    db: AsyncSession, user_id: uuid.UUID, supplement_id: uuid.UUID
) -> SupplementLog:
    entry = SupplementLog(user_id=user_id, supplement_id=supplement_id)
    db.add(entry)
    await db.flush()
    return entry


# ---- n8n batch ----


async def get_pending_supplement_reminders(db: AsyncSession) -> list[dict]:
    """Users with supplement reminders due now."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    current_hour = now.hour
    current_minute = now.minute

    result = await db.execute(
        select(
            User.telegram_id, User.first_name,
            Supplement.name, UserSupplement.dose,
            UserSupplement.reminder_time,
        )
        .join(UserSupplement, UserSupplement.user_id == User.id)
        .join(Supplement, Supplement.id == UserSupplement.supplement_id)
        .outerjoin(
            NotificationPreference,
            NotificationPreference.user_id == User.id,
        )
        .where(UserSupplement.reminder_enabled.is_(True))
        .where(UserSupplement.reminder_time.isnot(None))
        .where(or_(
            NotificationPreference.id.is_(None),
            NotificationPreference.supplement_reminders.is_(True),
        ))
    )
    rows = result.all()
    reminders = []
    for r in rows:
        if (
            r.reminder_time
            and r.reminder_time.hour == current_hour
            and abs(r.reminder_time.minute - current_minute) < 15
        ):
            dose_part = f" ({r.dose})" if r.dose else ""
            reminders.append({
                "telegram_id": r.telegram_id,
                "first_name": r.first_name,
                "supplement_name": r.name,
                "dose": r.dose,
                "reminder_text": (
                    f"💊 Recuerda tomar tu {r.name}"
                    f"{dose_part}."
                ),
            })
    return reminders
