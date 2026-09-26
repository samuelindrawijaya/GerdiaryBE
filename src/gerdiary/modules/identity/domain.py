from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

EMAIL_MAX_LENGTH = 255
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class ValidationError(Exception):
    field: str
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class EmailAlreadyRegistered(Exception):
    email: str

    def __str__(self) -> str:
        return "Email sudah terdaftar."


@dataclass(frozen=True)
class ValidationErrors(Exception):
    errors: list[ValidationError]

    def fields(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for error in self.errors:
            grouped.setdefault(error.field, []).append(error.message)
        return grouped


def canonical_email(raw: str) -> str:
    return " ".join(raw.strip().lower().split())


def validate_email(raw: str) -> str:
    normalized = canonical_email(raw)
    if not normalized or len(normalized) > EMAIL_MAX_LENGTH or not _EMAIL_PATTERN.match(normalized):
        raise ValidationError(
            field="email",
            message="Email tidak valid.",
        )
    return normalized


def validate_password(raw: str) -> str:
    if not PASSWORD_MIN_LENGTH <= len(raw) <= PASSWORD_MAX_LENGTH:
        raise ValidationError(
            field="password",
            message=f"Password minimal {PASSWORD_MIN_LENGTH} karakter.",
        )
    return raw


def access_token_expiry(issued_at: datetime) -> datetime:
    return issued_at + ACCESS_TOKEN_LIFETIME
