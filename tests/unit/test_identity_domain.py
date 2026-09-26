from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gerdiary.modules.identity import domain


def test_email_is_trimmed_and_lowercased() -> None:
    assert domain.canonical_email("  Ayu@Example.COM ") == "ayu@example.com"


def test_email_whitespace_is_collapsed() -> None:
    assert domain.canonical_email("ayu\t lastname@example.com") == "ayu lastname@example.com"


@pytest.mark.parametrize(
    "value",
    ["", "   ", "not-an-email", "a@b", "missing-at.example.com", "@example.com", "ayu@"],
)
def test_invalid_email_is_rejected(value: str) -> None:
    with pytest.raises(domain.ValidationError) as error:
        domain.validate_email(value)

    assert error.value.field == "email"


def test_password_minimum_twelve_characters_accepted() -> None:
    domain.validate_password("twelve-chars!")


def test_password_rules_do_not_require_composition() -> None:
    domain.validate_password("abcdefghijkl")


@pytest.mark.parametrize("value", ["", "short", "exactly-11!", "a" * 200])
def test_password_outside_policy_is_rejected(value: str) -> None:
    with pytest.raises(domain.ValidationError) as error:
        domain.validate_password(value)

    assert error.value.field == "password"


def test_access_token_expiry_is_thirty_minutes() -> None:
    issued_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

    expires_at = domain.access_token_expiry(issued_at)

    assert expires_at == issued_at + timedelta(minutes=30)
