import pytest

from app.services.clauserisk.risk_engine import compute_risk_score


def _score(**overrides):
    defaults = dict(
        severity_hint="medium",
        subcategory=None,
        has_cap_or_limit=False,
        exposure_stated=False,
        evidence_verified=True,
        ai_confidence="high",
        uncertainty="explicit",
    )
    defaults.update(overrides)
    return compute_risk_score(**defaults)


def test_base_severity_maps_to_expected_band():
    result = _score(severity_hint="critical")
    assert result.final_severity in ("critical", "high")  # bonuses/penalties may shift the band
    assert result.factors["severity_hint"] == "critical"
    assert result.factors["base_score"] == 90


def test_uncapped_exposure_increases_score_over_capped():
    capped = _score(exposure_stated=True, has_cap_or_limit=True)
    uncapped = _score(exposure_stated=True, has_cap_or_limit=False)
    assert uncapped.final_score > capped.final_score
    assert uncapped.factors["uncapped_exposure_penalty"] == 15
    assert capped.factors["capped_exposure_reduction"] == -5


def test_unverified_evidence_reduces_score():
    verified = _score(evidence_verified=True)
    unverified = _score(evidence_verified=False)
    assert unverified.final_score < verified.final_score
    assert unverified.factors["unverified_evidence_penalty"] == -20
    assert unverified.factors["evidence_verified"] is False


def test_high_stakes_subcategory_gets_bonus():
    plain = _score(subcategory="payment")
    high_stakes = _score(subcategory="unlimited_liability")
    assert high_stakes.final_score > plain.final_score
    assert high_stakes.factors["high_stakes_category_bonus"] == 10


def test_low_control_subcategory_gets_bonus():
    baseline = _score(subcategory=None)
    low_control = _score(subcategory="weather")
    assert low_control.final_score > baseline.final_score
    assert low_control.factors["low_contractor_control_bonus"] == 5


def test_low_confidence_reduces_score():
    high_conf = _score(ai_confidence="high")
    low_conf = _score(ai_confidence="low")
    assert low_conf.final_score < high_conf.final_score


@pytest.mark.parametrize("uncertainty", ["ambiguous", "conflicting"])
def test_ambiguous_or_conflicting_uncertainty_reduces_score(uncertainty):
    explicit = _score(uncertainty="explicit")
    uncertain = _score(uncertainty=uncertainty)
    assert uncertain.final_score < explicit.final_score


def test_score_is_clamped_between_0_and_100():
    very_low = _score(
        severity_hint="informational",
        ai_confidence="low",
        uncertainty="ambiguous",
        evidence_verified=False,
    )
    assert 0 <= very_low.final_score <= 100

    very_high = _score(
        severity_hint="critical",
        subcategory="unlimited_liability",
        exposure_stated=True,
        has_cap_or_limit=False,
    )
    assert 0 <= very_high.final_score <= 100


def test_factors_are_fully_explainable():
    result = _score(severity_hint="high", subcategory="liability_cap", evidence_verified=False)
    assert result.factors["final_score"] == result.final_score
    assert result.factors["final_severity"] == result.final_severity
    assert "severity_hint" in result.factors
    assert "evidence_verified" in result.factors
