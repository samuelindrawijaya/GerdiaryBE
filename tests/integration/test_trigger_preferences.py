from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.integration.test_auth import _register

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient, email: str = "ayu@example.com") -> None:
    _register(api_client, email="Ayu@Example.com")
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "portrait-of-you-1961"},
    )
    assert response.status_code == 200


def _preferences_payload() -> list[dict]:
    return [
        {"trigger_key": "spicy", "reaction_level": "strong"},
        {
            "trigger_key": None,
            "label": "Susu sapi",
            "emoji": "🥛",
            "reaction_level": "mild",
            "is_custom": True,
        },
    ]


def _complete(api_client: FlaskClient, json: dict) -> object:
    return api_client.post("/api/v1/onboarding/complete", json=json)


def _preference_count(test_engine: Engine) -> int:
    with test_engine.begin() as connection:
        return connection.execute(
            text("SELECT count(*) FROM user_trigger_preferences")
        ).scalar_one()


def test_onboarding_saves_builtin_and_custom_trigger_preferences(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "name": "Ayu",
            "sleep_time": "23:00",
            "timezone": "Asia/Jakarta",
            "trigger_preferences": _preferences_payload(),
        },
    )

    assert response.status_code == 200, response.json
    preferences = response.json["data"]["trigger_preferences"]
    assert len(preferences) == 2
    builtin = next(item for item in preferences if item["trigger_key"] == "spicy")
    custom = next(item for item in preferences if item["is_custom"] is True)
    assert builtin["label"] == "Pedas"
    assert builtin["reaction_level"] == "strong"
    assert builtin["is_custom"] is False
    assert custom["label"] == "Susu sapi"
    assert custom["reaction_level"] == "mild"
    assert response.json["data"]["sensitivity_level"] == "severe"


def test_identical_resubmission_keeps_ids_and_no_duplicates(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)
    first = _complete(
        api_client,
        {
            "name": "Ayu",
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"}
            ],
        },
    )
    second = _complete(
        api_client,
        {
            "name": "Ayu",
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"}
            ],
        },
    )

    assert first.status_code == second.status_code == 200
    assert _preference_count(test_engine) == 1
    assert (
        first.json["data"]["trigger_preferences"][0]["id"]
        == second.json["data"]["trigger_preferences"][0]["id"]
    )


def test_resend_replaces_collection_and_recomputes_sensitivity(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)
    _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"},
                {"trigger_key": "coffee", "reaction_level": "mild"},
            ]
        },
    )
    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "coffee", "reaction_level": "mild"}
            ]
        },
    )

    assert response.status_code == 200
    assert _preference_count(test_engine) == 1
    assert response.json["data"]["sensitivity_level"] == "moderate"


def test_empty_array_clears_preferences_and_sensitivity(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)
    _complete(
        api_client,
        {"trigger_preferences": [{"trigger_key": "spicy", "reaction_level": "strong"}]},
    )
    response = _complete(api_client, {"trigger_preferences": []})

    assert response.status_code == 200
    assert _preference_count(test_engine) == 0
    assert response.json["data"]["trigger_preferences"] == []
    assert response.json["data"]["sensitivity_level"] is None


def test_missing_field_preserves_preferences(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)
    _complete(
        api_client,
        {"trigger_preferences": [{"trigger_key": "spicy", "reaction_level": "strong"}]},
    )
    response = _complete(api_client, {"name": "Ayu Baru"})

    assert response.status_code == 200
    assert _preference_count(test_engine) == 1
    assert response.json["data"]["trigger_preferences"][0]["trigger_key"] == "spicy"


def test_sensitivity_level_ignored_when_trigger_preferences_sent(
    api_client: FlaskClient,
) -> None:
    _login(api_client)
    response = _complete(
        api_client,
        {
            "sensitivity_level": "mild",
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"}
            ],
        },
    )

    assert response.status_code == 200
    assert response.json["data"]["sensitivity_level"] == "severe"


def test_auth_me_returns_stored_trigger_preferences(api_client: FlaskClient) -> None:
    _login(api_client)
    _complete(
        api_client,
        {"trigger_preferences": [{"trigger_key": "spicy", "reaction_level": "strong"}]},
    )

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    preferences = response.json["data"]["trigger_preferences"]
    assert len(preferences) == 1
    assert preferences[0]["trigger_key"] == "spicy"
    assert preferences[0]["label"] == "Pedas"


def test_invalid_reaction_level_rejected_with_indexed_field(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"},
                {"trigger_key": "coffee", "reaction_level": "extreme"},
            ]
        },
    )

    assert response.status_code == 400
    assert (
        response.json["error"]["fields"]["trigger_preferences.1.reaction_level"]
    )
    assert _preference_count(test_engine) == 0


def test_duplicate_trigger_key_rejected_on_second_item(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"},
                {"trigger_key": "spicy", "reaction_level": "mild"},
            ]
        },
    )

    assert response.status_code == 400
    assert "trigger_preferences.1.trigger_key" in response.json["error"]["fields"]


def test_inconsistent_is_custom_and_trigger_key_rejected(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong", "is_custom": True}
            ]
        },
    )

    assert response.status_code == 400
    fields = response.json["error"]["fields"]
    assert (
        "trigger_preferences.0.trigger_key" in fields
        or "trigger_preferences.0.is_custom" in fields
    )


def test_custom_label_case_and_whitespace_collapsed(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {
                    "trigger_key": None,
                    "label": "  Susu   sapi ",
                    "reaction_level": "mild",
                    "is_custom": True,
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json["data"]["trigger_preferences"][0]["label"] == "Susu sapi"


def test_custom_label_matching_builtin_rejected(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {
                    "trigger_key": None,
                    "label": " PEDAS ",
                    "reaction_level": "mild",
                    "is_custom": True,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "trigger_preferences.0.label" in response.json["error"]["fields"]


def test_custom_label_matching_alias_rejected(
    api_client: FlaskClient,
) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {
                    "trigger_key": None,
                    "label": "Santan Kental",
                    "reaction_level": "mild",
                    "is_custom": True,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "trigger_preferences.0.label" in response.json["error"]["fields"]


def test_more_than_twenty_items_rejected(api_client: FlaskClient) -> None:
    _login(api_client)

    response = _complete(
        api_client,
        {
            "trigger_preferences": [
                {"trigger_key": "spicy", "reaction_level": "strong"},
                *[
                    {
                        "trigger_key": None,
                        "label": f"Pantangan {index}",
                        "reaction_level": "mild",
                        "is_custom": True,
                    }
                    for index in range(20)
                ],
            ]
        },
    )

    assert response.status_code == 400
    assert "trigger_preferences" in response.json["error"]["fields"]


def test_settings_endpoint_replaces_preferences(
    api_client: FlaskClient,
    test_engine: Engine,
) -> None:
    _login(api_client)
    _complete(
        api_client,
        {"trigger_preferences": [{"trigger_key": "spicy", "reaction_level": "strong"}]},
    )

    response = api_client.put(
        "/api/v1/trigger-preferences",
        json={
            "trigger_preferences": [
                {"trigger_key": "coffee", "reaction_level": "tolerated"}
            ]
        },
    )

    assert response.status_code == 200, response.json
    assert _preference_count(test_engine) == 1
    preferences = response.json["data"]["trigger_preferences"]
    assert preferences[0]["trigger_key"] == "coffee"
    assert response.json["data"]["sensitivity_level"] == "mild"


def test_settings_endpoint_requires_authentication(api_client: FlaskClient) -> None:
    response = api_client.put(
        "/api/v1/trigger-preferences",
        json={"trigger_preferences": []},
    )

    assert response.status_code == 401


def test_settings_endpoint_rejects_bad_payload(api_client: FlaskClient) -> None:
    _login(api_client)

    response = api_client.put(
        "/api/v1/trigger-preferences",
        json={"trigger_preferences": [{"trigger_key": "spicy"}]},
    )

    assert response.status_code == 400
    assert "trigger_preferences.0.reaction_level" in response.json["error"]["fields"]
