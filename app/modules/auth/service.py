"""Auth service — Telegram login and JWT management."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import AuthSession
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import User


async def telegram_login(
    db: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> tuple[User, str, datetime]:
    """Authenticate via Telegram — create or get user, return JWT."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            locale=language_code[:2] if language_code else "es",
        )
        db.add(user)
        await db.flush()

        # Create default notification preferences
        prefs = NotificationPreference(user_id=user.id)
        db.add(prefs)
    else:
        # Update profile fields from Telegram
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name

    token, expires = create_access_token(str(user.id))

    session = AuthSession(
        user_id=user.id,
        access_token=token,
        expires_at=expires,
    )
    db.add(session)

    return user, token, expires
