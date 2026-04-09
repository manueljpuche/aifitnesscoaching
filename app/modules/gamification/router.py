"""Gamification router — streaks and achievements."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.schemas import UserAchievementResponse, UserStreakResponse
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.gamification.service import get_achievements, get_streak_risk_batch, get_streaks

router = APIRouter()


@router.get("/streaks", response_model=list[UserStreakResponse])
async def list_streaks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_streaks(db, user.id)


@router.get("/achievements", response_model=list[UserAchievementResponse])
async def list_achievements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_achievements(db, user.id)


# ---- n8n batch endpoints ----


@router.get("/streak-risk-batch", dependencies=[Depends(verify_n8n_secret)])
async def streak_risk_batch(db: AsyncSession = Depends(get_db)):
    return await get_streak_risk_batch(db)
