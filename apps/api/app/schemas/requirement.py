import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.assessment import AssessmentConfidence, AssessmentStatus, EvidenceQuality, Priority
from app.models.requirement import MandatoryStatus


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    page_number: int
    excerpt: str
    retrieval_method: str
    evidence_type: str | None
    relevance_note: str | None
    potential_conflict: str | None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AssessmentStatus
    evidence_quality: EvidenceQuality
    assessment_confidence: AssessmentConfidence
    priority: Priority
    reason: str
    missing_information: list[str]
    requires_human_review: bool
    ai_provider: str | None
    prompt_version: str | None
    reviewer_status: str
    reviewer_user_id: str | None
    updated_at: datetime

    @field_validator("missing_information", mode="before")
    @classmethod
    def parse_missing_information(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return list(json.loads(value)) if value else []
        if isinstance(value, list):
            return value
        return []


class ReviewActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    action_type: str
    previous_status: str | None
    new_status: str | None
    comment: str | None
    created_at: datetime


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_document_id: str
    source_page: int
    source_clause: str | None
    source_excerpt: str
    title: str
    normalized_requirement: str
    category: str
    mandatory_status: MandatoryStatus
    conditions: str | None
    required_evidence: str | None
    extraction_uncertain: bool
    assessment: AssessmentRead | None


class RequirementDetailRead(RequirementRead):
    evidence_records: list[EvidenceRead]
    review_actions: list[ReviewActionRead]


class ReviewActionCreate(BaseModel):
    new_status: AssessmentStatus | None = None
    comment: str | None = Field(default=None, max_length=4000)
