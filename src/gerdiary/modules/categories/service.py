from __future__ import annotations

from typing import Any, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.modules.categories import domain
from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.models import Category, User
from gerdiary.modules.journal import domain as journal_domain


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _session() -> Session:
    return cast("Session", db.session)


def list_categories(user: User) -> list[Category]:
    return list(
        db.session.query(Category)
        .filter(Category.user_id == user.id)
        .order_by(Category.sort_order.asc().nullslast(), Category.name.asc())
        .all()
    )


def get_category(user: User, category_id: str) -> Category:
    category = db.session.get(Category, category_id)
    if category is None or category.user_id != user.id:
        raise NotFoundError()
    return category


def _resolve_parent(user: User, data: dict[str, Any], exclude_id: str | None) -> str | None:
    if "parent_id" not in data:
        return None
    raw = data.get("parent_id")
    if raw is None:
        return None
    parent_id = str(journal_domain.validate_uuid(raw, "parent_id"))
    if exclude_id is not None and parent_id == exclude_id:
        raise ValidationError(
            field="parent_id", message="Kategori tidak bisa menjadi induk dirinya sendiri."
        )
    parent = get_category(user, parent_id)
    if exclude_id is not None and parent.parent_id == exclude_id:
        raise ValidationError(
            field="parent_id", message="Struktur induk kategori tidak boleh melingkar."
        )
    return parent.id


def create_category(user: User, data: dict[str, Any]) -> Category:
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    parent_id = run(lambda: _resolve_parent(user, data, None))
    category = Category(
        user_id=user.id,
        parent_id=parent_id,
        name=run(lambda: domain.validate_name(data.get("name"))) or "",
        category_type=run(lambda: domain.validate_category_type(data.get("category_type"))),
        icon=run(lambda: domain.validate_icon(data.get("icon"))),
        color=run(lambda: domain.validate_color(data.get("color"))),
        sort_order=run(lambda: domain.validate_sort_order(data.get("sort_order"))) or 0,
        is_active=run(lambda: domain.validate_is_active(data.get("is_active")))
        if data.get("is_active") is not None
        else True,
    )

    if errors:
        raise ValidationErrors(errors)

    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError("Kategori dengan nama ini sudah ada.") from None
    return category


def update_category(user: User, category_id: str, data: dict[str, Any]) -> Category:
    category = get_category(user, category_id)
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    if "parent_id" in data:
        resolved = run(lambda: _resolve_parent(user, data, category_id))
        if "parent_id" in data and data.get("parent_id") is None:
            category.parent_id = None
        elif resolved is not None:
            category.parent_id = resolved
    if "name" in data:
        name = run(lambda: domain.validate_name(data.get("name")))
        if name is not None:
            category.name = name
    if "category_type" in data:
        category.category_type = run(
            lambda: domain.validate_category_type(data.get("category_type"))
        )
    if "icon" in data:
        category.icon = run(lambda: domain.validate_icon(data.get("icon")))
    if "color" in data:
        category.color = run(lambda: domain.validate_color(data.get("color")))
    if "sort_order" in data:
        sort_order = run(lambda: domain.validate_sort_order(data.get("sort_order")))
        if sort_order is not None:
            category.sort_order = sort_order
    if "is_active" in data:
        is_active = run(lambda: domain.validate_is_active(data.get("is_active")))
        if is_active is not None:
            category.is_active = is_active

    if errors:
        raise ValidationErrors(errors)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError("Kategori dengan nama ini sudah ada.") from None
    return category


def delete_category(user: User, category_id: str) -> None:
    category = get_category(user, category_id)
    db.session.delete(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError("Kategori masih dipakai oleh catatan makanan.") from None


def payload(category: Category) -> dict[str, Any]:
    return {
        "id": str(category.id),
        "parent_id": str(category.parent_id) if category.parent_id else None,
        "name": category.name,
        "category_type": category.category_type,
        "icon": category.icon,
        "color": category.color,
        "sort_order": category.sort_order,
        "is_active": category.is_active,
    }


__all__ = [
    "ConflictError",
    "NotFoundError",
    "create_category",
    "delete_category",
    "get_category",
    "list_categories",
    "payload",
    "update_category",
]
