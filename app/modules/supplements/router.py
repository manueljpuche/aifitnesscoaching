"""Supplements router — catalogue, user supplements, logging."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplements.schemas import (
    SupplementCreate,
    SupplementLogCreate,
    SupplementLogResponse,
    SupplementResponse,
    UserSupplementCreate,
    UserSupplementResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.supplements.service import (
    add_user_supplement,
    create_supplement,
    get_pending_supplement_reminders,
    get_user_supplements,
    list_supplements,
    log_supplement,
    remove_user_supplement,
)

router = APIRouter()


@router.get("/catalogue", response_model=list[SupplementResponse])
async def catalogue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_supplements(db)


@router.post("/catalogue", response_model=SupplementResponse, status_code=201)
async def create(
    body: SupplementCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_supplement(db, body.model_dump())


@router.get("/mine", response_model=list[UserSupplementResponse])
async def my_supplements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_supplements(db, user.id)


@router.post("/mine", response_model=UserSupplementResponse, status_code=201)
async def add_mine(
    body: UserSupplementCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await add_user_supplement(db, user.id, body.model_dump())


@router.delete("/mine/{supp_id}", status_code=204)
async def remove_mine(
    supp_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await remove_user_supplement(db, supp_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Supplement not found")


@router.post("/log", response_model=SupplementLogResponse, status_code=201)
async def log(
    body: SupplementLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_supplement(db, user.id, body.supplement_id)


# ---- n8n batch endpoints ----


@router.get("/pending-reminders", dependencies=[Depends(verify_n8n_secret)])
async def pending_reminders(db: AsyncSession = Depends(get_db)):
    return await get_pending_supplement_reminders(db)
