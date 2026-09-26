from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gerdiary.extensions import db
from gerdiary.modules.identity.domain import ValidationError, ValidationErrors
from gerdiary.modules.identity.models import User
from gerdiary.modules.journal import domain as journal_domain
from gerdiary.modules.journal import service as journal_service
from gerdiary.modules.journal.models import FoodEntry
from gerdiary.modules.spending import domain
from gerdiary.modules.spending.models import Account, Vendor


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _session() -> Session:
    return cast("Session", db.session)


# ---------------------------------------------------------------------------
# Accounts (payment sources)
# ---------------------------------------------------------------------------


def list_accounts(user: User) -> list[Account]:
    rows = (
        _session()
        .scalars(
            select(Account)
            .where(Account.user_id == user.id, Account.deleted_at.is_(None))
            .order_by(Account.created_at.asc())
        )
        .all()
    )
    return list(rows)


def get_account(user: User, account_id: str) -> Account:
    try:
        validated = journal_domain.validate_uuid(account_id, "account_id")
    except ValidationError:
        raise NotFoundError() from None
    account = _session().scalar(
        select(Account).where(
            Account.id == validated,
            Account.user_id == user.id,
            Account.deleted_at.is_(None),
        )
    )
    if account is None:
        raise NotFoundError()
    return account


def create_account(user: User, data: dict[str, Any]) -> Account:
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    name = run(lambda: domain.validate_account_name(data.get("name")))
    emoji = run(lambda: domain.validate_emoji(data.get("emoji")))
    is_active = run(lambda: domain.validate_account_is_active(data.get("is_active")))

    if errors:
        raise ValidationErrors(errors)

    account = Account(
        user_id=user.id,
        name=name or "",
        emoji=emoji,
        is_active=is_active if is_active is not None else True,
    )
    _session().add(account)
    try:
        _session().commit()
    except IntegrityError:
        _session().rollback()
        raise ConflictError("Sumber pembayaran gagal disimpan.") from None
    return account


def update_account(user: User, account_id: str, data: dict[str, Any]) -> Account:
    account = get_account(user, account_id)
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    if "name" in data:
        name = run(lambda: domain.validate_account_name(data.get("name")))
        if name is not None:
            account.name = name
    if "emoji" in data:
        account.emoji = run(lambda: domain.validate_emoji(data.get("emoji")))
    if "is_active" in data:
        is_active = run(lambda: domain.validate_account_is_active(data.get("is_active")))
        if is_active is not None:
            account.is_active = is_active

    if errors:
        raise ValidationErrors(errors)

    _session().commit()
    return account


def delete_account(user: User, account_id: str) -> None:
    account = get_account(user, account_id)
    used = _session().scalar(
        select(FoodEntry.id).where(
            FoodEntry.account_id == account.id, FoodEntry.deleted_at.is_(None)
        )
    )
    if used is not None:
        raise ConflictError("Sumber pembayaran masih dipakai oleh catatan makanan.")
    account.deleted_at = journal_service._now()  # noqa: SLF001 - reuse helper
    _session().commit()


def account_payload(account: Account) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "name": account.name,
        "emoji": account.emoji,
        "is_active": account.is_active,
    }


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------


def list_vendors(user: User) -> list[Vendor]:
    rows = (
        _session()
        .scalars(
            select(Vendor)
            .where(Vendor.user_id == user.id, Vendor.deleted_at.is_(None))
            .order_by(Vendor.created_at.asc())
        )
        .all()
    )
    return list(rows)


def get_vendor(user: User, vendor_id: str) -> Vendor:
    try:
        validated = journal_domain.validate_uuid(vendor_id, "vendor_id")
    except ValidationError:
        raise NotFoundError() from None
    vendor = _session().scalar(
        select(Vendor).where(
            Vendor.id == validated,
            Vendor.user_id == user.id,
            Vendor.deleted_at.is_(None),
        )
    )
    if vendor is None:
        raise NotFoundError()
    return vendor


def create_vendor(user: User, data: dict[str, Any]) -> Vendor:
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    name = run(lambda: domain.validate_vendor_name(data.get("name")))
    category = run(lambda: domain.validate_vendor_category(data.get("category")))
    is_active = run(lambda: domain.validate_account_is_active(data.get("is_active")))

    if errors:
        raise ValidationErrors(errors)

    vendor = Vendor(
        user_id=user.id,
        name=name or "",
        category=category,
        is_active=is_active if is_active is not None else True,
    )
    _session().add(vendor)
    try:
        _session().commit()
    except IntegrityError:
        _session().rollback()
        raise ConflictError("Vendor gagal disimpan.") from None
    return vendor


def update_vendor(user: User, vendor_id: str, data: dict[str, Any]) -> Vendor:
    vendor = get_vendor(user, vendor_id)
    errors: list[ValidationError] = []

    def run(validator: Any) -> Any:
        try:
            return validator()
        except ValidationError as error:
            errors.append(error)
            return None

    if "name" in data:
        name = run(lambda: domain.validate_vendor_name(data.get("name")))
        if name is not None:
            vendor.name = name
    if "category" in data:
        vendor.category = run(lambda: domain.validate_vendor_category(data.get("category")))
    if "is_active" in data:
        is_active = run(lambda: domain.validate_account_is_active(data.get("is_active")))
        if is_active is not None:
            vendor.is_active = is_active

    if errors:
        raise ValidationErrors(errors)

    _session().commit()
    return vendor


def delete_vendor(user: User, vendor_id: str) -> None:
    vendor = get_vendor(user, vendor_id)
    used = _session().scalar(
        select(FoodEntry.id).where(
            FoodEntry.vendor_id == vendor.id, FoodEntry.deleted_at.is_(None)
        )
    )
    if used is not None:
        raise ConflictError("Vendor masih dipakai oleh catatan makanan.")
    vendor.deleted_at = journal_service._now()  # noqa: SLF001 - reuse helper
    _session().commit()


def vendor_payload(vendor: Vendor) -> dict[str, Any]:
    return {
        "id": str(vendor.id),
        "name": vendor.name,
        "category": vendor.category,
        "is_active": vendor.is_active,
    }


__all__ = [
    "ConflictError",
    "NotFoundError",
    "account_payload",
    "create_account",
    "create_vendor",
    "delete_account",
    "delete_vendor",
    "get_account",
    "get_vendor",
    "list_accounts",
    "list_vendors",
    "update_account",
    "update_vendor",
    "vendor_payload",
]
