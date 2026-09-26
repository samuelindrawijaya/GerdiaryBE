from __future__ import annotations

from typing import Any, cast

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.infrastructure.providers.openfoodfacts import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    OpenFoodFactsProvider,
)
from gerdiary.modules.nutrition.models import NutritionCacheEntry


class NotFoundError(Exception):
    pass


CACHED_PROVIDER = "openfoodfacts"


def _session() -> Session:
    return cast("Session", db.session)


def _provider() -> Any:
    provider = current_app.config.get("NUTRITION_PROVIDER")
    if provider is not None:
        return provider
    base_url = current_app.config.get("NUTRITION_BASE_URL") or DEFAULT_BASE_URL
    timeout = current_app.config.get("NUTRITION_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT_SECONDS
    return OpenFoodFactsProvider(
        base_url=str(base_url),
        timeout_seconds=float(timeout),
    )


def search(query: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = _provider().search(query)
    return products


def lookup_barcode(barcode: str) -> dict[str, Any]:
    cached = _session().scalar(
        select(NutritionCacheEntry).where(
            NutritionCacheEntry.provider == CACHED_PROVIDER,
            NutritionCacheEntry.barcode == barcode,
        )
    )
    if cached is not None:
        return payload_from_cache(cached)

    product = _provider().get_by_barcode(barcode)
    if product is None:
        raise NotFoundError()
    entry = _cache_entry(product)
    _session().add(entry)
    _session().commit()
    return payload_from_cache(entry)


def _cache_entry(product: dict[str, Any]) -> NutritionCacheEntry:
    nutrition = product.get("nutrition") or {}
    return NutritionCacheEntry(
        provider=str(product.get("provider") or CACHED_PROVIDER),
        provider_product_id=str(product.get("provider_product_id") or ""),
        barcode=product.get("barcode"),
        name=str(product.get("name") or ""),
        brand=product.get("brand"),
        energy_kcal_100g=nutrition.get("energy_kcal_100g"),
        fat_100g=nutrition.get("fat_100g"),
        carbohydrates_100g=nutrition.get("carbohydrates_100g"),
        sugars_100g=nutrition.get("sugars_100g"),
        protein_100g=nutrition.get("protein_100g"),
        salt_100g=nutrition.get("salt_100g"),
    )


def payload_from_cache(entry: NutritionCacheEntry) -> dict[str, Any]:
    return {
        "provider": entry.provider,
        "provider_product_id": entry.provider_product_id,
        "barcode": entry.barcode,
        "name": entry.name,
        "brand": entry.brand,
        "nutrition": {
            "energy_kcal_100g": _num(entry.energy_kcal_100g),
            "fat_100g": _num(entry.fat_100g),
            "carbohydrates_100g": _num(entry.carbohydrates_100g),
            "sugars_100g": _num(entry.sugars_100g),
            "protein_100g": _num(entry.protein_100g),
            "salt_100g": _num(entry.salt_100g),
        },
        "cached_at": entry.cached_at.isoformat() if entry.cached_at else None,
    }


def _num(value: Any) -> float | None:
    return float(value) if value is not None else None


__all__ = ["NotFoundError", "lookup_barcode", "payload_from_cache", "search"]
