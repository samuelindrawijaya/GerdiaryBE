from __future__ import annotations

import re
from typing import Any

from gerdiary.modules.identity.domain import ValidationError

CATEGORY_NAME_MAX_LENGTH = 100
ICON_MAX_LENGTH = 50
SORT_ORDER_MIN = -10000
SORT_ORDER_MAX = 10000

CATEGORY_TYPES = {"expense", "food", "both"}

_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")


def validate_name(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="name", message="Nama kategori wajib diisi.")
    name = raw.strip()
    if len(name) > CATEGORY_NAME_MAX_LENGTH:
        raise ValidationError(field="name", message="Nama kategori terlalu panjang.")
    return name


def validate_category_type(raw: Any) -> str | None:
    if raw is None:
        return None
    if raw not in CATEGORY_TYPES:
        raise ValidationError(field="category_type", message="Tipe kategori tidak valid.")
    return str(raw)


def validate_icon(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(field="icon", message="Ikon tidak valid.")
    value = raw.strip()
    if not value:
        return None
    if len(value) > ICON_MAX_LENGTH:
        raise ValidationError(field="icon", message="Ikon terlalu panjang.")
    return value


def validate_color(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not _COLOR_PATTERN.fullmatch(raw):
        raise ValidationError(field="color", message="Warna harus format #RRGGBB.")
    return raw.lower()


def validate_sort_order(raw: Any) -> int | None:
    if raw is None:
        return None
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ValidationError(field="sort_order", message="Urutan tidak valid.")
    if not SORT_ORDER_MIN <= raw <= SORT_ORDER_MAX:
        raise ValidationError(field="sort_order", message="Urutan di luar batas.")
    return raw


def validate_is_active(raw: Any) -> bool | None:
    if raw is None:
        return None
    if not isinstance(raw, bool):
        raise ValidationError(field="is_active", message="Status aktif tidak valid.")
    return raw


__all__ = [
    "CATEGORY_NAME_MAX_LENGTH",
    "CATEGORY_TYPES",
    "validate_category_type",
    "validate_color",
    "validate_icon",
    "validate_is_active",
    "validate_name",
    "validate_sort_order",
]
