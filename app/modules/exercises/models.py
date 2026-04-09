"""Exercises domain models."""

from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.db.utils import new_uuid


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    muscle_group: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    muscle_secondary: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    equipment: Mapped[str] = mapped_column(String(30), nullable=False)
    movement_pattern: Mapped[str | None] = mapped_column(String(30))
    demo_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
