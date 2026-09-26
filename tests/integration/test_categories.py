from __future__ import annotations

import pytest
from flask.testing import FlaskClient

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient) -> str:
    from tests.integration.test_auth import _register

    _register(api_client)
    api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )
    return api_client.get("/api/v1/auth/me").json["data"]["id"]


def test_create_and_list_categories(api_client: FlaskClient) -> None:
    _login(api_client)

    created = api_client.post(
        "/api/v1/categories",
        json={"name": "Makanan Pedas", "category_type": "food", "color": "#FF0000"},
    )
    assert created.status_code == 201
    data = created.json["data"]
    assert data["name"] == "Makanan Pedas"
    assert data["parent_id"] is None

    listed = api_client.get("/api/v1/categories")
    names = [c["name"] for c in listed.json["data"]["categories"]]
    assert "Makanan Pedas" in names


def test_create_child_and_edit_category(api_client: FlaskClient) -> None:
    _login(api_client)

    parent = api_client.post("/api/v1/categories", json={"name": "Snack"})
    parent_id = parent.json["data"]["id"]

    child = api_client.post(
        "/api/v1/categories", json={"name": "Gorengan", "parent_id": parent_id}
    )
    assert child.status_code == 201
    child_id = child.json["data"]["id"]
    assert child.json["data"]["parent_id"] == parent_id

    updated = api_client.post(
        f"/api/v1/categories/{child_id}",
        json={"name": "Gorengan Renyah", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json["data"]["name"] == "Gorengan Renyah"
    assert updated.json["data"]["is_active"] is False


def test_duplicate_root_category_conflict(api_client: FlaskClient) -> None:
    _login(api_client)

    first = api_client.post("/api/v1/categories", json={"name": "Unik"})
    assert first.status_code == 201

    duplicate = api_client.post("/api/v1/categories", json={"name": "Unik"})
    assert duplicate.status_code == 409
    assert duplicate.json["error"]["code"] == "conflict"


def test_delete_category_and_cross_user_denied(api_client: FlaskClient) -> None:
    _login(api_client)

    created = api_client.post("/api/v1/categories", json={"name": "Hapus Saya"})
    category_id = created.json["data"]["id"]

    api_client.post(
        "/api/v1/auth/register",
        json={"email": "budi@example.com", "password": "portrait-of-you-1961", "name": "Budi"},
    )

    denied = api_client.delete(f"/api/v1/categories/{category_id}")
    assert denied.status_code == 404

    login_back = api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": "portrait-of-you-1961"},
    )
    assert login_back.status_code == 200

    deleted = api_client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 204
