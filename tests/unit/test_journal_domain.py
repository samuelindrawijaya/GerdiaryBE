from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from gerdiary.modules.identity.domain import ValidationError
from gerdiary.modules.journal import domain

JAKARTA = ZoneInfo("Asia/Jakarta")


def test_meal_type_must_be_known() -> None:
    assert domain.validate_meal_type("lunch") == "lunch"

    with pytest.raises(ValidationError) as error:
        domain.validate_meal_type("brunch")

    assert error.value.field == "meal_type"


def test_food_attributes_deduplicate_and_reject_unknown() -> None:
    assert domain.validate_food_attributes(["spicy", "spicy", "oily"]) == ["spicy", "oily"]

    with pytest.raises(ValidationError) as error:
        domain.validate_food_attributes(["spicy", "unknown-attr"])

    assert error.value.field == "food_attributes"


def test_food_attributes_accept_empty_list() -> None:
    assert domain.validate_food_attributes([]) == []


def test_symptom_must_be_known() -> None:
    assert domain.validate_symptom("chest_pain") == "chest_pain"

    with pytest.raises(ValidationError) as error:
        domain.validate_symptom("dizzy")

    assert error.value.field == "symptom"


def test_severity_must_be_known() -> None:
    assert domain.validate_severity("severe") == "severe"

    with pytest.raises(ValidationError):
        domain.validate_severity("extreme")


def test_food_name_required_and_bounded() -> None:
    assert domain.validate_food_name("Nasi goreng") == "Nasi goreng"

    with pytest.raises(ValidationError):
        domain.validate_food_name("   ")

    with pytest.raises(ValidationError):
        domain.validate_food_name("x" * 256)


@pytest.mark.parametrize(
    ("consumed_at", "sleep_time", "expected"),
    [
        (datetime(2026, 9, 4, 20, 30, tzinfo=JAKARTA), "23:00", True),
        (datetime(2026, 9, 4, 19, 30, tzinfo=JAKARTA), "23:00", False),
        (datetime(2026, 9, 4, 23, 30, tzinfo=JAKARTA), "23:00", False),
        (datetime(2026, 9, 4, 23, 30, tzinfo=JAKARTA), "01:00", True),
        (datetime(2026, 9, 4, 22, 0, tzinfo=JAKARTA), "01:00", True),
        (datetime(2026, 9, 4, 12, 0, tzinfo=JAKARTA), "23:00", False),
        (datetime(2026, 9, 4, 12, 0, tzinfo=JAKARTA), None, False),
        (datetime(2026, 9, 4, 12, 0, tzinfo=JAKARTA), "25:99", False),
    ],
)
def test_is_late_night(
    consumed_at: datetime, sleep_time: str | None, expected: bool
) -> None:
    assert domain.is_late_night(consumed_at, sleep_time, "Asia/Jakarta") is expected


def test_future_timestamp_within_grace_is_allowed() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=JAKARTA)

    assert domain.is_future(datetime(2026, 9, 4, 12, 3, tzinfo=JAKARTA), now) is False


def test_future_timestamp_beyond_grace_is_rejected() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=JAKARTA)

    assert domain.is_future(datetime(2026, 9, 4, 12, 10, tzinfo=JAKARTA), now) is True
