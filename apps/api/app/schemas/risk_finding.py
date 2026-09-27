import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.risk_finding import AffectedParty, FindingReviewerStatus, RiskSeverity, RiskUncertainty
from app.services.clauserisk.risk_types import risk_type_label


def _parse_json_list(value: object) -> list:
    if isinstance(value, str):
        return list(json.loads(value)) if value else []
    if isinstance(value, list):
        return value
    return []


class EvidenceItem(BaseModel):
    document_id: str | None = None
    clause_id: str | None = None
    # PDF page (what a viewer's page box shows), and the page number printed
    # on that page when the document has one ("7 of 12"); they differ when
    # a cover letter comes first. See clauserisk/evidence_location.py.
    page: int | None = None
    page_label: str | None = None
    clause_number: str | None = None
    clause_title: str | None = None
    section_title: str | None = None
    excerpt: str
    verified: bool


class RiskFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_version_id: str
    clause_id: str | None
    category: str
    risk_type: str
    severity: RiskSeverity
    risk_description: str
    contractual_effect: str | None
    potential_exposure: str | None
    trigger: str | None
    affected_party: AffectedParty
    uncertainty: RiskUncertainty
    recommended_review_action: str | None
    computed_score: float
    reviewer_status: FindingReviewerStatus
    assigned_to_user_id: str | None
    ai_provider: str | None
    prompt_version: str | None
    updated_at: datetime

    evidence: list[EvidenceItem]
    related_clauses: list[str]
    risk_factors: dict

    @field_validator("evidence", mode="before")
    @classmethod
    def _validate_evidence(cls, value: object) -> list:
        return _parse_json_list(value)

    @field_validator("related_clauses", mode="before")
    @classmethod
    def _validate_related(cls, value: object) -> list:
        return _parse_json_list(value)

    @field_validator("risk_factors", mode="before")
    @classmethod
    def _validate_factors(cls, value: object) -> dict:
        if isinstance(value, str):
            return dict(json.loads(value)) if value else {}
        if isinstance(value, dict):
            return value
        return {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def risk_type_label(self) -> str:
        """Human-readable name for risk_type, resolved server-side so the
        taxonomy lives in exactly one place (services/clauserisk/risk_types.py)
        rather than being mirrored in the web app."""
        return risk_type_label(self.risk_type)


class RiskFindingDetailRead(RiskFindingRead):
    review_actions: list["FindingReviewActionRead"]


class RiskFindingListItem(RiskFindingRead):
    """RiskFindingRead plus the parent contract's id/name and (when the
    finding is attached to one) the clause number — for the org-wide Risk
    Register, which spans contracts rather than being scoped to one
    contract version like RiskFindingRead's usual list endpoint."""

    contract_id: str
    contract_name: str
    clause_number: str | None


class FindingReviewActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    action_type: str
    previous_status: str | None
    new_status: str | None
    comment: str | None
    created_at: datetime


class FindingReviewActionCreate(BaseModel):
    new_status: FindingReviewerStatus | None = None
    assign_to_user_id: str | None = None
    comment: str | None = Field(default=None, max_length=4000)


RiskFindingDetailRead.model_rebuild()
