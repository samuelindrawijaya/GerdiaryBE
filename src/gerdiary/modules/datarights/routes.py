from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, Response, jsonify, request

from gerdiary.modules.datarights import service
from gerdiary.modules.identity.domain import ValidationError
from gerdiary.modules.identity.guards import require_user
from gerdiary.modules.identity.models import User
from gerdiary.modules.journal.domain import validate_date
from gerdiary.shared.request_id import current_request_id

datarights_blueprint = Blueprint("datarights", __name__)

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


def _parse_date_arg(name: str) -> date | None:
    raw = request.args.get(name)
    if raw is None:
        return None
    return validate_date(raw, name)


@datarights_blueprint.get("/export")
@require_user
def export_data(user: User) -> Any:
    try:
        start = _parse_date_arg("start")
        end = _parse_date_arg("end")
    except ValidationError as error:
        fields = {error.field: [error.message]}
        return _error("invalid_query", "Parameter tanggal tidak valid.", fields)

    data = service.export_csv(user, start=start, end=end)
    food_csv = data.pop("food_entries")
    symptom_csv = data.pop("symptom_events")

    combined = (
        "# food_entries\n" + food_csv + "\n# symptom_events\n" + symptom_csv
    )
    return Response(
        combined,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=gerdiary-export.csv"},
    )


@datarights_blueprint.delete("/account")
@require_user
def delete_account(user: User) -> Any:
    service.delete_account(user)
    return "", 204
