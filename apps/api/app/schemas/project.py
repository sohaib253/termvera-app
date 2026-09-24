from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import AnalysisStatus, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_name: str | None = None
    tender_reference: str | None = None
    sector: str | None = None
    submission_deadline: date | None = None
    currency: str | None = None
    confidentiality: str | None = None
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = None
    tender_reference: str | None = None
    sector: str | None = None
    status: ProjectStatus | None = None
    submission_deadline: date | None = None
    currency: str | None = None
    confidentiality: str | None = None
    notes: str | None = None
    owner_user_id: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    client_name: str | None
    tender_reference: str | None
    sector: str | None
    status: ProjectStatus
    submission_deadline: date | None
    currency: str | None
    confidentiality: str | None
    notes: str | None
    owner_user_id: str | None
    created_by_user_id: str
    is_demo: bool
    analysis_status: AnalysisStatus
    analysis_error: str | None
    created_at: datetime
    updated_at: datetime
