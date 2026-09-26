from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, jsonify, request
from werkzeug.exceptions import Unauthorized

from gerdiary.modules.identity import service
from gerdiary.modules.identity.models import User


class OriginNotAllowed(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def same_origin_protected(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*arguments: Any, **keywords: Any) -> Any:
        origin = request.headers.get("Origin")
        if origin is not None:
            allowed = current_app.config.get("FRONTEND_ORIGIN", "")
            if origin.rstrip("/") != allowed.rstrip("/"):
                raise OriginNotAllowed("Origin tidak diizinkan.")
        return view(*arguments, **keywords)

    return wrapped


def require_user(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*arguments: Any, **keywords: Any) -> Any:
        user: User | None = service.current_user()
        if user is None:
            raise Unauthorized("Sesi tidak valid atau sudah berakhir.")
        return view(user, *arguments, **keywords)

    return wrapped


def _origin_body(_: OriginNotAllowed) -> dict[str, Any]:
    return {
        "error": {
            "code": "origin_not_allowed",
            "message": "Permintaan tidak berasal dari aplikasi resmi.",
            "fields": {},
            "request_id": "",
        }
    }


def _credentials_body(_: InvalidCredentials) -> dict[str, Any]:
    return {
        "error": {
            "code": "invalid_credentials",
            "message": "Email atau password salah.",
            "fields": {},
            "request_id": "",
        }
    }


def register_identity_error_handlers(blueprint: Any) -> None:
    @blueprint.errorhandler(OriginNotAllowed)  # type: ignore[untyped-decorator]
    def handle_origin(error: OriginNotAllowed) -> tuple[Any, int]:
        return jsonify(_origin_body(error)), 403

    @blueprint.errorhandler(InvalidCredentials)  # type: ignore[untyped-decorator]
    def handle_credentials(error: InvalidCredentials) -> tuple[Any, int]:
        return jsonify(_credentials_body(error)), 401


ErrorBody = dict[str, Any]


__all__ = [
    "InvalidCredentials",
    "OriginNotAllowed",
    "register_identity_error_handlers",
    "require_user",
    "same_origin_protected",
]
