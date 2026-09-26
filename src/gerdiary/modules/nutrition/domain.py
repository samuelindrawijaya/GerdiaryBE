from __future__ import annotations

from gerdiary.modules.identity.domain import ValidationError

SEARCH_QUERY_MAX_LENGTH = 100


class ProviderUnavailable(Exception):
    pass


def validate_search_query(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="q", message="Kata kunci pencarian wajib diisi.")
    value = raw.strip()
    if len(value) > SEARCH_QUERY_MAX_LENGTH:
        raise ValidationError(field="q", message="Kata kunci pencarian terlalu panjang.")
    return value


def validate_barcode(raw: object) -> str:
    if not isinstance(raw, str) or not raw.isdigit() or not (8 <= len(raw) <= 14):
        raise ValidationError(field="barcode", message="Barcode tidak valid.")
    return raw


__all__ = [
    "ProviderUnavailable",
    "validate_barcode",
    "validate_search_query",
]
