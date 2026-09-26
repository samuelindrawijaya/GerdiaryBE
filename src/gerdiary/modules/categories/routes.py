from __future__ import annotations

from typing import Any
from uuid import UUID

from flask import Blueprint, jsonify, request

from gerdiary.modules.categories import service
from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.guards import require_user
from gerdiary.shared.request_id import current_request_id

categories_blueprint = Blueprint("categories", __name__)

VALIDATION_MESSAGE = "Periksa kembali data yang kamu isi."
NOT_FOUND_MESSAGE = "Data tidak ditemukan."


def _error(code: str, message: str, fields: dict[str, list[str]] | None = None) -> tuple[Any, int]:
    return (
        jsonify({
            "error": {
                "code": code,
                "message": message,
                "fields": fields or {},
                "request_id": current_request_id(),
            }
        }),
        422 if code == "domain_rule_violated" else 400,
    )


@categories_blueprint.errorhandler(service.NotFoundError)
def handle_not_found(_: service.NotFoundError) -> tuple[Any, int]:
    payload: dict[str, Any] = {
        "error": {
            "code": "not_found",
            "message": NOT_FOUND_MESSAGE,
            "fields": {},
            "request_id": current_request_id(),
        }
    }
    return jsonify(payload), 404


@categories_blueprint.errorhandler(service.ConflictError)
def handle_conflict(error: service.ConflictError) -> tuple[Any, int]:
    return (
        jsonify({
            "error": {
                "code": "conflict",
                "message": error.message,
                "fields": {},
                "request_id": current_request_id(),
            }
        }),
        409,
    )


@categories_blueprint.errorhandler(ValidationErrors)
def handle_validation_errors(error: ValidationErrors) -> tuple[Any, int]:
    payload: dict[str, Any] = {
        "error": {
            "code": "validation_failed",
            "message": VALIDATION_MESSAGE,
            "fields": error.fields(),
            "request_id": current_request_id(),
        }
    }
    return jsonify(payload), 400


@categories_blueprint.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> tuple[Any, int]:
    return _error("validation_failed", VALIDATION_MESSAGE, {error.field: [error.message]})


@categories_blueprint.get("/categories")
@require_user
def list_categories(user: Any) -> tuple[Any, int]:
    categories = service.list_categories(user)
    return jsonify({
        "data": {"categories": [service.payload(category) for category in categories]},
        "meta": {"total": len(categories)},
    }), 200


@categories_blueprint.post("/categories")
@require_user
def create_category(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}
    category = service.create_category(user, body)
    return jsonify({"data": service.payload(category), "meta": {}}), 201


@categories_blueprint.post("/categories/<uuid:category_id>")
@require_user
def update_category(user: Any, category_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    category = service.update_category(user, str(category_id), body)
    return jsonify({"data": service.payload(category), "meta": {}}), 200


@categories_blueprint.delete("/categories/<uuid:category_id>")
@require_user
def delete_category(user: Any, category_id: UUID) -> tuple[Any, int]:
    service.delete_category(user, str(category_id))
    return "", 204
