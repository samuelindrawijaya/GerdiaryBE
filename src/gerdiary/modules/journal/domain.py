from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from gerdiary.modules.identity.domain import ValidationError

FOOD_NAME_MAX_LENGTH = 255
NOTES_MAX_LENGTH = 2000
EMOJI_MAX_LENGTH = 32
TAG_MAX_LENGTH = 50
TAG_MAX_ITEMS = 20
FUTURE_GRACE = timedelta(minutes=5)

MEAL_TYPES = {
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "drink",
    "supplement",
}

FOOD_ATTRIBUTES = {
    "spicy",
    "acidic",
    "oily",
    "high-fat",
    "caffeinated",
    "carbonated",
    "dairy",
    "gluten",
}

SYMPTOMS = {
    "heartburn",
    "bloating",
    "nausea",
    "stomach_ache",
    "gas",
    "burping",
    "regurgitation",
    "difficulty_swallowing",
    "chest_pain",
    "vomit_blood",
    "black_stool",
    "other",
}

SEVERITIES = {"mild", "moderate", "severe"}

PORTION_UNITS = {"g", "ml", "cup", "pcs", "slice", "bowl", "pack"}
SERVING_SIZES = {"small", "medium", "large", "extra_large"}
PREPARATION_METHODS = {
    "fried",
    "boiled",
    "steamed",
    "grilled",
    "raw",
    "baked",
    "roasted",
    "other",
}
SOURCE_TYPES = {"home_cooked", "takeaway", "dine_in", "instant"}
MOOD_AFTERS = {"good", "neutral", "tired", "uncomfortable", "nauseous"}
ENERGY_LEVELS = {"low", "normal", "high"}
SOURCES = {"entry_form", "quick_check", "manual"}


def validate_choice(raw: Any, allowed: set[str], field: str, message: str) -> str:
    if raw not in allowed:
        raise ValidationError(field=field, message=message)
    return str(raw)


def validate_optional_choice(
    raw: Any, allowed: set[str], field: str, message: str
) -> str | None:
    if raw is None:
        return None
    return validate_choice(raw, allowed, field, message)


def validate_food_name(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="food_name", message="Nama makanan wajib diisi.")
    name = raw.strip()
    if len(name) > FOOD_NAME_MAX_LENGTH:
        raise ValidationError(field="food_name", message="Nama makanan terlalu panjang.")
    return name


def validate_timestamp(raw: Any, field: str, now: datetime | None = None) -> datetime:
    if not isinstance(raw, str):
        raise ValidationError(field=field, message="Waktu tidak valid.")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        raise ValidationError(field=field, message="Waktu tidak valid.") from None
    if value.tzinfo is None:
        raise ValidationError(field=field, message="Waktu harus menyertakan zona waktu.")
    if is_future(value, now or datetime.now(UTC)):
        raise ValidationError(field=field, message="Waktu tidak boleh di masa depan.")
    return value


def validate_optional_text(
    raw: Any, field: str, max_length: int, message: str
) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(field=field, message=message)
    value = raw.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ValidationError(field=field, message=message)
    return value


def validate_rating(raw: Any) -> int | None:
    if raw is None:
        return None
    if not isinstance(raw, int) or isinstance(raw, bool) or not 1 <= raw <= 5:
        raise ValidationError(field="rating", message="Rating harus antara 1 sampai 5.")
    return raw


def validate_portion(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValidationError(field="portion", message="Porsi tidak valid.")
    if isinstance(raw, int):
        raw = float(raw)
    if not isinstance(raw, float) or not (0 < raw <= 100000):
        raise ValidationError(field="portion", message="Porsi tidak valid.")
    return raw


def validate_tags(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValidationError(field="tags", message="Tag tidak valid.")
    tags = [item.strip() for item in raw if item.strip()]
    if any(len(tag) > TAG_MAX_LENGTH for tag in tags):
        raise ValidationError(field="tags", message="Tag terlalu panjang.")
    tags = list(dict.fromkeys(tags))
    if len(tags) > TAG_MAX_ITEMS:
        raise ValidationError(field="tags", message="Terlalu banyak tag.")
    return tags or None


def validate_uuid(raw: Any, field: str) -> UUID:
    if not isinstance(raw, str):
        raise ValidationError(field=field, message="Identitas tidak valid.")
    try:
        return UUID(raw)
    except ValueError:
        raise ValidationError(field=field, message="Identitas tidak valid.") from None


def validate_meal_type(raw: Any) -> str:
    if raw not in MEAL_TYPES:
        raise ValidationError(field="meal_type", message="Tipe makan tidak valid.")
    return str(raw)


def validate_food_attributes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValidationError(field="food_attributes", message="Atribut makanan tidak valid.")
    attributes = list(dict.fromkeys(raw))
    unknown = [item for item in attributes if item not in FOOD_ATTRIBUTES]
    if unknown:
        raise ValidationError(field="food_attributes", message="Atribut makanan tidak valid.")
    return attributes


def validate_symptom(raw: Any) -> str:
    if raw not in SYMPTOMS:
        raise ValidationError(field="symptom", message="Gejala tidak valid.")
    return str(raw)


def validate_severity(raw: Any) -> str:
    if raw not in SEVERITIES:
        raise ValidationError(field="severity", message="Tingkat keparahan tidak valid.")
    return str(raw)


def is_future(value: datetime, now: datetime) -> bool:
    return value > now + FUTURE_GRACE


def parse_timeline_date(raw: Any) -> date:
    if not isinstance(raw, str):
        raise ValidationError(field="date", message="Tanggal tidak valid.")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError(field="date", message="Tanggal tidak valid.") from None


def validate_date(raw: Any, field: str) -> date:
    if not isinstance(raw, str):
        raise ValidationError(field=field, message="Tanggal tidak valid.")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError(field=field, message="Tanggal tidak valid.") from None


def day_bounds(local_date: date, timezone: str) -> tuple[datetime, datetime]:
    tz: ZoneInfo | dt_timezone
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = UTC
    start = datetime.combine(local_date, time(0, 0), tzinfo=tz)
    return start, start + timedelta(days=1)


def is_late_night(consumed_at: datetime, sleep_time: str | None, timezone: str | None) -> bool:
    if not sleep_time:
        return False
    parts = sleep_time.split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return False
    try:
        tz = ZoneInfo(timezone) if timezone else None
    except Exception:
        tz = None
    local = consumed_at.astimezone(tz) if tz else consumed_at
    bedtime_today = datetime.combine(
        local.date(), time(hour, minute), tzinfo=local.tzinfo
    )
    next_bedtime = bedtime_today if bedtime_today >= local else bedtime_today + timedelta(days=1)
    return timedelta(0) <= next_bedtime - local <= timedelta(hours=3)


__all__ = [
    "ENERGY_LEVELS",
    "FOOD_ATTRIBUTES",
    "FOOD_NAME_MAX_LENGTH",
    "MEAL_TYPES",
    "MOOD_AFTERS",
    "PORTION_UNITS",
    "PREPARATION_METHODS",
    "SERVING_SIZES",
    "SEVERITIES",
    "SOURCE_TYPES",
    "SOURCES",
    "SYMPTOMS",
    "is_future",
    "is_late_night",
    "parse_timeline_date",
    "validate_choice",
    "validate_food_attributes",
    "validate_food_name",
    "validate_meal_type",
    "validate_optional_choice",
    "validate_optional_text",
    "validate_portion",
    "validate_rating",
    "validate_severity",
    "validate_symptom",
    "validate_tags",
    "validate_timestamp",
    "validate_uuid",
    "day_bounds",
]
