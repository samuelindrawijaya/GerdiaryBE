from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from gerdiary.app import create_app
from gerdiary.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="testing",
        database_url="postgresql+psycopg://postgres:test@localhost:5432/gerdiary_test",
        secret_key="test-secret-key-with-at-least-32-characters",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        frontend_origin="http://localhost:5173",
        cookie_secure=False,
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[Flask]:
    application = create_app(settings)
    application.config.update(TESTING=True)
    yield application


@pytest.fixture
def client(app: Flask) -> Iterator[FlaskClient]:
    yield app.test_client()
