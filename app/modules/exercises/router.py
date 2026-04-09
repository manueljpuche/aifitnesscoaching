"""Exercises router — catalogue."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exercises.schemas import ExerciseCreate, ExerciseResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.exercises.service import create_exercise, get_exercise, list_exercises

router = APIRouter()


@router.get("/", response_model=list[ExerciseResponse])
async def list_all(
    muscle_group: str | None = None,
    equipment: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_exercises(db, muscle_group, equipment)


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_one(
    exercise_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await get_exercise(db, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ex


@router.post("/", response_model=ExerciseResponse, status_code=201)
async def create(
    body: ExerciseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_exercise(db, body.model_dump())
