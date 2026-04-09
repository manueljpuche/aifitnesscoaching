"""Users service — profile CRUD + n8n batch."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, UserPreference


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user: User, data: dict) -> User:
    for key, value in data.items():
        if value is not None:
            setattr(user, key, value)
    return user


async def get_preferences(db: AsyncSession, user_id: uuid.UUID) -> list[UserPreference]:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return list(result.scalars().all())


async def add_preference(db: AsyncSession, user_id: uuid.UUID, data: dict) -> UserPreference:
    pref = UserPreference(user_id=user_id, **data)
    db.add(pref)
    await db.flush()
    return pref


async def delete_preference(db: AsyncSession, pref_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(UserPreference).where(
            UserPreference.id == pref_id,
            UserPreference.user_id == user_id,
        )
    )
    pref = result.scalar_one_or_none()
    if pref:
        await db.delete(pref)
        return True
    return False


# ---- n8n batch ----


async def expire_temporary_preferences(db: AsyncSession) -> dict:
    """Remove expired temporary preferences and return affected users."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserPreference, User.telegram_id, User.first_name)
        .join(User, User.id == UserPreference.user_id)
        .where(UserPreference.is_temporary.is_(True))
        .where(UserPreference.expires_at.isnot(None))
        .where(UserPreference.expires_at <= now)
    )
    rows = result.all()

    affected_users = []
    for pref, telegram_id, first_name in rows:
        affected_users.append({
            "telegram_id": telegram_id,
            "first_name": first_name,
            "restriction_name": f"{pref.category}: {pref.value}",
        })
        await db.delete(pref)

    await db.commit()
    return {"expired_count": len(affected_users), "users": affected_users}
