from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gerdiary.infrastructure.database import Base


class UserTriggerPreference(Base):
    __tablename__ = "user_trigger_preferences"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    trigger_key: Mapped[str | None] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(32))
    reaction_level: Mapped[str] = mapped_column(String(20), nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "reaction_level IN ('strong','mild','tolerated')",
            name="ck_user_trigger_preferences_reaction_level",
        ),
        CheckConstraint(
            "(is_custom = true AND trigger_key IS NULL) OR "
            "(is_custom = false AND trigger_key IS NOT NULL)",
            name="ck_user_trigger_preferences_custom_key",
        ),
        Index(
            "uq_user_trigger_preferences_user_key",
            "user_id",
            "trigger_key",
            unique=True,
            postgresql_where=text("trigger_key IS NOT NULL"),
        ),
    )


__all__ = ["UserTriggerPreference"]
