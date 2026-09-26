from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from gerdiary.extensions import db

pytestmark = pytest.mark.usefixtures("api_app")


DEFAULT_PASSWORD = "portrait-of-you-1961"


def _register(
    api_client: FlaskClient,
    email: str = "Ayu@Example.com",
    password: str = DEFAULT_PASSWORD,
) -> dict:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Ayu"},
    )
    assert response.status_code == 201, response.json
    return response.json["data"]


def test_register_hashes_password_and_returns_user(api_client: FlaskClient) -> None:
    data = _register(api_client)

    assert data["email"] == "ayu@example.com"
    assert data["auth_provider"] == "local"
    assert "password_hash" not in data
    assert "password" not in data


def test_register_normalizes_duplicate_email_to_409(api_client: FlaskClient) -> None:
    _register(api_client, email="Ayu@Example.com")

    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "  AYU@example.COM  ", "password": "another-pass-1234"},
    )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "email_already_registered"


def test_register_stores_argon2id_hash_not_plaintext(api_client: FlaskClient) -> None:
    from argon2 import PasswordHasher

    _register(api_client, password="plaintext-secret-123")

    row = db.session.execute(
        db.text("SELECT password_hash FROM users WHERE email = 'ayu@example.com'")
    ).scalar_one()

    assert row.startswith("$argon2id$")
    PasswordHasher().verify(row, "plaintext-secret-123")


def test_login_returns_session_cookie_with_secure_flags(api_client: FlaskClient) -> None:
    _register(api_client)

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "  ayu@EXAMPLE.com ", "password": "portrait-of-you-1961"},
    )

    assert response.status_code == 200
    cookie_header = response.headers["Set-Cookie"]
    assert "session_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=Lax" in cookie_header
    assert "Path=/" in cookie_header


def test_login_rejects_wrong_password_with_generic_error(api_client: FlaskClient) -> None:
    _register(api_client)

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": "wrong-password-123"},
    )

    assert response.status_code == 401
    assert response.json["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_same_error_shape_as_wrong_password(api_client: FlaskClient) -> None:
    missing = api_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-pass-123"},
    )
    known = api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": "wrong-password-123"},
    )
    _register(api_client)
    known_after = api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": "wrong-password-123"},
    )

    assert missing.status_code == known.status_code == known_after.status_code == 401
    assert missing.json["error"] == known.json["error"] == known_after.json["error"]


def test_me_resolves_authenticated_user_from_cookie(api_client: FlaskClient) -> None:
    _register(api_client)
    api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": DEFAULT_PASSWORD},
    )

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json["data"]["email"] == "ayu@example.com"


def test_me_without_session_is_401_before_any_user_query(api_client: FlaskClient) -> None:
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json["error"]["code"] == "unauthenticated"


def test_logout_clears_session_cookie(api_client: FlaskClient) -> None:
    _register(api_client)
    api_client.post(
        "/api/v1/auth/login",
        json={"email": "ayu@example.com", "password": DEFAULT_PASSWORD},
    )

    response = api_client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert "session_token=;" in response.headers["Set-Cookie"]
    assert "Expires=Thu, 01 Jan 1970" in response.headers["Set-Cookie"]


def test_state_changing_request_from_foreign_origin_is_blocked(api_client: FlaskClient) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "evil@example.com", "password": "portrait-of-you-1961"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "origin_not_allowed"


def test_validation_errors_name_the_field(api_client: FlaskClient) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 400
    fields = response.json["error"]["fields"]
    assert "email" in fields
    assert "password" in fields


def test_missing_body_is_400_not_500(api_client: FlaskClient) -> None:
    response = api_client.post("/api/v1/auth/register")

    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"



