"""Versioning service — plan snapshot and restore."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.versioning.models import PlanVersion


async def save_version(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_type: str,
    plan_id: uuid.UUID,
    snapshot: dict,
    change_reason: str | None = None,
) -> PlanVersion:
    version = PlanVersion(
        user_id=user_id,
        plan_type=plan_type,
        plan_id=plan_id,
        snapshot=snapshot,
        change_reason=change_reason,
    )
    db.add(version)
    await db.flush()
    return version


async def get_versions(
    db: AsyncSession, user_id: uuid.UUID, plan_type: str | None = None, limit: int = 10
) -> list[PlanVersion]:
    query = select(PlanVersion).where(PlanVersion.user_id == user_id)
    if plan_type:
        query = query.where(PlanVersion.plan_type == plan_type)
    result = await db.execute(
        query.order_by(PlanVersion.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_version(
    db: AsyncSession, version_id: uuid.UUID, user_id: uuid.UUID
) -> PlanVersion | None:
    result = await db.execute(
        select(PlanVersion).where(
            PlanVersion.id == version_id,
            PlanVersion.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
