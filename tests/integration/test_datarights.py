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


def test_export_csv(api_client: FlaskClient) -> None:
    _login(api_client)
    category_id = _category_id(api_client)

    api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category_id,
            "meal_type": "breakfast",
            "food_name": "Nasi goreng",
            "consumed_at": _wib_now(),
            "portion": 1,
            "portion_unit": "bowl",
            "amount": 20000,
        },
    )
    api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "heartburn",
            "severity": "moderate",
            "occurred_at": _wib_now(),
            "source": "quick_check",
        },
    )

    response = api_client.get("/api/v1/export")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)

    assert "# food_entries" in body
    assert "# symptom_events" in body
    assert "Nasi goreng" in body
    assert "heartburn" in body
    assert "food_name" in body
    assert "symptom" in body


def test_export_csv_invalid_date(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.get("/api/v1/export?start=bukan-tanggal")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_query"


def test_delete_account(api_client: FlaskClient) -> None:
    _login(api_client)

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    user_id = me.json["data"]["id"]

    response = api_client.delete("/api/v1/account")
    assert response.status_code == 204

    from gerdiary.extensions import db
    from gerdiary.modules.identity.models import User

    assert db.session.get(User, user_id) is None

    me_after = api_client.get("/api/v1/auth/me")
    assert me_after.status_code == 401
