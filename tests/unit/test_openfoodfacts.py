from __future__ import annotations

import pytest

from gerdiary.infrastructure.providers.openfoodfacts import normalize_product


def _product(**overrides: object) -> dict:
    product: dict = {
        "code": "8991002101234",
        "product_name": " Indomie Goreng ",
        "brands": "Indofood, Nestle",
        "nutriments": {
            "energy-kcal_100g": 453,
            "fat_100g": 19.0,
            "carbohydrates_100g": 59.0,
            "sugars_100g": 4,
            "proteins_100g": 8.0,
            "salt_100g": 3.6,
        },
    }
    product.update(overrides)
    return product


def test_normalize_full_product() -> None:
    result = normalize_product(_product())

    assert result is not None
    assert result["provider"] == "openfoodfacts"
    assert result["barcode"] == "8991002101234"
    assert result["name"] == "Indomie Goreng"
    assert result["brand"] == "Indofood"
    assert result["nutrition"] == {
        "energy_kcal_100g": 453.0,
        "fat_100g": 19.0,
        "carbohydrates_100g": 59.0,
        "sugars_100g": 4.0,
        "protein_100g": 8.0,
        "salt_100g": 3.6,
    }


def test_normalize_falls_back_to_generic_name() -> None:
    result = normalize_product(_product(product_name="", generic_name="Instant noodles"))

    assert result is not None
    assert result["name"] == "Instant noodles"


def test_normalize_skips_product_without_name() -> None:
    assert normalize_product(_product(product_name="", generic_name=None)) is None


def test_normalize_missing_nutriments_become_none() -> None:
    result = normalize_product(_product(nutriments={}))

    assert result is not None
    assert result["nutrition"]["energy_kcal_100g"] is None
    assert result["nutrition"]["protein_100g"] is None


def test_normalize_negative_values_become_none() -> None:
    result = normalize_product(
        _product(nutriments={"energy-kcal_100g": -10, "fat_100g": 5})
    )

    assert result is not None
    assert result["nutrition"]["energy_kcal_100g"] is None
    assert result["nutrition"]["fat_100g"] == 5.0


def test_normalize_single_brand_without_comma() -> None:
    result = normalize_product(_product(brands="Indofood"))

    assert result is not None
    assert result["brand"] == "Indofood"


def test_normalize_blank_brands_become_none() -> None:
    result = normalize_product(_product(brands=" , "))

    assert result is not None
    assert result["brand"] is None


@pytest.mark.parametrize(
    ("source_field", "result_field"),
    [
        ("energy-kcal_100g", "energy_kcal_100g"),
        ("fat_100g", "fat_100g"),
        ("carbohydrates_100g", "carbohydrates_100g"),
        ("sugars_100g", "sugars_100g"),
        ("proteins_100g", "protein_100g"),
        ("salt_100g", "salt_100g"),
    ],
)
def test_normalize_non_numeric_nutriment_is_none(source_field: str, result_field: str) -> None:
    result = normalize_product(_product(nutriments={source_field: "much"}))

    assert result is not None
    assert result["nutrition"][result_field] is None
