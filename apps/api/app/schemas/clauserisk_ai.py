from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLiteral = Literal["high", "medium", "low"]
AffectedPartyLiteral = Literal["contractor", "client", "both", "third_party", "unclear"]
UncertaintyLiteral = Literal[
    "explicit", "not_applicable", "not_found", "ambiguous", "conflicting", "requires_review"
]
SeverityHintLiteral = Literal["critical", "high", "medium", "low", "informational"]


class ClauseExtractionOutput(BaseModel):
    """Stage 6-8 combined: classification + obligation/rights/parameter
    extraction for one clause. Kept as a single, fairly flat schema —
    empirically, local models (see docs/ai-evaluation.md) produce
    meaningfully worse output on deeply nested schemas, and the fields
    below are naturally answered together from one read of the clause."""

    subcategory: str = Field(
        default="",
        description=(
            "Specific label from the configured subcategory list, or empty string if none fit. "
            "The parent category is derived deterministically from this — do not also ask for a "
            "separate top-level category, which empirically produces mismatched pairs (see "
            "docs/ai-evaluation.md)."
        ),
    )
    obligations: list[str] = Field(default_factory=list)
    rights: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    amounts: list[str] = Field(default_factory=list, description="Explicit monetary amounts only")
    dates: list[str] = Field(default_factory=list, description="Explicit calendar dates only")
    percentages: list[str] = Field(default_factory=list, description="Explicit percentage figures only")
    time_periods: list[str] = Field(
        default_factory=list, description="Explicit durations, e.g. '30 days', '12 months'"
    )
    referenced_clauses: list[str] = Field(
        default_factory=list, description="Other clause numbers explicitly referenced in the text"
    )
    confidence: ConfidenceLiteral = "medium"


class RiskFindingCandidate(BaseModel):
    """No `category` field: a clause-scoped finding inherits its category
    from the parent clause (already determined deterministically from
    `ClauseExtractionOutput.subcategory`) rather than asking the model to
    redundantly re-classify it — same rationale as dropping the top-level
    `category` from ClauseExtractionOutput above."""

    risk_type: str
    severity_hint: SeverityHintLiteral
    description: str
    contractual_effect: str = ""
    potential_exposure: str = ""
    trigger: str = ""
    affected_party: AffectedPartyLiteral
    uncertainty: UncertaintyLiteral
    recommended_review_action: str = ""
    evidence_excerpt: str = Field(min_length=1, description="A short verbatim quote from the source text")


class RiskAnalysisOutput(BaseModel):
    findings: list[RiskFindingCandidate] = Field(default_factory=list)


class MissingProtectionFinding(BaseModel):
    """Contract-wide findings not tied to one clause — e.g. "no force
    majeure clause found anywhere in this contract". Distinct from
    RiskFindingCandidate because it has no single evidence excerpt to
    verify against — by definition it's about absence, not a quote."""

    risk_type: str
    category: str
    severity_hint: SeverityHintLiteral
    description: str
    recommended_review_action: str = ""


class MissingProtectionsOutput(BaseModel):
    missing_protections: list[MissingProtectionFinding] = Field(default_factory=list)
