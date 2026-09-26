from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from gerdiary.modules.journal.models import FoodEntry, SymptomEvent


def get_food_entry(db: Session, entry_id: str, user_id: str) -> FoodEntry | None:
    return db.scalar(
        select(FoodEntry).where(
            FoodEntry.id == entry_id,
            FoodEntry.user_id == user_id,
            FoodEntry.deleted_at.is_(None),
        )
    )


def get_symptom_event(db: Session, event_id: str, user_id: str) -> SymptomEvent | None:
    return db.scalar(
        select(SymptomEvent).where(
            SymptomEvent.id == event_id,
            SymptomEvent.user_id == user_id,
            SymptomEvent.deleted_at.is_(None),
        )
    )


def search_food_entries(
    db: Session,
    user_id: str,
    *,
    q: str | None = None,
    category_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[FoodEntry]:
    query = select(FoodEntry).where(
        FoodEntry.user_id == user_id,
        FoodEntry.deleted_at.is_(None),
    )
    if q:
        query = query.where(FoodEntry.food_name.ilike(f"%{q}%"))
    if category_id:
        query = query.where(FoodEntry.category_id == category_id)
    if start is not None:
        query = query.where(FoodEntry.consumed_at >= start)
    if end is not None:
        query = query.where(FoodEntry.consumed_at < end)
    return list(
        db.scalars(query.order_by(FoodEntry.consumed_at.desc()).limit(100)).all()
    )


def list_timeline_food(
    db: Session, user_id: str, start: datetime, end: datetime
) -> list[FoodEntry]:
    return list(
        db.scalars(
            select(FoodEntry)
            .where(
                FoodEntry.user_id == user_id,
                FoodEntry.deleted_at.is_(None),
                FoodEntry.consumed_at >= start,
                FoodEntry.consumed_at < end,
            )
            .order_by(FoodEntry.consumed_at.asc())
        )
    )


def list_timeline_symptoms(
    db: Session, user_id: str, start: datetime, end: datetime
) -> list[SymptomEvent]:
    return list(
        db.scalars(
            select(SymptomEvent)
            .where(
                SymptomEvent.user_id == user_id,
                SymptomEvent.deleted_at.is_(None),
                SymptomEvent.occurred_at >= start,
                SymptomEvent.occurred_at < end,
            )
            .order_by(SymptomEvent.occurred_at.asc())
        )
    )
