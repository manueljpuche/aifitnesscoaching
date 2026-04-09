"""Check-ins router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.checkins.schemas import WeeklyCheckinCreate, WeeklyCheckinResponse
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.checkins.service import create_checkin, get_checkins, get_weekly_checkin_batch

router = APIRouter()


@router.post("/", response_model=WeeklyCheckinResponse, status_code=201)
async def create(
    body: WeeklyCheckinCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_checkin(db, user.id, body.model_dump())


@router.get("/", response_model=list[WeeklyCheckinResponse])
async def list_all(
    limit: int = Query(8, ge=1, le=52),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_checkins(db, user.id, limit)


# ---- n8n batch endpoints ----


@router.post("/weekly-batch", dependencies=[Depends(verify_n8n_secret)])
async def weekly_batch(db: AsyncSession = Depends(get_db)):
    return await get_weekly_checkin_batch(db)
