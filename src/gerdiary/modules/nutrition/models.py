from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gerdiary.infrastructure.database import Base


class NutritionCacheEntry(Base):
    __tablename__ = "nutrition_cache"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(14))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    energy_kcal_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    fat_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    carbohydrates_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sugars_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    protein_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    salt_100g: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "provider <> '' AND provider_product_id <> ''",
            name="ck_nutrition_cache_provider_not_blank",
        ),
        CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_nutrition_cache_name_not_blank"
        ),
        CheckConstraint(
            "energy_kcal_100g IS NULL OR energy_kcal_100g >= 0",
            name="ck_nutrition_cache_energy_non_negative",
        ),
        CheckConstraint(
            "fat_100g IS NULL OR fat_100g >= 0",
            name="ck_nutrition_cache_fat_non_negative",
        ),
        CheckConstraint(
            "carbohydrates_100g IS NULL OR carbohydrates_100g >= 0",
            name="ck_nutrition_cache_carbs_non_negative",
        ),
        CheckConstraint(
            "sugars_100g IS NULL OR sugars_100g >= 0",
            name="ck_nutrition_cache_sugars_non_negative",
        ),
        CheckConstraint(
            "protein_100g IS NULL OR protein_100g >= 0",
            name="ck_nutrition_cache_protein_non_negative",
        ),
        CheckConstraint(
            "salt_100g IS NULL OR salt_100g >= 0",
            name="ck_nutrition_cache_salt_non_negative",
        ),
    )


__all__ = ["NutritionCacheEntry"]
