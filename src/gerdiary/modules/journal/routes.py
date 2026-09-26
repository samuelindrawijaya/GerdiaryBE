from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from flask import Blueprint, jsonify, request

from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.guards import require_user
from gerdiary.modules.journal import domain, service
from gerdiary.modules.safety import red_flags
from gerdiary.shared.request_id import current_request_id

journal_blueprint = Blueprint("journal", __name__)

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


@journal_blueprint.errorhandler(service.NotFoundError)
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


@journal_blueprint.errorhandler(ValidationErrors)
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


@journal_blueprint.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> tuple[Any, int]:
    return _error("validation_failed", VALIDATION_MESSAGE, {error.field: [error.message]})


@journal_blueprint.post("/food-entries")
@require_user
def create_food_entry(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}

    category_id_raw = body.get("category_id")
    if not category_id_raw:
        return _error(
            "missing_field", "Kategori wajib diisi.", {"category_id": ["Field ini wajib."]}
        )

    try:
        category_id = str(UUID(category_id_raw))
    except (TypeError, ValueError):
        return _error(
            "invalid_uuid", "ID kategori tidak valid.", {"category_id": ["ID tidak valid."]}
        )

    food_data = {k: v for k, v in body.items() if k != "symptoms"}
    symptoms = body.get("symptoms", [])
    if isinstance(symptoms, list):
        created_entry, created_symptoms = service.create_food_entry_with_symptoms(
            user, category_id=category_id, data=food_data, symptoms=symptoms
        )
    else:
        created_entry = service.create_food_entry(user, category_id=category_id, data=food_data)
        created_symptoms = []

    payload = dict(service._food_payload(created_entry, user))
    payload["symptoms"] = [
        {
            "id": str(s.id),
            "occurred_at": s.occurred_at.isoformat(),
            "symptom": s.symptom,
            "severity": s.severity,
            "red_flag": red_flags.payload(s.red_flag_code) if s.red_flag_code else None,
        }
        for s in created_symptoms
    ]

    return jsonify({"data": payload, "meta": {}}), 201


@journal_blueprint.get("/food-entries/<uuid:entry_id>")
@require_user
def get_food_entry_route(user: Any, entry_id: UUID) -> tuple[Any, int]:
    entry = service.get_food_entry(user, str(entry_id))
    return jsonify({"data": service._food_payload(entry, user), "meta": {}}), 200


@journal_blueprint.post("/food-entries/<uuid:entry_id>")
@require_user
def update_food_entry(user: Any, entry_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    updated = service.update_food_entry(user, str(entry_id), body)
    return jsonify({"data": service._food_payload(updated, user), "meta": {}}), 200


@journal_blueprint.delete("/food-entries/<uuid:entry_id>")
@require_user
def delete_food_entry(user: Any, entry_id: UUID) -> tuple[Any, int]:
    service.delete_food_entry(user, str(entry_id))
    return "", 204


@journal_blueprint.post("/food-entries/<uuid:entry_id>/repeat")
@require_user
def repeat_food_entry(user: Any, entry_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}

    consumed_at_raw = body.get("consumed_at")
    if consumed_at_raw is not None:
        consumed_at = domain.validate_timestamp(consumed_at_raw, "consumed_at")
    else:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(user.timezone) if user.timezone else ZoneInfo("UTC")
        consumed_at = datetime.now(tz)

    new_entry = service.repeat_food_entry(user, str(entry_id), consumed_at=consumed_at)
    return jsonify({"data": service._food_payload(new_entry, user), "meta": {}}), 201


@journal_blueprint.post("/symptom-events")
@require_user
def create_symptom_event(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}

    entry_id_raw = body.get("food_entry_id")
    entry_id = entry_id_raw if isinstance(entry_id_raw, str) and entry_id_raw else None

    event, flag_code = service.create_symptom_event(user, food_entry_id=entry_id, data=body)

    payload = service._symptom_payload(event, flag_code)
    return jsonify({"data": payload, "meta": {}}), 201


@journal_blueprint.post("/symptom-events/<uuid:event_id>")
@require_user
def update_symptom_event(user: Any, event_id: UUID) -> tuple[Any, int]:
    body = request.get_json() or {}
    event, flag_code = service.update_symptom_event(user, str(event_id), body)
    return jsonify({"data": service._symptom_payload(event, flag_code), "meta": {}}), 200


@journal_blueprint.delete("/symptom-events/<uuid:event_id>")
@require_user
def delete_symptom_event(user: Any, event_id: UUID) -> tuple[Any, int]:
    service.delete_symptom_event(user, str(event_id))
    return "", 204


@journal_blueprint.get("/food-entries/search")
@require_user
def search_food_entries(user: Any) -> tuple[Any, int]:
    q = request.args.get("q")
    category_id = request.args.get("category_id")
    start = None
    end = None
    if "start" in request.args:
        start = domain.validate_date(request.args.get("start"), "start")
    if "end" in request.args:
        end = domain.validate_date(request.args.get("end"), "end")
    entries = service.search_food_entries(
        user, q=q or None, category_id=category_id or None, start=start, end=end
    )
    return jsonify({
        "data": {"entries": [service._food_payload(entry, user) for entry in entries]},
        "meta": {"total": len(entries)},
    }), 200


@journal_blueprint.get("/timeline")
@require_user
def get_timeline(user: Any) -> tuple[Any, int]:
    date_str = request.args.get("date")
    if not date_str:
        return _error(
            "missing_field",
            "Tanggal wajib disertakan.",
            {"date": ["Query parameter ?date=YYYY-MM-DD wajib."]},
        )

    try:
        local_date = date.fromisoformat(date_str)
    except ValueError:
        return _error(
            "invalid_query", "Format tanggal tidak valid.", {"date": ["Gunakan YYYY-MM-DD."]}
        )

    items = service.get_timeline(user, local_date)
    return jsonify({
        "data": {
            "items": [
                {
                    "kind": item.kind,
                    "occurred_at": item.occurred_at.isoformat(),
                    "payload": item.payload,
                }
                for item in items
            ],
        },
        "meta": {"date": date_str},
    }), 200


@journal_blueprint.get("/favorites")
@require_user
def list_favorites(user: Any) -> tuple[Any, int]:
    favorites = service.list_favorites(user)
    return jsonify({
        "data": {"items": [service._favorite_payload(f) for f in favorites]},
        "meta": {},
    }), 200


@journal_blueprint.post("/favorites")
@require_user
def add_favorite(user: Any) -> tuple[Any, int]:
    body = request.get_json() or {}
    favorite = service.add_favorite(user, body)
    return jsonify({"data": service._favorite_payload(favorite), "meta": {}}), 201


@journal_blueprint.delete("/favorites/<uuid:favorite_id>")
@require_user
def remove_favorite(user: Any, favorite_id: UUID) -> tuple[Any, int]:
    service.remove_favorite(user, str(favorite_id))
    return "", 204
