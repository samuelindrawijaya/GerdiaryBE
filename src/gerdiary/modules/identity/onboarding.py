from __future__ import annotations

import re
from datetime import UTC, datetime

from flask import current_app
from sqlalchemy import select

from gerdiary.extensions import db
from gerdiary.modules.identity import domain
from gerdiary.modules.identity.models import Category, User
from gerdiary.modules.trigger_preferences import domain as trigger_domain
from gerdiary.modules.trigger_preferences import service as trigger_service

DEFAULT_CATEGORY_NAME = "Makanan"
_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_TZ_MAX_LENGTH = 50
_SENSITIVITY_LEVELS = {"mild", "moderate", "severe"}
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def complete_onboarding(
    user: User,
    *,
    name: str | None,
    sleep_time: str | None,
    timezone: str | None,
    sensitivity_level: str | None = None,
    currency: str | None = None,
    trigger_preferences: list[object] | None = None,
) -> User:
    errors: list[domain.ValidationError] = []

    if sleep_time is not None and not _TIME_PATTERN.match(sleep_time):
        errors.append(
            domain.ValidationError(field="sleep_time", message="Format jam tidur harus HH:MM.")
        )
    if timezone is not None and not (0 < len(timezone) <= _TZ_MAX_LENGTH):
        errors.append(
            domain.ValidationError(field="timezone", message="Timezone tidak valid.")
        )
    if (
        trigger_preferences is None
        and sensitivity_level is not None
        and sensitivity_level not in _SENSITIVITY_LEVELS
    ):
        errors.append(
            domain.ValidationError(
                field="sensitivity_level", message="Tingkat sensitivitas tidak valid."
            )
        )
    if currency is not None and not _CURRENCY_PATTERN.match(currency):
        errors.append(
            domain.ValidationError(field="currency", message="Kode mata uang harus 3 huruf.")
        )

    validated_triggers: list[trigger_domain.TriggerPreferenceInput] | None = None
    if trigger_preferences is not None:
        try:
            validated_triggers = trigger_domain.validate_preferences(trigger_preferences)
        except trigger_domain.TriggerPreferenceValidationErrors as error:
            errors.extend(error.errors)

    if errors:
        raise domain.ValidationErrors(errors)

    user.name = name if name else user.name
    user.sleep_time = sleep_time if sleep_time is not None else user.sleep_time
    user.timezone = timezone if timezone is not None else user.timezone
    if trigger_preferences is None and sensitivity_level is not None:
        user.sensitivity_level = sensitivity_level
    if currency is not None:
        user.currency = currency
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)

    if validated_triggers is not None:
        trigger_service.replace_preferences(user, validated_triggers)
        user.sensitivity_level = trigger_domain.sensitivity_from_preferences(
            validated_triggers
        )

    _seed_default_category(user)
    db.session.commit()
    return user


def _seed_default_category(user: User) -> None:
    exists = db.session.execute(
        select(Category.id)
        .where(Category.user_id == user.id, Category.name == DEFAULT_CATEGORY_NAME)
        .limit(1)
    ).scalar_one_or_none()

    if exists is None:
        db.session.add(
            Category(user_id=user.id, name=DEFAULT_CATEGORY_NAME, category_type="food")
        )


def seed_default_category_for_tests() -> None:
    current_app.logger.debug("seed helper unused")
