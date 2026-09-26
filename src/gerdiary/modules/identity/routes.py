from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest, Unauthorized

from gerdiary.modules.identity import domain, service
from gerdiary.modules.identity import onboarding as onboarding_service
from gerdiary.modules.identity.guards import (
    InvalidCredentials,
    register_identity_error_handlers,
    require_user,
    same_origin_protected,
)
from gerdiary.modules.identity.models import User
from gerdiary.modules.trigger_preferences import service as trigger_service
from gerdiary.shared.request_id import current_request_id

identity_blueprint = Blueprint("identity", __name__)
register_identity_error_handlers(identity_blueprint)

GENERIC_CREDENTIAL_ERROR = "Email atau password salah."


def _validation_fields(errors: list[domain.ValidationError]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for error in errors:
        fields.setdefault(error.field, []).append(error.message)
    return fields


def _error(code: str, message: str, fields: dict[str, list[str]] | None = None) -> tuple[Any, int]:

    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": current_request_id(),
        }
    }
    return jsonify(payload), (
        HTTPStatus.CONFLICT.value
        if code == "email_already_registered"
        else HTTPStatus.BAD_REQUEST.value
    )


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "auth_provider": user.auth_provider,
        "sleep_time": user.sleep_time,
        "timezone": user.timezone,
        "journal_theme": user.journal_theme,
        "sensitivity_level": user.sensitivity_level,
        "currency": user.currency,
        "trigger_preferences": trigger_service.preferences_payload(user),
        "onboarding_completed": user.onboarding_completed_at is not None,
    }


@identity_blueprint.post("/auth/register")
@same_origin_protected
def register() -> tuple[Any, int]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("Permintaan tidak valid.")

    errors: list[domain.ValidationError] = []
    email_raw = body.get("email")
    password = body.get("password")
    name = body.get("name")
    journal_theme = body.get("journal_theme", "kawaii")

    if not isinstance(email_raw, str):
        errors.append(domain.ValidationError(field="email", message="Email wajib diisi."))
    if not isinstance(password, str):
        errors.append(domain.ValidationError(field="password", message="Password wajib diisi."))
    if name is not None and not isinstance(name, str):
        errors.append(domain.ValidationError(field="name", message="Nama tidak valid."))
    if not isinstance(journal_theme, str) or journal_theme not in {"calm", "kawaii"}:
        errors.append(
            domain.ValidationError(
                field="journal_theme", message="Tema jurnal tidak valid."
            )
        )

    if isinstance(email_raw, str):
        try:
            domain.validate_email(email_raw)
        except domain.ValidationError as error:
            errors.append(error)
    if isinstance(password, str):
        try:
            domain.validate_password(password)
        except domain.ValidationError as error:
            errors.append(error)

    if errors:
        return _error(
            "validation_failed",
            "Periksa kembali data yang kamu isi.",
            _validation_fields(errors),
        )

    try:
        user = service.register_user(
            email_raw if isinstance(email_raw, str) else "",
            password if isinstance(password, str) else "",
            name,
            journal_theme,
        )
    except domain.EmailAlreadyRegistered:
        return _error("email_already_registered", "Email sudah terdaftar.")

    token = service.issue_token(str(user.id))
    response = jsonify({"data": _user_payload(user), "meta": {}})
    response.status_code = HTTPStatus.CREATED.value
    service.set_session_cookie(response, token)
    return response, HTTPStatus.CREATED.value


@identity_blueprint.post("/auth/login")
@same_origin_protected
def login() -> tuple[Any, int]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("Permintaan tidak valid.")

    email_raw = body.get("email")
    password = body.get("password")
    if not isinstance(email_raw, str) or not isinstance(password, str):
        return _error(
            "validation_failed",
            "Periksa kembali data yang kamu isi.",
            {
                key: ["wajib diisi"]
                for key, value in (("email", email_raw), ("password", password))
                if not isinstance(value, str)
            },
        )

    user = service.authenticate(email_raw, password)
    if user is None:
        raise InvalidCredentials(GENERIC_CREDENTIAL_ERROR)

    token = service.issue_token(str(user.id))
    response = jsonify({"data": _user_payload(user), "meta": {}})
    service.set_session_cookie(response, token)
    return response, HTTPStatus.OK.value


@identity_blueprint.get("/auth/me")
@require_user
def me(user: User) -> tuple[Any, int]:
    return jsonify({"data": _user_payload(user), "meta": {}}), HTTPStatus.OK.value


@identity_blueprint.post("/auth/logout")
def logout() -> tuple[Any, int]:
    response = current_app.response_class(b"", status=HTTPStatus.NO_CONTENT.value)
    service.clear_session_cookie(response)
    return response, HTTPStatus.NO_CONTENT.value


@identity_blueprint.errorhandler(Unauthorized)
def handle_unauthorized(error: Unauthorized) -> tuple[Any, int]:

    payload: dict[str, Any] = {
        "error": {
            "code": "unauthenticated",
            "message": error.description or "Sesi tidak valid.",
            "fields": {},
            "request_id": current_request_id(),
        }
    }
    return jsonify(payload), HTTPStatus.UNAUTHORIZED.value


@identity_blueprint.post("/onboarding/complete")
@same_origin_protected
@require_user
def complete_onboarding(user: User) -> tuple[Any, int]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("Permintaan tidak valid.")

    try:
        trigger_preferences = body.get("trigger_preferences")
        updated = onboarding_service.complete_onboarding(
            user,
            name=body.get("name") if isinstance(body.get("name"), str) else None,
            sleep_time=body.get("sleep_time") if isinstance(body.get("sleep_time"), str) else None,
            timezone=body.get("timezone") if isinstance(body.get("timezone"), str) else None,
            sensitivity_level=(
                body.get("sensitivity_level")
                if isinstance(body.get("sensitivity_level"), str)
                else None
            ),
            currency=body.get("currency") if isinstance(body.get("currency"), str) else None,
            trigger_preferences=(
                trigger_preferences
                if isinstance(trigger_preferences, list)
                else None
            ),
        )
    except domain.ValidationErrors as error:
        return _error(
            "validation_failed",
            "Periksa kembali data yang kamu isi.",
            error.fields(),
        )

    return jsonify({"data": _user_payload(updated), "meta": {}}), HTTPStatus.OK.value
