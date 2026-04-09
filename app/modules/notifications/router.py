"""Notifications router — preferences management + n8n batch endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.schemas import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.core.database import get_db
from app.core.security import get_current_user, verify_n8n_secret
from app.modules.users.models import User
from app.modules.notifications.service import (
    get_daily_plan_batch,
    get_hydration_batch,
    get_morning_sleep_batch,
    get_preferences,
    get_progress_photo_batch,
    get_recovery_followup_batch,
    get_symptom_followup_batch,
    get_workout_nutrition_batch,
    update_preferences,
)

router = APIRouter()


@router.get("/preferences", response_model=NotificationPreferenceResponse | None)
async def get_prefs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_preferences(db, user.id)


@router.patch("/preferences", response_model=NotificationPreferenceResponse)
async def update_prefs(
    body: NotificationPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_preferences(db, user.id, body.model_dump(exclude_unset=True))


# ---- n8n batch endpoints (X-N8N-Secret auth) ----


@router.get("/daily-plan-batch", dependencies=[Depends(verify_n8n_secret)])
async def daily_plan_batch(db: AsyncSession = Depends(get_db)):
    return await get_daily_plan_batch(db)


@router.get("/morning-sleep-batch", dependencies=[Depends(verify_n8n_secret)])
async def morning_sleep_batch(db: AsyncSession = Depends(get_db)):
    return await get_morning_sleep_batch(db)


@router.get("/workout-nutrition-batch", dependencies=[Depends(verify_n8n_secret)])
async def workout_nutrition_batch(db: AsyncSession = Depends(get_db)):
    return await get_workout_nutrition_batch(db)


@router.get("/hydration-batch", dependencies=[Depends(verify_n8n_secret)])
async def hydration_batch(db: AsyncSession = Depends(get_db)):
    return await get_hydration_batch(db)


@router.get("/progress-photo-batch", dependencies=[Depends(verify_n8n_secret)])
async def progress_photo_batch(db: AsyncSession = Depends(get_db)):
    return await get_progress_photo_batch(db)


@router.get("/symptom-followup-batch", dependencies=[Depends(verify_n8n_secret)])
async def symptom_followup_batch(db: AsyncSession = Depends(get_db)):
    return await get_symptom_followup_batch(db)


@router.get("/recovery-followup-batch", dependencies=[Depends(verify_n8n_secret)])
async def recovery_followup_batch(db: AsyncSession = Depends(get_db)):
    return await get_recovery_followup_batch(db)
