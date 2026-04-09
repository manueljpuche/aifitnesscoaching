"""Admin router — internal maintenance endpoints for n8n."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_n8n_secret
from app.modules.admin.service import run_data_cleanup

router = APIRouter()


class DataCleanupRequest(BaseModel):
    conversation_retention_days: int = Field(90, ge=1)
    ai_log_retention_days: int = Field(30, ge=1)
    expired_preferences: bool = True
    orphaned_files: bool = True


@router.post("/data-cleanup", dependencies=[Depends(verify_n8n_secret)])
async def data_cleanup(
    body: DataCleanupRequest,
    db: AsyncSession = Depends(get_db),
):
    return await run_data_cleanup(
        db,
        conversation_retention_days=body.conversation_retention_days,
        ai_log_retention_days=body.ai_log_retention_days,
        expired_preferences=body.expired_preferences,
        orphaned_files=body.orphaned_files,
    )
