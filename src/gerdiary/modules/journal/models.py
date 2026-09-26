from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from gerdiary.infrastructure.database import Base


class FoodEntry(Base):
    __tablename__ = "food_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(32))
    brand: Mapped[str | None] = mapped_column(String(255))
    portion: Mapped[float | None] = mapped_column(Numeric(10, 2))
    portion_unit: Mapped[str | None] = mapped_column(String(20))
    serving_size: Mapped[str | None] = mapped_column(String(20))
    preparation_method: Mapped[str | None] = mapped_column(String(20))
    food_attributes: Mapped[list[str] | None] = mapped_column(JSONB)
    source_type: Mapped[str | None] = mapped_column(String(20))
    rating: Mapped[int | None] = mapped_column(Integer)
    mood_after: Mapped[str | None] = mapped_column(String(20))
    energy_level: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list[str] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    account_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT")
    )
    vendor_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT")
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
            "meal_type IN ('breakfast','lunch','dinner','snack','drink','supplement')",
            name="ck_food_entries_meal_type",
        ),
        CheckConstraint(
            "portion_unit IS NULL OR portion_unit IN ('g','ml','cup','pcs','slice','bowl','pack')",
            name="ck_food_entries_portion_unit",
        ),
        CheckConstraint(
            "serving_size IS NULL OR serving_size IN ('small','medium','large','extra_large')",
            name="ck_food_entries_serving_size",
        ),
        CheckConstraint(
            "preparation_method IS NULL OR preparation_method IN "
            "('fried','boiled','steamed','grilled','raw','baked','roasted','other')",
            name="ck_food_entries_preparation_method",
        ),
        CheckConstraint(
            "source_type IS NULL OR source_type IN "
            "('home_cooked','takeaway','dine_in','instant')",
            name="ck_food_entries_source_type",
        ),
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_food_entries_rating"
        ),
        CheckConstraint(
            "amount IS NULL OR amount >= 0", name="ck_food_entries_amount_non_negative"
        ),
        CheckConstraint(
            "mood_after IS NULL OR mood_after IN "
            "('good','neutral','tired','uncomfortable','nauseous')",
            name="ck_food_entries_mood_after",
        ),
        CheckConstraint(
            "energy_level IS NULL OR energy_level IN ('low','normal','high')",
            name="ck_food_entries_energy_level",
        ),
    )


class SymptomEvent(Base):
    __tablename__ = "symptom_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    food_entry_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("food_entries.id", ondelete="SET NULL")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symptom: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="quick_check")
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
            "symptom IN ('heartburn','bloating','nausea','stomach_ache','gas','burping',"
            "'regurgitation','difficulty_swallowing','chest_pain','vomit_blood','black_stool','other')",
            name="ck_symptom_events_symptom",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN ('mild','moderate','severe')",
            name="ck_symptom_events_severity",
        ),
        CheckConstraint(
            "source IN ('entry_form','quick_check','manual')",
            name="ck_symptom_events_source",
        ),
    )


class FavoriteFood(Base):
    __tablename__ = "favorite_foods"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(32))
    brand: Mapped[str | None] = mapped_column(String(255))
    portion: Mapped[float | None] = mapped_column(Numeric(8, 2))
    portion_unit: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
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
            "portion_unit IS NULL OR portion_unit IN ('g','ml','cup','pcs','slice','bowl','pack')",
            name="ck_favorite_foods_portion_unit",
        ),
    )


__all__ = ["FoodEntry", "SymptomEvent", "FavoriteFood"]
