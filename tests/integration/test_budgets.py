from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from flask.testing import FlaskClient

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient) -> None:
    from tests.integration.test_auth import _register

    _register(api_client)
    api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )


def _wib_now(minutes_from_now: int = 0) -> str:
    wib = timezone(timedelta(hours=7))
    now = datetime.now(UTC).astimezone(wib) + timedelta(minutes=minutes_from_now)
    return now.strftime("%Y-%m-%dT%H:%M:%S+07:00")


def _category_id(api_client: FlaskClient) -> str:
    from uuid import uuid4

    from gerdiary.extensions import db
    from gerdiary.modules.identity.models import Category, User

    user_id = api_client.get("/api/v1/auth/me").json["data"]["id"]
    user = db.session.get(User, user_id)
    category = Category(id=str(uuid4()), user_id=user.id, name="Test Food", category_type="food")
    db.session.add(category)
    db.session.commit()
    return str(category.id)


def _create_entry(api_client: FlaskClient, *, category_id: str, **overrides: object) -> dict:
    payload: dict = {
        "category_id": category_id,
        "meal_type": "breakfast",
        "food_name": "Ayam geprek",
        "consumed_at": _wib_now(),
        "portion": 1,
        "portion_unit": "pcs",
        "amount": 25000,
    }
    payload.update(overrides)
    response = api_client.post("/api/v1/food-entries", json=payload)
    assert response.status_code == 201, response.json
    return response.json["data"]


def _current_year_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def test_budgets_crud(api_client: FlaskClient) -> None:
    _login(api_client)
    category_id = _category_id(api_client)

    # Awalnya kosong
    response = api_client.get("/api/v1/budgets")
    assert response.status_code == 200
    assert response.json["data"]["items"] == []

    # Create
    response = api_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category_id,
            "year_month": _current_year_month(),
            "amount": 500000,
        },
    )
    assert response.status_code == 201, response.json
    budget = response.json["data"]
    assert budget["amount"] == 500000.0
    assert budget["target"] == 500000.0

    # List
    response = api_client.get("/api/v1/budgets")
    assert response.status_code == 200
    assert len(response.json["data"]["items"]) == 1

    # Update
    response = api_client.post(
        f"/api/v1/budgets/{budget['id']}",
        json={"amount": 600000},
    )
    assert response.status_code == 200
    assert response.json["data"]["amount"] == 600000.0

    # Delete
    response = api_client.delete(f"/api/v1/budgets/{budget['id']}")
    assert response.status_code == 204

    response = api_client.get("/api/v1/budgets")
    assert response.json["data"]["items"] == []


def test_budget_progress(api_client: FlaskClient) -> None:
    _login(api_client)
    category_id = _category_id(api_client)

    budget = api_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category_id,
            "year_month": _current_year_month(),
            "amount": 100000,
        },
    ).json["data"]
    assert budget["actual"] == 0.0
    assert budget["remaining"] == 100000.0

    # Tambah food entry dengan amount
    _create_entry(api_client, category_id=category_id, amount=30000)

    # Progress terhitung
    response = api_client.get("/api/v1/budgets")
    items = response.json["data"]["items"]
    assert len(items) == 1
    assert items[0]["actual"] == 30000.0
    assert items[0]["remaining"] == 70000.0


def test_budget_validation_error(api_client: FlaskClient) -> None:
    _login(api_client)
    category_id = _category_id(api_client)

    # amount negatif
    response = api_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category_id,
            "year_month": _current_year_month(),
            "amount": -100,
        },
    )
    assert response.status_code == 400
    assert "amount" in response.json["error"]["fields"]

    # year_month format salah
    response = api_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category_id,
            "year_month": "2026/09",
            "amount": 100,
        },
    )
    assert response.status_code == 400
    assert "year_month" in response.json["error"]["fields"]

    # category_id acak -> 404
    from uuid import uuid4

    response = api_client.post(
        "/api/v1/budgets",
        json={
            "category_id": str(uuid4()),
            "year_month": _current_year_month(),
            "amount": 100,
        },
    )
    assert response.status_code == 404
