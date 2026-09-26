from __future__ import annotations

import pytest
from flask.testing import FlaskClient

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient, email: str = "ayu@example.com") -> None:
    from tests.integration.test_auth import _register

    _register(api_client)


def test_add_list_remove_favorite(api_client: FlaskClient) -> None:
    _login(api_client)

    # Initially empty
    list_response = api_client.get("/api/v1/favorites")
    assert list_response.status_code == 200
    assert list_response.json["data"]["items"] == []

    # Add a favorite
    add_response = api_client.post(
        "/api/v1/favorites",
        json={
            "food_name": "Greek yogurt",
            "emoji": "🥛",
            "brand": "Cimory",
            "portion": 1,
            "portion_unit": "cup",
            "notes": "Sarapan favorit",
        },
    )
    assert add_response.status_code == 201, add_response.json
    favorite = add_response.json["data"]
    assert favorite["food_name"] == "Greek yogurt"
    assert favorite["portion_unit"] == "cup"

    # List shows the favorite
    list_response = api_client.get("/api/v1/favorites")
    assert list_response.status_code == 200
    items = list_response.json["data"]["items"]
    assert len(items) == 1
    assert items[0]["food_name"] == "Greek yogurt"

    # Remove the favorite
    remove_response = api_client.delete(f"/api/v1/favorites/{favorite['id']}")
    assert remove_response.status_code == 204

    # List is empty again
    list_response = api_client.get("/api/v1/favorites")
    assert list_response.status_code == 200
    assert list_response.json["data"]["items"] == []


def test_add_favorite_validation_error(api_client: FlaskClient) -> None:
    _login(api_client)

    # Missing food_name -> validation error
    response = api_client.post(
        "/api/v1/favorites",
        json={"portion": 1},
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"
    assert "food_name" in response.json["error"]["fields"]


def test_remove_favorite_not_found(api_client: FlaskClient) -> None:
    _login(api_client)

    from uuid import uuid4

    response = api_client.delete(f"/api/v1/favorites/{uuid4()}")
    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
