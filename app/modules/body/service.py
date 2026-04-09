"""Body service — measurements and progress photos."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.body.models import BodyMeasurement, ProgressPhoto


async def log_measurement(db: AsyncSession, user_id: uuid.UUID, data: dict) -> BodyMeasurement:
    # Auto-compute lean/fat mass if body_fat_pct and user weight available
    entry = BodyMeasurement(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


async def get_measurements(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 10
) -> list[BodyMeasurement]:
    result = await db.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(BodyMeasurement.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def add_progress_photo(
    db: AsyncSession, user_id: uuid.UUID, image_url: str, notes: str | None = None
) -> ProgressPhoto:
    photo = ProgressPhoto(user_id=user_id, image_url=image_url, notes=notes)
    db.add(photo)
    await db.flush()
    return photo


async def get_progress_photos(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[ProgressPhoto]:
    result = await db.execute(
        select(ProgressPhoto)
        .where(ProgressPhoto.user_id == user_id)
        .order_by(ProgressPhoto.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
