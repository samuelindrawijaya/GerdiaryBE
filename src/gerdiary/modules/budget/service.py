from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.modules.budget import domain
from gerdiary.modules.budget.models import Budget
from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.models import Category, User
from gerdiary.modules.journal import service as journal_service
from gerdiary.modules.journal.models import FoodEntry
from gerdiary.modules.spending.service import NotFoundError


def _session() -> Session:
    return cast("Session", db.session)


def list_budgets(user: User, *, year_month: str | None = None) -> list[Budget]:
    query = (
        select(Budget)
        .where(Budget.user_id == user.id, Budget.deleted_at.is_(None), Budget.is_active.is_(True))
    )
    if year_month:
        query = query.where(Budget.year_month == year_month)
    rows = _session().scalars(query.order_by(Budget.created_at.asc())).all()
    return list(rows)


def get_budget(user: User, budget_id: str) -> Budget:
    from gerdiary.modules.journal.domain import validate_uuid

    try:
        validated = validate_uuid(budget_id, "budget_id")
    except ValidationError:
        raise NotFoundError() from None
    result = _session().scalar(
        select(Budget).where(
            Budget.id == validated,
            Budget.user_id == user.id,
            Budget.deleted_at.is_(None),
            Budget.is_active.is_(True),
        )
    )
    if result is None:
        raise NotFoundError()
    return result


def create_budget(user: User, data: dict[str, Any]) -> Budget:
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    category_id = run(lambda: _validate_category_id(data.get("category_id"), user.id))
    year_month = run(lambda: _validate_year_month(data.get("year_month")))
    amount = run(lambda: domain.validate_budget_amount(data.get("amount")))

    if errors:
        raise ValidationErrors(errors)

    budget = Budget(
        user_id=user.id,
        category_id=category_id or "",
        year_month=year_month or "",
        amount=float(amount) if amount is not None else None,
    )
    _session().add(budget)
    _session().commit()
    return budget


def update_budget(user: User, budget_id: str, data: dict[str, Any]) -> Budget:
    budget = get_budget(user, budget_id)
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    if "category_id" in data:
        budget.category_id = run(_validate_category_id(data["category_id"], user.id))
    if "year_month" in data:
        budget.year_month = run(_validate_year_month(data["year_month"]))
    if "amount" in data:
        budget.amount = float(run(lambda: domain.validate_budget_amount(data["amount"])))
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            errors.append(ValidationError(field="is_active", message="Status aktif tidak valid."))
        else:
            budget.is_active = data["is_active"]

    if errors:
        raise ValidationErrors(errors)

    _session().commit()
    return budget


def delete_budget(user: User, budget_id: str) -> None:
    budget = get_budget(user, budget_id)
    budget.deleted_at = journal_service._now()  # noqa: SLF001
    _session().commit()


def calculate_progress(budget: Budget, as_of: date | None = None) -> dict[str, Any | float]:
    """Hitung progress actual vs target untuk budget ini."""
    if not budget.amount:
        return {"target": None, "actual": 0.0, "remaining": 0.0}

    budget_date = datetime.strptime(budget.year_month, "%Y-%m").date()
    if budget_date.month < 12:
        next_month = budget_date.replace(month=budget_date.month + 1)
    else:
        next_month = budget_date.replace(year=budget_date.year + 1, month=1)

    query = (
        select(func.sum(FoodEntry.amount))
        .where(
            FoodEntry.category_id == budget.category_id,
            FoodEntry.consumed_at >= budget_date,
            FoodEntry.consumed_at < next_month,
            FoodEntry.deleted_at.is_(None),
        )
    )
    actual = float(_session().scalar(query) or 0)
    target = float(budget.amount)
    remaining = max(target - actual, 0.0)

    return {
        "target": target,
        "actual": actual,
        "remaining": remaining,
    }


def payload(budget: Budget) -> dict[str, Any]:
    result = {
        "id": str(budget.id),
        "user_id": budget.user_id,
        "category_id": budget.category_id,
        "year_month": budget.year_month,
        "amount": float(budget.amount) if budget.amount is not None else None,
        "is_active": budget.is_active,
    }
    result.update(calculate_progress(budget))
    return result


def _validate_category_id(raw: Any | None, user_id: str) -> str:
    from gerdiary.modules.journal.domain import validate_uuid

    if raw is None:
        raise ValidationError(field="category_id", message="Kategori wajib diisi.")
    validated = validate_uuid(str(raw), "category_id")
    cat = _session().scalar(
        select(Category).where(Category.id == validated, Category.user_id == user_id)
    )
    if cat is None:
        raise NotFoundError()
    return str(validated)


def _validate_year_month(raw: Any | None) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(field="year_month", message="Bulan wajib diisi.")
    value = raw.strip()
    if len(value) != 7 or value[4] != "-":
        raise ValidationError(field="year_month", message="Format bulan YYYY-MM diperlukan.")
    year_part, month_part = value[:4], value[5:]
    if not (year_part.isdigit() and month_part.isdigit()):
        raise ValidationError(field="year_month", message="Format bulan YYYY-MM diperlukan.")
    if not (1 <= int(month_part) <= 12):
        raise ValidationError(field="year_month", message="Bulan tidak valid.")
    return value


__all__ = [
    "calculate_progress",
    "create_budget",
    "delete_budget",
    "get_budget",
    "list_budgets",
    "payload",
    "update_budget",
]
