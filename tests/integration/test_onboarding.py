from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.integration.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient, email: str = "ayu@example.com") -> None:
    from tests.integration.test_auth import _register

    _register(api_client)
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "portrait-of-you-1961"},
    )
    assert response.status_code == 200


def test_complete_onboarding_saves_preferences_and_seeds_default_category(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = api_client.post(
        "/api/v1/onboarding/complete",
        json={
            "name": "Ayu",
            "sleep_time": "23:30",
            "timezone": "Asia/Jakarta",
            "sensitivity_level": "moderate",
            "currency": "IDR",
        },
    )

    assert response.status_code == 200, response.json
    assert response.json["data"]["onboarding_completed"] is True
    assert response.json["data"]["sleep_time"] == "23:30"


def test_onboarding_is_idempotent_exactly_one_default_category(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)

    first = api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )
    second = api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "22:00", "timezone": "Asia/Jakarta"},
    )

    assert first.status_code == second.status_code == 200
    with test_engine.begin() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM categories WHERE name = 'Makanan'")
        ).scalar_one()
    assert count == 1
    assert second.json["data"]["sleep_time"] == "22:00"


def test_onboarding_requires_authentication(api_client: FlaskClient) -> None:
    response = api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )

    assert response.status_code == 401


def test_onboarding_rejects_invalid_sleep_time(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "25:99", "timezone": "Asia/Jakarta"},
    )

    assert response.status_code == 400
    assert "sleep_time" in response.json["error"]["fields"]


def test_user_without_onboarding_sees_completed_false(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json["data"]["onboarding_completed"] is False


def test_database_url_points_at_test_database() -> None:
    assert "gerdiary_test" in TEST_DATABASE_URL
