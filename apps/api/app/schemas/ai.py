from typing import Literal

from pydantic import BaseModel, Field

MandatoryStatusLiteral = Literal["mandatory", "conditional", "indicative", "unclear"]
AssessmentStatusLiteral = Literal[
    "compliant_looking",
    "partially_addressed",
    "evidence_not_found",
    "potential_non_compliance",
    "not_applicable_pending_verification",
]
EvidenceQualityLiteral = Literal["strong", "adequate", "insufficient", "none", "unknown"]
ConfidenceLiteral = Literal["high", "medium", "low"]


class ExtractedRequirement(BaseModel):
    """One requirement extracted from tender text. `source_excerpt` must be
    an exact substring of the source page text supplied to the model —
    validated deterministically after the call, not trusted blindly."""

    source_page: int
    source_clause: str | None = None
    source_excerpt: str = Field(min_length=1)
    title: str
    normalized_requirement: str
    category: str
    mandatory_status: MandatoryStatusLiteral
    conditions: str | None = None
    required_evidence: str | None = None
    extraction_uncertain: bool = False


class RequirementExtractionOutput(BaseModel):
    requirements: list[ExtractedRequirement]


class EvidenceCandidate(BaseModel):
    document_id: str
    page_number: int
    excerpt: str = Field(min_length=1)
    retrieval_method: str
    evidence_type: str | None = None
    relevance_note: str | None = None
    potential_conflict: str | None = None


class ComplianceAssessmentOutput(BaseModel):
    status: AssessmentStatusLiteral
    evidence_quality: EvidenceQualityLiteral
    assessment_confidence: ConfidenceLiteral
    reason: str
    missing_information: list[str] = Field(default_factory=list)
    requires_human_review: bool
    evidence: list[EvidenceCandidate] = Field(default_factory=list)
