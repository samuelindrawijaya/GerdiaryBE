from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.models import Category, User
from gerdiary.modules.journal import domain, repository
from gerdiary.modules.journal.models import FavoriteFood, FoodEntry, SymptomEvent
from gerdiary.modules.safety import red_flags
from gerdiary.modules.spending import domain as spending_domain


class NotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CreatedSymptom:
    id: str
    symptom: str
    severity: str | None
    occurred_at: datetime
    red_flag_code: str | None


@dataclass(frozen=True)
class TimelineItem:
    kind: str
    occurred_at: datetime
    payload: dict[str, Any]


class _Collector:
    def __init__(self) -> None:
        self.errors: list[ValidationError] = []

    def run(self, validator: Callable[[], Any]) -> Any:
        try:
            return validator()
        except ValidationError as error:
            self.errors.append(error)
            return None

    def raise_if_any(self) -> None:
        if self.errors:
            raise ValidationErrors(self.errors)


def _now() -> datetime:
    return datetime.now(UTC)


def _session() -> Session:
    return cast("Session", db.session)


def _owned_category(category_id: str, user_id: str) -> Category:
    category = db.session.get(Category, category_id)
    if category is None or category.user_id != user_id:
        raise NotFoundError()
    return category


def _owned_account(account_id: Any, user_id: str) -> Any:
    from gerdiary.modules.spending.models import Account

    account = db.session.get(Account, account_id)
    if account is None or account.user_id != user_id or account.deleted_at is not None:
        raise NotFoundError()
    return account


def _owned_vendor(vendor_id: Any, user_id: str) -> Any:
    from gerdiary.modules.spending.models import Vendor

    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None or vendor.user_id != user_id or vendor.deleted_at is not None:
        raise NotFoundError()
    return vendor


def _optional_vendor_id(raw: Any | None, user_id: str) -> str | None:
    """Validate optional vendor UUID and check ownership."""
    if raw is None:
        return None
    try:
        validated = domain.validate_uuid(str(raw), "vendor_id")
    except ValidationError as error:
        raise NotFoundError() from error
    return str(_owned_vendor(validated, user_id).id)


def _optional_account_id(raw: Any | None, user_id: str) -> str | None:
    """Validate optional UUID and check ownership."""
    if raw is None:
        return None
    try:
        validated = domain.validate_uuid(str(raw), "account_id")
    except ValidationError as error:
        raise NotFoundError() from error
    return str(_owned_account(validated, user_id).id)


def _choice(field: str) -> tuple[set[str], str]:
    return {
        "portion_unit": (domain.PORTION_UNITS, "Satuan porsi tidak valid."),
        "serving_size": (domain.SERVING_SIZES, "Ukuran porsi tidak valid."),
        "preparation_method": (domain.PREPARATION_METHODS, "Cara masak tidak valid."),
        "source_type": (domain.SOURCE_TYPES, "Sumber makanan tidak valid."),
        "mood_after": (domain.MOOD_AFTERS, "Kondisi setelah makan tidak valid."),
        "energy_level": (domain.ENERGY_LEVELS, "Tingkat energi tidak valid."),
    }[field]


def _text_limit(field: str) -> int:
    if field == "emoji":
        return domain.EMOJI_MAX_LENGTH
    if field == "brand":
        return domain.FOOD_NAME_MAX_LENGTH
    return domain.NOTES_MAX_LENGTH


def _build_food(
    user: User, category: Category, data: dict[str, Any], collector: _Collector
) -> FoodEntry:
    optional_choice = domain.validate_optional_choice
    
    portion_unit_field = "portion_unit"
    serving_size_field = "serving_size"
    preparation_method_field = "preparation_method"
    source_type_field = "source_type"
    mood_after_field = "mood_after"
    energy_level_field = "energy_level"
    
    return FoodEntry(
        user_id=user.id,
        category_id=category.id,
        meal_type=collector.run(lambda: domain.validate_meal_type(data.get("meal_type"))),
        food_name=collector.run(lambda: domain.validate_food_name(data.get("food_name"))),
        consumed_at=collector.run(
            lambda: domain.validate_timestamp(data.get("consumed_at"), "consumed_at")
        ),
        emoji=collector.run(
            lambda: domain.validate_optional_text(
                data.get("emoji"), "emoji", domain.EMOJI_MAX_LENGTH, "Emoji tidak valid."
            )
        ),
        brand=collector.run(
            lambda: domain.validate_optional_text(
                data.get("brand"), "brand", domain.FOOD_NAME_MAX_LENGTH, "Merek tidak valid."
            )
        ),
        portion=collector.run(lambda: domain.validate_portion(data.get("portion"))),
        portion_unit=collector.run(
            lambda: optional_choice(
                data.get(portion_unit_field),
                domain.PORTION_UNITS,
                portion_unit_field,
                "Satuan porsi tidak valid."
            )
        ),
        serving_size=collector.run(
            lambda: optional_choice(
                data.get(serving_size_field),
                domain.SERVING_SIZES,
                serving_size_field,
                "Ukuran porsi tidak valid."
            )
        ),
        preparation_method=collector.run(
            lambda: optional_choice(
                data.get(preparation_method_field),
                domain.PREPARATION_METHODS,
                preparation_method_field,
                "Cara masak tidak valid."
            )
        ),
        food_attributes=collector.run(
            lambda: domain.validate_food_attributes(data.get("food_attributes"))
        ),
        source_type=collector.run(
            lambda: optional_choice(
                data.get(source_type_field),
                domain.SOURCE_TYPES,
                source_type_field,
                "Sumber makanan tidak valid."
            )
        ),
        rating=collector.run(lambda: domain.validate_rating(data.get("rating"))),
        mood_after=collector.run(
            lambda: optional_choice(
                data.get(mood_after_field),
                domain.MOOD_AFTERS,
                mood_after_field,
                "Kondisi setelah makan tidak valid."
            )
        ),
        energy_level=collector.run(
            lambda: optional_choice(
                data.get(energy_level_field),
                domain.ENERGY_LEVELS,
                energy_level_field,
                "Tingkat energi tidak valid."
            )
        ),
        tags=collector.run(lambda: domain.validate_tags(data.get("tags"))),
        notes=collector.run(
            lambda: domain.validate_optional_text(
                data.get("notes"), "notes", domain.NOTES_MAX_LENGTH, "Catatan terlalu panjang."
            )
        ),
        amount=collector.run(
            lambda: spending_domain.validate_amount(data.get("amount"))
        ),
        account_id=collector.run(
            lambda: _optional_account_id(data.get("account_id"), user.id)
        ),
        vendor_id=collector.run(
            lambda: _optional_vendor_id(data.get("vendor_id"), user.id)
        ),
    )


def create_food_entry(user: User, *, category_id: str, data: dict[str, Any]) -> FoodEntry:
    category = _owned_category(category_id, user.id)
    collector = _Collector()
    entry = _build_food(user, category, data, collector)
    collector.raise_if_any()

    db.session.add(entry)
    db.session.commit()
    return entry


def _build_symptom(
    user: User,
    entry_id: str | None,
    symptom_data: dict[str, Any],
    collector: _Collector,
) -> tuple[SymptomEvent, str | None]:
    symptom = collector.run(lambda: domain.validate_symptom(symptom_data.get("symptom")))
    severity = collector.run(
        lambda: domain.validate_optional_choice(
            symptom_data.get("severity"),
            domain.SEVERITIES,
            "severity",
            "Tingkat keparahan tidak valid.",
        )
    )
    occurred_at = collector.run(
        lambda: domain.validate_timestamp(symptom_data.get("occurred_at"), "occurred_at")
    )
    source = symptom_data.get("source", "entry_form")
    if source not in domain.SOURCES:
        collector.errors.append(
            ValidationError(field="source", message="Sumber gejala tidak valid.")
        )

    event = SymptomEvent(
        user_id=user.id,
        food_entry_id=entry_id,
        symptom=symptom or "",
        severity=severity,
        occurred_at=occurred_at or _now(),
        source=source if source in domain.SOURCES else "entry_form",
        notes=collector.run(
            lambda: domain.validate_optional_text(
                symptom_data.get("notes"),
                "notes",
                domain.NOTES_MAX_LENGTH,
                "Catatan terlalu panjang.",
            )
        ),
    )
    return event, red_flags.code_for(event.symptom, event.severity or "")


def create_symptom_event(
    user: User, *, food_entry_id: str | None, data: dict[str, Any]
) -> tuple[SymptomEvent, str | None]:
    entry_id: str | None = None
    if food_entry_id is not None:
        entry_id = str(domain.validate_uuid(food_entry_id, "food_entry_id"))
        if repository.get_food_entry(_session(), entry_id, user.id) is None:
            raise NotFoundError()

    collector = _Collector()
    event, flag_code = _build_symptom(user, entry_id, data, collector)
    collector.raise_if_any()

    db.session.add(event)
    db.session.commit()
    return event, flag_code


def create_food_entry_with_symptoms(
    user: User, *, category_id: str, data: dict[str, Any], symptoms: list[dict[str, Any]]
) -> tuple[FoodEntry, list[CreatedSymptom]]:
    category = _owned_category(category_id, user.id)
    collector = _Collector()
    entry = _build_food(user, category, data, collector)

    created: list[CreatedSymptom] = []
    pending: list[tuple[SymptomEvent, str | None]] = []
    for symptom_data in symptoms:
        if not isinstance(symptom_data, dict):
            collector.errors.append(
                ValidationError(field="symptoms", message="Data gejala tidak valid.")
            )
            continue
        event, flag_code = _build_symptom(user, entry.id, symptom_data, collector)
        pending.append((event, flag_code))

    collector.raise_if_any()

    db.session.add(entry)
    db.session.flush()
    for event, flag_code in pending:
        event.food_entry_id = entry.id
        db.session.add(event)
        db.session.flush()
        created.append(
            CreatedSymptom(
                id=event.id,
                symptom=event.symptom,
                severity=event.severity,
                occurred_at=event.occurred_at,
                red_flag_code=flag_code,
            )
        )

    db.session.commit()
    return entry, created


def get_timeline(user: User, local_date: date) -> list[TimelineItem]:
    start, end = domain.day_bounds(local_date, user.timezone or "UTC")
    items: list[TimelineItem] = []

    for entry in repository.list_timeline_food(_session(), user.id, start, end):
        items.append(
            TimelineItem(
                kind="food", occurred_at=entry.consumed_at, payload=_food_payload(entry, user)
            )
        )

    for event in repository.list_timeline_symptoms(_session(), user.id, start, end):
        flag_code = red_flags.code_for(event.symptom, event.severity or "")
        items.append(
            TimelineItem(
                kind="symptom",
                occurred_at=event.occurred_at,
                payload=_symptom_payload(event, flag_code),
            )
        )

    items.sort(key=lambda item: item.occurred_at)
    return items


def get_food_entry(user: User, entry_id: str) -> FoodEntry:
    entry = repository.get_food_entry(_session(), entry_id, user.id)
    if entry is None:
        raise NotFoundError()
    return entry


def get_symptom_event(user: User, event_id: str) -> SymptomEvent:
    event = repository.get_symptom_event(_session(), event_id, user.id)
    if event is None:
        raise NotFoundError()
    return event


def update_food_entry(user: User, entry_id: str, data: dict[str, Any]) -> FoodEntry:
    entry = get_food_entry(user, entry_id)
    collector = _Collector()

    if "category_id" in data and data.get("category_id") is not None:
        category_id = collector.run(
            lambda: domain.validate_uuid(data.get("category_id"), "category_id")
        )
        if category_id is not None:
            entry.category_id = _owned_category(str(category_id), user.id).id

    if "meal_type" in data:
        entry.meal_type = collector.run(lambda: domain.validate_meal_type(data.get("meal_type")))
    if "food_name" in data:
        entry.food_name = collector.run(lambda: domain.validate_food_name(data.get("food_name")))
    if "consumed_at" in data:
        entry.consumed_at = collector.run(
            lambda: domain.validate_timestamp(data.get("consumed_at"), "consumed_at")
        )

    optional_choice = domain.validate_optional_choice

    def apply_choice(field_name: str) -> None:
        values, message = _choice(field_name)
        setattr(
            entry,
            field_name,
            collector.run(
                lambda: optional_choice(data.get(field_name), values, field_name, message)
            ),
        )

    for field in (
        "portion_unit",
        "serving_size",
        "preparation_method",
        "source_type",
        "mood_after",
        "energy_level",
    ):
        if field in data:
            apply_choice(field)

    def apply_text(field_name: str) -> None:
        setattr(
            entry,
            field_name,
            collector.run(
                lambda: domain.validate_optional_text(
                    data.get(field_name), field_name, _text_limit(field_name), "Nilai tidak valid."
                )
            ),
        )

    for field in ("emoji", "brand", "notes"):
        if field in data:
            apply_text(field)

    if "portion" in data:
        entry.portion = collector.run(lambda: domain.validate_portion(data.get("portion")))
    if "rating" in data:
        entry.rating = collector.run(lambda: domain.validate_rating(data.get("rating")))
    if "food_attributes" in data:
        entry.food_attributes = collector.run(
            lambda: domain.validate_food_attributes(data.get("food_attributes"))
        )
    if "tags" in data:
        entry.tags = collector.run(lambda: domain.validate_tags(data.get("tags")))
    if "amount" in data:
        entry.amount = collector.run(
            lambda: spending_domain.validate_amount(data.get("amount"))
        )
    if "account_id" in data:
        entry.account_id = collector.run(
            lambda: _optional_account_id(data.get("account_id"), user.id)
        )
    if "vendor_id" in data:
        entry.vendor_id = collector.run(
            lambda: _optional_vendor_id(data.get("vendor_id"), user.id)
        )

    collector.raise_if_any()
    db.session.commit()
    return entry


def update_symptom_event(
    user: User, event_id: str, data: dict[str, Any]
) -> tuple[SymptomEvent, str | None]:
    event = get_symptom_event(user, event_id)
    collector = _Collector()

    if "food_entry_id" in data:
        raw_entry_id = data.get("food_entry_id")
        if raw_entry_id is None:
            event.food_entry_id = None
        else:
            entry_uuid = collector.run(
                lambda: domain.validate_uuid(raw_entry_id, "food_entry_id")
            )
            if entry_uuid is not None:
                entry = repository.get_food_entry(_session(), str(entry_uuid), user.id)
                if entry is None:
                    raise NotFoundError()
                event.food_entry_id = entry.id

    if "symptom" in data:
        event.symptom = collector.run(lambda: domain.validate_symptom(data.get("symptom")))
    if "severity" in data:
        event.severity = collector.run(
            lambda: domain.validate_optional_choice(
                data.get("severity"),
                domain.SEVERITIES,
                "severity",
                "Tingkat keparahan tidak valid.",
            )
        )
    if "occurred_at" in data:
        event.occurred_at = collector.run(
            lambda: domain.validate_timestamp(data.get("occurred_at"), "occurred_at")
        )
    if "source" in data:
        source = data.get("source")
        if source not in domain.SOURCES:
            collector.errors.append(
                ValidationError(field="source", message="Sumber gejala tidak valid.")
            )
        else:
            event.source = source
    if "notes" in data:
        event.notes = collector.run(
            lambda: domain.validate_optional_text(
                data.get("notes"), "notes", domain.NOTES_MAX_LENGTH, "Catatan terlalu panjang."
            )
        )

    collector.raise_if_any()
    db.session.commit()
    return event, red_flags.code_for(event.symptom, event.severity or "")


def delete_food_entry(user: User, entry_id: str) -> None:
    entry = get_food_entry(user, entry_id)
    entry.deleted_at = _now()
    db.session.commit()


def repeat_food_entry(
    user: User, entry_id: str, *, consumed_at: datetime | None = None
) -> FoodEntry:
    """Salin food entry lama menjadi entry baru dengan consumed_at baru.

    Symptom event tidak ikut disalin — repeat hanya untuk makanan.
    Jika consumed_at tidak diberikan, gunakan waktu sekarang.
    """
    old_entry = get_food_entry(user, entry_id)

    new_entry = FoodEntry(
        user_id=old_entry.user_id,
        category_id=old_entry.category_id,
        meal_type=old_entry.meal_type,
        food_name=old_entry.food_name,
        consumed_at=consumed_at if consumed_at is not None else _now(),
        emoji=old_entry.emoji,
        brand=old_entry.brand,
        portion=old_entry.portion,
        portion_unit=old_entry.portion_unit,
        serving_size=old_entry.serving_size,
        preparation_method=old_entry.preparation_method,
        food_attributes=old_entry.food_attributes,
        source_type=old_entry.source_type,
        rating=old_entry.rating,
        mood_after=old_entry.mood_after,
        energy_level=old_entry.energy_level,
        tags=old_entry.tags,
        notes=old_entry.notes,
        amount=old_entry.amount,
        account_id=old_entry.account_id,
        vendor_id=old_entry.vendor_id,
    )

    db.session.add(new_entry)
    db.session.commit()
    return new_entry


def list_favorites(user: User) -> list[FavoriteFood]:
    rows = (
        _session()
        .scalars(
            select(FavoriteFood)
            .where(
                FavoriteFood.user_id == user.id,
                FavoriteFood.deleted_at.is_(None),
            )
            .order_by(FavoriteFood.created_at.desc())
        )
        .all()
    )
    return list(rows)


def add_favorite(user: User, data: dict[str, Any]) -> FavoriteFood:
    collector = _Collector()

    food_name = collector.run(lambda: domain.validate_food_name(data.get("food_name")))
    emoji = collector.run(
        lambda: domain.validate_optional_text(
            data.get("emoji"), "emoji", domain.EMOJI_MAX_LENGTH, "Emoji tidak valid."
        )
    )
    brand = collector.run(
        lambda: domain.validate_optional_text(
            data.get("brand"), "brand", domain.FOOD_NAME_MAX_LENGTH, "Merek tidak valid."
        )
    )
    portion = collector.run(lambda: domain.validate_portion(data.get("portion")))
    portion_unit = collector.run(
        lambda: domain.validate_optional_choice(
            data.get("portion_unit"),
            domain.PORTION_UNITS,
            "portion_unit",
            "Satuan porsi tidak valid.",
        )
    )
    notes = collector.run(
        lambda: domain.validate_optional_text(
            data.get("notes"), "notes", domain.NOTES_MAX_LENGTH, "Catatan terlalu panjang."
        )
    )

    if collector.errors:
        raise ValidationErrors(collector.errors)

    favorite = FavoriteFood(
        user_id=user.id,
        food_name=food_name,
        emoji=emoji,
        brand=brand,
        portion=portion,
        portion_unit=portion_unit,
        notes=notes,
    )
    db.session.add(favorite)
    db.session.commit()
    return favorite


def remove_favorite(user: User, favorite_id: str) -> None:
    favorite = _session().scalar(
        select(FavoriteFood).where(
            FavoriteFood.id == favorite_id,
            FavoriteFood.user_id == user.id,
            FavoriteFood.deleted_at.is_(None),
        )
    )
    if favorite is None:
        raise NotFoundError()
    favorite.deleted_at = _now()
    db.session.commit()


def _favorite_payload(favorite: FavoriteFood) -> dict[str, Any]:
    return {
        "id": str(favorite.id),
        "food_name": favorite.food_name,
        "emoji": favorite.emoji,
        "brand": favorite.brand,
        "portion": float(favorite.portion) if favorite.portion is not None else None,
        "portion_unit": favorite.portion_unit,
        "notes": favorite.notes,
    }


def delete_symptom_event(user: User, event_id: str) -> None:
    event = get_symptom_event(user, event_id)
    event.deleted_at = _now()
    db.session.commit()


def search_food_entries(
    user: User,
    *,
    q: str | None = None,
    category_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[FoodEntry]:
    if category_id is not None:
        category_id = str(_owned_category(category_id, user.id).id)
    start_dt = end_dt = None
    if start is not None:
        start_dt, _ = domain.day_bounds(start, user.timezone or "UTC")
    if end is not None:
        _, end_dt = domain.day_bounds(end, user.timezone or "UTC")
    if start_dt is not None and end_dt is not None and start_dt >= end_dt:
        raise ValidationError(field="start", message="Rentang tanggal tidak valid.")
    return repository.search_food_entries(
        _session(), user.id, q=q, category_id=category_id, start=start_dt, end=end_dt
    )


def _food_payload(entry: FoodEntry, user: User) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "consumed_at": entry.consumed_at.isoformat(),
        "meal_type": entry.meal_type,
        "food_name": entry.food_name,
        "emoji": entry.emoji,
        "brand": entry.brand,
        "portion": float(entry.portion) if entry.portion is not None else None,
        "portion_unit": entry.portion_unit,
        "serving_size": entry.serving_size,
        "preparation_method": entry.preparation_method,
        "food_attributes": entry.food_attributes or [],
        "source_type": entry.source_type,
        "rating": entry.rating,
        "mood_after": entry.mood_after,
        "energy_level": entry.energy_level,
        "tags": entry.tags or [],
        "notes": entry.notes,
        "amount": float(entry.amount) if entry.amount is not None else None,
        "account_id": str(entry.account_id) if entry.account_id is not None else None,
        "vendor_id": str(entry.vendor_id) if entry.vendor_id is not None else None,
        "late_night": domain.is_late_night(entry.consumed_at, user.sleep_time, user.timezone),
    }


def _symptom_payload(event: SymptomEvent, flag_code: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "symptom": event.symptom,
        "severity": event.severity,
        "source": event.source,
        "notes": event.notes,
        "food_entry_id": str(event.food_entry_id) if event.food_entry_id else None,
    }
    if flag_code:
        payload["red_flag"] = red_flags.payload(flag_code)
    return payload
