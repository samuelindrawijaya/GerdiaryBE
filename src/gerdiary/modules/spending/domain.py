from __future__ import annotations

from decimal import Decimal
from typing import Any

from gerdiary.modules.identity.domain import ValidationError

# ---------------------------------------------------------------------------
# Accounts (payment sources)
# ---------------------------------------------------------------------------

ACCOUNT_NAME_MAX_LENGTH = 100
EMOJI_MAX_LENGTH = 32

AMOUNT_MIN = Decimal("0")
AMOUNT_MAX = Decimal("999999999.99")


def validate_account_name(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="name", message="Nama sumber pembayaran wajib diisi.")
    name = raw.strip()
    if len(name) > ACCOUNT_NAME_MAX_LENGTH:
        raise ValidationError(field="name", message="Nama sumber pembayaran terlalu panjang.")
    return name


def validate_emoji(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(field="emoji", message="Emoji tidak valid.")
    value = raw.strip()
    if not value:
        return None
    if len(value) > EMOJI_MAX_LENGTH:
        raise ValidationError(field="emoji", message="Emoji terlalu panjang.")
    return value


def validate_account_is_active(raw: Any) -> bool | None:
    if raw is None:
        return None
    if not isinstance(raw, bool):
        raise ValidationError(field="is_active", message="Status aktif tidak valid.")
    return raw


def validate_amount(raw: Any) -> Decimal | None:
    """Validasi jumlah pengeluaran. None berarti field tidak diisi (0/boleh kosong)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise ValidationError(field="amount", message="Jumlah pengeluaran tidak valid.")
    try:
        value = Decimal(str(raw))
    except Exception:  # noqa: BLE001 - parse error jadi validation error
        raise ValidationError(field="amount", message="Jumlah pengeluaran tidak valid.") from None
    if not AMOUNT_MIN <= value <= AMOUNT_MAX:
        raise ValidationError(field="amount", message="Jumlah pengeluaran di luar batas.")
    return value


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

VENDOR_NAME_MAX_LENGTH = 150
VENDOR_CATEGORY_MAX_LENGTH = 80


def validate_vendor_name(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="name", message="Nama vendor wajib diisi.")
    name = raw.strip()
    if len(name) > VENDOR_NAME_MAX_LENGTH:
        raise ValidationError(
            field="name", message="Nama vendor terlalu panjang."
        )
    return name


def validate_vendor_category(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(field="category", message="Kategori vendor tidak valid.")
    value = raw.strip().lower()
    if not value:
        return None
    if len(value) > VENDOR_CATEGORY_MAX_LENGTH:
        raise ValidationError(field="category", message="Kategori vendor terlalu panjang.")
    return value


__all__ = [
    "ACCOUNT_NAME_MAX_LENGTH",
    "AMOUNT_MAX",
    "AMOUNT_MIN",
    "EMOJI_MAX_LENGTH",
    "VENDOR_CATEGORY_MAX_LENGTH",
    "VENDOR_NAME_MAX_LENGTH",
    "validate_account_is_active",
    "validate_account_name",
    "validate_amount",
    "validate_emoji",
    "validate_vendor_category",
    "validate_vendor_name",
]
