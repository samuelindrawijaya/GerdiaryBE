import pytest

from gerdiary.config import ConfigurationError, Settings


def test_settings_reports_missing_names_without_secret_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        Settings.from_env({"SECRET_KEY": "should-not-appear"})

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "should-not-appear" not in message


def test_production_requires_secure_cookie() -> None:
    environment = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://example.invalid/database",
        "SECRET_KEY": "a" * 32,
        "JWT_SECRET_KEY": "b" * 32,
        "FRONTEND_ORIGIN": "https://example.invalid",
        "COOKIE_SECURE": "false",
    }

    with pytest.raises(ConfigurationError, match="secure cookies"):
        Settings.from_env(environment)
