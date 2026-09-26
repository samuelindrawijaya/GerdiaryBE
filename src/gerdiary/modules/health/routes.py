from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, current_app, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from gerdiary.shared.request_id import current_request_id

health_blueprint = Blueprint("health", __name__)


def success_response(data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> tuple[Any, int]:
    return jsonify({"data": data, "meta": {}}), status.value


def error_payload(code: str, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": {},
            "request_id": current_request_id(),
        }
    }


@health_blueprint.get("/health")
def health() -> tuple[Any, int]:
    return success_response({"status": "available"})


@health_blueprint.get("/ready")
def ready() -> tuple[Any, int]:
    database_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except SQLAlchemyError:
        current_app.logger.exception("Readiness database check failed")
        return (
            jsonify(error_payload("dependency_unavailable", "Layanan belum siap.")),
            HTTPStatus.SERVICE_UNAVAILABLE.value,
        )

    return success_response({"status": "ready"})
