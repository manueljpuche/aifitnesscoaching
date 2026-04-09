"""Workouts service — plans, logs, sets, PRs."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workouts.models import (
    CardioLog,
    PersonalRecord,
    WorkoutLog,
    WorkoutPlan,
    WorkoutPlanDay,
    WorkoutPlanExercise,
    WorkoutSetLog,
)


# ---- Workout Plans ----


async def get_active_workout_plan(
    db: AsyncSession, user_id: uuid.UUID
) -> WorkoutPlan | None:
    result = await db.execute(
        select(WorkoutPlan).where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def create_workout_plan(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> WorkoutPlan:
    # Deactivate existing active plan
    result = await db.execute(
        select(WorkoutPlan).where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.is_active.is_(True),
        )
    )
    for old_plan in result.scalars().all():
        old_plan.is_active = False

    plan = WorkoutPlan(user_id=user_id, start_date=date.today(), **data)
    db.add(plan)
    await db.flush()
    return plan


async def add_plan_day(
    db: AsyncSession, plan_id: uuid.UUID, data: dict
) -> WorkoutPlanDay:
    day = WorkoutPlanDay(plan_id=plan_id, **data)
    db.add(day)
    await db.flush()
    return day


async def add_plan_exercise(
    db: AsyncSession, plan_day_id: uuid.UUID, data: dict
) -> WorkoutPlanExercise:
    exercise = WorkoutPlanExercise(plan_day_id=plan_day_id, **data)
    db.add(exercise)
    await db.flush()
    return exercise


async def get_today_workout(
    db: AsyncSession, user_id: uuid.UUID
) -> WorkoutPlanDay | None:
    plan = await get_active_workout_plan(db, user_id)
    if not plan:
        return None

    today_dow = date.today().isoweekday()  # 1=Monday..7=Sunday
    result = await db.execute(
        select(WorkoutPlanDay).where(
            WorkoutPlanDay.plan_id == plan.id,
            WorkoutPlanDay.day_number == today_dow,
        )
    )
    return result.scalar_one_or_none()


# ---- Workout Logs ----


async def create_workout_log(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> WorkoutLog:
    log = WorkoutLog(user_id=user_id, **data)
    db.add(log)
    await db.flush()
    return log


async def log_set(
    db: AsyncSession,
    workout_log_id: uuid.UUID,
    user_id: uuid.UUID,
    data: dict,
) -> tuple[WorkoutSetLog, PersonalRecord | None]:
    set_log = WorkoutSetLog(workout_log_id=workout_log_id, **data)
    db.add(set_log)
    await db.flush()

    # Check for PR
    pr = await _check_pr(
        db,
        user_id=user_id,
        exercise_id=data["exercise_id"],
        weight_kg=data.get("weight_kg"),
        reps_done=data["reps_done"],
        workout_log_id=workout_log_id,
    )
    return set_log, pr


async def _check_pr(
    db: AsyncSession,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    weight_kg: float | None,
    reps_done: int,
    workout_log_id: uuid.UUID,
) -> PersonalRecord | None:
    if not weight_kg:
        return None

    # Check max_weight PR
    result = await db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id == exercise_id,
            PersonalRecord.record_type == "max_weight",
        )
    )
    existing_pr = result.scalar_one_or_none()

    if existing_pr is None or weight_kg > existing_pr.value:
        pr = PersonalRecord(
            user_id=user_id,
            exercise_id=exercise_id,
            record_type="max_weight",
            value=weight_kg,
            workout_log_id=workout_log_id,
        )
        db.add(pr)
        await db.flush()
        return pr

    return None


async def get_workout_logs(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[WorkoutLog]:
    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user_id)
        .order_by(WorkoutLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---- Cardio ----


async def log_cardio(db: AsyncSession, user_id: uuid.UUID, data: dict) -> CardioLog:
    entry = CardioLog(user_id=user_id, **data)
    db.add(entry)
    await db.flush()
    return entry


# ---- PRs ----


async def get_personal_records(
    db: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID | None = None
) -> list[PersonalRecord]:
    query = select(PersonalRecord).where(PersonalRecord.user_id == user_id)
    if exercise_id:
        query = query.where(PersonalRecord.exercise_id == exercise_id)
    result = await db.execute(query.order_by(PersonalRecord.created_at.desc()))
    return list(result.scalars().all())


# ---- n8n batch ----


async def get_phase_transition_batch(db: AsyncSession) -> list[dict]:
    """Users whose current training phase is complete (phase_week >= phase_total_weeks)."""
    from app.modules.users.models import User

    result = await db.execute(
        select(
            User.telegram_id,
            User.first_name,
            WorkoutPlan.id.label("plan_id"),
            WorkoutPlan.name,
            WorkoutPlan.phase,
            WorkoutPlan.phase_week,
            WorkoutPlan.phase_total_weeks,
        )
        .join(WorkoutPlan, WorkoutPlan.user_id == User.id)
        .where(WorkoutPlan.is_active.is_(True))
        .where(WorkoutPlan.phase_week >= WorkoutPlan.phase_total_weeks)
    )
    rows = result.all()
    return [
        {
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "plan_id": str(r.plan_id),
            "current_phase": r.phase,
            "weeks_completed": r.phase_week,
            "transition_message": (
                f"🎯 ¡Has completado la fase de {r.phase} ({r.phase_week} semanas)!\n\n"
                "¿Quieres avanzar a la siguiente fase o repetir la actual?"
            ),
        }
        for r in rows
    ]
