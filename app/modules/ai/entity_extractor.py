"""Entity extractor — uses AI to convert free text into structured domain data."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.openai.client import (
    AIBudgetExceeded,
    AIRateLimited,
    AIServiceUnavailable,
    chat_completion,
)

logger = structlog.stdlib.get_logger()


async def extract_meal(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract structured meal data from free text.

    Returns:
        {
            "description": str,
            "items": [{"food_name": str, "quantity": float|null, "unit": str|null,
                       "calories": float|null, "protein": float|null,
                       "carbs": float|null, "fat": float|null}],
            "total_calories": float|null,
            "is_cheat": bool
        }
    """
    system = (
        "You are a nutrition database. Extract structured meal data from the user message. "
        "Use common food nutrition values (per 100g or per unit). Estimate when not certain. "
        "Respond ONLY with a JSON object in this exact schema:\n"
        '{"description": "<brief meal description>", '
        '"total_calories": <number or null>, '
        '"is_cheat": <true if clearly unhealthy/cheat meal, else false>, '
        '"items": [{"food_name": "<name>", "quantity": <number or null>, '
        '"unit": "<g|ml|unit|slice|etc or null>", '
        '"calories": <number or null>, "protein": <number or null>, '
        '"carbs": <number or null>, "fat": <number or null>}]}\n'
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="meal_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return data
    except (AIBudgetExceeded, AIRateLimited, AIServiceUnavailable):
        raise
    except (json.JSONDecodeError, KeyError):
        # Minimal fallback — save description only
        return {
            "description": text,
            "items": [],
            "total_calories": None,
            "is_cheat": False,
        }


async def extract_water(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> float:
    """Extract water amount in ml from free text. Returns ml as float."""
    system = (
        "Extract the water/liquid amount from the user message. "
        "Convert to milliliters (ml). A glass = 250ml, a bottle = 500ml, a cup = 200ml. "
        'Respond ONLY with a JSON object: {"amount_ml": <number>}. '
        "If unclear, use 250 as default. Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="water_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return float(data.get("amount_ml", 250))
    except Exception:
        return 250.0


async def extract_weight(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> float | None:
    """Extract body weight in kg from free text."""
    system = (
        "Extract the body weight value from the user message. "
        "Convert to kilograms (kg) if needed (lbs ÷ 2.205). "
        'Respond ONLY with a JSON object: {"weight_kg": <number or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="weight_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        val = data.get("weight_kg")
        return float(val) if val is not None else None
    except Exception:
        return None


async def extract_sleep(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract sleep data from free text.

    Returns: {"hours_slept": float, "quality": int (1-5) or null}
    """
    system = (
        "Extract sleep data from the user message. "
        "Quality scale: 1=terrible, 2=bad, 3=ok, 4=good, 5=excellent. "
        "Infer quality from words like 'bien', 'mal', 'fatal', 'genial', 'good', 'bad'. "
        'Respond ONLY with JSON: {"hours_slept": <number>, "quality": <1-5 or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="sleep_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=60,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return {
            "hours_slept": float(data.get("hours_slept", 7)),
            "quality": int(data["quality"]) if data.get("quality") else None,
        }
    except Exception:
        return {"hours_slept": 7.0, "quality": None}


async def extract_alcohol(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract alcohol data. Returns {"drink_type": str, "units": float, "calories": float|null}."""
    system = (
        "Extract alcohol consumption data from the user message. "
        "A standard unit = 10ml pure alcohol. "
        "Beer 330ml = 1.5 units, wine 150ml = 1.5 units, spirits 30ml = 1 unit. "
        'Respond ONLY with JSON: {"drink_type": "<type>", "units": <number>, "calories": <number or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="alcohol_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return {
            "drink_type": data.get("drink_type", "unknown"),
            "units": float(data.get("units", 1.0)),
            "calories": float(data["calories"]) if data.get("calories") else None,
        }
    except Exception:
        return {"drink_type": "unknown", "units": 1.0, "calories": None}


async def extract_workout_set(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract workout set data from free text.

    Returns: {"exercise_name": str, "reps_done": int, "weight_kg": float|null,
              "sets": int, "rpe": float|null, "notes": str|null}
    """
    system = (
        "Extract workout set data from the user message. "
        "RPE (Rate of Perceived Exertion) scale 1-10. "
        'Respond ONLY with JSON: {"exercise_name": "<name>", "reps_done": <int>, '
        '"weight_kg": <number or null>, "sets": <int default 1>, '
        '"rpe": <1-10 or null>, "notes": <string or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="workout_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return data
    except Exception:
        return {
            "exercise_name": "unknown",
            "reps_done": 0,
            "weight_kg": None,
            "sets": 1,
            "rpe": None,
            "notes": text,
        }


async def extract_cardio(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract cardio data. Returns {"cardio_type": str, "duration_minutes": int, "distance_km": float|null, "calories_burned": float|null}."""  # noqa: E501
    system = (
        "Extract cardio session data from the user message. "
        'Respond ONLY with JSON: {"cardio_type": "<running|cycling|swimming|walking|elliptical|other>", '
        '"duration_minutes": <int>, "distance_km": <number or null>, "calories_burned": <number or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="cardio_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return {
            "cardio_type": data.get("cardio_type", "other"),
            "duration_minutes": int(data.get("duration_minutes", 30)),
            "distance_km": (
                float(data["distance_km"]) if data.get("distance_km") else None
            ),
            "calories_burned": (
                float(data["calories_burned"]) if data.get("calories_burned") else None
            ),
        }
    except Exception:
        return {
            "cardio_type": "other",
            "duration_minutes": 30,
            "distance_km": None,
            "calories_burned": None,
        }


async def extract_user_profile(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract user profile/goal data from free text.

    Returns partial dict — only include fields the user actually mentioned.
    Valid field keys: age, height_cm, weight_kg, gender, body_fat_pct,
    activity_level (sedentary|light|moderate|active|very_active),
    goal (lose_weight|gain_muscle|maintain|recomp|health),
    restrictions (text of dietary restrictions), water_goal_ml
    """
    system = (
        "Extract user profile and fitness goal data from the user message. "
        "ONLY include fields the user explicitly mentioned. Do NOT guess. "
        "Respond ONLY with a JSON object using this schema (include only mentioned fields):\n"
        '{"age": <int>, "height_cm": <float>, "weight_kg": <float>, '
        '"gender": "<male|female|other>", "body_fat_pct": <float>, '
        '"activity_level": "<sedentary|light|moderate|active|very_active>", '
        '"goal": "<lose_weight|gain_muscle|maintain|recomp|health>", '
        '"restrictions": "<comma separated dietary restrictions or null>", '
        '"diet_type": "<omnivore|vegetarian|vegan|keto|paleo|other>", '
        '"water_goal_ml": <int>}\n'
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="profile_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        # Remove null values
        return {k: v for k, v in data.items() if v is not None}
    except Exception:
        return {}


async def extract_nutrition_plan_request(
    text: str,
    user_profile: dict[str, Any],
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate a full nutrition plan from user profile + request.

    Returns: {
        "calories_target": int, "protein_g": int, "carbs_g": int, "fat_g": int,
        "meals_per_day": int,
        "schedules": [{"name": str, "target_time": "HH:MM",
                       "calories_target": int, "protein_target": int,
                       "carbs_target": int, "fat_target": int,
                       "planned_meals": [{"food_name": str, "quantity": float,
                                          "unit": str, "calories": float,
                                          "protein": float, "carbs": float, "fat": float}]}]
    }
    """
    profile_summary = ", ".join(f"{k}: {v}" for k, v in user_profile.items() if v)
    system = (
        "You are a certified sports nutritionist. Generate a complete nutrition plan. "
        f"User profile: {profile_summary}\n"
        "Calculate TDEE from the profile (Mifflin-St Jeor + activity multiplier). "
        "Adjust for goal: deficit for weight loss, surplus for muscle gain. "
        "Respond ONLY with a JSON object:\n"
        '{"calories_target": <int>, "protein_g": <int>, "carbs_g": <int>, "fat_g": <int>, '
        '"fiber_g": <int>, "meals_per_day": <int 3-6>, '
        '"schedules": [{"name": "<meal name>", "target_time": "<HH:MM>", '
        '"calories_target": <int>, "protein_target": <int>, "carbs_target": <int>, "fat_target": <int>, '
        '"planned_meals": [{"food_name": "<food>", "quantity": <float>, "unit": "<g|ml|unit>", '
        '"calories": <float>, "protein": <float>, "carbs": <float>, "fat": <float>}]}]}\n'
        "Include 3-6 meal slots with specific food suggestions. "
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="plan_generation",
            redis_client=redis_client,
            db_session=db,
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        return json.loads(response)
    except Exception:
        return {}


async def extract_symptom(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract symptom data. Returns {"symptom": str, "severity": int 1-5, "symptom_raw": str}."""
    system = (
        "Extract health symptom data from the user message. "
        "Severity: 1=minimal, 2=mild, 3=moderate, 4=severe, 5=emergency. "
        'Respond ONLY with JSON: {"symptom": "<short name>", "severity": <1-5>, "symptom_raw": "<user words>"}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="symptom_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        return json.loads(response)
    except Exception:
        return {"symptom": "unknown", "severity": 1, "symptom_raw": text}


async def extract_body_measurements(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract body measurements. Only include fields the user mentioned."""
    system = (
        "Extract body measurements from the user message. "
        "ONLY include fields the user explicitly mentioned. "
        "Respond ONLY with JSON (include only present): "
        '{"waist_cm": <float>, "hip_cm": <float>, "chest_cm": <float>, '
        '"arm_cm": <float>, "thigh_cm": <float>, '
        '"body_fat_pct": <float>, "body_fat_method": "<caliper|scan|scale|visual>"}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="measurement_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return {k: v for k, v in data.items() if v is not None}
    except Exception:
        return {}


async def extract_pantry_items(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """Extract pantry item(s) from free text."""
    system = (
        "Extract pantry/food items from the user message. "
        'Respond ONLY with JSON: {"items": [{"food_name": "<name>", '
        '"quantity": <number or null>, "unit": "<g|ml|unit|kg|etc or null>"}]}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="pantry_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return data.get("items", [])
    except Exception:
        return []


async def extract_cycle_data(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract menstrual cycle data from free text."""
    system = (
        "Extract menstrual cycle data. "
        'Respond ONLY with JSON: {"cycle_start": "<YYYY-MM-DD or null>", '
        '"cycle_end": "<YYYY-MM-DD or null>", "phase": "<menstruation|follicular|ovulation|luteal or null>"}. '
        "If the user says 'today' use today's date. "
        "Do not include any other text."
    )
    try:
        from datetime import date as _date

        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Today is {_date.today().isoformat()}. User says: {text}",
                },
            ],
            user_id=user_id,
            feature="cycle_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        return json.loads(response)
    except Exception:
        return {"cycle_start": None}


async def extract_supplement_name(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> str:
    """Extract supplement name from free text."""
    system = (
        "Extract the supplement name from the user message. "
        'Respond ONLY with JSON: {"supplement_name": "<name>"}. '
        "Common supplements: creatine, protein, omega-3, vitamin D, magnesium, zinc, caffeine, BCAA, multivitamin. "
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="supplement_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        return data.get("supplement_name", "unknown")
    except Exception:
        return "unknown"


async def extract_mood(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract mood and energy level from free text."""
    system = (
        "Extract the user's mood and energy level. "
        'Respond ONLY with JSON: {"mood": "<happy|sad|anxious|tired|energetic|stressed|neutral|angry|motivated|frustrated>", '
        '"energy_level": <1-5 or null>, "notes": "<brief note or null>"}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="mood_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        return json.loads(response)
    except Exception:
        return {"mood": "neutral", "energy_level": None, "notes": text}


async def extract_steps(
    text: str,
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract step count from free text."""
    system = (
        "Extract step count data from the user message. "
        'Respond ONLY with JSON: {"steps": <int>, "distance_km": <float or null>, '
        '"calories_burned": <float or null>}. '
        "Do not include any other text."
    )
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            user_id=user_id,
            feature="steps_extraction",
            redis_client=redis_client,
            db_session=db,
            temperature=0.1,
            max_tokens=60,
            response_format={"type": "json_object"},
        )
        return json.loads(response)
    except Exception:
        return {"steps": 0}


async def extract_workout_plan_request(
    text: str,
    profile: dict[str, Any],
    user_id: str,
    redis_client: aioredis.Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Extract workout plan parameters from free text + user profile."""
    system = (
        "You are a personal trainer. Generate a structured workout plan based on the user's request and profile. "
        "Respond ONLY with JSON:\n"
        '{"name": "<plan name>", "days_per_week": <int>, "goal": "<strength|hypertrophy|endurance|weight_loss|general>", '
        '"level": "<beginner|intermediate|advanced>", "equipment": "<gym|home|bodyweight|minimal>", '
        '"days": [{"day_number": <int>, "name": "<day name, e.g. Upper Body>", "muscle_groups": "<comma separated>", '
        '"exercises": [{"exercise_name": "<name>", "sets": <int>, "reps_min": <int>, "reps_max": <int>, '
        '"rest_seconds": <int>, "rpe_target": <float or null>, "notes": "<note or null>"}]}]}. '
        "Create a complete plan with proper periodization. Do not include any other text."
    )
    profile_str = ", ".join(f"{k}: {v}" for k, v in profile.items() if v)
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Profile: {profile_str}\n\nRequest: {text}",
                },
            ],
            user_id=user_id,
            feature="workout_plan_generation",
            redis_client=redis_client,
            db_session=db,
            temperature=0.4,
            max_tokens=2000,
            response_format={"type": "json_object"},
            model_tier="advanced",
        )
        return json.loads(response)
    except Exception:
        return {}
