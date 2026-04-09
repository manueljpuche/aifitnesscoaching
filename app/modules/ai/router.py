"""AI router — conversation processing, feedback, and audio transcription."""

from __future__ import annotations

import base64
import uuid as _uuid

import structlog
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.schemas import (
    AIFeedbackCreate,
    AIFeedbackResponse,
    MessageResponse,
    TranscribeResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user
from app.core.storage import upload_file as s3_upload
from app.modules.ai.models import AIFeedback
from app.modules.users.models import User
from app.modules.ai.service import process_message
from app.integrations.openai.client import (
    AIBudgetExceeded,
    AIRateLimited,
    AIServiceUnavailable,
    transcribe_audio,
    vision_completion,
)

logger = structlog.stdlib.get_logger()
router = APIRouter()

_RATE_LIMIT_MAX = 20  # messages per window
_RATE_LIMIT_WINDOW = 60  # seconds


async def _check_rate_limit(
    user: User = Depends(get_current_user),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> User:
    """Enforce per-user rate limit using a Redis sliding window."""
    key = f"ratelimit:msg:{user.id}"
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, _RATE_LIMIT_WINDOW)
        if current > _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {_RATE_LIMIT_MAX} messages per minute.",
            )
    except HTTPException:
        raise
    except Exception:
        # If Redis is down, allow the request (fail-open)
        pass
    return user


_ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB (Groq base64 limit)

_VISION_PROMPT = (
    "Describe this image in detail for a fitness/nutrition coach context. "
    "If it's food, estimate portions and ingredients. "
    "If it's a body/progress photo, describe physique observations. "
    "If it's a supplement label or barcode, extract the relevant text. "
    "Be concise and factual. Respond in the user's language if you can infer it."
)


@router.post("/message", response_model=MessageResponse)
async def handle_message(
    text: str = Form("", max_length=2000),
    file: UploadFile | None = File(None),
    user: User = Depends(_check_rate_limit),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    if not text.strip() and file is None:
        raise HTTPException(status_code=422, detail="Text or image is required.")

    image_description: str | None = None

    if file is not None:
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Only JPEG, PNG, WebP or GIF images are supported.",
            )

        image_data = await file.read()
        if len(image_data) > _MAX_IMAGE_BYTES:
            raise HTTPException(status_code=422, detail="Image too large. Maximum 4 MB.")

        # Persist in MinIO for history
        ext = (
            file.filename.rsplit(".", 1)[-1]
            if file.filename and "." in file.filename
            else "jpg"
        )
        object_key = f"{user.id}/{_uuid.uuid4().hex}.{ext}"
        try:
            s3_upload(
                bucket=settings.minio_bucket_progress_photos,
                key=object_key,
                data=image_data,
                content_type=file.content_type or "image/jpeg",
            )
        except Exception:
            logger.warning("s3_upload_failed", key=object_key)

        # Analyse with vision model
        b64 = base64.b64encode(image_data).decode()
        data_uri = f"data:{file.content_type};base64,{b64}"

        try:
            image_description = await vision_completion(
                image_url=data_uri,
                prompt=_VISION_PROMPT,
                user_id=str(user.id),
                feature="vision",
                redis_client=redis_client,
                db_session=db,
            )
        except (AIBudgetExceeded, AIRateLimited, AIServiceUnavailable) as exc:
            logger.warning("vision_analysis_failed", detail=str(exc))
            # Fall through — the user's text (if any) still gets processed
        except Exception as exc:
            logger.error("vision_unexpected_error", detail=str(exc))

    # Build effective text merging image analysis + user caption
    effective_text = text.strip()
    if image_description:
        effective_text = f"[Foto del usuario: {image_description}] {effective_text}".strip()

    if not effective_text:
        raise HTTPException(
            status_code=422,
            detail="Could not process the image and no text was provided.",
        )

    try:
        result = await process_message(
            text=effective_text,
            user_id=user.id,
            locale=user.locale,
            redis_client=redis_client,
            db=db,
        )
        return MessageResponse(**result)
    except AIBudgetExceeded:
        raise HTTPException(status_code=429, detail="Daily AI budget exceeded. Try again tomorrow.")
    except AIRateLimited:
        raise HTTPException(status_code=429, detail="AI rate limit reached. Please wait a moment.")
    except AIServiceUnavailable as e:
        logger.error("ai_service_unavailable_message", detail=str(e))
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable.")
    except Exception as e:
        logger.error("unexpected_message_error", detail=str(e))
        raise HTTPException(status_code=500, detail="Internal error processing message.")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    """Transcribe an audio file using Whisper. n8n sends the audio downloaded from Telegram."""
    try:
        audio_data = await file.read()
        text = await transcribe_audio(audio_data, filename=file.filename or "audio.ogg")
        return TranscribeResponse(text=text)
    except AIRateLimited:
        raise HTTPException(status_code=429, detail="Transcription rate limit reached.")
    except AIServiceUnavailable as e:
        logger.error("ai_service_unavailable_transcribe", detail=str(e))
        raise HTTPException(status_code=503, detail="Transcription service unavailable.")
    except Exception as e:
        logger.error("unexpected_transcribe_error", detail=str(e))
        raise HTTPException(status_code=500, detail="Internal error during transcription.")


@router.post("/feedback", response_model=AIFeedbackResponse, status_code=201)
async def submit_feedback(
    body: AIFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback = AIFeedback(user_id=user.id, **body.model_dump())
    db.add(feedback)
    await db.flush()
    return feedback
