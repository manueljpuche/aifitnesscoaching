"""Wellness router — sleep, alcohol, cycle, symptoms, status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wellness.schemas import (
    AlcoholLogCreate,
    AlcoholLogResponse,
    CycleLogCreate,
    CycleLogResponse,
    SleepLogCreate,
    SleepLogResponse,
    SymptomLogCreate,
    SymptomLogResponse,
    UserStatusCreate,
    UserStatusResponse,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.wellness.service import (
    get_current_status,
    get_cycle_history,
    get_sleep_history,
    get_symptom_history,
    log_alcohol,
    log_cycle,
    log_sleep,
    log_symptom,
    set_status,
)

router = APIRouter()


# ---- Sleep ----

@router.post("/sleep", response_model=SleepLogResponse, status_code=201)
async def create_sleep(
    body: SleepLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_sleep(db, user.id, body.model_dump())


@router.get("/sleep", response_model=list[SleepLogResponse])
async def list_sleep(
    limit: int = Query(14, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_sleep_history(db, user.id, limit)


# ---- Alcohol ----

@router.post("/alcohol", response_model=AlcoholLogResponse, status_code=201)
async def create_alcohol(
    body: AlcoholLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_alcohol(db, user.id, body.model_dump())


# ---- Cycle ----

@router.post("/cycle", response_model=CycleLogResponse, status_code=201)
async def create_cycle(
    body: CycleLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_cycle(db, user.id, body.model_dump())


@router.get("/cycle", response_model=list[CycleLogResponse])
async def list_cycles(
    limit: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_cycle_history(db, user.id, limit)


# ---- Symptoms ----

@router.post("/symptoms", response_model=SymptomLogResponse, status_code=201)
async def create_symptom(
    body: SymptomLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await log_symptom(db, user.id, body.model_dump())


@router.get("/symptoms", response_model=list[SymptomLogResponse])
async def list_symptoms(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_symptom_history(db, user.id, limit)


# ---- Status ----

@router.post("/status", response_model=UserStatusResponse, status_code=201)
async def create_status(
    body: UserStatusCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await set_status(db, user.id, body.model_dump())


@router.get("/status", response_model=UserStatusResponse | None)
async def current_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_current_status(db, user.id)
