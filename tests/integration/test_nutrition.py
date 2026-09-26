from __future__ import annotations

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from gerdiary.modules.nutrition.domain import ProviderUnavailable

pytestmark = pytest.mark.usefixtures("api_app")

PRODUCT = {
    "provider": "openfoodfacts",
    "provider_product_id": "8991002101234",
    "barcode": "8991002101234",
    "name": "Indomie Goreng",
    "brand": "Indofood",
    "nutrition": {
        "energy_kcal_100g": 453.0,
        "fat_100g": 19.0,
        "carbohydrates_100g": 59.0,
        "sugars_100g": 4.0,
        "protein_100g": 8.0,
        "salt_100g": 3.6,
    },
}


class StubProvider:
    def __init__(
        self,
        products: list[dict[str, Any]] | None = None,
        barcode_hits: dict[str, dict[str, Any]] | None = None,
        unavailable: bool = False,
    ) -> None:
        self.products = products if products is not None else [PRODUCT]
        self.barcode_hits = barcode_hits if barcode_hits is not None else {}
        self.unavailable = unavailable
        self.search_calls: list[str] = []
        self.barcode_calls: list[str] = []

    def search(self, query: str) -> list[dict[str, Any]]:
        self.search_calls.append(query)
        if self.unavailable:
            raise ProviderUnavailable()
        return self.products

    def get_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        self.barcode_calls.append(barcode)
        if self.unavailable:
            raise ProviderUnavailable()
        return self.barcode_hits.get(barcode)


def _login(api_client: FlaskClient) -> None:
    from tests.integration.test_auth import _register

    _register(api_client)
    api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )


def _use_provider(api_app: Flask, provider: StubProvider) -> None:
    api_app.config["NUTRITION_PROVIDER"] = provider


def test_search_returns_normalized_products(api_client: FlaskClient, api_app: Flask) -> None:
    _login(api_client)
    provider = StubProvider()
    _use_provider(api_app, provider)

    response = api_client.get("/api/v1/nutrition/search?q=indomie")

    assert response.status_code == 200, response.json
    items = response.json["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Indomie Goreng"
    assert items[0]["provider"] == "openfoodfacts"
    assert items[0]["provider_product_id"] == "8991002101234"
    assert items[0]["nutrition"]["energy_kcal_100g"] == 453.0
    assert provider.search_calls == ["indomie"]


def test_search_without_query_is_400(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.get("/api/v1/nutrition/search")

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert "q" in response.json["error"]["fields"]


def test_barcode_miss_fetches_provider_and_caches(
    api_client: FlaskClient, api_app: Flask
) -> None:
    _login(api_client)
    provider = StubProvider(barcode_hits={"8991002101234": PRODUCT})
    _use_provider(api_app, provider)

    first = api_client.get("/api/v1/nutrition/barcode/8991002101234")
    assert first.status_code == 200, first.json
    data = first.json["data"]
    assert data["name"] == "Indomie Goreng"
    assert data["provider"] == "openfoodfacts"
    assert data["cached_at"]
    assert provider.barcode_calls == ["8991002101234"]

    second = api_client.get("/api/v1/nutrition/barcode/8991002101234")
    assert second.status_code == 200
    assert second.json["data"]["name"] == "Indomie Goreng"
    assert provider.barcode_calls == ["8991002101234"]


def test_barcode_not_found_is_404(api_client: FlaskClient, api_app: Flask) -> None:
    _login(api_client)
    _use_provider(api_app, StubProvider(barcode_hits={}))

    response = api_client.get("/api/v1/nutrition/barcode/8999999999999")

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_provider_unavailable_is_503(api_client: FlaskClient, api_app: Flask) -> None:
    _login(api_client)
    _use_provider(api_app, StubProvider(unavailable=True))

    response = api_client.get("/api/v1/nutrition/barcode/8991002101234")

    assert response.status_code == 503
    assert response.json["error"]["code"] == "provider_unavailable"

    search = api_client.get("/api/v1/nutrition/search?q=indomie")
    assert search.status_code == 503


def test_barcode_invalid_format_is_400(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.get("/api/v1/nutrition/barcode/abc123")

    assert response.status_code == 400
    assert "barcode" in response.json["error"]["fields"]


def test_nutrition_requires_authentication(api_client: FlaskClient) -> None:
    response = api_client.get("/api/v1/nutrition/search?q=indomie")

    assert response.status_code == 401
