import pytest

from app.services.clauserisk.risk_types import RISK_TYPES, normalize_risk_type, risk_type_label


@pytest.mark.parametrize(
    "raw",
    [
        # The exact junk a local 7B model produced by copying neighbouring
        # field names and enum values into the free-text risk_type slot.
        "explicit",
        "uncertainty",
        "potential exposure",
        "liability",
        "compliance",
        "",
        None,
    ],
)
def test_leaked_field_names_fall_back_to_the_clause_subcategory(raw):
    assert normalize_risk_type(raw, subcategory="liability_cap") == "liability_cap_low"


def test_exact_taxonomy_key_is_kept():
    assert normalize_risk_type("uncapped_liability", subcategory="payment") == "uncapped_liability"


def test_display_label_is_accepted():
    assert normalize_risk_type("Uncapped liability", subcategory=None) == "uncapped_liability"


def test_loose_formatting_is_accepted():
    assert normalize_risk_type("broad-indemnity", subcategory=None) == "broad_indemnity"


def test_unknown_value_without_a_subcategory_falls_back_to_other():
    assert normalize_risk_type("something invented", subcategory=None) == "other"


def test_every_subcategory_fallback_points_at_a_real_risk_type():
    from app.services.clauserisk.risk_categories import ALL_SUBCATEGORIES

    for subcategory in ALL_SUBCATEGORIES:
        assert normalize_risk_type(None, subcategory=subcategory) in RISK_TYPES


def test_labels_are_human_readable():
    assert risk_type_label("liquidated_damages_exposure") == "Liquidated damages exposure"
    assert risk_type_label("not_a_real_key") == RISK_TYPES["other"]
