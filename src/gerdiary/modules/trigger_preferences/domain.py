from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from gerdiary.modules.identity.domain import ValidationError

REACTION_LEVELS = ("strong", "mild", "tolerated")
MAX_PREFERENCES = 20
LABEL_MAX_LENGTH = 100
EMOJI_MAX_LENGTH = 32

BUILTIN_TRIGGERS: dict[str, dict[str, str]] = {
    "spicy": {"label": "Pedas", "emoji": "🌶️"},
    "acidic": {"label": "Asam", "emoji": "🍋"},
    "coconut_milk": {"label": "Bersantan", "emoji": "🍛"},
    "coffee": {"label": "Kopi", "emoji": "☕"},
    "carbonated": {"label": "Bersoda", "emoji": "🥤"},
    "fried": {"label": "Gorengan", "emoji": "🍟"},
}

BUILTIN_ALIASES: dict[str, tuple[str, ...]] = {
    "spicy": ("pedas",),
    "acidic": ("asam",),
    "coconut_milk": ("bersantan", "santan", "santan kental"),
    "coffee": ("kopi",),
    "carbonated": ("bersoda", "minuman soda", "soda"),
    "fried": ("gorengan", "digoreng"),
}

_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class TriggerPreferenceInput:
    trigger_key: str | None
    label: str | None
    emoji: str | None
    reaction_level: str
    is_custom: bool


def canonical_label(raw: str) -> str:
    stripped = raw.strip()
    collapsed = _WHITESPACE_PATTERN.sub(" ", stripped)
    return collapsed.casefold()


def _builtin_lookup(canonical: str) -> tuple[str, str] | None:
    for key, info in BUILTIN_TRIGGERS.items():
        candidates = (info["label"],) + BUILTIN_ALIASES.get(key, ())
        if canonical in {candidate.casefold() for candidate in candidates}:
            return key, info["label"]
    return None


def sensitivity_from_preferences(
    preferences: list[TriggerPreferenceInput],
) -> str | None:
    if not preferences:
        return None
    levels = {item.reaction_level for item in preferences}
    if "strong" in levels:
        return "severe"
    if "mild" in levels:
        return "moderate"
    return "mild"


def validate_preferences(
    raw_items: Any,
) -> list[TriggerPreferenceInput]:
    errors: list[ValidationError] = []

    if not isinstance(raw_items, list):
        raise TriggerPreferenceValidationErrors(
            [
                ValidationError(
                    field="trigger_preferences",
                    message="Daftar pantangan tidak valid.",
                )
            ]
        )
    if len(raw_items) > MAX_PREFERENCES:
        raise TriggerPreferenceValidationErrors(
            [
                ValidationError(
                    field="trigger_preferences",
                    message=f"Maksimal {MAX_PREFERENCES} pantangan.",
                )
            ]
        )

    inputs: list[TriggerPreferenceInput] = []
    seen_keys: dict[str, int] = {}
    seen_custom_labels: dict[str, int] = {}

    for index, item in enumerate(raw_items):
        prefix = f"trigger_preferences.{index}"

        if not isinstance(item, dict):
            errors.append(
                ValidationError(
                    field=f"{prefix}.label",
                    message="Format pantangan tidak valid.",
                )
            )
            continue

        trigger_key = item.get("trigger_key")
        label = item.get("label")
        emoji = item.get("emoji")
        reaction_level = item.get("reaction_level")
        is_custom = item.get("is_custom", False)

        if not isinstance(is_custom, bool):
            errors.append(
                ValidationError(
                    field=f"{prefix}.is_custom",
                    message="Nilai is_custom tidak valid.",
                )
            )
            continue

        if not isinstance(reaction_level, str) or reaction_level not in REACTION_LEVELS:
            errors.append(
                ValidationError(
                    field=f"{prefix}.reaction_level",
                    message="Tingkat respons tidak valid.",
                )
            )
            continue

        if trigger_key is None:
            if not is_custom:
                errors.append(
                    ValidationError(
                        field=f"{prefix}.is_custom",
                        message="Pantangan tanpa trigger_key harus custom.",
                    )
                )
                continue
            if not isinstance(label, str) or not label.strip():
                errors.append(
                    ValidationError(
                        field=f"{prefix}.label",
                        message="Nama pantangan wajib diisi.",
                    )
                )
                continue
            cleaned = _WHITESPACE_PATTERN.sub(" ", label.strip())
            if len(cleaned) > LABEL_MAX_LENGTH:
                errors.append(
                    ValidationError(
                        field=f"{prefix}.label",
                        message=f"Nama pantangan maksimal {LABEL_MAX_LENGTH} karakter.",
                    )
                )
                continue
            canonical = canonical_label(cleaned)
            builtin_match = _builtin_lookup(canonical)
            if builtin_match is not None:
                key, _ = builtin_match
                errors.append(
                    ValidationError(
                        field=f"{prefix}.label",
                        message=(
                            "Pantangan ini sudah tersedia sebagai pilihan bawaan. "
                            f"Gunakan trigger_key {key}."
                        ),
                    )
                )
                continue
            if canonical in seen_custom_labels:
                errors.append(
                    ValidationError(
                        field=f"{prefix}.label",
                        message="Nama pantangan ini sudah dipakai.",
                    )
                )
                continue
            seen_custom_labels[canonical] = index

            emoji_value: str | None = None
            if emoji is not None:
                if not isinstance(emoji, str) or not emoji.strip():
                    errors.append(
                        ValidationError(
                            field=f"{prefix}.emoji",
                            message="Emoji tidak valid.",
                        )
                    )
                    continue
                emoji_value = emoji.strip()
                if len(emoji_value) > EMOJI_MAX_LENGTH:
                    errors.append(
                        ValidationError(
                            field=f"{prefix}.emoji",
                            message=f"Emoji maksimal {EMOJI_MAX_LENGTH} karakter.",
                        )
                    )
                    continue

            inputs.append(
                TriggerPreferenceInput(
                    trigger_key=None,
                    label=cleaned,
                    emoji=emoji_value,
                    reaction_level=reaction_level,
                    is_custom=True,
                )
            )
            continue

        if not isinstance(trigger_key, str) or trigger_key not in BUILTIN_TRIGGERS:
            errors.append(
                ValidationError(
                    field=f"{prefix}.trigger_key",
                    message="Pemicu tidak dikenal.",
                )
            )
            continue
        if is_custom:
            errors.append(
                ValidationError(
                    field=f"{prefix}.is_custom",
                    message="Pantangan bawaan tidak boleh is_custom.",
                )
            )
            continue
        if trigger_key in seen_keys:
            errors.append(
                ValidationError(
                    field=f"{prefix}.trigger_key",
                    message="Pemicu ini dipilih lebih dari sekali.",
                )
            )
            continue
        seen_keys[trigger_key] = index

        inputs.append(
            TriggerPreferenceInput(
                trigger_key=trigger_key,
                label=None,
                emoji=None,
                reaction_level=reaction_level,
                is_custom=False,
            )
        )

    if errors:
        raise TriggerPreferenceValidationErrors(errors)

    return inputs


@dataclass(frozen=True)
class TriggerPreferenceValidationErrors(Exception):
    errors: list[ValidationError]

    def fields(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for error in self.errors:
            grouped.setdefault(error.field, []).append(error.message)
        return grouped


__all__ = [
    "BUILTIN_ALIASES",
    "BUILTIN_TRIGGERS",
    "TriggerPreferenceInput",
    "TriggerPreferenceValidationErrors",
    "canonical_label",
    "sensitivity_from_preferences",
    "validate_preferences",
]
