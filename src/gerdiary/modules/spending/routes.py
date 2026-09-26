from __future__ import annotations

from typing import Any
from uuid import UUID

from flask import Blueprint, jsonify, request

from gerdiary.modules.identity.domain import ValidationErrors
from gerdiary.modules.identity.guards import require_user
from gerdiary.modules.spending import service
from gerdiary.shared.request_id import current_request_id

spending_blueprint = Blueprint("spending", __name__)

VALIDATION_MESSAGE = "Periksa kembali data yang kamu isi."
NOT_FOUND_MESSAGE = "Data tidak ditemukan."
CONFLICT_MESSAGE = "Data tidak bisa diproses karena konflik."


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


@spending_blueprint.get("/accounts")
@require_user
def list_accounts(user: Any) -> tuple[Any, int]:
    accounts = service.list_accounts(user)
    return (
        jsonify({"data": {"items": [service.account_payload(a) for a in accounts]}, "meta": {}}),
        200,
    )


@spending_blueprint.post("/accounts")
@require_user
def create_account(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        account = service.create_account(user, body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    return jsonify({"data": service.account_payload(account), "meta": {}}), 201


@spending_blueprint.post("/accounts/<uuid:account_id>")
@require_user
def update_account(user: Any, account_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        account = service.update_account(user, str(account_id), body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    except service.NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return jsonify({"data": service.account_payload(account), "meta": {}}), 200


@spending_blueprint.delete("/accounts/<uuid:account_id>")
@require_user
def delete_account(user: Any, account_id: UUID) -> tuple[Any, int]:
    try:
        service.delete_account(user, str(account_id))
    except service.NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    except service.ConflictError as error:
        return _error("conflict", error.message, status=409)
    return "", 204


@spending_blueprint.get("/vendors")
@require_user
def list_vendors(user: Any) -> tuple[Any, int]:
    vendors = service.list_vendors(user)
    return (
        jsonify({"data": {"items": [service.vendor_payload(v) for v in vendors]}, "meta": {}}),
        200,
    )


@spending_blueprint.post("/vendors")
@require_user
def create_vendor(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        vendor = service.create_vendor(user, body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    return jsonify({"data": service.vendor_payload(vendor), "meta": {}}), 201


@spending_blueprint.post("/vendors/<uuid:vendor_id>")
@require_user
def update_vendor(user: Any, vendor_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    try:
        vendor = service.update_vendor(user, str(vendor_id), body)
    except ValidationErrors as error:
        return _error(
            "validation_failed",
            VALIDATION_MESSAGE,
            {e.field: [e.message] for e in error.errors},
        )
    except service.NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return jsonify({"data": service.vendor_payload(vendor), "meta": {}}), 200


@spending_blueprint.delete("/vendors/<uuid:vendor_id>")
@require_user
def delete_vendor(user: Any, vendor_id: UUID) -> tuple[Any, int]:
    try:
        service.delete_vendor(user, str(vendor_id))
    except service.NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    except service.ConflictError as error:
        return _error("conflict", error.message, status=409)
    return "", 204
