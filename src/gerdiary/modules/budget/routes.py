from __future__ import annotations

from typing import Any
from uuid import UUID

from flask import Blueprint, jsonify, request

from gerdiary.modules.budget import service
from gerdiary.modules.identity.domain import ValidationErrors
from gerdiary.modules.identity.guards import require_user
from gerdiary.modules.spending.service import NotFoundError
from gerdiary.shared.request_id import current_request_id

budget_blueprint = Blueprint("budget", __name__)

VALIDATION_MESSAGE = "Periksa kembali data yang kamu isi."
NOT_FOUND_MESSAGE = "Data tidak ditemukan."


def _error(
    code: str,
    message: str,
    fields: dict[str, list[str]] | None = None,
    status: int = 400,
) -> tuple[Any, int]:
    body: dict[str, Any] = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return (
        jsonify({"error": body, "meta": {"request_id": current_request_id()}}),
        status,
    )


@budget_blueprint.get("/budgets")
@require_user
def list_budgets(user: Any) -> tuple[Any, int]:
    year_month = request.args.get("year_month")
    budgets = service.list_budgets(user, year_month=year_month)
    return (
        jsonify({"data": {"items": [service.payload(b) for b in budgets]}, "meta": {}}),
        200,
    )


@budget_blueprint.post("/budgets")
@require_user
def create_budget(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        budget = service.create_budget(user, body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    except NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return jsonify({"data": service.payload(budget), "meta": {}}), 201


@budget_blueprint.post("/budgets/<uuid:budget_id>")
@require_user
def update_budget(user: Any, budget_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        budget = service.update_budget(user, str(budget_id), body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    except NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return jsonify({"data": service.payload(budget), "meta": {}}), 200


@budget_blueprint.delete("/budgets/<uuid:budget_id>")
@require_user
def delete_budget(user: Any, budget_id: UUID) -> tuple[Any, int]:
    try:
        service.delete_budget(user, str(budget_id))
    except NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return "", 204
