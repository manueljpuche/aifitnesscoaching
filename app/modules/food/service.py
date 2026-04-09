"""Food service — food database and barcode lookup."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.food.models import BarcodeScan, Food


async def search_foods(db: AsyncSession, query: str, limit: int = 20) -> list[Food]:
    result = await db.execute(
        select(Food).where(Food.name.ilike(f"%{query}%")).limit(limit)
    )
    return list(result.scalars().all())


async def get_food_by_barcode(db: AsyncSession, barcode: str) -> Food | None:
    result = await db.execute(select(Food).where(Food.barcode == barcode))
    return result.scalar_one_or_none()


async def create_food(db: AsyncSession, data: dict) -> Food:
    food = Food(**data)
    db.add(food)
    await db.flush()
    return food


async def log_barcode_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    barcode: str,
    food_id: uuid.UUID | None,
    found: bool,
    raw_result: dict | None,
) -> BarcodeScan:
    scan = BarcodeScan(
        user_id=user_id,
        barcode=barcode,
        food_id=food_id,
        found=found,
        raw_result=raw_result,
    )
    db.add(scan)
    await db.flush()
    return scan
