"""Intent dispatcher — executes the real action for each classified intent."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.entity_extractor import (
    extract_alcohol,
    extract_body_measurements,
    extract_cardio,
    extract_cycle_data,
    extract_meal,
    extract_mood,
    extract_nutrition_plan_request,
    extract_pantry_items,
    extract_sleep,
    extract_steps,
    extract_supplement_name,
    extract_symptom,
    extract_user_profile,
    extract_water,
    extract_weight,
    extract_workout_plan_request,
    extract_workout_set,
)
from app.modules.tracking.service import (
    create_meal_log,
    copy_meals_from_date,
    get_meals_by_date,
    get_water_today,
    get_weight_history,
    log_water,
    log_weight,
)
from app.modules.wellness.service import (
    log_alcohol,
    log_sleep,
    log_symptom,
    set_status,
    get_current_status,
)
from app.modules.workouts.service import (
    create_workout_log,
    get_active_workout_plan,
    get_personal_records,
    get_today_workout,
    get_workout_logs,
)
from app.modules.workouts.models import CardioLog, WorkoutLog
from app.modules.users.service import get_user, update_user
from app.modules.gamification.service import get_streaks, get_achievements, update_streak
from app.modules.versioning.service import save_version

logger = structlog.stdlib.get_logger()

# Redis key for active workout session
_WORKOUT_SESSION_KEY = "user:{user_id}:active_workout_id"


def _escape_like(value: str) -> str:
    """Escape special LIKE pattern characters in user input."""
    return value.replace("%", r"\%").replace("_", r"\_")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def dispatch(
    intent: str,
    text: str,
    entities: dict[str, Any],
    user_id: uuid.UUID,
    locale: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Execute the action for an intent and return {action_done, data, response_hint}.

    response_hint: short structured string the LLM uses to build the final reply.
    Returns None for action_done when intent is purely conversational.
    """
    uid = str(user_id)

    try:
        if intent == "log_meal":
            return await _handle_log_meal(text, uid, user_id, redis_client, db)

        elif intent == "log_meal_from_photo":
            return await _handle_log_meal(text, uid, user_id, redis_client, db, source="photo")

        elif intent == "repeat_meal":
            return await _handle_repeat_meal(user_id, db)

        elif intent == "log_water":
            return await _handle_log_water(text, uid, user_id, redis_client, db)

        elif intent == "log_weight":
            return await _handle_log_weight(text, uid, user_id, redis_client, db)

        elif intent == "log_sleep":
            return await _handle_log_sleep(text, uid, user_id, redis_client, db)

        elif intent == "log_alcohol":
            return await _handle_log_alcohol(text, uid, user_id, redis_client, db)

        elif intent == "start_workout":
            return await _handle_start_workout(user_id, uid, redis_client, db)

        elif intent == "end_workout":
            return await _handle_end_workout(uid, redis_client, db)

        elif intent == "log_set":
            return await _handle_log_set(text, uid, user_id, redis_client, db)

        elif intent == "log_cardio":
            return await _handle_log_cardio(text, uid, user_id, redis_client, db)

        elif intent == "view_today_plan":
            return await _handle_view_today_plan(user_id, db)

        elif intent == "plan_status":
            return await _handle_plan_status(user_id, db)

        elif intent == "change_goal":
            return await _handle_change_goal(text, uid, user_id, redis_client, db)

        elif intent == "generate_plan":
            return await _handle_generate_plan(text, uid, user_id, redis_client, db)

        elif intent == "view_history":
            return await _handle_view_history(user_id, db)

        elif intent == "ask_macros":
            return await _handle_ask_macros(user_id, db)

        elif intent == "view_prs":
            return await _handle_view_prs(user_id, db)

        elif intent == "view_achievements":
            return await _handle_view_achievements(user_id, db)

        elif intent == "symptom_report":
            return await _handle_symptom_report(text, uid, user_id, redis_client, db)

        elif intent == "log_measurements":
            return await _handle_log_measurements(text, uid, user_id, redis_client, db)

        elif intent == "log_supplement":
            return await _handle_log_supplement(text, uid, user_id, redis_client, db)

        elif intent in ("travel_mode", "sick_mode", "injury_mode", "vacation_mode"):
            return await _handle_set_status(intent, text, user_id, db)

        elif intent == "skip_gym":
            return await _handle_skip_gym(text, user_id, db)

        elif intent == "add_to_pantry":
            return await _handle_add_to_pantry(text, uid, user_id, redis_client, db)

        elif intent == "remove_from_pantry":
            return await _handle_remove_from_pantry(
                text, uid, user_id, redis_client, db
            )

        elif intent == "start_challenge":
            return await _handle_start_challenge(user_id, db)

        elif intent == "log_cycle":
            return await _handle_log_cycle(text, uid, user_id, redis_client, db)

        # --- DB-action intents ---
        elif intent == "restaurant_meal":
            return await _handle_restaurant_meal(text, uid, user_id, redis_client, db)

        elif intent == "social_event":
            return await _handle_social_event(text, uid, user_id, redis_client, db)

        elif intent == "exercise_pain":
            return await _handle_exercise_pain(text, uid, user_id, redis_client, db)

        elif intent in ("what_can_i_cook", "check_pantry_for_recipe"):
            return await _handle_what_can_i_cook(user_id, db)

        elif intent == "shopping_list":
            return await _handle_shopping_list(user_id, db)

        elif intent == "view_meal_slot":
            return await _handle_view_meal_slot(text, user_id, db)

        elif intent == "manage_supplements":
            return await _handle_manage_supplements(user_id, db)

        elif intent == "weekly_checkin":
            return await _handle_weekly_checkin(text, uid, user_id, redis_client, db)

        elif intent == "restore_plan":
            return await _handle_restore_plan(user_id, db)

        elif intent == "temporary_restriction":
            return await _handle_temporary_restriction(
                text, uid, user_id, redis_client, db
            )

        elif intent == "ask_plan_adjustment":
            return await _handle_ask_plan_adjustment(user_id, db)

        elif intent == "express_workout":
            return await _handle_express_workout(user_id, db)

        elif intent == "notification_settings":
            return await _handle_notification_settings(user_id, db)

        # --- Context-enhanced AI intents ---
        elif intent == "craving":
            return await _handle_craving(user_id, db)

        elif intent == "extra_hunger":
            return await _handle_extra_hunger(user_id, db)

        elif intent == "meal_prep":
            return await _handle_meal_prep(user_id, db)

        elif intent == "ask_nutrition":
            return await _handle_ask_nutrition(user_id, db)

        elif intent == "demotivation":
            return await _handle_demotivation(user_id, db)

        # --- Guidance-only intents ---
        elif intent in (
            "log_weight_from_photo",
            "progress_photo",
        ):
            return _handle_photo_guidance(intent)

        elif intent in ("scan_fridge", "scan_receipt", "scan_barcode"):
            return _handle_scan_guidance(intent)

        elif intent == "export_data":
            return _handle_export_guidance()

        elif intent == "delete_account":
            return _handle_delete_guidance()

        elif intent == "log_voice":
            return _handle_voice_guidance()

        # --- New critical intents ---
        elif intent == "generate_workout_plan":
            return await _handle_generate_workout_plan(
                text, uid, user_id, redis_client, db
            )

        elif intent in ("greeting", "goodbye", "thanks"):
            return _handle_conversational(intent)

        elif intent == "help":
            return _handle_help()

        elif intent == "undo_last":
            return await _handle_undo_last(user_id, db)

        elif intent == "edit_entry":
            return await _handle_edit_entry(text, uid, user_id, redis_client, db)

        elif intent == "recipe_request":
            return await _handle_recipe_request(text, uid, user_id, redis_client, db)

        elif intent == "calculate_bmi":
            return await _handle_calculate_bmi(user_id, db)

        elif intent == "food_substitution":
            return await _handle_food_substitution(text, uid, user_id, redis_client, db)

        elif intent == "workout_alternative":
            return await _handle_workout_alternative(text, uid, user_id, redis_client, db)

        # --- Important intents ---
        elif intent == "cheat_day":
            return await _handle_cheat_day(user_id, db)

        elif intent == "fasting":
            return await _handle_fasting(user_id, db)

        elif intent == "pre_post_workout_meal":
            return await _handle_pre_post_workout_meal(user_id, db)

        elif intent == "exercise_tutorial":
            return await _handle_exercise_tutorial(text, uid, user_id, redis_client, db)

        elif intent == "compare_progress":
            return await _handle_compare_progress(user_id, db)

        elif intent == "plateau_help":
            return await _handle_plateau_help(user_id, db)

        elif intent == "set_water_goal":
            return await _handle_set_water_goal(text, uid, user_id, redis_client, db)

        elif intent == "rest_day_advice":
            return await _handle_rest_day_advice(user_id, db)

        elif intent == "sleep_tips":
            return await _handle_sleep_tips(user_id, db)

        elif intent == "stress":
            return await _handle_stress(text, uid, user_id, redis_client, db)

        elif intent == "budget_meals":
            return await _handle_budget_meals(user_id, db)

        elif intent == "calorie_lookup":
            return await _handle_calorie_lookup(text, uid, user_id, redis_client, db)

        # --- Less urgent but useful ---
        elif intent == "set_reminder":
            return _handle_set_reminder_guidance()

        elif intent == "log_steps":
            return await _handle_log_steps(text, uid, user_id, redis_client, db)

        elif intent == "log_mood":
            return await _handle_log_mood(text, uid, user_id, redis_client, db)

        elif intent == "refeed_day":
            return await _handle_refeed_day(user_id, db)

        elif intent == "deload_week":
            return await _handle_deload_week(user_id, db)

        elif intent == "injury_exercise":
            return await _handle_injury_exercise(user_id, db)

        elif intent == "meal_timing":
            return await _handle_meal_timing(user_id, db)

        elif intent == "hydration_check":
            return await _handle_hydration_check(user_id, db)

        elif intent == "body_recomp":
            return await _handle_body_recomp(user_id, db)

        elif intent == "protein_goal":
            return await _handle_protein_goal(user_id, db)

        else:
            # Conversational intent — no action, just generate AI response
            return {"action_done": None, "data": {}, "response_hint": None}

    except Exception as e:
        logger.error("intent_dispatch_error", intent=intent, user_id=uid, detail=str(e))
        return {"action_done": None, "data": {}, "response_hint": None}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _handle_log_meal(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
    source: str = "text",
) -> dict[str, Any]:
    meal_data = await extract_meal(text, uid, redis_client, db)
    meal = await create_meal_log(
        db,
        user_id,
        {
            "description": meal_data.get("description", text),
            "total_calories": meal_data.get("total_calories"),
            "source": source,
            "is_cheat": meal_data.get("is_cheat", False),
            "items": meal_data.get("items", []),
        },
    )
    kcal = meal.total_calories
    items = meal_data.get("items", [])
    protein = sum(i.get("protein") or 0 for i in items)

    await update_streak(db, user_id, "nutrition")

    hint = f"MEAL_LOGGED: {meal_data.get('description', text)}"
    if kcal:
        hint += f" | {round(kcal)} kcal"
    if protein:
        hint += f" | {round(protein)}g proteína"

    return {
        "action_done": "meal_logged",
        "data": {"meal_id": str(meal.id)},
        "response_hint": hint,
    }


async def _handle_repeat_meal(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    yesterday = date.today() - timedelta(days=1)
    meals = await copy_meals_from_date(db, user_id, yesterday)
    if not meals:
        return {
            "action_done": "repeat_meal_no_data",
            "data": {},
            "response_hint": "REPEAT_MEAL: no meals found from yesterday to copy",
        }
    total_kcal = sum(m.total_calories or 0 for m in meals)
    hint = f"REPEAT_MEAL: copied {len(meals)} meals from yesterday | {round(total_kcal)} kcal total"
    return {
        "action_done": "meals_repeated",
        "data": {"count": len(meals)},
        "response_hint": hint,
    }


async def _handle_log_water(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    amount_ml = await extract_water(text, uid, redis_client, db)
    await log_water(db, user_id, amount_ml)
    total_today = await get_water_today(db, user_id)
    await update_streak(db, user_id, "hydration")
    hint = f"WATER_LOGGED: {round(amount_ml)}ml | total today: {round(total_today)}ml"
    return {
        "action_done": "water_logged",
        "data": {"amount_ml": amount_ml, "total_ml": total_today},
        "response_hint": hint,
    }


async def _handle_log_weight(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    weight_kg = await extract_weight(text, uid, redis_client, db)
    if weight_kg is None:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "WEIGHT_NOT_FOUND: ask user to clarify their weight",
        }
    await log_weight(db, user_id, {"weight": weight_kg, "source": "text"})
    await update_streak(db, user_id, "weight_tracking")
    hint = f"WEIGHT_LOGGED: {weight_kg} kg"
    return {
        "action_done": "weight_logged",
        "data": {"weight_kg": weight_kg},
        "response_hint": hint,
    }


async def _handle_log_sleep(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    sleep_data = await extract_sleep(text, uid, redis_client, db)
    await log_sleep(
        db,
        user_id,
        {
            "hours": sleep_data["hours_slept"],
            "quality": sleep_data.get("quality"),
        },
    )
    quality_labels = {
        1: "terrible",
        2: "malo",
        3: "regular",
        4: "bueno",
        5: "excelente",
    }
    quality_str = quality_labels.get(sleep_data.get("quality", 0), "")
    await update_streak(db, user_id, "sleep_tracking")
    hint = f"SLEEP_LOGGED: {sleep_data['hours_slept']}h"
    if quality_str:
        hint += f" | quality: {quality_str}"
    return {"action_done": "sleep_logged", "data": sleep_data, "response_hint": hint}


async def _handle_log_alcohol(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    alcohol_data = await extract_alcohol(text, uid, redis_client, db)
    await log_alcohol(
        db,
        user_id,
        {
            "description": alcohol_data["drink_type"],
            "units": alcohol_data["units"],
            "calories": alcohol_data.get("calories"),
        },
    )
    hint = (
        f"ALCOHOL_LOGGED: {alcohol_data['drink_type']} | {alcohol_data['units']} units"
    )
    return {
        "action_done": "alcohol_logged",
        "data": alcohol_data,
        "response_hint": hint,
    }


async def _handle_start_workout(
    user_id: uuid.UUID,
    uid: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    # Check if session already open
    session_key = _WORKOUT_SESSION_KEY.format(user_id=uid)
    existing = await redis_client.get(session_key)
    if existing:
        return {
            "action_done": "workout_already_active",
            "data": {
                "workout_log_id": (
                    existing.decode() if isinstance(existing, bytes) else existing
                )
            },
            "response_hint": "WORKOUT_ALREADY_ACTIVE: session is already open",
        }

    workout_log = await create_workout_log(db, user_id, {"notes": None})
    session_key = _WORKOUT_SESSION_KEY.format(user_id=uid)
    await redis_client.set(session_key, str(workout_log.id), ex=7200)  # 2h TTL

    today_plan = await get_today_workout(db, user_id)
    plan_info = f" | today: {today_plan.name}" if today_plan else ""
    hint = f"WORKOUT_STARTED: session {workout_log.id}{plan_info}"
    return {
        "action_done": "workout_started",
        "data": {"workout_log_id": str(workout_log.id)},
        "response_hint": hint,
    }


async def _handle_end_workout(
    uid: str, redis_client: aioredis.Redis, db: AsyncSession
) -> dict[str, Any]:
    from datetime import datetime, timezone
    from sqlalchemy import select as sa_select

    session_key = _WORKOUT_SESSION_KEY.format(user_id=uid)
    workout_log_id_raw = await redis_client.get(session_key)
    if not workout_log_id_raw:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "NO_ACTIVE_WORKOUT: no workout session open",
        }

    workout_log_id = uuid.UUID(
        workout_log_id_raw.decode()
        if isinstance(workout_log_id_raw, bytes)
        else workout_log_id_raw
    )
    result = await db.execute(
        sa_select(WorkoutLog).where(WorkoutLog.id == workout_log_id)
    )
    workout_log = result.scalar_one_or_none()
    if workout_log:
        elapsed = (datetime.now(timezone.utc) - workout_log.created_at).seconds // 60
        workout_log.duration_minutes = elapsed

    await redis_client.delete(session_key)
    await update_streak(db, uuid.UUID(uid), "workout")
    hint = "WORKOUT_ENDED: session closed"
    return {
        "action_done": "workout_ended",
        "data": {"workout_log_id": str(workout_log_id)},
        "response_hint": hint,
    }


async def _handle_log_set(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.modules.exercises.models import Exercise

    session_key = _WORKOUT_SESSION_KEY.format(user_id=uid)
    workout_log_id_raw = await redis_client.get(session_key)

    # Auto-start workout if none open
    if not workout_log_id_raw:
        start_result = await _handle_start_workout(user_id, uid, redis_client, db)
        workout_log_id = uuid.UUID(start_result["data"]["workout_log_id"])
    else:
        workout_log_id = uuid.UUID(
            workout_log_id_raw.decode()
            if isinstance(workout_log_id_raw, bytes)
            else workout_log_id_raw
        )

    set_data = await extract_workout_set(text, uid, redis_client, db)
    exercise_name = set_data.get("exercise_name", "unknown")

    # Find or create exercise
    result = await db.execute(
        select(Exercise).where(Exercise.name.ilike(f"%{_escape_like(exercise_name)}%")).limit(1)
    )
    exercise = result.scalar_one_or_none()
    if not exercise:
        exercise = Exercise(name=exercise_name, muscle_group="other", equipment="other")
        db.add(exercise)
        await db.flush()

    from app.modules.workouts.service import log_set
    from app.modules.workouts.models import WorkoutSetLog
    from sqlalchemy import func as sa_func

    # Auto-increment set_number per exercise within this workout session
    count_result = await db.execute(
        select(sa_func.count()).where(
            WorkoutSetLog.workout_log_id == workout_log_id,
            WorkoutSetLog.exercise_id == exercise.id,
        )
    )
    next_set_number = (count_result.scalar() or 0) + 1

    set_log, pr = await log_set(
        db,
        workout_log_id,
        user_id,
        {
            "exercise_id": exercise.id,
            "set_number": next_set_number,
            "reps_done": set_data.get("reps_done", 0),
            "weight_kg": set_data.get("weight_kg"),
            "rpe_actual": set_data.get("rpe"),
            "notes": set_data.get("notes"),
        },
    )

    await update_streak(db, user_id, "workout")

    hint = f"SET_LOGGED: {exercise_name} | {set_data.get('reps_done')} reps"
    if set_data.get("weight_kg"):
        hint += f" @ {set_data['weight_kg']}kg"
    if pr:
        hint += " | 🏆 NEW PR!"

    return {
        "action_done": "set_logged",
        "data": {"set_id": str(set_log.id), "is_pr": pr is not None},
        "response_hint": hint,
    }


async def _handle_log_cardio(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    cardio_data = await extract_cardio(text, uid, redis_client, db)
    entry = CardioLog(
        user_id=user_id,
        type=cardio_data["cardio_type"],
        duration_minutes=cardio_data["duration_minutes"],
        distance_km=cardio_data.get("distance_km"),
        calories_burned=cardio_data.get("calories_burned"),
    )
    db.add(entry)
    await db.flush()

    await update_streak(db, user_id, "workout")

    hint = f"CARDIO_LOGGED: {cardio_data['cardio_type']} | {cardio_data['duration_minutes']} min"
    if cardio_data.get("distance_km"):
        hint += f" | {cardio_data['distance_km']} km"
    return {"action_done": "cardio_logged", "data": cardio_data, "response_hint": hint}


async def _handle_view_today_plan(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan, get_schedules

    nutrition_plan = await get_active_plan(db, user_id)
    workout_day = await get_today_workout(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())

    parts = []
    if nutrition_plan:
        schedules = await get_schedules(db, nutrition_plan.id)
        schedule_info = (
            ", ".join(s.name for s in schedules) if schedules else "no slots"
        )
        parts.append(
            f"NUTRITION: {nutrition_plan.calories_target or '?'} kcal target | slots: {schedule_info}"
        )
    else:
        parts.append("NUTRITION: no active plan")

    if workout_day:
        parts.append(
            f"WORKOUT: {workout_day.name} | {len(workout_day.exercises)} exercises"
        )
    else:
        parts.append("WORKOUT: rest day or no plan")

    logged_kcal = sum(m.total_calories or 0 for m in meals_today)
    parts.append(f"LOGGED TODAY: {len(meals_today)} meals | {round(logged_kcal)} kcal")

    hint = "VIEW_TODAY_PLAN: " + " || ".join(parts)
    return {"action_done": "plan_shown", "data": {}, "response_hint": hint}


async def _handle_plan_status(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan
    from app.modules.tracking.service import get_water_today

    meals_today = await get_meals_by_date(db, user_id, date.today())
    water_today = await get_water_today(db, user_id)
    nutrition_plan = await get_active_plan(db, user_id)

    logged_kcal = sum(m.total_calories or 0 for m in meals_today)
    target_kcal = nutrition_plan.calories_target if nutrition_plan else None
    remaining = (target_kcal - logged_kcal) if target_kcal else None

    hint = f"PLAN_STATUS: logged {round(logged_kcal)} kcal"
    if remaining is not None:
        hint += f" | {round(remaining)} kcal remaining"
    hint += f" | water: {round(water_today)} ml"

    return {
        "action_done": "status_shown",
        "data": {"logged_kcal": logged_kcal, "water_ml": water_today},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# Profile & goal handlers
# ---------------------------------------------------------------------------


async def _handle_change_goal(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    profile_data = await extract_user_profile(text, uid, redis_client, db)
    if not profile_data:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "Could not extract profile changes from message.",
        }

    user = await get_user(db, user_id)
    if not user:
        return {"action_done": None, "data": {}, "response_hint": "User not found."}

    user = await update_user(db, user, profile_data)
    changed = ", ".join(f"{k}={v}" for k, v in profile_data.items())
    hint = f"PROFILE_UPDATED: {changed}"
    return {
        "action_done": "profile_updated",
        "data": profile_data,
        "response_hint": hint,
    }


async def _handle_generate_plan(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.nutrition.service import (
        create_plan,
        create_schedule,
        create_planned_meal,
        get_active_plan,
        update_plan,
    )

    user = await get_user(db, user_id)
    profile = {}
    if user:
        profile = {
            "age": user.age,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "gender": user.gender,
            "activity_level": user.activity_level,
            "goal": user.goal,
            "restrictions": user.restrictions,
        }

    plan_data = await extract_nutrition_plan_request(
        text, profile, uid, redis_client, db
    )
    if not plan_data or not plan_data.get("calories_target"):
        return {
            "action_done": None,
            "data": {},
            "response_hint": "Could not generate a valid nutrition plan from the request.",
        }

    # Deactivate existing plan (save version first)
    existing = await get_active_plan(db, user_id)
    if existing:
        await save_version(
            db,
            user_id,
            plan_type="nutrition",
            plan_id=existing.id,
            snapshot={
                "calories_target": existing.calories_target,
                "protein_g": existing.protein_g,
                "carbs_g": existing.carbs_g,
                "fat_g": existing.fat_g,
                "meals_per_day": existing.meals_per_day,
            },
            change_reason="new_plan_generated",
        )
        await update_plan(db, existing, {"is_active": False})

    new_plan = await create_plan(
        db,
        user_id,
        {
            "calories_target": plan_data["calories_target"],
            "protein_g": plan_data.get("protein_g", 0),
            "carbs_g": plan_data.get("carbs_g", 0),
            "fat_g": plan_data.get("fat_g", 0),
            "fiber_g": plan_data.get("fiber_g"),
            "meals_per_day": plan_data.get("meals_per_day", 4),
            "start_date": date.today(),
            "is_active": True,
        },
    )

    # Create meal schedules and planned meals
    for schedule_data in plan_data.get("schedules", []):
        schedule = await create_schedule(
            db,
            new_plan.id,
            {
                "meal_number": schedule_data.get("meal_number", 1),
                "name": schedule_data.get("name", "Comida"),
                "calories_target": schedule_data.get("calories_target"),
                "protein_target": schedule_data.get("protein_target"),
                "carbs_target": schedule_data.get("carbs_target"),
                "fat_target": schedule_data.get("fat_target"),
            },
        )
        for meal in schedule_data.get("meals", []):
            await create_planned_meal(
                db,
                schedule.id,
                {
                    "food_name": meal.get("food_name", ""),
                    "quantity": meal.get("quantity"),
                    "unit": meal.get("unit"),
                    "calories": meal.get("calories"),
                    "protein": meal.get("protein"),
                    "carbs": meal.get("carbs"),
                    "fat": meal.get("fat"),
                },
            )

    hint = (
        f"PLAN_GENERATED: {plan_data['calories_target']} kcal | "
        f"P:{plan_data.get('protein_g',0)}g C:{plan_data.get('carbs_g',0)}g F:{plan_data.get('fat_g',0)}g | "
        f"{plan_data.get('meals_per_day',4)} meals/day"
    )
    return {
        "action_done": "plan_generated",
        "data": {"plan_id": str(new_plan.id)},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# History & query handlers
# ---------------------------------------------------------------------------


async def _handle_view_history(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    meals = await get_meals_by_date(db, user_id, date.today())
    weight_history = await get_weight_history(db, user_id, limit=7)
    workouts = await get_workout_logs(db, user_id, limit=5)

    parts = []
    if meals:
        total_kcal = sum(m.total_calories or 0 for m in meals)
        parts.append(f"Today: {len(meals)} meals, {round(total_kcal)} kcal")
    if weight_history:
        weights = [
            f"{w.weight_kg}kg ({w.created_at.strftime('%d/%m')})"
            for w in weight_history[:5]
        ]
        parts.append(f"Weight: {', '.join(weights)}")
    if workouts:
        wo_info = [
            f"{w.type or 'workout'} ({w.created_at.strftime('%d/%m')})"
            for w in workouts[:5]
        ]
        parts.append(f"Workouts: {', '.join(wo_info)}")

    hint = "HISTORY: " + (" || ".join(parts) if parts else "no data yet")
    return {"action_done": "history_shown", "data": {}, "response_hint": hint}


async def _handle_ask_macros(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())

    consumed_cal = sum(m.total_calories or 0 for m in meals_today)
    consumed_p = sum(
        item.protein or 0 for m in meals_today for item in (m.items or [])
    )
    consumed_c = sum(
        item.carbs or 0 for m in meals_today for item in (m.items or [])
    )
    consumed_f = sum(
        item.fat or 0 for m in meals_today for item in (m.items or [])
    )

    if plan:
        hint = (
            f"MACROS: Target {plan.calories_target} kcal "
            f"(P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g) | "
            f"Consumed {round(consumed_cal)} kcal "
            f"(P:{round(consumed_p)}g C:{round(consumed_c)}g F:{round(consumed_f)}g) | "
            f"Remaining {round(plan.calories_target - consumed_cal)} kcal"
        )
    else:
        hint = (
            f"MACROS: No active plan | "
            f"Consumed today {round(consumed_cal)} kcal "
            f"(P:{round(consumed_p)}g C:{round(consumed_c)}g F:{round(consumed_f)}g)"
        )
    return {"action_done": "macros_shown", "data": {}, "response_hint": hint}


async def _handle_view_prs(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    prs = await get_personal_records(db, user_id)
    if not prs:
        hint = "PERSONAL_RECORDS: No PRs recorded yet"
    else:
        pr_lines = []
        for pr in prs[:10]:
            pr_lines.append(f"{pr.record_type}: {pr.value}")
        hint = "PERSONAL_RECORDS: " + " | ".join(pr_lines)
    return {
        "action_done": "prs_shown",
        "data": {"count": len(prs)},
        "response_hint": hint,
    }


async def _handle_view_achievements(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    achievements = await get_achievements(db, user_id)
    streaks = await get_streaks(db, user_id)

    parts = []
    if achievements:
        ach_lines = [f"🏆 {a.title}" for a in achievements[:5]]
        parts.append("Achievements: " + ", ".join(ach_lines))
    else:
        parts.append("Achievements: none yet")

    if streaks:
        streak_lines = [
            f"{s.streak_type}: {s.current_streak}d (best: {s.best_streak}d)"
            for s in streaks
        ]
        parts.append("Streaks: " + ", ".join(streak_lines))

    hint = "ACHIEVEMENTS: " + " || ".join(parts)
    return {"action_done": "achievements_shown", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Wellness handlers
# ---------------------------------------------------------------------------


async def _handle_symptom_report(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    symptom_data = await extract_symptom(text, uid, redis_client, db)
    entry = await log_symptom(
        db,
        user_id,
        {
            "symptom": symptom_data.get("symptom", "unknown"),
            "symptom_raw": symptom_data.get("symptom_raw", text),
            "severity": symptom_data.get("severity", 1),
        },
    )

    hint = f"SYMPTOM_LOGGED: {symptom_data.get('symptom')} | severity {symptom_data.get('severity', 1)}/5"
    return {
        "action_done": "symptom_logged",
        "data": {"symptom_id": str(entry.id)},
        "response_hint": hint,
    }


async def _handle_log_measurements(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.body.service import log_measurement

    measurements = await extract_body_measurements(text, uid, redis_client, db)
    if not measurements:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "Could not extract measurements from message.",
        }

    entry = await log_measurement(db, user_id, measurements)
    parts = [f"{k}: {v}" for k, v in measurements.items()]
    hint = f"MEASUREMENTS_LOGGED: {', '.join(parts)}"
    return {
        "action_done": "measurements_logged",
        "data": measurements,
        "response_hint": hint,
    }


async def _handle_log_supplement(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.modules.supplements.service import (
        log_supplement as svc_log_supplement,
        create_supplement,
    )
    from app.modules.supplements.models import Supplement

    supp_name = await extract_supplement_name(text, uid, redis_client, db)

    # Find or create supplement
    result = await db.execute(
        select(Supplement).where(Supplement.name.ilike(f"%{_escape_like(supp_name)}%")).limit(1)
    )
    supplement = result.scalar_one_or_none()
    if not supplement:
        supplement = await create_supplement(db, {"name": supp_name})

    entry = await svc_log_supplement(db, user_id, supplement.id)
    await update_streak(db, user_id, "supplements")
    hint = f"SUPPLEMENT_LOGGED: {supp_name}"
    return {
        "action_done": "supplement_logged",
        "data": {"supplement": supp_name},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# Status & lifestyle handlers
# ---------------------------------------------------------------------------


async def _handle_set_status(
    intent: str,
    text: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    status_map = {
        "travel_mode": "traveling",
        "sick_mode": "sick",
        "injury_mode": "injured",
        "vacation_mode": "vacation",
    }
    status_str = status_map.get(intent, "normal")
    entry = await set_status(db, user_id, {"status": status_str, "reason": text})

    hint = f"STATUS_SET: {status_str}"
    return {
        "action_done": "status_set",
        "data": {"status": status_str},
        "response_hint": hint,
    }


async def _handle_skip_gym(
    text: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    entry = await create_workout_log(
        db,
        user_id,
        {
            "type": "gym",
            "skipped": True,
            "skip_reason": text,
            "duration_minutes": 0,
        },
    )

    hint = "GYM_SKIPPED: logged as skipped day"
    return {
        "action_done": "gym_skipped",
        "data": {"workout_log_id": str(entry.id)},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# Pantry handlers
# ---------------------------------------------------------------------------


async def _handle_add_to_pantry(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.pantry.service import add_pantry_item

    items = await extract_pantry_items(text, uid, redis_client, db)
    if not items:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "Could not extract pantry items.",
        }

    added = []
    for item in items:
        entry = await add_pantry_item(
            db,
            user_id,
            {
                "food_name": item.get("food_name", "unknown"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "source": "text",
            },
        )
        added.append(item.get("food_name", "unknown"))

    hint = f"PANTRY_ADDED: {', '.join(added)}"
    return {
        "action_done": "pantry_updated",
        "data": {"items": added},
        "response_hint": hint,
    }


async def _handle_remove_from_pantry(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.modules.pantry.service import remove_pantry_item
    from app.modules.pantry.models import PantryItem

    items = await extract_pantry_items(text, uid, redis_client, db)
    removed = []
    for item in items:
        food_name = item.get("food_name", "")
        result = await db.execute(
            select(PantryItem)
            .where(
                PantryItem.user_id == user_id,
                PantryItem.food_name.ilike(f"%{_escape_like(food_name)}%"),
            )
            .limit(1)
        )
        pantry_item = result.scalar_one_or_none()
        if pantry_item:
            await remove_pantry_item(db, pantry_item.id, user_id)
            removed.append(food_name)

    if not removed:
        hint = "PANTRY_REMOVE: no matching items found"
    else:
        hint = f"PANTRY_REMOVED: {', '.join(removed)}"
    return {
        "action_done": "pantry_updated",
        "data": {"removed": removed},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# Challenge & cycle handlers
# ---------------------------------------------------------------------------


async def _handle_start_challenge(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    from app.modules.challenges.service import (
        list_challenges,
        start_challenge as svc_start_challenge,
        get_active_challenge,
    )

    active = await get_active_challenge(db, user_id)
    if active:
        hint = f"CHALLENGE_ACTIVE: already in a challenge (started {active.started_at.strftime('%d/%m')})"
        return {"action_done": "challenge_exists", "data": {}, "response_hint": hint}

    challenges = await list_challenges(db)
    if not challenges:
        hint = "CHALLENGE_NONE: no challenges available"
        return {"action_done": None, "data": {}, "response_hint": hint}

    # Start the first available challenge
    challenge = challenges[0]
    entry = await svc_start_challenge(db, user_id, challenge.id)
    hint = f"CHALLENGE_STARTED: {challenge.title} | {challenge.duration_days} days"
    return {
        "action_done": "challenge_started",
        "data": {"challenge_id": str(challenge.id)},
        "response_hint": hint,
    }


async def _handle_log_cycle(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.wellness.service import log_cycle

    cycle_data = await extract_cycle_data(text, uid, redis_client, db)
    cycle_start = cycle_data.get("cycle_start")
    if not cycle_start:
        cycle_start = date.today().isoformat()

    entry = await log_cycle(
        db,
        user_id,
        {
            "cycle_start": cycle_start,
            "cycle_end": cycle_data.get("cycle_end"),
            "phase": cycle_data.get("phase"),
        },
    )

    hint = f"CYCLE_LOGGED: start {cycle_start}"
    if cycle_data.get("phase"):
        hint += f" | phase: {cycle_data['phase']}"
    return {
        "action_done": "cycle_logged",
        "data": {"cycle_id": str(entry.id)},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# DB-action intents (new batch)
# ---------------------------------------------------------------------------


async def _handle_restaurant_meal(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Log a restaurant meal — same as log_meal but flagged as restaurant."""
    meal_data = await extract_meal(text, uid, redis_client, db)
    meal = await create_meal_log(
        db,
        user_id,
        {
            "description": meal_data.get("description", text),
            "total_calories": meal_data.get("total_calories"),
            "source": "restaurant",
            "is_cheat": meal_data.get("is_cheat", False),
            "items": meal_data.get("items", []),
        },
    )
    kcal = meal.total_calories
    hint = f"RESTAURANT_MEAL_LOGGED: {meal_data.get('description', text)}"
    if kcal:
        hint += f" | ~{round(kcal)} kcal (estimated)"
    return {
        "action_done": "restaurant_meal_logged",
        "data": {"meal_id": str(meal.id)},
        "response_hint": hint,
    }


async def _handle_social_event(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Log a social-event meal (party, dinner out, etc.)."""
    meal_data = await extract_meal(text, uid, redis_client, db)
    meal = await create_meal_log(
        db,
        user_id,
        {
            "description": f"[Evento social] {meal_data.get('description', text)}",
            "total_calories": meal_data.get("total_calories"),
            "source": "social_event",
            "is_cheat": meal_data.get("is_cheat", False),
            "items": meal_data.get("items", []),
        },
    )
    hint = f"SOCIAL_EVENT_LOGGED: {meal_data.get('description', text)}"
    if meal.total_calories:
        hint += f" | ~{round(meal.total_calories)} kcal"
    return {
        "action_done": "social_event_logged",
        "data": {"meal_id": str(meal.id)},
        "response_hint": hint,
    }


async def _handle_exercise_pain(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Log pain/discomfort during exercise as a symptom."""
    symptom_data = await extract_symptom(text, uid, redis_client, db)
    entry = await log_symptom(
        db,
        user_id,
        {
            "symptom": f"exercise_pain: {symptom_data.get('symptom', 'pain')}",
            "symptom_raw": text,
            "severity": symptom_data.get("severity", 2),
        },
    )
    hint = (
        f"EXERCISE_PAIN_LOGGED: {symptom_data.get('symptom', 'pain')} | "
        f"severity {symptom_data.get('severity', 2)}/5 | "
        "Consider adjusting today's workout"
    )
    return {
        "action_done": "exercise_pain_logged",
        "data": {"symptom_id": str(entry.id)},
        "response_hint": hint,
    }


async def _handle_what_can_i_cook(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """List pantry items so AI can suggest recipes."""
    from app.modules.pantry.service import get_pantry_items
    from app.modules.nutrition.service import get_active_plan

    items = await get_pantry_items(db, user_id)
    plan = await get_active_plan(db, user_id)

    if not items:
        hint = "PANTRY_EMPTY: user has no pantry items registered"
    else:
        item_list = ", ".join(i.food_name for i in items[:20])
        hint = f"PANTRY_ITEMS: {item_list}"
    if plan:
        hint += f" | TARGETS: {plan.calories_target} kcal P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g"

    return {
        "action_done": "pantry_listed_for_recipes",
        "data": {},
        "response_hint": hint,
    }


async def _handle_shopping_list(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """Generate context for a shopping list based on plan vs pantry."""
    from app.modules.pantry.service import get_pantry_items
    from app.modules.nutrition.service import (
        get_active_plan,
        get_schedules,
        get_planned_meals,
    )

    plan = await get_active_plan(db, user_id)
    pantry = await get_pantry_items(db, user_id)
    pantry_names = {i.food_name.lower() for i in pantry}

    needed = []
    if plan:
        schedules = await get_schedules(db, plan.id)
        for sched in schedules:
            meals = await get_planned_meals(db, sched.id)
            for m in meals:
                if m.food_name.lower() not in pantry_names:
                    needed.append(m.food_name)

    if needed:
        hint = f"SHOPPING_LIST: items not in pantry: {', '.join(set(needed))}"
    elif plan:
        hint = "SHOPPING_LIST: all planned foods are already in pantry"
    else:
        hint = "SHOPPING_LIST: no active nutrition plan to compare against"

    return {
        "action_done": "shopping_list_shown",
        "data": {"needed": list(set(needed))},
        "response_hint": hint,
    }


async def _handle_view_meal_slot(
    text: str, user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Show what's planned for a specific meal slot."""
    from app.modules.nutrition.service import (
        get_active_plan,
        get_schedules,
        get_planned_meals,
    )

    plan = await get_active_plan(db, user_id)
    if not plan:
        return {
            "action_done": "no_plan",
            "data": {},
            "response_hint": "VIEW_MEAL_SLOT: no active nutrition plan",
        }

    schedules = await get_schedules(db, plan.id)
    parts = []
    for s in schedules:
        meals = await get_planned_meals(db, s.id)
        meal_names = (
            ", ".join(m.food_name for m in meals) if meals else "no meals planned"
        )
        cals = f" ({round(s.calories_target)} kcal)" if s.calories_target else ""
        parts.append(f"{s.name}{cals}: {meal_names}")

    hint = "MEAL_SLOTS: " + " || ".join(parts)
    return {"action_done": "meal_slots_shown", "data": {}, "response_hint": hint}


async def _handle_manage_supplements(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Show current supplement stack."""
    from app.modules.supplements.service import get_user_supplements

    supps = await get_user_supplements(db, user_id)
    if not supps:
        hint = "SUPPLEMENTS: no supplements configured"
    else:
        lines = [
            f"{s.supplement.name} ({s.dose or '?'}, {s.timing or '?'})"
            for s in supps
            if hasattr(s, "supplement") and s.supplement
        ]
        if not lines:
            lines = [f"supplement #{i+1}" for i in range(len(supps))]
        hint = "SUPPLEMENTS: " + " | ".join(lines)
    return {
        "action_done": "supplements_shown",
        "data": {"count": len(supps)},
        "response_hint": hint,
    }


async def _handle_weekly_checkin(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Compile a weekly summary for the user."""
    from app.modules.nutrition.service import get_active_plan
    from app.modules.tracking.service import get_water_today

    week_start = date.today() - timedelta(days=7)
    weight_history = await get_weight_history(db, user_id, limit=7)
    workouts = await get_workout_logs(db, user_id, limit=7)
    streaks = await get_streaks(db, user_id)
    plan = await get_active_plan(db, user_id)

    parts = []
    if weight_history:
        first_w = weight_history[-1].weight_kg if weight_history else None
        last_w = weight_history[0].weight_kg if weight_history else None
        if first_w and last_w:
            diff = round(last_w - first_w, 1)
            sign = "+" if diff > 0 else ""
            parts.append(f"Weight: {last_w}kg ({sign}{diff}kg this week)")

    workout_count = len([w for w in workouts if w.created_at.date() >= week_start])
    parts.append(f"Workouts: {workout_count} this week")

    if plan:
        parts.append(f"Plan: {plan.calories_target} kcal/day target")

    if streaks:
        best = max(streaks, key=lambda s: s.current_streak)
        parts.append(f"Best streak: {best.streak_type} {best.current_streak}d")

    hint = (
        "WEEKLY_CHECKIN: " + " || ".join(parts)
        if parts
        else "WEEKLY_CHECKIN: not enough data yet"
    )
    return {"action_done": "weekly_checkin_shown", "data": {}, "response_hint": hint}


async def _handle_restore_plan(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """Restore status to normal and attempt to restore the previous plan version."""
    from app.modules.versioning.service import get_versions
    from app.modules.nutrition.service import get_active_plan, create_plan, update_plan

    current = await get_current_status(db, user_id)
    if current and current.status != "normal":
        await set_status(
            db, user_id, {"status": "normal", "reason": "restored by user"}
        )

    # Try to restore the most recent plan version
    versions = await get_versions(db, user_id, plan_type="nutrition", limit=1)
    if versions:
        snapshot = versions[0].snapshot
        # Deactivate current plan
        active = await get_active_plan(db, user_id)
        if active:
            await update_plan(db, active, {"is_active": False})

        # Recreate plan from snapshot
        restored = await create_plan(
            db,
            user_id,
            {
                "calories_target": snapshot.get("calories_target"),
                "protein_g": snapshot.get("protein_g", 0),
                "carbs_g": snapshot.get("carbs_g", 0),
                "fat_g": snapshot.get("fat_g", 0),
                "meals_per_day": snapshot.get("meals_per_day", 4),
                "is_active": True,
            },
        )
        hint = (
            f"PLAN_RESTORED: status → normal | "
            f"Restored plan: {restored.calories_target} kcal "
            f"(P:{restored.protein_g}g C:{restored.carbs_g}g F:{restored.fat_g}g)"
        )
    else:
        plan = await get_active_plan(db, user_id)
        if plan:
            hint = (
                f"PLAN_RESTORED: status → normal | "
                f"Active plan: {plan.calories_target} kcal "
                f"(P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g)"
            )
        else:
            hint = "PLAN_RESTORED: status → normal | No active nutrition plan and no previous version to restore"

    return {"action_done": "plan_restored", "data": {}, "response_hint": hint}


async def _handle_temporary_restriction(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Add a temporary food restriction/preference."""
    from app.modules.users.service import add_preference

    profile_data = await extract_user_profile(text, uid, redis_client, db)
    restriction = profile_data.get("restrictions", text)

    pref = await add_preference(
        db,
        user_id,
        {
            "type": "restriction",
            "category": "food",
            "value": restriction,
            "is_temporary": True,
            "reason": text,
        },
    )
    hint = f"TEMPORARY_RESTRICTION_ADDED: {restriction}"
    return {
        "action_done": "restriction_added",
        "data": {"preference_id": str(pref.id)},
        "response_hint": hint,
    }


async def _handle_ask_plan_adjustment(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Gather context so AI can suggest plan adjustments."""
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    weight_history = await get_weight_history(db, user_id, limit=14)
    workouts = await get_workout_logs(db, user_id, limit=14)
    status = await get_current_status(db, user_id)

    parts = []
    if plan:
        parts.append(
            f"Current plan: {plan.calories_target} kcal "
            f"(P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g) | "
            f"{plan.meals_per_day} meals/day"
        )
    else:
        parts.append("No active plan")

    if weight_history and len(weight_history) >= 2:
        trend = round(weight_history[0].weight_kg - weight_history[-1].weight_kg, 1)
        sign = "+" if trend > 0 else ""
        parts.append(f"Weight trend (2w): {sign}{trend}kg")

    wo_count = len(workouts)
    parts.append(f"Workouts last 2w: {wo_count}")

    if status and status.status != "normal":
        parts.append(f"Status: {status.status}")

    hint = "PLAN_ADJUSTMENT_CONTEXT: " + " || ".join(parts)
    return {
        "action_done": "adjustment_context_shown",
        "data": {},
        "response_hint": hint,
    }


async def _handle_express_workout(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Gather context for AI to suggest a quick workout."""
    workout_plan = await get_active_workout_plan(db, user_id)
    today_plan = await get_today_workout(db, user_id)
    status = await get_current_status(db, user_id)

    parts = []
    if today_plan:
        parts.append(
            f"Today's planned: {today_plan.name} ({len(today_plan.exercises)} exercises)"
        )
    elif workout_plan:
        parts.append(
            f"Has plan: {workout_plan.name} ({workout_plan.days_per_week}d/wk)"
        )
    else:
        parts.append("No workout plan")

    if status and status.status != "normal":
        parts.append(f"Status: {status.status} — adjust accordingly")

    hint = "EXPRESS_WORKOUT_CONTEXT: " + " || ".join(parts)
    return {"action_done": "express_workout_context", "data": {}, "response_hint": hint}


async def _handle_notification_settings(
    user_id: uuid.UUID, db: AsyncSession
) -> dict[str, Any]:
    """Show user's current notification/reminder state."""
    from app.modules.supplements.service import get_user_supplements
    from app.modules.users.service import get_preferences

    prefs = await get_preferences(db, user_id)
    supps = await get_user_supplements(db, user_id)

    notif_prefs = [p for p in prefs if p.category == "notification"]
    reminder_supps = [s for s in supps if s.reminder_enabled]

    parts = []
    if notif_prefs:
        parts.append(f"Notification preferences: {len(notif_prefs)}")
    if reminder_supps:
        parts.append(f"Supplement reminders: {len(reminder_supps)} active")
    if not parts:
        parts.append("No notification settings configured")

    hint = "NOTIFICATION_SETTINGS: " + " | ".join(parts)
    return {"action_done": "notifications_shown", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Context-enhanced AI intents (fetch user data, let AI advise)
# ---------------------------------------------------------------------------


async def _handle_craving(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())
    logged_kcal = sum(m.total_calories or 0 for m in meals_today)

    remaining = (plan.calories_target - logged_kcal) if plan else None
    hint = f"CRAVING_CONTEXT: logged {round(logged_kcal)} kcal today"
    if remaining is not None:
        hint += f" | {round(remaining)} kcal remaining"
    hint += " | Help the user manage the craving with healthy alternatives"
    return {"action_done": "craving_context", "data": {}, "response_hint": hint}


async def _handle_extra_hunger(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())
    workouts_today = await get_workout_logs(db, user_id, limit=3)

    logged_kcal = sum(m.total_calories or 0 for m in meals_today)
    trained = any(w.created_at.date() == date.today() for w in workouts_today)

    hint = f"EXTRA_HUNGER_CONTEXT: logged {round(logged_kcal)} kcal"
    if plan:
        hint += f" of {plan.calories_target} target"
    if trained:
        hint += " | trained today (may need extra)"
    hint += " | Advise on whether to eat more or manage hunger"
    return {"action_done": "hunger_context", "data": {}, "response_hint": hint}


async def _handle_meal_prep(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import (
        get_active_plan,
        get_schedules,
        get_planned_meals,
    )
    from app.modules.pantry.service import get_pantry_items

    plan = await get_active_plan(db, user_id)
    pantry = await get_pantry_items(db, user_id)

    parts = []
    if plan:
        schedules = await get_schedules(db, plan.id)
        for s in schedules:
            meals = await get_planned_meals(db, s.id)
            if meals:
                parts.append(f"{s.name}: {', '.join(m.food_name for m in meals)}")
        parts.insert(0, f"Plan: {plan.calories_target} kcal/day")
    else:
        parts.append("No active plan")

    if pantry:
        parts.append(f"Pantry: {', '.join(i.food_name for i in pantry[:15])}")

    hint = "MEAL_PREP_CONTEXT: " + " || ".join(parts)
    hint += " | Help create a meal prep plan for the week"
    return {"action_done": "meal_prep_context", "data": {}, "response_hint": hint}


async def _handle_ask_nutrition(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)

    parts = []
    if user:
        if user.goal:
            parts.append(f"Goal: {user.goal}")
        if user.restrictions:
            parts.append(f"Restrictions: {user.restrictions}")
    if plan:
        parts.append(
            f"Plan: {plan.calories_target} kcal "
            f"(P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g)"
        )

    hint = "NUTRITION_CONTEXT: " + (
        " | ".join(parts) if parts else "no plan/profile data"
    )
    hint += " | Answer the user's nutrition question considering their context"
    return {"action_done": "nutrition_context", "data": {}, "response_hint": hint}


async def _handle_demotivation(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    achievements = await get_achievements(db, user_id)
    streaks = await get_streaks(db, user_id)
    workouts = await get_workout_logs(db, user_id, limit=30)
    weight_history = await get_weight_history(db, user_id, limit=30)

    parts = []
    if achievements:
        parts.append(f"Achievements: {len(achievements)} earned")
    if streaks:
        best = max(streaks, key=lambda s: s.best_streak)
        parts.append(f"Best streak: {best.streak_type} {best.best_streak}d")
    if workouts:
        parts.append(f"Total workouts: {len(workouts)}")
    if weight_history and len(weight_history) >= 2:
        diff = round(weight_history[0].weight_kg - weight_history[-1].weight_kg, 1)
        if diff != 0:
            parts.append(f"Weight change: {'+' if diff > 0 else ''}{diff}kg")

    hint = "DEMOTIVATION_CONTEXT: " + (
        " | ".join(parts) if parts else "new user, encourage to start"
    )
    hint += " | Motivate the user, highlight progress, be empathetic"
    return {"action_done": "demotivation_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Guidance-only intents (no DB action, instruct the user)
# ---------------------------------------------------------------------------


def _handle_photo_guidance(intent: str) -> dict[str, Any]:
    guidance_map = {
        "log_meal_from_photo": "PHOTO_GUIDANCE: To log a meal from a photo, send the image through Telegram and I'll analyze it",
        "log_weight_from_photo": "PHOTO_GUIDANCE: To log weight from a scale photo, send the image through Telegram",
        "progress_photo": "PHOTO_GUIDANCE: To save a progress photo, send it through Telegram with the caption 'foto de progreso'",
    }
    hint = guidance_map.get(intent, "PHOTO_GUIDANCE: send the photo through Telegram")
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}


def _handle_scan_guidance(intent: str) -> dict[str, Any]:
    guidance_map = {
        "scan_fridge": "SCAN_GUIDANCE: To scan your fridge, send a photo through Telegram and I'll identify the items",
        "scan_receipt": "SCAN_GUIDANCE: To scan a receipt, send a photo through Telegram and I'll extract the food items",
        "scan_barcode": "SCAN_GUIDANCE: To scan a barcode, send a photo of it through Telegram",
    }
    hint = guidance_map.get(intent, "SCAN_GUIDANCE: send the image through Telegram")
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}


def _handle_export_guidance() -> dict[str, Any]:
    hint = "EXPORT_GUIDANCE: Data export is available through the web dashboard or by contacting support"
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}


def _handle_delete_guidance() -> dict[str, Any]:
    hint = "DELETE_GUIDANCE: Account deletion requires confirmation. Contact support or use the web dashboard settings"
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}


def _handle_voice_guidance() -> dict[str, Any]:
    hint = "VOICE_GUIDANCE: To log by voice, send a voice message through Telegram and I'll transcribe and process it"
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Workout plan generation
# ---------------------------------------------------------------------------


async def _handle_generate_workout_plan(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.workouts.service import (
        create_workout_plan,
        add_plan_day,
        add_plan_exercise,
        get_active_workout_plan,
    )
    from sqlalchemy import select
    from app.modules.exercises.models import Exercise

    user = await get_user(db, user_id)
    profile = {}
    if user:
        profile = {
            "age": user.age,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "gender": user.gender,
            "activity_level": user.activity_level,
            "goal": user.goal,
        }

    plan_data = await extract_workout_plan_request(text, profile, uid, redis_client, db)
    if not plan_data or not plan_data.get("days"):
        return {
            "action_done": None,
            "data": {},
            "response_hint": "Could not generate workout plan from the request.",
        }

    # Deactivate existing plan (save version first)
    existing = await get_active_workout_plan(db, user_id)
    if existing:
        await save_version(
            db,
            user_id,
            plan_type="workout",
            plan_id=existing.id,
            snapshot={
                "name": existing.name,
                "days_per_week": existing.days_per_week,
                "goal": existing.goal,
                "level": existing.level,
                "equipment": existing.equipment,
            },
            change_reason="new_workout_plan_generated",
        )
        existing.is_active = False
        await db.flush()

    new_plan = await create_workout_plan(
        db,
        user_id,
        {
            "name": plan_data.get("name", "AI Plan"),
            "days_per_week": plan_data.get("days_per_week", len(plan_data["days"])),
            "goal": plan_data.get("goal", "general"),
            "level": plan_data.get("level", "intermediate"),
            "equipment": plan_data.get("equipment", "gym"),
            "start_date": date.today(),
            "is_active": True,
            "ai_generated": True,
        },
    )

    for day_data in plan_data["days"]:
        day = await add_plan_day(
            db,
            new_plan.id,
            {
                "day_number": day_data.get("day_number", 1),
                "name": day_data.get("name", "Day"),
                "muscle_groups": day_data.get("muscle_groups", ""),
                "order_index": day_data.get("day_number", 1) - 1,
            },
        )

        for idx, ex_data in enumerate(day_data.get("exercises", [])):
            ex_name = ex_data.get("exercise_name", "unknown")
            result = await db.execute(
                select(Exercise).where(Exercise.name.ilike(f"%{_escape_like(ex_name)}%")).limit(1)
            )
            exercise = result.scalar_one_or_none()
            if not exercise:
                exercise = Exercise(
                    name=ex_name, muscle_group="other", equipment="other"
                )
                db.add(exercise)
                await db.flush()

            await add_plan_exercise(
                db,
                day.id,
                {
                    "exercise_id": exercise.id,
                    "order_index": idx,
                    "sets": ex_data.get("sets", 3),
                    "reps_min": ex_data.get("reps_min", 8),
                    "reps_max": ex_data.get("reps_max", 12),
                    "rest_seconds": ex_data.get("rest_seconds", 90),
                    "rpe_target": ex_data.get("rpe_target"),
                    "notes": ex_data.get("notes"),
                },
            )

    day_names = [d.get("name", "?") for d in plan_data["days"]]
    hint = (
        f"WORKOUT_PLAN_GENERATED: {plan_data.get('name', 'AI Plan')} | "
        f"{len(plan_data['days'])} days/week | "
        f"Goal: {plan_data.get('goal', '?')} | "
        f"Days: {', '.join(day_names)}"
    )
    return {
        "action_done": "workout_plan_generated",
        "data": {"plan_id": str(new_plan.id)},
        "response_hint": hint,
    }


# ---------------------------------------------------------------------------
# Conversational intents
# ---------------------------------------------------------------------------


def _handle_conversational(intent: str) -> dict[str, Any]:
    hints = {
        "greeting": "GREETING: The user is greeting you. Respond warmly and ask how you can help with their fitness/nutrition today.",
        "goodbye": "GOODBYE: The user is saying goodbye. Wish them well and remind them you're here when they need you.",
        "thanks": "THANKS: The user is thanking you. Acknowledge warmly and offer further help.",
    }
    return {
        "action_done": "conversational",
        "data": {},
        "response_hint": hints.get(intent, "Respond naturally."),
    }


def _handle_help() -> dict[str, Any]:
    hint = (
        "HELP: Show the user what I can do. Key capabilities:\n"
        "📋 NUTRITION: Log meals, generate nutrition plans, track macros, ask about calories, recipes, meal prep\n"
        "🏋️ WORKOUT: Start/end workouts, log sets & cardio, generate workout plans, view PRs, exercise tutorials\n"
        "⚖️ TRACKING: Log weight, body measurements, water, sleep, mood, steps\n"
        "🥗 PANTRY: Add/remove pantry items, recipe suggestions, shopping lists\n"
        "💊 SUPPLEMENTS: Log intake, manage supplement stack\n"
        "🏆 PROGRESS: View achievements, streaks, compare progress, weekly check-in\n"
        "⚙️ CONFIG: Change goals, set restrictions, adjust plans, notification settings\n"
        "🩺 WELLNESS: Report symptoms, log cycle, stress/demotivation support\n"
        "📸 PHOTOS: Send photos to log meals, weight, or track progress\n"
        "🎙️ VOICE: Send voice messages to log anything\n"
        "✏️ CORRECTIONS: Undo last action or edit entries"
    )
    return {"action_done": "help_shown", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Corrections (undo / edit)
# ---------------------------------------------------------------------------


async def _handle_undo_last(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from sqlalchemy import select, desc
    from app.modules.tracking.models import MealLog, WaterLog, WeightLog

    # Try to find the most recent log across types
    latest = None
    latest_type = None

    for model, label in [
        (MealLog, "meal"),
        (WaterLog, "water"),
        (WeightLog, "weight"),
    ]:
        result = await db.execute(
            select(model)
            .where(model.user_id == user_id)
            .order_by(desc(model.created_at))
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry and (latest is None or entry.created_at > latest.created_at):
            latest = entry
            latest_type = label

    # Also check wellness models
    from app.modules.wellness.models import SleepLog, AlcoholLog, MoodLog, StepLog

    for model, label in [
        (SleepLog, "sleep"),
        (AlcoholLog, "alcohol"),
        (MoodLog, "mood"),
        (StepLog, "steps"),
    ]:
        result = await db.execute(
            select(model)
            .where(model.user_id == user_id)
            .order_by(desc(model.created_at))
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry and (latest is None or entry.created_at > latest.created_at):
            latest = entry
            latest_type = label

    if not latest:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "UNDO: nothing to undo, no recent entries found",
        }

    await db.delete(latest)
    await db.flush()

    hint = f"UNDO_DONE: deleted last {latest_type} entry (created {latest.created_at.strftime('%d/%m %H:%M')})"
    return {
        "action_done": "undo_done",
        "data": {"deleted_type": latest_type},
        "response_hint": hint,
    }


async def _handle_edit_entry(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Try to find and edit the most recent matching entry."""
    from sqlalchemy import select, desc
    from app.modules.tracking.models import MealLog, WeightLog

    # Check if user wants to edit weight
    weight = await extract_weight(text, uid, redis_client, db)
    if weight is not None:
        result = await db.execute(
            select(WeightLog)
            .where(WeightLog.user_id == user_id)
            .order_by(desc(WeightLog.created_at))
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry:
            old_val = entry.weight
            entry.weight = weight
            await db.flush()
            hint = f"EDIT_DONE: weight updated from {old_val}kg to {weight}kg"
            return {"action_done": "entry_edited", "data": {"type": "weight"}, "response_hint": hint}

    # Check if user wants to edit calories on last meal
    meal_data = await extract_meal(text, uid, redis_client, db)
    if meal_data.get("total_calories"):
        result = await db.execute(
            select(MealLog)
            .where(MealLog.user_id == user_id)
            .order_by(desc(MealLog.created_at))
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry:
            old_cal = entry.total_calories
            entry.total_calories = meal_data["total_calories"]
            if meal_data.get("description"):
                entry.description = meal_data["description"]
            await db.flush()
            hint = f"EDIT_DONE: last meal updated — calories: {old_cal} → {meal_data['total_calories']}"
            return {"action_done": "entry_edited", "data": {"type": "meal"}, "response_hint": hint}

    return {
        "action_done": None,
        "data": {},
        "response_hint": "EDIT: could not determine what to edit. Try 'cambia mi peso a Xkg' or specify the entry.",
    }


# ---------------------------------------------------------------------------
# Recipe & food helpers
# ---------------------------------------------------------------------------


async def _handle_recipe_request(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan
    from app.modules.pantry.service import get_pantry_items

    plan = await get_active_plan(db, user_id)
    pantry = await get_pantry_items(db, user_id)
    user = await get_user(db, user_id)

    parts = [f"REQUEST: {text}"]
    if plan:
        parts.append(
            f"TARGETS: {plan.calories_target} kcal P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g"
        )
    if user and user.restrictions:
        parts.append(f"RESTRICTIONS: {user.restrictions}")
    if pantry:
        parts.append(f"PANTRY: {', '.join(i.food_name for i in pantry[:15])}")

    hint = "RECIPE_CONTEXT: " + " || ".join(parts)
    hint += " | Suggest a recipe that matches the request, targets, and restrictions"
    return {"action_done": "recipe_context", "data": {}, "response_hint": hint}


async def _handle_calorie_lookup(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    meal_data = await extract_meal(text, uid, redis_client, db)
    items = meal_data.get("items", [])
    if items:
        lines = []
        for item in items:
            line = f"{item.get('food_name', '?')}: {item.get('calories', '?')} kcal"
            if item.get("protein"):
                line += f" | P:{item['protein']}g C:{item.get('carbs','?')}g F:{item.get('fat','?')}g"
            lines.append(line)
        hint = "CALORIE_LOOKUP: " + " || ".join(lines)
    else:
        hint = f"CALORIE_LOOKUP: Could not identify food in '{text}'"
    return {"action_done": "calorie_lookup", "data": {"items": items}, "response_hint": hint}


async def _handle_food_substitution(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)

    parts = [f"REQUEST: {text}"]
    if user and user.restrictions:
        parts.append(f"RESTRICTIONS: {user.restrictions}")
    if plan:
        parts.append(f"TARGETS: P:{plan.protein_g}g C:{plan.carbs_g}g F:{plan.fat_g}g")

    hint = "FOOD_SUBSTITUTION_CONTEXT: " + " || ".join(parts)
    hint += " | Suggest substitutions that match macros and restrictions"
    return {"action_done": "substitution_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# BMI / body calculations
# ---------------------------------------------------------------------------


async def _handle_calculate_bmi(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    user = await get_user(db, user_id)
    if not user or not user.height_cm or not user.weight_kg:
        return {
            "action_done": None,
            "data": {},
            "response_hint": "CALCULATE_BMI: Missing height or weight. Ask user to provide them.",
        }

    height_m = user.height_cm / 100
    bmi = round(user.weight_kg / (height_m ** 2), 1)

    if bmi < 18.5:
        category = "bajo peso"
    elif bmi < 25:
        category = "peso normal"
    elif bmi < 30:
        category = "sobrepeso"
    else:
        category = "obesidad"

    # BMR (Mifflin-St Jeor)
    bmr = None
    if user.age and user.gender:
        if user.gender.lower() in ("m", "male", "masculino", "hombre"):
            bmr = round(10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + 5)
        else:
            bmr = round(10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age - 161)

    hint = f"BMI_CALCULATED: {bmi} ({category}) | Height: {user.height_cm}cm Weight: {user.weight_kg}kg"
    if bmr:
        hint += f" | BMR: {bmr} kcal/day"
    return {"action_done": "bmi_calculated", "data": {"bmi": bmi, "bmr": bmr}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Workout helpers
# ---------------------------------------------------------------------------


async def _handle_workout_alternative(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.modules.exercises.models import Exercise

    set_data = await extract_workout_set(text, uid, redis_client, db)
    ex_name = set_data.get("exercise_name", text)

    result = await db.execute(
        select(Exercise).where(Exercise.name.ilike(f"%{_escape_like(ex_name)}%")).limit(1)
    )
    exercise = result.scalar_one_or_none()

    parts = [f"EXERCISE: {ex_name}"]
    if exercise:
        parts.append(f"Muscle: {exercise.muscle_group}")
        if exercise.equipment:
            parts.append(f"Equipment: {exercise.equipment}")

    status = await get_current_status(db, user_id)
    if status and status.status != "normal":
        parts.append(f"Status: {status.status}")

    hint = "WORKOUT_ALTERNATIVE_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest alternative exercises for the same muscle group"
    return {"action_done": "alternative_context", "data": {}, "response_hint": hint}


async def _handle_exercise_tutorial(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.modules.exercises.models import Exercise

    set_data = await extract_workout_set(text, uid, redis_client, db)
    ex_name = set_data.get("exercise_name", text)

    result = await db.execute(
        select(Exercise).where(Exercise.name.ilike(f"%{_escape_like(ex_name)}%")).limit(1)
    )
    exercise = result.scalar_one_or_none()

    parts = [f"EXERCISE: {ex_name}"]
    if exercise:
        parts.append(f"Muscle: {exercise.muscle_group}")
        if exercise.demo_url:
            parts.append(f"Demo: {exercise.demo_url}")
        if exercise.notes:
            parts.append(f"Notes: {exercise.notes}")

    hint = "EXERCISE_TUTORIAL_CONTEXT: " + " | ".join(parts)
    hint += " | Explain proper form, common mistakes, and cues"
    return {"action_done": "tutorial_context", "data": {}, "response_hint": hint}


async def _handle_deload_week(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    plan = await get_active_workout_plan(db, user_id)
    workouts = await get_workout_logs(db, user_id, limit=14)

    parts = []
    if plan:
        parts.append(f"Plan: {plan.name} | phase: {plan.phase or '?'} week {plan.phase_week or '?'}")
    parts.append(f"Recent workouts: {len(workouts)} in last 2 weeks")

    hint = "DELOAD_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest a deload week protocol: reduce volume 40-50%, keep intensity moderate"
    return {"action_done": "deload_context", "data": {}, "response_hint": hint}


async def _handle_rest_day_advice(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    today_plan = await get_today_workout(db, user_id)
    status = await get_current_status(db, user_id)

    parts = []
    if today_plan:
        parts.append(f"Today's plan: {today_plan.name} (but user wants rest)")
    else:
        parts.append("No workout planned today")
    if status and status.status != "normal":
        parts.append(f"Status: {status.status}")

    hint = "REST_DAY_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest active recovery, stretching, or mobility work"
    return {"action_done": "rest_day_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Nutrition lifestyle intents
# ---------------------------------------------------------------------------


async def _handle_cheat_day(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())
    logged_kcal = sum(m.total_calories or 0 for m in meals_today)

    parts = []
    if plan:
        parts.append(f"Normal target: {plan.calories_target} kcal")
    parts.append(f"Already logged: {round(logged_kcal)} kcal")

    hint = "CHEAT_DAY_CONTEXT: " + " | ".join(parts)
    hint += " | Acknowledge the cheat day positively, suggest logging meals anyway, remind that one day doesn't ruin progress"
    return {"action_done": "cheat_day_context", "data": {}, "response_hint": hint}


async def _handle_fasting(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)

    parts = []
    if plan:
        parts.append(f"Current plan: {plan.calories_target} kcal, {plan.meals_per_day} meals/day")
    if user and user.goal:
        parts.append(f"Goal: {user.goal}")

    hint = "FASTING_CONTEXT: " + " | ".join(parts)
    hint += " | Advise on intermittent fasting (16/8, 18/6, etc.), how to adjust meal plan, when to eat, what to drink during fasting"
    return {"action_done": "fasting_context", "data": {}, "response_hint": hint}


async def _handle_pre_post_workout_meal(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    today_workout = await get_today_workout(db, user_id)
    user = await get_user(db, user_id)

    parts = []
    if plan:
        parts.append(f"Targets: {plan.calories_target} kcal P:{plan.protein_g}g C:{plan.carbs_g}g")
    if today_workout:
        parts.append(f"Today's workout: {today_workout.name}")
    if user and user.goal:
        parts.append(f"Goal: {user.goal}")

    hint = "PRE_POST_WORKOUT_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest pre-workout (1-2h before) and post-workout meals based on plan & goal"
    return {"action_done": "pre_post_workout_context", "data": {}, "response_hint": hint}


async def _handle_meal_timing(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan, get_schedules

    plan = await get_active_plan(db, user_id)
    parts = []
    if plan:
        schedules = await get_schedules(db, plan.id)
        for s in schedules:
            t = s.target_time.strftime("%H:%M") if s.target_time else "?"
            parts.append(f"{s.name}: {t}")
        parts.insert(0, f"Plan: {plan.meals_per_day} meals/day")
    else:
        parts.append("No active plan")

    hint = "MEAL_TIMING_CONTEXT: " + " | ".join(parts)
    hint += " | Advise on optimal meal timing for their goals"
    return {"action_done": "meal_timing_context", "data": {}, "response_hint": hint}


async def _handle_budget_meals(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)

    parts = []
    if plan:
        parts.append(f"Targets: {plan.calories_target} kcal P:{plan.protein_g}g")
    if user:
        if user.restrictions:
            parts.append(f"Restrictions: {user.restrictions}")
        if user.weekly_budget:
            parts.append(f"Weekly budget: ${user.weekly_budget}")

    hint = "BUDGET_MEALS_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest affordable, nutritious meals that fit their macros and budget"
    return {"action_done": "budget_meals_context", "data": {}, "response_hint": hint}


async def _handle_refeed_day(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    weight_history = await get_weight_history(db, user_id, limit=14)

    parts = []
    if plan:
        parts.append(f"Current target: {plan.calories_target} kcal")
    if weight_history and len(weight_history) >= 2:
        trend = round(weight_history[0].weight_kg - weight_history[-1].weight_kg, 1)
        parts.append(f"Weight trend (2w): {'+' if trend > 0 else ''}{trend}kg")

    hint = "REFEED_CONTEXT: " + " | ".join(parts)
    hint += " | Suggest a refeed day protocol: increase carbs 20-30%, keep protein same, explain benefits for metabolism and hormones"
    return {"action_done": "refeed_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Progress & analytics
# ---------------------------------------------------------------------------


async def _handle_compare_progress(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.body.service import get_measurements

    weight_history = await get_weight_history(db, user_id, limit=30)
    workouts = await get_workout_logs(db, user_id, limit=30)
    measurements = await get_measurements(db, user_id, limit=2)
    prs = await get_personal_records(db, user_id)
    streaks = await get_streaks(db, user_id)

    parts = []
    if weight_history and len(weight_history) >= 2:
        w_now = weight_history[0].weight_kg
        w_then = weight_history[-1].weight_kg
        diff = round(w_now - w_then, 1)
        parts.append(f"Weight: {w_then}→{w_now}kg ({'+' if diff > 0 else ''}{diff})")

    if workouts:
        this_week = len([w for w in workouts if (date.today() - w.created_at.date()).days < 7])
        last_week = len([w for w in workouts if 7 <= (date.today() - w.created_at.date()).days < 14])
        parts.append(f"Workouts: this week {this_week}, last week {last_week}")

    if measurements and len(measurements) >= 2:
        new, old = measurements[0], measurements[1]
        if new.waist_cm and old.waist_cm:
            parts.append(f"Waist: {old.waist_cm}→{new.waist_cm}cm")

    if prs:
        parts.append(f"PRs: {len(prs)} total")

    if streaks:
        best = max(streaks, key=lambda s: s.current_streak)
        parts.append(f"Best streak: {best.streak_type} {best.current_streak}d")

    hint = "COMPARE_PROGRESS: " + (" | ".join(parts) if parts else "not enough data to compare")
    hint += " | Highlight improvements and encourage the user"
    return {"action_done": "progress_compared", "data": {}, "response_hint": hint}


async def _handle_plateau_help(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    weight_history = await get_weight_history(db, user_id, limit=21)
    workouts = await get_workout_logs(db, user_id, limit=14)
    sleep_history = []
    from app.modules.wellness.service import get_sleep_history
    sleep_history = await get_sleep_history(db, user_id, limit=7)

    parts = []
    if plan:
        parts.append(f"Plan: {plan.calories_target} kcal")
    if weight_history and len(weight_history) >= 3:
        weights = [w.weight_kg for w in weight_history[:7]]
        avg_recent = round(sum(weights) / len(weights), 1)
        parts.append(f"Avg weight last week: {avg_recent}kg")
    parts.append(f"Workouts last 2w: {len(workouts)}")
    if sleep_history:
        avg_sleep = round(sum(s.hours for s in sleep_history) / len(sleep_history), 1)
        parts.append(f"Avg sleep: {avg_sleep}h")

    hint = "PLATEAU_CONTEXT: " + " | ".join(parts)
    hint += " | Analyze possible causes (calories too low/high, not enough protein, sleep, stress, overtraining) and suggest adjustments"
    return {"action_done": "plateau_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Wellness & lifestyle (new)
# ---------------------------------------------------------------------------


async def _handle_set_water_goal(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    water_data = await extract_water(text, uid, redis_client, db)
    user = await get_user(db, user_id)
    if not user:
        return {"action_done": None, "data": {}, "response_hint": "User not found."}

    await update_user(db, user, {"water_goal_ml": water_data})
    hint = f"WATER_GOAL_SET: {round(water_data)} ml/day"
    return {
        "action_done": "water_goal_set",
        "data": {"water_goal_ml": water_data},
        "response_hint": hint,
    }


async def _handle_sleep_tips(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.wellness.service import get_sleep_history

    sleep_history = await get_sleep_history(db, user_id, limit=7)

    parts = []
    if sleep_history:
        avg_hours = round(sum(s.hours for s in sleep_history) / len(sleep_history), 1)
        avg_quality = [s.quality for s in sleep_history if s.quality]
        parts.append(f"Avg sleep: {avg_hours}h")
        if avg_quality:
            parts.append(f"Avg quality: {round(sum(avg_quality) / len(avg_quality), 1)}/5")
    else:
        parts.append("No sleep data logged")

    hint = "SLEEP_TIPS_CONTEXT: " + " | ".join(parts)
    hint += " | Give personalized sleep improvement tips based on their data"
    return {"action_done": "sleep_tips_context", "data": {}, "response_hint": hint}


async def _handle_stress(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.wellness.service import log_mood

    mood_data = await extract_mood(text, uid, redis_client, db)
    await log_mood(db, user_id, {
        "mood": mood_data.get("mood", "stressed"),
        "energy_level": mood_data.get("energy_level"),
        "notes": mood_data.get("notes", text),
    })

    hint = f"STRESS_LOGGED: mood={mood_data.get('mood', 'stressed')}"
    if mood_data.get("energy_level"):
        hint += f" | energy: {mood_data['energy_level']}/5"
    hint += " | Acknowledge the stress empathetically, suggest coping strategies (exercise, breathing, rest)"
    return {"action_done": "stress_logged", "data": {}, "response_hint": hint}


async def _handle_log_mood(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.wellness.service import log_mood

    mood_data = await extract_mood(text, uid, redis_client, db)
    entry = await log_mood(db, user_id, {
        "mood": mood_data.get("mood", "neutral"),
        "energy_level": mood_data.get("energy_level"),
        "notes": mood_data.get("notes"),
    })

    hint = f"MOOD_LOGGED: {mood_data.get('mood', 'neutral')}"
    if mood_data.get("energy_level"):
        hint += f" | energy: {mood_data['energy_level']}/5"
    return {
        "action_done": "mood_logged",
        "data": {"mood_id": str(entry.id)},
        "response_hint": hint,
    }


async def _handle_log_steps(
    text: str,
    uid: str,
    user_id: uuid.UUID,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    from app.modules.wellness.service import log_steps, get_steps_today

    steps_data = await extract_steps(text, uid, redis_client, db)
    entry = await log_steps(db, user_id, {
        "steps": steps_data.get("steps", 0),
        "distance_km": steps_data.get("distance_km"),
        "calories_burned": steps_data.get("calories_burned"),
    })

    total = await get_steps_today(db, user_id)
    hint = f"STEPS_LOGGED: {steps_data.get('steps', 0)} steps | total today: {total}"
    if steps_data.get("distance_km"):
        hint += f" | {steps_data['distance_km']} km"
    return {
        "action_done": "steps_logged",
        "data": {"step_id": str(entry.id), "total_today": total},
        "response_hint": hint,
    }


async def _handle_hydration_check(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.tracking.service import get_water_today

    water_today = await get_water_today(db, user_id)
    user = await get_user(db, user_id)
    goal = user.water_goal_ml if user and user.water_goal_ml else 2500

    pct = round((water_today / goal) * 100) if goal else 0
    remaining = max(0, goal - water_today)

    hint = (
        f"HYDRATION_CHECK: {round(water_today)}ml of {round(goal)}ml ({pct}%) | "
        f"Remaining: {round(remaining)}ml"
    )
    if pct >= 100:
        hint += " | Goal reached! 🎉"
    elif pct >= 75:
        hint += " | Almost there, keep drinking!"
    elif pct < 50:
        hint += " | You need to drink more water today"

    return {"action_done": "hydration_checked", "data": {"water_ml": water_today, "goal_ml": goal}, "response_hint": hint}


async def _handle_protein_goal(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)
    meals_today = await get_meals_by_date(db, user_id, date.today())

    consumed_p = sum(getattr(m, "protein", 0) or 0 for m in meals_today)

    parts = []
    if plan:
        parts.append(f"Target: {plan.protein_g}g/day")
        remaining = max(0, plan.protein_g - consumed_p)
        parts.append(f"Consumed: {round(consumed_p)}g | Remaining: {round(remaining)}g")
    elif user and user.weight_kg:
        recommended = round(user.weight_kg * 1.6)
        parts.append(f"Recommended (1.6g/kg): {recommended}g/day")
        parts.append(f"Consumed today: {round(consumed_p)}g")
    else:
        parts.append(f"Consumed today: {round(consumed_p)}g | No plan/weight for recommendation")

    hint = "PROTEIN_GOAL: " + " | ".join(parts)
    return {"action_done": "protein_goal_shown", "data": {}, "response_hint": hint}


async def _handle_body_recomp(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    from app.modules.nutrition.service import get_active_plan

    plan = await get_active_plan(db, user_id)
    user = await get_user(db, user_id)
    weight_history = await get_weight_history(db, user_id, limit=14)

    parts = []
    if user:
        if user.weight_kg:
            parts.append(f"Weight: {user.weight_kg}kg")
        if user.body_fat_pct:
            parts.append(f"BF: {user.body_fat_pct}%")
        if user.goal:
            parts.append(f"Goal: {user.goal}")
    if plan:
        parts.append(f"Current plan: {plan.calories_target} kcal P:{plan.protein_g}g")

    hint = "BODY_RECOMP_CONTEXT: " + " | ".join(parts)
    hint += " | Advise on body recomposition: slight deficit or maintenance, high protein (2g/kg), progressive overload, sleep importance"
    return {"action_done": "body_recomp_context", "data": {}, "response_hint": hint}


async def _handle_injury_exercise(user_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    status = await get_current_status(db, user_id)
    from app.modules.wellness.service import get_symptom_history

    symptoms = await get_symptom_history(db, user_id, limit=5)

    parts = []
    if status and status.status != "normal":
        parts.append(f"Status: {status.status}")
    if symptoms:
        recent = [f"{s.symptom} (severity {s.severity})" for s in symptoms[:3]]
        parts.append(f"Recent symptoms: {', '.join(recent)}")

    hint = "INJURY_EXERCISE_CONTEXT: " + " | ".join(parts) if parts else "INJURY_EXERCISE_CONTEXT: no injury data"
    hint += " | Suggest exercises that avoid the injured area, focus on safe alternatives"
    return {"action_done": "injury_exercise_context", "data": {}, "response_hint": hint}


# ---------------------------------------------------------------------------
# Reminders (guidance only — actual reminders are via n8n)
# ---------------------------------------------------------------------------


def _handle_set_reminder_guidance() -> dict[str, Any]:
    hint = (
        "SET_REMINDER_GUIDANCE: Reminders are managed through notifications. "
        "You can set supplement reminders, meal reminders, and workout reminders. "
        "Tell me what you want to be reminded about and when."
    )
    return {"action_done": "guidance_given", "data": {}, "response_hint": hint}
