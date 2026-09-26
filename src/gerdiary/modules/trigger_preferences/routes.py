from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request

from gerdiary.extensions import db
from gerdiary.modules.identity.domain import ValidationErrors
from gerdiary.modules.identity.guards import require_user, same_origin_protected
from gerdiary.modules.identity.models import User
from gerdiary.modules.trigger_preferences import domain, service
from gerdiary.shared.request_id import current_request_id

trigger_preferences_blueprint = Blueprint("trigger_preferences", __name__)

VALIDATION_MESSAGE = "Periksa kembali data yang kamu isi."


def _validation_error(fields: dict[str, list[str]]) -> tuple[Any, int]:
    payload: dict[str, Any] = {
        "error": {
            "code": "validation_failed",
            "message": VALIDATION_MESSAGE,
            "fields": fields,
            "request_id": current_request_id(),
        }
    }
    return jsonify(payload), HTTPStatus.BAD_REQUEST.value


@trigger_preferences_blueprint.put("/trigger-preferences")
@same_origin_protected
@require_user
def replace_trigger_preferences(user: User) -> tuple[Any, int]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(
        body.get("trigger_preferences"), list
    ):
        return _validation_error(
            {"trigger_preferences": ["Daftar pantangan wajib diisi."]}
        )

    try:
        inputs = domain.validate_preferences(body["trigger_preferences"])
    except (
        domain.TriggerPreferenceValidationErrors,
        ValidationErrors,
    ) as error:
        if isinstance(error, domain.TriggerPreferenceValidationErrors):
            return _validation_error(error.fields())
        return _validation_error(
            {item.field: [item.message] for item in error.errors}
        )

    preferences = service.replace_preferences(user, inputs)
    user.sensitivity_level = domain.sensitivity_from_preferences(inputs)
    db.session.commit()

    return (
        jsonify(
            {
                "data": {
                    "trigger_preferences": [
                        service.preference_payload(item) for item in preferences
                    ],
                    "sensitivity_level": user.sensitivity_level,
                },
                "meta": {},
            }
        ),
        HTTPStatus.OK.value,
    )


__all__ = ["trigger_preferences_blueprint"]
