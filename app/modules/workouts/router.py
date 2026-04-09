"""Workouts router — plans, logs, sets, cardio, PRs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workouts.schemas import (
    CardioLogCreate,
    CardioLogResponse,
    PersonalRecordResponse,
    WorkoutLogCreate,
    WorkoutLogResponse,
    WorkoutPlanCreate,
    WorkoutPlanDayCreate,
    WorkoutPlanDayResponse,
    WorkoutPlanExerciseCreate,
    WorkoutPlanExerciseResponse,
    WorkoutPlanResponse,
    WorkoutSetLogCreate,
    WorkoutSetLogResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.workouts.service import (
    add_plan_day,
    add_plan_exercise,
    create_workout_log,
    create_workout_plan,
    get_active_workout_plan,
    get_personal_records,
    get_phase_transition_batch,
    get_today_workout,
    get_workout_logs,
    log_cardio,
    log_set,
)

router = APIRouter()


# ---- Plans ----


@router.get("/plans/active", response_model=WorkoutPlanResponse | None)
async def active_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_workout_plan(db, user.id)


@router.post("/plans", response_model=WorkoutPlanResponse, status_code=201)
async def create_plan(
    body: WorkoutPlanCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_workout_plan(db, user.id, body.model_dump())


@router.get("/plans/today", response_model=WorkoutPlanDayResponse | None)
async def today_workout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_today_workout(db, user.id)


@router.post(
    "/plans/{plan_id}/days", response_model=WorkoutPlanDayResponse, status_code=201
)
async def add_day(
    plan_id: uuid.UUID,
    body: WorkoutPlanDayCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await add_plan_day(db, plan_id, body.model_dump())


@router.post(
    "/plans/days/{plan_day_id}/exercises",
    response_model=WorkoutPlanExerciseResponse,
    status_code=201,
)
async def add_exercise(
    plan_day_id: uuid.UUID,
    body: WorkoutPlanExerciseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await add_plan_exercise(db, plan_day_id, body.model_dump())


# ---- Logs ----


@router.post("/logs", response_model=WorkoutLogResponse, status_code=201)
async def create_log(
    body: WorkoutLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_workout_log(db, user.id, body.model_dump())


@router.get("/logs", response_model=list[WorkoutLogResponse])
async def list_logs(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_workout_logs(db, user.id, limit)


@router.post(
    "/logs/{workout_log_id}/sets",
    response_model=WorkoutSetLogResponse,
    status_code=201,
)
async def add_set(
    workout_log_id: uuid.UUID,
    body: WorkoutSetLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    set_log, pr = await log_set(db, workout_log_id, user.id, body.model_dump())
    return set_log


# ---- Cardio ----


@router.post("/cardio", response_model=CardioLogResponse, status_code=201)
async def create_cardio(
    body: CardioLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_cardio(db, user.id, body.model_dump())


# ---- PRs ----


@router.get("/personal-records", response_model=list[PersonalRecordResponse])
async def list_prs(
    exercise_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_personal_records(db, user.id, exercise_id)


# ---- n8n batch endpoints ----


@router.post("/phase-transition-batch", dependencies=[Depends(verify_n8n_secret)])
async def phase_transition_batch(db: AsyncSession = Depends(get_db)):
    return await get_phase_transition_batch(db)
