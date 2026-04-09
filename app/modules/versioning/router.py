"""Versioning router — plan history."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.versioning.schemas import PlanVersionResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.versioning.service import get_version, get_versions

router = APIRouter()


@router.get("/", response_model=list[PlanVersionResponse])
async def list_versions(
    plan_type: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_versions(db, user.id, plan_type, limit)


@router.get("/{version_id}", response_model=PlanVersionResponse)
async def get_one(
    version_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version = await get_version(db, version_id, user.id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version
