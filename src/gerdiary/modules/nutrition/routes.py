from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from gerdiary.modules.identity.domain import ValidationError
from gerdiary.modules.identity.guards import require_user
from gerdiary.modules.identity.models import User
from gerdiary.modules.nutrition import domain, service
from gerdiary.shared.request_id import current_request_id

nutrition_blueprint = Blueprint("nutrition", __name__)

VALIDATION_MESSAGE = "Periksa kembali data yang kamu isi."
NOT_FOUND_MESSAGE = "Data tidak ditemukan."
PROVIDER_UNAVAILABLE_MESSAGE = "Layanan nutrisi sedang tidak tersedia."


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


@nutrition_blueprint.get("/nutrition/search")
@require_user
def search_products(user: User) -> tuple[Any, int]:
    try:
        query = domain.validate_search_query(request.args.get("q"))
    except ValidationError as error:
        return _error(
            "validation_failed", VALIDATION_MESSAGE, {error.field: [error.message]}
        )
    try:
        products = service.search(query)
    except domain.ProviderUnavailable:
        return _error("provider_unavailable", PROVIDER_UNAVAILABLE_MESSAGE, status=503)
    return jsonify({"data": {"items": products}, "meta": {}}), 200


@nutrition_blueprint.get("/nutrition/barcode/<barcode>")
@require_user
def lookup_barcode(user: User, barcode: str) -> tuple[Any, int]:
    try:
        validated = domain.validate_barcode(barcode)
    except ValidationError as error:
        return _error(
            "validation_failed", VALIDATION_MESSAGE, {error.field: [error.message]}
        )
    try:
        product = service.lookup_barcode(validated)
    except domain.ProviderUnavailable:
        return _error("provider_unavailable", PROVIDER_UNAVAILABLE_MESSAGE, status=503)
    except service.NotFoundError:
        return _error("not_found", NOT_FOUND_MESSAGE, status=404)
    return jsonify({"data": product, "meta": {}}), 200
