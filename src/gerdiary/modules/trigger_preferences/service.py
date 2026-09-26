from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from gerdiary.extensions import db
from gerdiary.modules.trigger_preferences import domain
from gerdiary.modules.trigger_preferences.models import UserTriggerPreference

if TYPE_CHECKING:
    from gerdiary.modules.identity.models import User


def list_preferences(user: User) -> list[UserTriggerPreference]:
    return list(
        db.session.scalars(
            select(UserTriggerPreference)
            .where(UserTriggerPreference.user_id == user.id)
            .order_by(UserTriggerPreference.created_at, UserTriggerPreference.id)
        ).all()
    )


def replace_preferences(
    user: User, inputs: list[domain.TriggerPreferenceInput]
) -> list[UserTriggerPreference]:
    existing = list_preferences(user)

    by_key = {
        preference.trigger_key: preference
        for preference in existing
        if preference.trigger_key is not None
    }
    by_label = {
        domain.canonical_label(preference.label): preference
        for preference in existing
        if preference.trigger_key is None
    }

    kept_ids: set[str] = set()
    for item in inputs:
        preference: UserTriggerPreference | None
        label: str
        emoji: str | None
        if item.trigger_key is not None:
            preference = by_key.get(item.trigger_key)
            info = domain.BUILTIN_TRIGGERS[item.trigger_key]
            label = info["label"]
            emoji = info["emoji"]
        else:
            preference = by_label.get(domain.canonical_label(item.label or ""))
            label = item.label or ""
            emoji = item.emoji

        if preference is None:
            preference = UserTriggerPreference(user_id=user.id)
            db.session.add(preference)

        preference.trigger_key = item.trigger_key
        preference.label = label
        preference.emoji = emoji
        preference.reaction_level = item.reaction_level
        preference.is_custom = item.is_custom
        kept_ids.add(str(preference.id))

    for preference in existing:
        if str(preference.id) not in kept_ids:
            db.session.delete(preference)

    return list_preferences(user)

def preference_payload(preference: UserTriggerPreference) -> dict[str, object]:
    return {
        "id": str(preference.id),
        "trigger_key": preference.trigger_key,
        "label": preference.label,
        "emoji": preference.emoji,
        "reaction_level": preference.reaction_level,
        "is_custom": preference.is_custom,
    }


def preferences_payload(user: User) -> list[dict[str, object]]:
    return [preference_payload(item) for item in list_preferences(user)]


__all__ = [
    "list_preferences",
    "preference_payload",
    "preferences_payload",
    "replace_preferences",
]
