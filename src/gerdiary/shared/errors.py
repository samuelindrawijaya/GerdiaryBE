from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from gerdiary.shared.request_id import current_request_id

_STATUS_CODES = {
    HTTPStatus.BAD_REQUEST: "bad_request",
    HTTPStatus.UNAUTHORIZED: "unauthenticated",
    HTTPStatus.NOT_FOUND: "not_found",
    HTTPStatus.CONFLICT: "conflict",
    HTTPStatus.UNPROCESSABLE_ENTITY: "domain_rule_violated",
    HTTPStatus.TOO_MANY_REQUESTS: "rate_limited",
    HTTPStatus.SERVICE_UNAVAILABLE: "dependency_unavailable",
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Any, int]:
        status = HTTPStatus(error.code or HTTPStatus.INTERNAL_SERVER_ERROR)
        code = _STATUS_CODES.get(status, "http_error")
        payload: dict[str, Any] = {
            "error": {
                "code": code,
                "message": error.description,
                "fields": {},
                "request_id": current_request_id(),
            }
        }
        return jsonify(payload), status.value

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Any, int]:
        app.logger.exception("Unhandled application error", exc_info=error)
        payload: dict[str, Any] = {
            "error": {
                "code": "internal_error",
                "message": "Terjadi kesalahan yang tidak terduga.",
                "fields": {},
                "request_id": current_request_id(),
            }
        }
        return jsonify(payload), HTTPStatus.INTERNAL_SERVER_ERROR.value
