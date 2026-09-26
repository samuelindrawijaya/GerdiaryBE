from __future__ import annotations

from decimal import Decimal
from typing import Any

from gerdiary.modules.identity.domain import ValidationError


def validate_budget_amount(raw: Any) -> Decimal | None:
    """Validasi nominal budget. None = field tidak diisi (boleh)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise ValidationError(field="amount", message="Nominal budget tidak valid.")
    try:
        value = Decimal(str(raw))
    except Exception:  # noqa: BLE001
        raise ValidationError(field="amount", message="Nominal budget tidak valid.") from None
    if value < 0:
        raise ValidationError(field="amount", message="Nominal budget tidak boleh negatif.")
    return value


__all__ = ["validate_budget_amount"]
