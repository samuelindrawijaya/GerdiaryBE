from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from flask.testing import FlaskClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from gerdiary.extensions import db

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:test@localhost:5433/gerdiary_test",
)

requires_test_database = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS", "").lower() in {"1", "true"},
    reason="TEST_DATABASE_URL not available",
)


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture()
def clean_database(test_engine: Engine) -> Iterator[Engine]:
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    yield test_engine
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture()
def api_app(clean_database: Engine):
    from gerdiary.app import create_app
    from gerdiary.config import Settings

    settings = Settings(
        app_env="testing",
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key-with-at-least-32-characters",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        frontend_origin="http://localhost:5173",
        cookie_secure=False,
    )
    application = create_app(settings)
    application.config.update(TESTING=True)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def api_client(api_app) -> Iterator[FlaskClient]:
    yield api_app.test_client()
