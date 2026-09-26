"""Open Food Facts provider adapter.

Uses stdlib urllib only; the repository intentionally avoids an HTTP client
dependency. USDA can be added later behind the same provider seam.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gerdiary.modules.nutrition.domain import ProviderUnavailable

PROVIDER_NAME = "openfoodfacts"
DEFAULT_BASE_URL = "https://world.openfoodfacts.org"
DEFAULT_TIMEOUT_SECONDS = 5.0


class OpenFoodFactsProvider:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search(self, query: str) -> list[dict[str, Any]]:
        params = urlencode(
            {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 20,
            }
        )
        payload = self._get(f"/cgi/search.pl?{params}")
        products = payload.get("products")
        if not isinstance(products, list):
            return []
        results = [normalize_product(p) for p in products]
        return [r for r in results if r is not None]

    def get_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        payload = self._get(f"/api/v2/product/{barcode}.json")
        status = payload.get("status")
        product = payload.get("product")
        if status != 1 or not isinstance(product, dict):
            return None
        return normalize_product(product, barcode=barcode)

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        request = Request(url, headers={"User-Agent": "Gerdiary/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except HTTPError as error:
            if error.code == 404:
                return {"status": 0}
            raise ProviderUnavailable(str(error)) from error
        except (URLError, TimeoutError, OSError) as error:
            raise ProviderUnavailable(str(error)) from error
        try:
            decoded = json.loads(body)
        except ValueError as error:
            raise ProviderUnavailable("Invalid provider response") from error
        if not isinstance(decoded, dict):
            raise ProviderUnavailable("Invalid provider response")
        return decoded


def _first_number(nutriments: dict[str, Any], key: str) -> float | None:
    value = nutriments.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if result >= 0 else None


def normalize_product(
    product: dict[str, Any], *, barcode: str | None = None
) -> dict[str, Any] | None:
    """Normalize an Open Food Facts product payload to the shared shape."""
    name = product.get("product_name") or product.get("generic_name")
    if not isinstance(name, str) or not name.strip():
        return None
    brands = product.get("brands")
    if isinstance(brands, str):
        brand = brands.split(",")[0].strip() or None
    else:
        brand = None
    raw_id = product.get("id") or product.get("_id")
    provider_product_id = str(raw_id) if raw_id is not None else ""
    code = barcode or product.get("code")
    barcode_value = code.strip() if isinstance(code, str) and code.strip() else None
    nutriments = product.get("nutriments")
    if not isinstance(nutriments, dict):
        nutriments = {}
    return {
        "provider": PROVIDER_NAME,
        "provider_product_id": provider_product_id,
        "barcode": barcode_value,
        "name": name.strip(),
        "brand": brand,
        "nutrition": {
            "energy_kcal_100g": _first_number(nutriments, "energy-kcal_100g"),
            "fat_100g": _first_number(nutriments, "fat_100g"),
            "carbohydrates_100g": _first_number(nutriments, "carbohydrates_100g"),
            "sugars_100g": _first_number(nutriments, "sugars_100g"),
            "protein_100g": _first_number(nutriments, "proteins_100g"),
            "salt_100g": _first_number(nutriments, "salt_100g"),
        },
    }


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "PROVIDER_NAME",
    "OpenFoodFactsProvider",
    "ProviderUnavailable",
    "normalize_product",
]
