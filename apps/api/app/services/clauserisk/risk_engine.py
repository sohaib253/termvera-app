"""Deterministic, explainable risk scoring — pipeline stage 11 (part of
"deterministic validation").

The brief is explicit: "Do not allow the AI alone to determine final
risk." The AI's `severity_hint` (see app/schemas/clauserisk_ai.py) is
only ever a starting point; this module adjusts it based on factors the
AI does not control, and always returns the full set of factors it used
so the result is explainable to a reviewer — never just a number.

This is a plain scoring function, not a database-backed configurable
rule builder — a deliberate MVP scope decision (see
docs/architecture.md), consistent with app/services/priority.py's
lookup table for TenderGuard. The weights below are the tunable surface;
change them here, not scattered through the pipeline.
"""

from dataclasses import dataclass, field

_SEVERITY_BASE_SCORE = {
    "critical": 90,
    "high": 70,
    "medium": 45,
    "low": 20,
    "informational": 5,
}

_SEVERITY_BANDS: list[tuple[int, str]] = [
    (90, "critical"),
    (70, "high"),
    (45, "medium"),
    (20, "low"),
    (0, "informational"),
]

# Subcategories that are inherently higher-stakes regardless of how the
# AI framed them — brief's "liability scope" / "duration" factors.
_HIGH_STAKES_SUBCATEGORIES = {
    "unlimited_liability",
    "liquidated_damages",
    "termination_for_cause",
    "consequential_loss",
}

# Subcategories where the contractor typically has little control over
# the triggering event — brief's "contractor control" / "client
# dependency" factors.
_LOW_CONTROL_SUBCATEGORIES = {
    "client_dependencies",
    "weather",
    "site_conditions",
    "force_majeure",
}


@dataclass
class RiskScoreResult:
    final_severity: str
    final_score: int
    factors: dict = field(default_factory=dict)


def compute_risk_score(
    *,
    severity_hint: str,
    subcategory: str | None,
    has_cap_or_limit: bool,
    exposure_stated: bool,
    evidence_verified: bool,
    ai_confidence: str,
    uncertainty: str,
) -> RiskScoreResult:
    factors: dict = {}

    base = _SEVERITY_BASE_SCORE.get(severity_hint, _SEVERITY_BASE_SCORE["medium"])
    factors["severity_hint"] = severity_hint
    factors["base_score"] = base
    score = base

    if subcategory in _HIGH_STAKES_SUBCATEGORIES:
        score += 10
        factors["high_stakes_category_bonus"] = 10

    if exposure_stated and not has_cap_or_limit:
        score += 15
        factors["uncapped_exposure_penalty"] = 15
    elif has_cap_or_limit:
        score -= 5
        factors["capped_exposure_reduction"] = -5

    if subcategory in _LOW_CONTROL_SUBCATEGORIES:
        score += 5
        factors["low_contractor_control_bonus"] = 5

    confidence_adjustment = {"high": 0, "medium": -5, "low": -10}.get(ai_confidence, -5)
    if confidence_adjustment:
        score += confidence_adjustment
        factors["ai_confidence_adjustment"] = confidence_adjustment
    factors["ai_confidence"] = ai_confidence

    if uncertainty in ("ambiguous", "conflicting"):
        score -= 10
        factors["uncertainty_penalty"] = -10
    factors["uncertainty"] = uncertainty

    if not evidence_verified:
        score -= 20
        factors["unverified_evidence_penalty"] = -20
    factors["evidence_verified"] = evidence_verified

    score = max(0, min(100, score))
    factors["final_score"] = score

    final_severity = next(label for threshold, label in _SEVERITY_BANDS if score >= threshold)
    factors["final_severity"] = final_severity

    return RiskScoreResult(final_severity=final_severity, final_score=score, factors=factors)
