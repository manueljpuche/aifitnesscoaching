"""Food router — food database and barcode."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.food.schemas import FoodCreate, FoodResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.food.service import create_food, get_food_by_barcode, search_foods

router = APIRouter()


@router.get("/search", response_model=list[FoodResponse])
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await search_foods(db, q, limit)


@router.get("/barcode/{barcode}", response_model=FoodResponse)
async def by_barcode(
    barcode: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    food = await get_food_by_barcode(db, barcode)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found for barcode")
    return food


@router.post("/", response_model=FoodResponse, status_code=201)
async def create(
    body: FoodCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_food(db, body.model_dump())
