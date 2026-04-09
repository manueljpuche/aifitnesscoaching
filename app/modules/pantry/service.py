"""Pantry service — inventory management and scans."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pantry.models import PantryItem, PantryScan


async def get_pantry_items(db: AsyncSession, user_id: uuid.UUID) -> list[PantryItem]:
    result = await db.execute(
        select(PantryItem)
        .where(PantryItem.user_id == user_id)
        .order_by(PantryItem.food_name)
    )
    return list(result.scalars().all())


async def add_pantry_item(db: AsyncSession, user_id: uuid.UUID, data: dict) -> PantryItem:
    # Check if item already exists, increment quantity
    result = await db.execute(
        select(PantryItem).where(
            PantryItem.user_id == user_id,
            PantryItem.food_name == data["food_name"],
        )
    )
    existing = result.scalar_one_or_none()

    if existing and data.get("quantity"):
        existing.quantity = (existing.quantity or 0) + data["quantity"]
        existing.unit = data.get("unit") or existing.unit
        return existing

    item = PantryItem(user_id=user_id, **data)
    db.add(item)
    await db.flush()
    return item


async def update_pantry_item(
    db: AsyncSession, item_id: uuid.UUID, user_id: uuid.UUID, data: dict
) -> PantryItem | None:
    result = await db.execute(
        select(PantryItem).where(
            PantryItem.id == item_id,
            PantryItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return None

    for key, value in data.items():
        if value is not None:
            setattr(item, key, value)
    return item


async def remove_pantry_item(db: AsyncSession, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(PantryItem).where(
            PantryItem.id == item_id,
            PantryItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        return True
    return False


async def create_scan(db: AsyncSession, user_id: uuid.UUID, data: dict) -> PantryScan:
    scan = PantryScan(user_id=user_id, **data)
    db.add(scan)
    await db.flush()
    return scan
