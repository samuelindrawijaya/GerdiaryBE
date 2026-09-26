from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from gerdiary.infrastructure.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="local"
    )
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    sleep_time: Mapped[str | None] = mapped_column(String(8))
    sensitivity_level: Mapped[str | None] = mapped_column(String(20))
    goals: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    currency: Mapped[str | None] = mapped_column(String(3), default="IDR")
    timezone: Mapped[str | None] = mapped_column(String(50), default="Asia/Jakarta")
    journal_theme: Mapped[str] = mapped_column(String(10), nullable=False, default="kawaii")
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "auth_provider IN ('local','google')", name="ck_users_auth_provider"
        ),
        CheckConstraint(
            "sensitivity_level IS NULL OR sensitivity_level IN ('mild','moderate','severe')",
            name="ck_users_sensitivity_level",
        ),
        CheckConstraint(
            "journal_theme IN ('calm','kawaii')", name="ck_users_journal_theme"
        ),
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str | None] = mapped_column(String(10))
    icon: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(7))
    sort_order: Mapped[int | None] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category_type IS NULL OR category_type IN ('expense','food','both')",
            name="ck_categories_type",
        ),
        Index(
            "uq_categories_root_user_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
    )


__all__ = ["User", "Category"]
