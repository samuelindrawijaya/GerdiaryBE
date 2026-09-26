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


def _create_entry(api_client: FlaskClient, *, category_id: str, **overrides: object) -> dict:
    payload: dict = {
        "category_id": category_id,
        "meal_type": "breakfast",
        "food_name": "Ayam geprek",
        "consumed_at": _wib_now(),
        "portion": 1,
        "portion_unit": "pcs",
    }
    payload.update(overrides)
    response = api_client.post("/api/v1/food-entries", json=payload)
    assert response.status_code == 201, response.json
    return response.json["data"]


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


def test_accounts_crud(api_client: FlaskClient) -> None:
    _login(api_client)

    # Awalnya kosong
    response = api_client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert response.json["data"]["items"] == []

    # Create
    response = api_client.post(
        "/api/v1/accounts",
        json={"name": "GoPay", "emoji": "🟢"},
    )
    assert response.status_code == 201, response.json
    account = response.json["data"]
    assert account["name"] == "GoPay"
    assert account["is_active"] is True

    # List
    response = api_client.get("/api/v1/accounts")
    assert response.status_code == 200
    items = response.json["data"]["items"]
    assert len(items) == 1

    # Update
    response = api_client.post(
        f"/api/v1/accounts/{account['id']}",
        json={"name": "GoPay Utama", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json["data"]["name"] == "GoPay Utama"
    assert response.json["data"]["is_active"] is False

    # Delete
    response = api_client.delete(f"/api/v1/accounts/{account['id']}")
    assert response.status_code == 204

    response = api_client.get("/api/v1/accounts")
    assert response.json["data"]["items"] == []


def test_account_validation_error(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.post("/api/v1/accounts", json={"name": "   "})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert "name" in response.json["error"]["fields"]


def test_food_entry_with_expense(api_client: FlaskClient) -> None:
    _login(api_client)

    account = api_client.post(
        "/api/v1/accounts", json={"name": "Tunai", "emoji": "💵"}
    ).json["data"]
    category_id = _category_id(api_client)

    entry = _create_entry(
        api_client,
        category_id=category_id,
        amount=25000,
        account_id=account["id"],
    )
    assert entry["amount"] == 25000.0
    assert entry["account_id"] == account["id"]

    # Update expense
    response = api_client.post(
        f"/api/v1/food-entries/{entry['id']}",
        json={"amount": 30000},
    )
    assert response.status_code == 200
    assert response.json["data"]["amount"] == 30000.0

    # Hapus account yang terpakai -> 409
    response = api_client.delete(f"/api/v1/accounts/{account['id']}")
    assert response.status_code == 409
    assert response.json["error"]["code"] == "conflict"


def test_food_entry_expense_validation(api_client: FlaskClient) -> None:
    _login(api_client)

    category_id = _category_id(api_client)

    # amount negatif -> validation error
    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "breakfast",
            "food_name": "Es teh",
            "consumed_at": _wib_now(),
            "amount": -1000,
        },
    )
    assert response.status_code == 400
    assert "amount" in response.json["error"]["fields"]

    # account_id milik user lain / acak -> 404
    from uuid import uuid4

    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "breakfast",
            "food_name": "Es teh",
            "consumed_at": _wib_now(),
            "account_id": str(uuid4()),
        },
    )
    assert response.status_code == 404


def test_vendors_crud(api_client: FlaskClient) -> None:
    _login(api_client)

    # Awalnya kosong
    response = api_client.get("/api/v1/vendors")
    assert response.status_code == 200
    assert response.json["data"]["items"] == []

    # Create
    response = api_client.post(
        "/api/v1/vendors",
        json={"name": "Indomaret", "category": "convenience_store"},
    )
    assert response.status_code == 201, response.json
    vendor = response.json["data"]
    assert vendor["name"] == "Indomaret"
    assert vendor["category"] == "convenience_store"
    assert vendor["is_active"] is True

    # List
    response = api_client.get("/api/v1/vendors")
    assert response.status_code == 200
    assert len(response.json["data"]["items"]) == 1

    # Update
    response = api_client.post(
        f"/api/v1/vendors/{vendor['id']}",
        json={"name": "Indomaret Plus", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json["data"]["name"] == "Indomaret Plus"
    assert response.json["data"]["is_active"] is False

    # Delete
    response = api_client.delete(f"/api/v1/vendors/{vendor['id']}")
    assert response.status_code == 204

    response = api_client.get("/api/v1/vendors")
    assert response.json["data"]["items"] == []


def test_vendor_validation_error(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.post("/api/v1/vendors", json={"name": "  "})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert "name" in response.json["error"]["fields"]


def test_food_entry_with_vendor(api_client: FlaskClient) -> None:
    _login(api_client)

    vendor = api_client.post(
        "/api/v1/vendors", json={"name": "Warung Bakso Pak Kumis"}
    ).json["data"]
    category_id = _category_id(api_client)

    entry = _create_entry(
        api_client,
        category_id=category_id,
        vendor_id=vendor["id"],
    )
    assert entry["vendor_id"] == vendor["id"]

    # Update vendor
    other_vendor = api_client.post(
        "/api/v1/vendors", json={"name": "Masaki"}
    ).json["data"]
    response = api_client.post(
        f"/api/v1/food-entries/{entry['id']}",
        json={"vendor_id": other_vendor["id"]},
    )
    assert response.status_code == 200
    assert response.json["data"]["vendor_id"] == other_vendor["id"]

    # Hapus vendor yang terpakai -> 409
    response = api_client.delete(f"/api/v1/vendors/{other_vendor['id']}")
    assert response.status_code == 409
    assert response.json["error"]["code"] == "conflict"

    # vendor_id acak -> 404
    from uuid import uuid4

    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "breakfast",
            "food_name": "Bakso",
            "consumed_at": _wib_now(),
            "vendor_id": str(uuid4()),
        },
    )
    assert response.status_code == 404
