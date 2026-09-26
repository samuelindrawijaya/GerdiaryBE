from __future__ import annotations

import pytest
from flask.testing import FlaskClient

pytestmark = pytest.mark.usefixtures("api_app")

PASSWORD = "portrait-of-you-1961"


def _login(api_client: FlaskClient) -> dict:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "ayu@example.com", "password": PASSWORD, "name": "Ayu"},
    )
    assert response.status_code == 201, response.json
    return response.json["data"]


def test_red_flag_symptom_returns_safety_payload_not_500(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "chest_pain",
            "severity": "severe",
            "occurred_at": "2026-09-03T10:00:00+07:00",
        },
    )

    assert response.status_code == 201, response.json
    assert response.json["data"]["red_flag"]["code"] == "RF_CHEST_PAIN"


def test_missing_food_entry_returns_404_not_500(api_client: FlaskClient) -> None:
    _login(api_client)
    missing = "11111111-1111-4111-8111-111111111111"

    response = api_client.delete(f"/api/v1/food-entries/{missing}")

    assert response.status_code == 404, response.json
    assert response.json["error"]["code"] == "not_found"


def test_invalid_meal_type_returns_400_not_500(api_client: FlaskClient) -> None:
    user = _login(api_client)

    from uuid import uuid4

    from gerdiary.extensions import db
    from gerdiary.modules.identity.models import Category

    category_id = str(uuid4())
    db.session.add(
        Category(id=category_id, user_id=user["id"], name="Cat", category_type="food")
    )
    db.session.commit()

    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "brunch",
            "food_name": "Test",
            "consumed_at": "2026-09-03T10:00:00+07:00",
        },
    )

    assert response.status_code in (400, 422), response.json
    assert "meal_type" in response.json["error"]["fields"]


def test_linked_symptom_has_real_id_not_none(api_client: FlaskClient) -> None:
    from uuid import uuid4

    user = _login(api_client)
    category_id = str(uuid4())
    from gerdiary.extensions import db
    from gerdiary.modules.identity.models import Category

    db.session.add(
        Category(id=category_id, user_id=user["id"], name="Cat", category_type="food")
    )
    db.session.commit()

    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "lunch",
            "food_name": "Nasi goreng",
            "consumed_at": "2026-09-03T12:00:00+07:00",
            "symptoms": [
                {
                    "symptom": "heartburn",
                    "severity": "mild",
                    "occurred_at": "2026-09-03T12:30:00+07:00",
                }
            ],
        },
    )

    assert response.status_code == 201, response.json
    symptom_id = response.json["data"]["symptoms"][0]["id"]
    assert symptom_id != "None", "linked symptom id is the literal string 'None'"
