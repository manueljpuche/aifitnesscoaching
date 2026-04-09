"""AI schemas — feedback and conversation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas_base import SchemaBase


class AIFeedbackCreate(BaseModel):
    suggestion_type: str = Field(..., max_length=50)
    suggestion_summary: str | None = None
    accepted: bool | None = None
    rejection_reason: str | None = None


class AIFeedbackResponse(SchemaBase):
    id: uuid.UUID
    suggestion_type: str
    suggestion_summary: str | None
    accepted: bool | None
    rejection_reason: str | None
    created_at: datetime


class ConversationCreate(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., min_length=1, max_length=2000)
    intent: str | None = None


class ConversationResponse(SchemaBase):
    id: uuid.UUID
    role: str
    content: str
    intent: str | None
    created_at: datetime


class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    intent: str
    response: str
    entities: dict = {}
    fallback: bool = False
    action_done: str | None = None


class TranscribeResponse(BaseModel):
    text: str
