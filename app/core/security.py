from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.users.models import User

logger = structlog.stdlib.get_logger()

_bearer = HTTPBearer()

_TELEGRAM_AUTH_MAX_AGE_SECONDS = 86400  # 24h


def verify_telegram_auth(data: dict) -> bool:
    """Validate Telegram login data via HMAC-SHA256.

    https://core.telegram.org/widgets/login#checking-authorization
    """
    bot_token = settings.telegram_bot_token
    if not bot_token:
        # If no bot token configured, skip validation (dev mode)
        logger.warning("telegram_auth_skip", reason="no bot token configured")
        return True

    received_hash = data.get("hash")
    if not received_hash:
        return False

    # Check auth_date freshness
    auth_date = data.get("auth_date")
    if auth_date:
        age = int(datetime.now(timezone.utc).timestamp()) - int(auth_date)
        if age > _TELEGRAM_AUTH_MAX_AGE_SECONDS:
            return False

    # Build check string: sorted key=value pairs (excluding hash)
    check_pairs = sorted(
        f"{k}={v}" for k, v in data.items() if k != "hash" and v is not None
    )
    check_string = "\n".join(check_pairs)

    # secret_key = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key, check_string.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, received_hash)


async def verify_n8n_secret(
    x_n8n_secret: str = Header(alias="X-N8N-Secret"),
) -> None:
    """Validate the shared secret sent by n8n for internal batch endpoints."""
    if not hmac.compare_digest(x_n8n_secret, settings.n8n_internal_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal secret")


def create_access_token(user_id: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {"sub": user_id, "exp": expires}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = verify_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
