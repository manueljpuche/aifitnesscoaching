"""Body router — measurements and progress photos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.body.schemas import BodyMeasurementCreate, BodyMeasurementResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.body.service import (
    get_measurements,
    get_progress_photos,
    log_measurement,
)

router = APIRouter()


@router.post("/measurements", response_model=BodyMeasurementResponse, status_code=201)
async def create_measurement(
    body: BodyMeasurementCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_measurement(db, user.id, body.model_dump(exclude_unset=True))


@router.get("/measurements", response_model=list[BodyMeasurementResponse])
async def list_measurements(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_measurements(db, user.id, limit)


@router.get("/photos")
async def list_photos(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    photos = await get_progress_photos(db, user.id, limit)
    return [
        {
            "id": str(p.id),
            "image_url": p.image_url,
            "notes": p.notes,
            "created_at": p.created_at,
        }
        for p in photos
    ]
