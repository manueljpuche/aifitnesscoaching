"""Pantry router — inventory and scans."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pantry.schemas import (
    PantryItemCreate,
    PantryItemResponse,
    PantryItemUpdate,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.pantry.service import (
    add_pantry_item,
    get_pantry_items,
    remove_pantry_item,
    update_pantry_item,
)

router = APIRouter()


@router.get("/items", response_model=list[PantryItemResponse])
async def list_items(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_pantry_items(db, user.id)


@router.post("/items", response_model=PantryItemResponse, status_code=201)
async def create_item(
    body: PantryItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await add_pantry_item(db, user.id, body.model_dump())


@router.patch("/items/{item_id}", response_model=PantryItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: PantryItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await update_pantry_item(
        db, item_id, user.id, body.model_dump(exclude_unset=True)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await remove_pantry_item(db, item_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
