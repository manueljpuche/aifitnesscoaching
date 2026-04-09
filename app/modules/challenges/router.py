"""Challenges router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.challenges.schemas import (
    ChallengeResponse,
    UserChallengeCreate,
    UserChallengeResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.challenges.service import (
    get_daily_progress_batch,
    get_user_challenges,
    list_challenges,
    start_challenge,
)

router = APIRouter()


@router.get("/", response_model=list[ChallengeResponse])
async def list_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_challenges(db, user.locale)


@router.post("/start", response_model=UserChallengeResponse, status_code=201)
async def start(
    body: UserChallengeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await start_challenge(db, user.id, body.challenge_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/mine", response_model=list[UserChallengeResponse])
async def my_challenges(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_challenges(db, user.id)


# ---- n8n batch endpoints ----


@router.post("/daily-progress-batch", dependencies=[Depends(verify_n8n_secret)])
async def daily_progress_batch(db: AsyncSession = Depends(get_db)):
    return await get_daily_progress_batch(db)
