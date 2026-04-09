"""Auth router — Telegram login endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_telegram_auth
from app.modules.auth.schemas import TelegramLoginRequest, TokenResponse
from app.modules.auth.service import telegram_login

router = APIRouter()


@router.post("/telegram-login", response_model=TokenResponse)
async def login_telegram(body: TelegramLoginRequest, db: AsyncSession = Depends(get_db)):
    # Validate Telegram HMAC signature
    auth_data = {
        "id": body.telegram_id,
        "username": body.username,
        "first_name": body.first_name,
        "last_name": body.last_name,
        "auth_date": body.auth_date,
        "hash": body.hash,
    }
    if not verify_telegram_auth(auth_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data",
        )

    user, token, expires = await telegram_login(
        db=db,
        telegram_id=body.telegram_id,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
        language_code=body.language_code,
    )
    return TokenResponse(access_token=token, expires_at=expires, user_id=user.id)
