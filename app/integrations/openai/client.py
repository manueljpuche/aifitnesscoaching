"""AI client wrapper — supports OpenAI and Groq with cost tracking."""

from __future__ import annotations

import time
from typing import Any

import openai
import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.stdlib.get_logger()

# Pricing per 1M tokens (0 for free-tier Groq)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"input": 0.0, "output": 0.0},
}

# Features that require the advanced model
ADVANCED_FEATURES = frozenset({
    "plan_generation",
    "vision",
    "recipe_generation",
    "chrono_nutrition",
    "complex_meal_advice",
})


def _build_client() -> openai.AsyncOpenAI:
    """Build the AI client based on configured provider."""
    if settings.ai_provider == "groq":
        return openai.AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
    return openai.AsyncOpenAI(api_key=settings.openai_api_key)


_client = _build_client()


def _get_models() -> tuple[str, str]:
    """Return (default_model, advanced_model) for the active provider."""
    if settings.ai_provider == "groq":
        return settings.groq_model_default, settings.groq_model_advanced
    return settings.openai_model_default, settings.openai_model_advanced


async def get_ai_model_for_user(user_id: str, feature: str, redis_client: redis.Redis) -> str:
    """Select model based on user daily budget and feature complexity."""
    # Vision requires a dedicated multimodal model
    if feature == "vision":
        if settings.ai_provider == "groq":
            return settings.groq_model_vision
        return settings.openai_model_advanced  # GPT-4o supports vision natively

    model_default, model_advanced = _get_models()
    if feature in ADVANCED_FEATURES:
        daily_cost = await redis_client.get(f"user:{user_id}:ai_daily_cost")
        if daily_cost and float(daily_cost) > settings.ai_daily_budget_usd_per_user:
            logger.warning("ai_budget_exceeded_fallback", user_id=user_id, cost=daily_cost)
            return model_default
        return model_advanced
    return model_default


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


async def _track_usage(
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    feature: str,
    redis_client: redis.Redis,
    db_session: Any,
) -> float:
    """Track AI usage in Redis (daily budget) and queue DB log."""
    from app.modules.ai.models import AIUsageLog

    cost = _estimate_cost(model, input_tokens, output_tokens)

    # Increment daily cost in Redis with TTL until end of day
    key = f"user:{user_id}:ai_daily_cost"
    await redis_client.incrbyfloat(key, cost)
    ttl = await redis_client.ttl(key)
    if ttl < 0:
        await redis_client.expire(key, 86400)

    # Insert usage log in DB
    usage_log = AIUsageLog(
        user_id=user_id,
        model=model,
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        cost_usd=cost,
        feature=feature,
    )
    db_session.add(usage_log)

    return cost


async def chat_completion(
    messages: list[dict[str, str]],
    user_id: str,
    feature: str,
    redis_client: redis.Redis,
    db_session: Any,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: dict | None = None,
) -> str:
    """Send a chat completion request with cost tracking and fallback."""
    model = await get_ai_model_for_user(user_id, feature, redis_client)

    # Check daily budget hard limit
    daily_cost = await redis_client.get(f"user:{user_id}:ai_daily_cost")
    if daily_cost and float(daily_cost) > settings.ai_daily_budget_usd_per_user * 2:
        logger.warning("ai_hard_limit_reached", user_id=user_id)
        raise AIBudgetExceeded(f"Daily AI budget exceeded for user {user_id}")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        # Groq supports json_object format too
        kwargs["response_format"] = response_format

    try:
        start = time.monotonic()
        response = await _client.chat.completions.create(**kwargs)
        elapsed = time.monotonic() - start

        content = response.choices[0].message.content or ""
        usage = response.usage

        await _track_usage(
            user_id=user_id,
            model=model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            feature=feature,
            redis_client=redis_client,
            db_session=db_session,
        )

        logger.info(
            "ai_request",
            provider=settings.ai_provider,
            model=model,
            feature=feature,
            user_id=user_id,
            elapsed=round(elapsed, 2),
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
        )
        return content

    except openai.AuthenticationError as e:
        logger.error("ai_auth_error", provider=settings.ai_provider, detail=str(e))
        raise AIServiceUnavailable("AI authentication failed — check API key") from e

    except openai.RateLimitError as e:
        logger.warning("ai_rate_limit", provider=settings.ai_provider, detail=str(e))
        raise AIRateLimited("AI rate limit reached, please try again later") from e

    except openai.APIStatusError as e:
        if e.status_code >= 500:
            logger.error("ai_server_error", provider=settings.ai_provider, status=e.status_code, detail=str(e))
            raise AIServiceUnavailable("AI service is currently unavailable") from e
        logger.error("ai_api_error", provider=settings.ai_provider, status=e.status_code, detail=str(e))
        raise AIServiceUnavailable(f"AI API error ({e.status_code})") from e

    except openai.APIConnectionError as e:
        logger.error("ai_connection_error", provider=settings.ai_provider, detail=str(e))
        raise AIServiceUnavailable("Cannot connect to AI service") from e

    except Exception as e:
        logger.error("ai_unexpected_error", provider=settings.ai_provider, detail=str(e))
        raise AIServiceUnavailable("Unexpected AI error") from e


async def vision_completion(
    image_url: str,
    prompt: str,
    user_id: str,
    feature: str,
    redis_client: redis.Redis,
    db_session: Any,
) -> str:
    """Send an image to GPT-4o Vision for analysis."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]
    return await chat_completion(
        messages=messages,
        user_id=user_id,
        feature="vision",
        redis_client=redis_client,
        db_session=db_session,
        max_tokens=512,
    )


async def transcribe_audio(audio_data: bytes, filename: str = "audio.ogg") -> str:
    """Transcribe audio using Whisper (OpenAI only — Groq doesn't support Whisper)."""
    # Whisper requires the OpenAI client regardless of provider
    whisper_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        transcript = await whisper_client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_data),
        )
        return transcript.text
    except openai.AuthenticationError as e:
        logger.error("whisper_auth_error", detail=str(e))
        raise AIServiceUnavailable("Whisper authentication failed — check OpenAI API key") from e
    except openai.RateLimitError as e:
        logger.warning("whisper_rate_limit", detail=str(e))
        raise AIRateLimited("Whisper rate limit reached") from e
    except openai.APIConnectionError as e:
        logger.error("whisper_connection_error", detail=str(e))
        raise AIServiceUnavailable("Cannot connect to Whisper service") from e
    except Exception as e:
        logger.error("whisper_transcription_error", detail=str(e))
        raise AIServiceUnavailable("Audio transcription failed") from e


class AIBudgetExceeded(Exception):
    pass


class AIRateLimited(Exception):
    pass


class AIServiceUnavailable(Exception):
    pass
