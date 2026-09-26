from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv


class ConfigurationError(RuntimeError):
    pass


def _parse_timeout(raw: str | None) -> float:
    if raw is None or not raw.strip():
        return 5.0
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError("NUTRITION_TIMEOUT_SECONDS must be a number") from None
    if value <= 0:
        raise ConfigurationError("NUTRITION_TIMEOUT_SECONDS must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    secret_key: str
    jwt_secret_key: str
    frontend_origin: str
    cookie_secure: bool
    nutrition_base_url: str = ""
    nutrition_timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> Settings:
        if environment is None:
            load_dotenv(find_dotenv(usecwd=True))
            values: Mapping[str, str] = os.environ
        else:
            values = environment
        required = ("DATABASE_URL", "SECRET_KEY", "JWT_SECRET_KEY", "FRONTEND_ORIGIN")
        missing = [name for name in required if not values.get(name)]
        if missing:
            names = ", ".join(missing)
            raise ConfigurationError(f"Missing required configuration: {names}")

        app_env = values.get("APP_ENV", "development")
        if app_env not in {"development", "testing", "production"}:
            raise ConfigurationError("APP_ENV must be development, testing, or production")

        cookie_secure = values.get("COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
        if app_env == "production" and not cookie_secure:
            raise ConfigurationError("Production requires secure cookies")

        return cls(
            app_env=app_env,
            database_url=values["DATABASE_URL"],
            secret_key=values["SECRET_KEY"],
            jwt_secret_key=values["JWT_SECRET_KEY"],
            frontend_origin=values["FRONTEND_ORIGIN"],
            cookie_secure=cookie_secure,
            nutrition_base_url=values.get("NUTRITION_BASE_URL", ""),
            nutrition_timeout_seconds=_parse_timeout(values.get("NUTRITION_TIMEOUT_SECONDS")),
        )

    def to_flask_config(self) -> dict[str, object]:
        return {
            "ENV": self.app_env,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": self.secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "FRONTEND_ORIGIN": self.frontend_origin,
            "SESSION_COOKIE_SECURE": self.cookie_secure,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "NUTRITION_BASE_URL": self.nutrition_base_url,
            "NUTRITION_TIMEOUT_SECONDS": self.nutrition_timeout_seconds,
        }
