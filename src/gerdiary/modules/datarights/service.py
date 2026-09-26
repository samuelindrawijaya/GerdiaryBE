from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.modules.identity.models import User
from gerdiary.modules.journal.models import FoodEntry, SymptomEvent

FOOD_CSV_COLUMNS = [
    "id",
    "consumed_at",
    "meal_type",
    "food_name",
    "emoji",
    "brand",
    "portion",
    "portion_unit",
    "serving_size",
    "preparation_method",
    "food_attributes",
    "source_type",
    "rating",
    "mood_after",
    "energy_level",
    "tags",
    "notes",
    "amount",
]

SYMPTOM_CSV_COLUMNS = [
    "id",
    "occurred_at",
    "symptom",
    "severity",
    "source",
    "notes",
    "food_entry_id",
]


def _session() -> Session:
    return cast("Session", db.session)


def _food_row(entry: FoodEntry) -> list[Any]:
    return [
        str(entry.id),
        entry.consumed_at.isoformat(),
        entry.meal_type,
        entry.food_name,
        entry.emoji or "",
        entry.brand or "",
        float(entry.portion) if entry.portion is not None else "",
        entry.portion_unit or "",
        entry.serving_size or "",
        entry.preparation_method or "",
        ";".join(entry.food_attributes or []),
        entry.source_type or "",
        entry.rating if entry.rating is not None else "",
        entry.mood_after or "",
        entry.energy_level or "",
        ";".join(entry.tags or []),
        entry.notes or "",
        float(entry.amount) if entry.amount is not None else "",
    ]


def _symptom_row(event: SymptomEvent) -> list[Any]:
    return [
        str(event.id),
        event.occurred_at.isoformat(),
        event.symptom,
        event.severity or "",
        event.source,
        event.notes or "",
        str(event.food_entry_id) if event.food_entry_id else "",
    ]


def _resolve_period(
    user: User, start: date | None, end: date | None
) -> tuple[datetime, datetime]:
    """Resolve export window; default: last 30 days in user timezone."""
    from gerdiary.modules.journal.domain import day_bounds

    tz = user.timezone or "UTC"
    if start is None or end is None:
        today = datetime.now().astimezone().date()
        from datetime import timedelta

        fallback_end = today
        fallback_start = today - timedelta(days=30)
        start = start or fallback_start
        end = end or fallback_end
    start_dt, _ = day_bounds(start, tz)
    _, end_dt = day_bounds(end, tz)
    return start_dt, end_dt


def export_csv(
    user: User, *, start: date | None = None, end: date | None = None
) -> dict[str, str]:
    """Return CSV strings for food entries and symptom events in period."""
    start_dt, end_dt = _resolve_period(user, start, end)

    food_entries = list(
        _session()
        .scalars(
            select(FoodEntry)
            .where(
                FoodEntry.user_id == user.id,
                FoodEntry.deleted_at.is_(None),
                FoodEntry.consumed_at >= start_dt,
                FoodEntry.consumed_at < end_dt,
            )
            .order_by(FoodEntry.consumed_at.asc())
        )
        .all()
    )

    symptom_events = list(
        _session()
        .scalars(
            select(SymptomEvent)
            .where(
                SymptomEvent.user_id == user.id,
                SymptomEvent.deleted_at.is_(None),
                SymptomEvent.occurred_at >= start_dt,
                SymptomEvent.occurred_at < end_dt,
            )
            .order_by(SymptomEvent.occurred_at.asc())
        )
        .all()
    )

    food_csv = _to_csv(FOOD_CSV_COLUMNS, [_food_row(e) for e in food_entries])
    symptom_csv = _to_csv(SYMPTOM_CSV_COLUMNS, [_symptom_row(e) for e in symptom_events])
    return {"food_entries": food_csv, "symptom_events": symptom_csv}


def _to_csv(columns: list[str], rows: list[list[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def delete_account(user: User) -> None:
    """Hard delete user dan semua data miliknya (cascade dari FK)."""
    _session().delete(user)
    _session().commit()


__all__ = ["delete_account", "export_csv"]
