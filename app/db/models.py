"""Re-export hub — imports all models so Alembic and other code can use a single import.

Usage:
    import app.db.models  # registers all models with SQLAlchemy Base
    from app.db.models import User, MealLog  # still works for convenience
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.db.utils import new_uuid, utcnow

from app.modules.users.models import *  # noqa: F401,F403
from app.modules.ai.models import *  # noqa: F401,F403
from app.modules.auth.models import *  # noqa: F401,F403
from app.modules.body.models import *  # noqa: F401,F403
from app.modules.challenges.models import *  # noqa: F401,F403
from app.modules.checkins.models import *  # noqa: F401,F403
from app.modules.exercises.models import *  # noqa: F401,F403
from app.modules.food.models import *  # noqa: F401,F403
from app.modules.gamification.models import *  # noqa: F401,F403
from app.modules.notifications.models import *  # noqa: F401,F403
from app.modules.nutrition.models import *  # noqa: F401,F403
from app.modules.pantry.models import *  # noqa: F401,F403
from app.modules.shopping.models import *  # noqa: F401,F403
from app.modules.supplements.models import *  # noqa: F401,F403
from app.modules.tracking.models import *  # noqa: F401,F403
from app.modules.versioning.models import *  # noqa: F401,F403
from app.modules.wellness.models import *  # noqa: F401,F403
from app.modules.workouts.models import *  # noqa: F401,F403


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    license_number: Mapped[str | None] = mapped_column(String(100))
    specialty: Mapped[str | None] = mapped_column(String(30))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    billing_period: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
