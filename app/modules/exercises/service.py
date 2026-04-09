"""Exercises service — catalogue CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exercises.models import Exercise


async def list_exercises(
    db: AsyncSession,
    muscle_group: str | None = None,
    equipment: str | None = None,
) -> list[Exercise]:
    query = select(Exercise)
    if muscle_group:
        query = query.where(Exercise.muscle_group == muscle_group)
    if equipment:
        query = query.where(Exercise.equipment == equipment)
    result = await db.execute(query.order_by(Exercise.name))
    return list(result.scalars().all())


async def get_exercise(db: AsyncSession, exercise_id: uuid.UUID) -> Exercise | None:
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    return result.scalar_one_or_none()


async def create_exercise(db: AsyncSession, data: dict) -> Exercise:
    exercise = Exercise(**data)
    db.add(exercise)
    await db.flush()
    return exercise
