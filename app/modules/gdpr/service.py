"""GDPR service — data export and account deletion."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.body.models import BodyMeasurement
from app.modules.workouts.models import PersonalRecord, WorkoutLog
from app.modules.tracking.models import MealLog, WeightLog, WaterLog
from app.modules.wellness.models import (
    SleepLog,
    AlcoholLog,
    MoodLog,
    StepLog,
    SymptomLog,
)
from app.modules.supplements.models import SupplementLog
from app.modules.gamification.models import UserAchievement, UserStreak
from app.modules.ai.models import ConversationHistory
from app.modules.challenges.models import UserChallenge
from app.modules.users.models import User, UserPreference


async def export_user_data(db: AsyncSession, user: User) -> bytes:
    """Generate a ZIP with all user data in JSON format."""
    data: dict[str, list] = {}

    # Profile
    data["profile"] = [
        {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "gender": user.gender,
            "goal": user.goal,
            "locale": user.locale,
            "timezone": user.timezone,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    ]

    # Preferences
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    data["preferences"] = [
        {"type": p.type, "category": p.category, "value": p.value}
        for p in result.scalars().all()
    ]

    # Weight log
    result = await db.execute(
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.created_at)
    )
    data["weight_log"] = [
        {"weight": w.weight, "source": w.source, "date": w.created_at.isoformat()}
        for w in result.scalars().all()
    ]

    # Meals
    result = await db.execute(
        select(MealLog).where(MealLog.user_id == user.id).order_by(MealLog.created_at)
    )
    data["meals"] = [
        {
            "description": m.description,
            "total_calories": m.total_calories,
            "source": m.source,
            "date": m.created_at.isoformat(),
        }
        for m in result.scalars().all()
    ]

    # Workouts
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user.id)
        .order_by(WorkoutLog.created_at)
    )
    data["workouts"] = [
        {
            "type": w.type,
            "duration_minutes": w.duration_minutes,
            "location": w.location,
            "date": w.created_at.isoformat(),
        }
        for w in result.scalars().all()
    ]

    # PRs
    result = await db.execute(
        select(PersonalRecord).where(PersonalRecord.user_id == user.id)
    )
    data["personal_records"] = [
        {
            "exercise_id": str(pr.exercise_id),
            "record_type": pr.record_type,
            "value": pr.value,
        }
        for pr in result.scalars().all()
    ]

    # Body measurements
    result = await db.execute(
        select(BodyMeasurement).where(BodyMeasurement.user_id == user.id)
    )
    data["body_measurements"] = [
        {
            "waist_cm": b.waist_cm,
            "hip_cm": b.hip_cm,
            "body_fat_pct": b.body_fat_pct,
            "date": b.created_at.isoformat(),
        }
        for b in result.scalars().all()
    ]

    # Water log
    result = await db.execute(
        select(WaterLog).where(WaterLog.user_id == user.id).order_by(WaterLog.created_at)
    )
    data["water_log"] = [
        {"amount_ml": w.amount_ml, "date": w.created_at.isoformat()}
        for w in result.scalars().all()
    ]

    # Sleep log
    result = await db.execute(
        select(SleepLog).where(SleepLog.user_id == user.id).order_by(SleepLog.created_at)
    )
    data["sleep_log"] = [
        {"hours": s.hours, "quality": s.quality, "date": s.created_at.isoformat()}
        for s in result.scalars().all()
    ]

    # Alcohol log
    result = await db.execute(
        select(AlcoholLog).where(AlcoholLog.user_id == user.id).order_by(AlcoholLog.created_at)
    )
    data["alcohol_log"] = [
        {"description": a.description, "units": a.units, "calories": a.calories, "date": a.created_at.isoformat()}
        for a in result.scalars().all()
    ]

    # Mood log
    result = await db.execute(
        select(MoodLog).where(MoodLog.user_id == user.id).order_by(MoodLog.created_at)
    )
    data["mood_log"] = [
        {"mood": m.mood, "energy": getattr(m, "energy", None), "date": m.created_at.isoformat()}
        for m in result.scalars().all()
    ]

    # Step log
    result = await db.execute(
        select(StepLog).where(StepLog.user_id == user.id).order_by(StepLog.created_at)
    )
    data["step_log"] = [
        {"steps": s.steps, "date": s.created_at.isoformat()}
        for s in result.scalars().all()
    ]

    # Symptom log
    result = await db.execute(
        select(SymptomLog).where(SymptomLog.user_id == user.id).order_by(SymptomLog.created_at)
    )
    data["symptom_log"] = [
        {"symptom": s.symptom, "severity": s.severity, "date": s.created_at.isoformat()}
        for s in result.scalars().all()
    ]

    # Supplement log
    result = await db.execute(
        select(SupplementLog).where(SupplementLog.user_id == user.id).order_by(SupplementLog.created_at)
    )
    data["supplement_log"] = [
        {"supplement_id": str(s.supplement_id), "date": s.created_at.isoformat()}
        for s in result.scalars().all()
    ]

    # Achievements
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == user.id)
    )
    data["achievements"] = [
        {"type": a.achievement_type, "title": a.title, "date": a.earned_at.isoformat() if a.earned_at else None}
        for a in result.scalars().all()
    ]

    # Streaks
    result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user.id)
    )
    data["streaks"] = [
        {"type": s.streak_type, "current": s.current_streak, "best": s.best_streak}
        for s in result.scalars().all()
    ]

    # Challenges
    result = await db.execute(
        select(UserChallenge).where(UserChallenge.user_id == user.id)
    )
    data["challenges"] = [
        {
            "challenge_id": str(c.challenge_id),
            "status": c.status,
            "started_at": c.started_at.isoformat() if c.started_at else None,
        }
        for c in result.scalars().all()
    ]

    # Conversation history
    result = await db.execute(
        select(ConversationHistory)
        .where(ConversationHistory.user_id == user.id)
        .order_by(ConversationHistory.created_at)
    )
    data["conversation_history"] = [
        {"role": ch.role, "content": ch.content, "intent": ch.intent, "date": ch.created_at.isoformat()}
        for ch in result.scalars().all()
    ]

    # Build ZIP in memory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, records in data.items():
            zf.writestr(
                f"{name}.json", json.dumps(records, indent=2, ensure_ascii=False)
            )

    return buffer.getvalue()


async def soft_delete_user(db: AsyncSession, user: User) -> None:
    """Mark user for deletion and anonymize PII. Full purge happens via cron after 30 days."""
    user.updated_at = datetime.now(timezone.utc)
    # Anonymize PII
    user.telegram_id = -abs(user.telegram_id)
    user.username = None
    user.first_name = "[deleted]"
    user.last_name = None
