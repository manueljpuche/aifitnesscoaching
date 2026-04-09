"""GDPR router — data export and account deletion."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.gdpr.service import export_user_data, soft_delete_user

router = APIRouter()


@router.get("/export")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    zip_bytes = await export_user_data(db, user)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=fitness_data_{user.id}.zip"},
    )


@router.post("/delete-account")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await soft_delete_user(db, user)
    return {"detail": "Account marked for deletion. Full purge in 30 days."}
