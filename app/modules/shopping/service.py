"""Shopping service — list generation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shopping.models import ShoppingList


async def create_shopping_list(db: AsyncSession, user_id: uuid.UUID, data: dict) -> ShoppingList:
    shopping = ShoppingList(user_id=user_id, **data)
    db.add(shopping)
    await db.flush()
    return shopping


async def get_shopping_lists(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 4
) -> list[ShoppingList]:
    result = await db.execute(
        select(ShoppingList)
        .where(ShoppingList.user_id == user_id)
        .order_by(ShoppingList.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_shopping_list(
    db: AsyncSession, list_id: uuid.UUID, user_id: uuid.UUID
) -> ShoppingList | None:
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
