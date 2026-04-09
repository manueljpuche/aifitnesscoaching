"""Shopping router — list management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shopping.schemas import ShoppingListCreate, ShoppingListResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.shopping.service import (
    create_shopping_list,
    get_shopping_list,
    get_shopping_lists,
)

router = APIRouter()


@router.post("/list", response_model=ShoppingListResponse, status_code=201)
async def create_list(
    body: ShoppingListCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_shopping_list(db, user.id, body.model_dump())


@router.get("/list", response_model=list[ShoppingListResponse])
async def list_all(
    limit: int = Query(4, ge=1, le=12),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_shopping_lists(db, user.id, limit)


@router.get("/list/{list_id}", response_model=ShoppingListResponse)
async def get_one(
    list_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_shopping_list(db, list_id, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return result
