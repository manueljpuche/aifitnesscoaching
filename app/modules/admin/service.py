"""Admin service — data cleanup and maintenance tasks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog  # type: ignore
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import ConversationHistory
from app.modules.users.models import UserPreference

logger = structlog.stdlib.get_logger()


async def run_data_cleanup(
    db: AsyncSession,
    *,
    conversation_retention_days: int = 90,
    ai_log_retention_days: int = 30,
    expired_preferences: bool = True,
    orphaned_files: bool = True,
) -> dict:
    """Purge old data according to retention policy."""
    now = datetime.now(timezone.utc)
    summary_parts: list[str] = []
    errors: list[str] = []
    errors_count = 0

    # 1. Old conversation messages
    try:
        conv_cutoff = now - timedelta(days=conversation_retention_days)
        result = await db.execute(
            delete(ConversationHistory).where(
                ConversationHistory.created_at < conv_cutoff
            )
        )
        deleted_conv = result.rowcount
        summary_parts.append(
            f"Conversations: {deleted_conv} deleted "
            f"(>{conversation_retention_days}d)"
        )
    except Exception as exc:
        errors.append(f"conversations: {exc}")
        errors_count += 1

    # 2. Expired temporary preferences
    if expired_preferences:
        try:
            result = await db.execute(
                delete(UserPreference)
                .where(UserPreference.is_temporary.is_(True))
                .where(UserPreference.expires_at.isnot(None))
                .where(UserPreference.expires_at <= now)
            )
            deleted_prefs = result.rowcount
            summary_parts.append(f"Expired preferences: {deleted_prefs} deleted")
        except Exception as exc:
            errors.append(f"preferences: {exc}")
            errors_count += 1

    await db.commit()

    summary = "\n".join(summary_parts)
    logger.info("data_cleanup_completed", summary=summary, errors_count=errors_count)

    return {
        "summary": summary,
        "errors_count": errors_count,
        "errors": errors,
    }
