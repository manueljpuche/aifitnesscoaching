"""Users router — profile and preferences."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.users.schemas import PreferenceCreate, PreferenceResponse, UserResponse, UserUpdate
from app.modules.users.service import (
    add_preference,
    delete_preference,
    expire_temporary_preferences,
    get_preferences,
    update_user,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await update_user(db, user, body.model_dump(exclude_unset=True))
    return updated


@router.get("/me/preferences", response_model=list[PreferenceResponse])
async def list_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_preferences(db, user.id)


@router.post("/me/preferences", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    body: PreferenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await add_preference(db, user.id, body.model_dump())


@router.delete("/me/preferences/{pref_id}", status_code=204)
async def remove_preference(
    pref_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_preference(db, pref_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preference not found")


# ---- n8n batch endpoints ----


@router.post("/expire-temporary", dependencies=[Depends(verify_n8n_secret)])
async def expire_temporary(db: AsyncSession = Depends(get_db)):
    return await expire_temporary_preferences(db)
