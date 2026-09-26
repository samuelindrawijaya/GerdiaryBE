from __future__ import annotations

from gerdiary.modules.safety import red_flags


def test_chest_pain_is_always_a_red_flag() -> None:
    assert red_flags.code_for("chest_pain", "mild") == "RF_CHEST_PAIN"
    assert red_flags.code_for("chest_pain", "severe") == "RF_CHEST_PAIN"


def test_vomit_blood_is_always_a_red_flag() -> None:
    assert red_flags.code_for("vomit_blood", "moderate") == "RF_VOMIT_BLOOD"


def test_black_stool_is_always_a_red_flag() -> None:
    assert red_flags.code_for("black_stool", "mild") == "RF_BLACK_STOOL"


def test_difficulty_swallowing_only_severe_is_a_red_flag() -> None:
    assert red_flags.code_for("difficulty_swallowing", "severe") == "RF_DYSPHAGIA_SEVERE"
    assert red_flags.code_for("difficulty_swallowing", "moderate") is None
    assert red_flags.code_for("difficulty_swallowing", "mild") is None


def test_ordinary_symptoms_are_not_red_flags() -> None:
    assert red_flags.code_for("heartburn", "severe") is None
    assert red_flags.code_for("bloating", "mild") is None
    assert red_flags.code_for("other", "severe") is None


def test_every_red_flag_has_reviewed_versioned_copy() -> None:
    for code in red_flags.ALL_CODES:
        payload = red_flags.payload(code)

        assert payload["code"] == code
        assert payload["version"] == red_flags.RED_FLAG_VERSION
        assert payload["title"]
        assert payload["message"]
